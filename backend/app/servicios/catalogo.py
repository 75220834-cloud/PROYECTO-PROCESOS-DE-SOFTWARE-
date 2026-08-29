"""Importación del catálogo de recursos turísticos desde el inventario del MINCETUR.

Fuente: Inventario Nacional de Recursos Turísticos, Dirección General de
Estrategia Turística del MINCETUR. Archivo CSV con delimitador ``;``.

Lo que hace este módulo, en orden:

1. Detecta la codificación del archivo probándola, sin adivinarla.
2. Filtra la región Junín y las cuatro provincias de la Ruta del Valle del
   Mantaro.
3. Normaliza los nombres de provincia y distrito.
4. Decide qué columna trae la latitud y cuál la longitud — el archivo oficial
   las trae intercambiadas, ver ``detectar_orden_de_coordenadas``.
5. Inserta o actualiza cada recurso, sin duplicar.

Regla que gobierna todo el módulo: **no se inventa ningún dato**. Un recurso
sin coordenadas se guarda sin coordenadas y la validación lo marcará; no se le
asigna la coordenada del centro del distrito ni ninguna aproximación.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.catalogo import RecursoTuristico

# --------------------------------------------------------------------------
# Constantes del dominio
# --------------------------------------------------------------------------

REGION_OBJETIVO = "JUNIN"

#: Las cuatro provincias que componen la Ruta del Valle del Mantaro.
PROVINCIAS_DE_LA_RUTA = frozenset({"HUANCAYO", "CONCEPCION", "JAUJA", "CHUPACA"})

#: Rangos del territorio continental del Perú. Son **disjuntos** entre sí
#: (la latitud nunca baja de -18.4 y la longitud nunca sube de -68.6), y esa
#: propiedad es la que permite decidir sin ambigüedad qué columna es cuál.
LATITUD_MINIMA_PERU, LATITUD_MAXIMA_PERU = -18.4, -0.03
LONGITUD_MINIMA_PERU, LONGITUD_MAXIMA_PERU = -81.4, -68.6

#: Codificaciones a probar, en orden. ``latin-1`` va al final porque nunca
#: falla —acepta cualquier byte— y por tanto enmascararía a las anteriores.
CODIFICACIONES_A_PROBAR = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

#: Nombres de las columnas del archivo oficial, ya normalizados a mayúsculas
#: sin tildes, porque la cabecera trae "REGIÓN" y "CATEGORÍA" con tilde.
COLUMNA_REGION = "REGION"
COLUMNA_PROVINCIA = "PROVINCIA"
COLUMNA_DISTRITO = "DISTRITO"
COLUMNA_CODIGO = "CODIGO DEL RECURSO"
COLUMNA_NOMBRE = "NOMBRE DEL RECURSO"
COLUMNA_CATEGORIA = "CATEGORIA"
COLUMNA_TIPO = "TIPO DE CATEGORIA"
COLUMNA_SUBTIPO = "SUB TIPO CATEGORIA"
COLUMNA_URL = "URL"
COLUMNA_LATITUD = "LATITUD"
COLUMNA_LONGITUD = "LONGITUD"
COLUMNA_FECHA_CORTE = "FECHA_DE_CORTE"

#: Marca combinante de la virgulilla (el trazo ondulado de la N). Se
#: declara aqui para no escribir un codigo de escape suelto dentro de la
#: funcion, donde se leeria peor.
VIRGULILLA = "\u0303"


@dataclass
class ResultadoImportacion:
    """Resumen de lo que ocurrió al importar el archivo.

    Se devuelve en lugar de imprimir por pantalla para que las pruebas puedan
    comprobarlo y para que el endpoint pueda mostrárselo al gestor.
    """

    codificacion_detectada: str = ""
    filas_en_el_archivo: int = 0
    filas_de_junin: int = 0
    filas_de_la_ruta: int = 0
    insertados: int = 0
    actualizados: int = 0
    sin_coordenadas: int = 0
    coordenadas_estaban_intercambiadas: bool = False
    advertencias: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------


def normalizar_texto(valor: object) -> str:
    """Pasa un texto a mayúsculas, sin tildes y sin espacios sobrantes.

    Sirve para comparar nombres de provincia y distrito: en el archivo oficial
    conviven "CONCEPCIÓN" y "CONCEPCION", y sin normalizar se contarían como
    dos provincias distintas.

    La normalización NFD separa cada letra acentuada en la letra base más el
    acento; luego se descartan los acentos (categoría Unicode "Mn", marca sin
    ancho).

    LA Ñ SE CONSERVA. Es una letra propia del alfabeto español, no una N con
    tilde. NFD también la descompone, así que se conserva a propósito la
    virgulilla cuando va sobre una N. Sin esta protección el distrito SAÑO,
    de la provincia de Huancayo, se guardaría como "SANO" y se mostraría mal
    escrito en toda la aplicación.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""

    # NFD descompone cada letra acentuada en su letra base mas una marca
    # combinante: "Ó" pasa a ser "O" + tilde, y "Ñ" pasa a ser "N" + virgulilla.
    descompuesto = unicodedata.normalize("NFD", str(valor).strip().upper())

    caracteres: list[str] = []
    for caracter in descompuesto:
        es_marca = unicodedata.category(caracter) == "Mn"

        if not es_marca:
            caracteres.append(caracter)
        elif caracter == VIRGULILLA and caracteres and caracteres[-1] == "N":
            # Se conserva solo la virgulilla que va sobre una N, para que la
            # Ñ sobreviva. Cualquier otra marca se descarta.
            caracteres.append(caracter)

    # NFC vuelve a unir "N" + virgulilla en el unico caracter "Ñ".
    return unicodedata.normalize("NFC", "".join(caracteres))


def limpiar(valor: object) -> str | None:
    """Devuelve el texto sin espacios sobrantes, o ``None`` si está vacío."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None

    texto = str(valor).strip()
    return texto or None


def convertir_a_numero(valor: object) -> float | None:
    """Convierte a número, aceptando la coma decimal, o devuelve ``None``.

    Algunos archivos oficiales usan coma como separador decimal. Se contempla
    para no descartar coordenadas válidas por un detalle de formato.
    """
    texto = limpiar(valor)
    if texto is None:
        return None

    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def convertir_fecha_de_corte(valor: object) -> date | None:
    """Interpreta la columna FECHA_DE_CORTE, que viene como ``AAAAMMDD``."""
    texto = limpiar(valor)
    if texto is None:
        return None

    for formato in ("%Y%m%d", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    return None


# --------------------------------------------------------------------------
# Lectura del archivo
# --------------------------------------------------------------------------


def detectar_codificacion(ruta: Path) -> str:
    """Averigua con qué codificación se puede leer el archivo.

    Se prueban las candidatas en orden y se devuelve la primera que no falle.
    No se adivina por el nombre ni se asume UTF-8: el inventario del MINCETUR
    viene en una codificación de Windows y leerlo como UTF-8 rompe todos los
    nombres con tilde.
    """
    crudo = ruta.read_bytes()

    for codificacion in CODIFICACIONES_A_PROBAR:
        try:
            crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
        return codificacion

    # No debería ocurrir: latin-1 acepta cualquier secuencia de bytes.
    raise ValueError(f"No se pudo determinar la codificación de {ruta}")


def normalizar_cabecera(columnas: list[str]) -> dict[str, str]:
    """Relaciona el nombre normalizado de cada columna con el nombre real.

    La cabecera trae "REGIÓN" y "CATEGORÍA" con tilde, y algún archivo podría
    traerlas sin ella. Normalizando se accede siempre igual.
    """
    return {normalizar_texto(columna): columna for columna in columnas}


def detectar_orden_de_coordenadas(marco: pd.DataFrame, cabecera: dict[str, str]) -> bool:
    """Decide si las columnas de latitud y longitud están intercambiadas.

    **Por qué existe esta función.** El archivo oficial del MINCETUR tiene los
    rótulos cambiados: la columna llamada LATITUD contiene la longitud y
    viceversa. Se comprobó sobre las 6 155 filas del archivo nacional: 4 910
    filas solo son coherentes si se invierten, y ninguna lo es tal como viene.

    No se codifica "siempre hay que invertir", porque si el MINCETUR corrige
    el archivo el importador seguiría rompiéndolo. En lugar de eso se decide
    por los datos: en el Perú continental la latitud vive entre -18.4 y -0.03
    y la longitud entre -81.4 y -68.6. Como los dos rangos no se solapan, cada
    fila indica sin ambigüedad qué columna es cuál, y se resuelve por mayoría.

    Devuelve ``True`` si hay que intercambiarlas.
    """
    columna_a = marco[cabecera[COLUMNA_LATITUD]].map(convertir_a_numero)
    columna_b = marco[cabecera[COLUMNA_LONGITUD]].map(convertir_a_numero)

    coherentes_tal_cual = 0
    coherentes_invertidas = 0

    for valor_a, valor_b in zip(columna_a, columna_b, strict=True):
        if valor_a is None or valor_b is None:
            continue

        tal_cual = (
            LATITUD_MINIMA_PERU <= valor_a <= LATITUD_MAXIMA_PERU
            and LONGITUD_MINIMA_PERU <= valor_b <= LONGITUD_MAXIMA_PERU
        )
        invertidas = (
            LATITUD_MINIMA_PERU <= valor_b <= LATITUD_MAXIMA_PERU
            and LONGITUD_MINIMA_PERU <= valor_a <= LONGITUD_MAXIMA_PERU
        )

        if tal_cual and not invertidas:
            coherentes_tal_cual += 1
        elif invertidas and not tal_cual:
            coherentes_invertidas += 1

    return coherentes_invertidas > coherentes_tal_cual


def leer_inventario(ruta: Path) -> tuple[pd.DataFrame, str]:
    """Lee el CSV del MINCETUR y devuelve la tabla junto con su codificación."""
    codificacion = detectar_codificacion(ruta)

    marco = pd.read_csv(
        ruta,
        sep=";",
        encoding=codificacion,
        dtype=str,  # todo como texto: la conversión se hace después, con control
        keep_default_na=False,
        na_values=[""],
    )

    return marco, codificacion


# --------------------------------------------------------------------------
# Importación
# --------------------------------------------------------------------------


def filtrar_la_ruta_del_mantaro(marco: pd.DataFrame, cabecera: dict[str, str]) -> pd.DataFrame:
    """Se queda solo con los recursos de las cuatro provincias de la ruta."""
    region = marco[cabecera[COLUMNA_REGION]].map(normalizar_texto)
    provincia = marco[cabecera[COLUMNA_PROVINCIA]].map(normalizar_texto)

    return marco[(region == REGION_OBJETIVO) & provincia.isin(PROVINCIAS_DE_LA_RUTA)]


def importar_inventario(
    sesion: Session,
    ruta_csv: Path,
) -> ResultadoImportacion:
    """Importa el inventario del MINCETUR a la tabla ``recurso_turistico``.

    Es idempotente: se puede ejecutar varias veces sin duplicar recursos,
    porque se identifica cada uno por su código oficial del MINCETUR. Si el
    recurso ya existe, se actualizan sus datos.
    """
    resultado = ResultadoImportacion()

    marco, codificacion = leer_inventario(ruta_csv)
    resultado.codificacion_detectada = codificacion
    resultado.filas_en_el_archivo = len(marco)

    cabecera = normalizar_cabecera(list(marco.columns))

    faltantes = [
        columna
        for columna in (COLUMNA_REGION, COLUMNA_PROVINCIA, COLUMNA_CODIGO, COLUMNA_NOMBRE)
        if columna not in cabecera
    ]
    if faltantes:
        raise ValueError(
            f"El archivo no tiene las columnas esperadas: {', '.join(faltantes)}. "
            f"Columnas encontradas: {', '.join(marco.columns)}"
        )

    region = marco[cabecera[COLUMNA_REGION]].map(normalizar_texto)
    resultado.filas_de_junin = int((region == REGION_OBJETIVO).sum())

    de_la_ruta = filtrar_la_ruta_del_mantaro(marco, cabecera)
    resultado.filas_de_la_ruta = len(de_la_ruta)

    if de_la_ruta.empty:
        resultado.advertencias.append(
            "El archivo no contiene ningún recurso de las provincias de la ruta."
        )
        return resultado

    # Se decide una sola vez para todo el archivo, no fila a fila.
    intercambiar = detectar_orden_de_coordenadas(marco, cabecera)
    resultado.coordenadas_estaban_intercambiadas = intercambiar

    if intercambiar:
        resultado.advertencias.append(
            "La fuente trae las columnas LATITUD y LONGITUD intercambiadas; "
            "se corrigió automáticamente al importar."
        )

    # Se cargan de golpe los recursos ya existentes: una sola consulta en vez
    # de una por fila.
    existentes = {
        recurso.codigo_mincetur: recurso
        for recurso in sesion.scalars(select(RecursoTuristico)).all()
    }

    for _, fila in de_la_ruta.iterrows():
        codigo = limpiar(fila[cabecera[COLUMNA_CODIGO]])
        nombre = limpiar(fila[cabecera[COLUMNA_NOMBRE]])

        if not codigo or not nombre:
            resultado.advertencias.append(
                f"Fila descartada por no tener código o nombre: {codigo or '(sin código)'}"
            )
            continue

        valor_columna_latitud = convertir_a_numero(fila.get(cabecera.get(COLUMNA_LATITUD, "")))
        valor_columna_longitud = convertir_a_numero(fila.get(cabecera.get(COLUMNA_LONGITUD, "")))

        if intercambiar:
            latitud, longitud = valor_columna_longitud, valor_columna_latitud
        else:
            latitud, longitud = valor_columna_latitud, valor_columna_longitud

        # WKT (Well-Known Text) es el formato estándar que entiende PostGIS.
        # Ojo al orden: POINT(longitud latitud), primero X y después Y. Es la
        # confusión más común al trabajar con datos geográficos.
        ubicacion = (
            f"SRID=4326;POINT({longitud} {latitud})"
            if latitud is not None and longitud is not None
            else None
        )

        if ubicacion is None:
            resultado.sin_coordenadas += 1

        datos = {
            "nombre": nombre,
            "provincia": normalizar_texto(fila[cabecera[COLUMNA_PROVINCIA]]),
            "distrito": normalizar_texto(fila[cabecera[COLUMNA_DISTRITO]]),
            "categoria": limpiar(fila.get(cabecera.get(COLUMNA_CATEGORIA, ""))),
            "tipo": limpiar(fila.get(cabecera.get(COLUMNA_TIPO, ""))),
            "subtipo": limpiar(fila.get(cabecera.get(COLUMNA_SUBTIPO, ""))),
            "url_ficha": limpiar(fila.get(cabecera.get(COLUMNA_URL, ""))),
            "ubicacion": ubicacion,
            "fecha_corte": convertir_fecha_de_corte(
                fila.get(cabecera.get(COLUMNA_FECHA_CORTE, ""))
            ),
        }

        recurso = existentes.get(codigo)

        if recurso is None:
            recurso = RecursoTuristico(codigo_mincetur=codigo, **datos)
            sesion.add(recurso)
            existentes[codigo] = recurso
            resultado.insertados += 1
        else:
            for campo, valor in datos.items():
                setattr(recurso, campo, valor)
            resultado.actualizados += 1

    sesion.commit()
    return resultado
