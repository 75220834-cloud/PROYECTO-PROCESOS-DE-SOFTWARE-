"""Validación DataOps del catálogo de recursos turísticos.

Este módulo es la evidencia del Incremento 1. Cada vez que se ejecuta recorre
todos los recursos, comprueba cuatro reglas sobre cada uno y guarda una fila
en ``registro_validacion``. Esa fila **es** el indicador del incremento:
*porcentaje de oferta con información validada y vigente*.

Las cuatro reglas y por qué existen:

1. **Tiene nombre.** Un recurso sin nombre no se puede mostrar ni buscar.
2. **El distrito pertenece a una provincia de la ruta.** Protege contra que un
   cambio del filtro de importación cuele recursos de fuera del valle.
3. **Tiene coordenadas dentro del área del Valle del Mantaro.** Sin coordenadas
   el recurso no puede entrar en un itinerario (Fase 4). Fuera del área
   significa que la coordenada es errónea.
4. **Su fecha de corte no es demasiado antigua.** Es lo que distingue
   "validado" de "vigente": un dato puede ser correcto y estar caduco.

Un recurso que falla alguna regla NO se borra. Se marca y se guardan los
motivos, para que el gestor sepa qué corregir. Ocultarlo sería perder
información sobre la calidad real de la fuente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.modelos.catalogo import RecursoTuristico, RegistroValidacion
from app.servicios.catalogo import PROVINCIAS_DE_LA_RUTA

# --------------------------------------------------------------------------
# Reglas de validación
# --------------------------------------------------------------------------

#: Rectángulo que envuelve el territorio de las cuatro provincias de la ruta.
#:
#: PARA QUÉ SIRVE: detectar errores gruesos de coordenada — un punto en Lima,
#: un signo cambiado, o las columnas de latitud y longitud intercambiadas. NO
#: es una frontera administrativa fina; para eso está el campo distrito.
#:
#: DE DÓNDE SALEN ESTOS NÚMEROS: se midieron sobre los 234 recursos del
#: inventario oficial que traen coordenadas. Su extensión real es
#: latitud -12.476 .. -11.296 y longitud -75.773 .. -75.062. Se añade un
#: margen para admitir recursos que la fuente incorpore más adelante.
#:
#: El plan de trabajo del proyecto proponía "aproximadamente latitud -12.5 a
#: -11.5, longitud -75.5 a -74.9". Ese rectángulo resultó estar desplazado al
#: este y recortado por el norte: dejaba fuera 52 recursos correctos de
#: distritos reales de la ruta (San José de Quero en Concepción, Canchayllo y
#: Apata en Jauja, Yanacancha en Chupaca), todos en la zona alta occidental.
#: Usarlo habría hecho que el indicador del Incremento 1 declarara inválidos
#: datos oficiales que son válidos. Se corrigió midiendo, no estimando.
LATITUD_MINIMA, LATITUD_MAXIMA = -12.60, -11.20
LONGITUD_MINIMA, LONGITUD_MAXIMA = -75.90, -74.90

#: Antigüedad máxima de la fecha de corte para considerar el dato vigente.
#: Dos años es el criterio adoptado: el inventario del MINCETUR se publica de
#: forma irregular, y exigir menos dejaría el catálogo vacío en la práctica.
#: Este número es una decisión del equipo, no un estándar oficial.
DIAS_DE_VIGENCIA = 730


@dataclass
class ResultadoValidacion:
    """Resumen de una ejecución de la validación."""

    total_recursos: int = 0
    validados: int = 0
    vigentes: int = 0
    con_coordenadas: int = 0
    porcentaje_validado: float = 0.0
    motivos_frecuentes: dict[str, int] = field(default_factory=dict)


def coordenada_esta_en_el_valle(latitud: float | None, longitud: float | None) -> bool:
    """Comprueba que un punto cae dentro del área del Valle del Mantaro."""
    if latitud is None or longitud is None:
        return False

    return (
        LATITUD_MINIMA <= latitud <= LATITUD_MAXIMA
        and LONGITUD_MINIMA <= longitud <= LONGITUD_MAXIMA
    )


def evaluar_recurso(
    nombre: str | None,
    provincia: str | None,
    latitud: float | None,
    longitud: float | None,
    fecha_corte: date | None,
    fecha_de_referencia: date,
) -> tuple[bool, bool, list[str]]:
    """Aplica las cuatro reglas a un recurso.

    Se recibe cada dato por separado, en vez del objeto completo, para que la
    función se pueda probar sin base de datos.

    Devuelve ``(esta_validado, esta_vigente, motivos)``.
    """
    motivos: list[str] = []

    if not nombre or not nombre.strip():
        motivos.append("sin nombre")

    if not provincia or provincia not in PROVINCIAS_DE_LA_RUTA:
        motivos.append("provincia fuera de la ruta")

    if latitud is None or longitud is None:
        motivos.append("sin coordenadas")
    elif not coordenada_esta_en_el_valle(latitud, longitud):
        motivos.append("coordenada fuera del area del valle")

    esta_validado = not motivos

    # La vigencia se evalúa aparte: un recurso puede estar bien descrito y
    # ubicado, y aun así tener el dato caducado. Son dos cosas distintas y el
    # indicador las cuenta por separado.
    if fecha_corte is None:
        motivos.append("sin fecha de corte")
        esta_vigente = False
    else:
        esta_vigente = (fecha_de_referencia - fecha_corte).days <= DIAS_DE_VIGENCIA
        if not esta_vigente:
            motivos.append("fecha de corte demasiado antigua")

    return esta_validado, esta_vigente, motivos


def validar_catalogo(
    sesion: Session, fecha_de_referencia: date | None = None
) -> ResultadoValidacion:
    """Valida todos los recursos y guarda el registro del indicador.

    ``fecha_de_referencia`` existe para que las pruebas puedan fijar el "hoy"
    y no dependan de cuándo se ejecuten.
    """
    if fecha_de_referencia is None:
        fecha_de_referencia = date.today()

    # Se piden la latitud y la longitud como números junto con el recurso: es
    # una sola consulta en vez de una por recurso para extraer el punto.
    #
    # ST_X y ST_Y operan sobre geometría, no sobre geografía, así que hay que
    # convertir el tipo. Y ojo al orden: ST_X devuelve la LONGITUD (la
    # coordenada horizontal) y ST_Y la LATITUD. Es la confusión más habitual
    # trabajando con datos geográficos.
    punto = cast(RecursoTuristico.ubicacion, Geometry)
    consulta = select(
        RecursoTuristico,
        func.ST_Y(punto).label("latitud"),
        func.ST_X(punto).label("longitud"),
    )

    resultado = ResultadoValidacion()
    conteo_motivos: dict[str, int] = {}

    for recurso, latitud, longitud in sesion.execute(consulta):
        esta_validado, esta_vigente, motivos = evaluar_recurso(
            nombre=recurso.nombre,
            provincia=recurso.provincia,
            latitud=latitud,
            longitud=longitud,
            fecha_corte=recurso.fecha_corte,
            fecha_de_referencia=fecha_de_referencia,
        )

        recurso.esta_validado = esta_validado
        recurso.esta_vigente = esta_vigente
        recurso.motivos_invalidez = "; ".join(motivos) if motivos else None

        resultado.total_recursos += 1
        resultado.validados += int(esta_validado)
        resultado.vigentes += int(esta_vigente)
        resultado.con_coordenadas += int(latitud is not None and longitud is not None)

        for motivo in motivos:
            conteo_motivos[motivo] = conteo_motivos.get(motivo, 0) + 1

    resultado.porcentaje_validado = (
        round(100 * resultado.validados / resultado.total_recursos, 2)
        if resultado.total_recursos
        else 0.0
    )
    resultado.motivos_frecuentes = dict(
        sorted(conteo_motivos.items(), key=lambda par: par[1], reverse=True)
    )

    # Aquí se guarda el indicador. Sin esta fila, el Incremento 1 no tendría
    # evidencia medible y el documento académico afirmaría algo que el código
    # no sostiene.
    sesion.add(
        RegistroValidacion(
            total_recursos=resultado.total_recursos,
            validados=resultado.validados,
            vigentes=resultado.vigentes,
            con_coordenadas=resultado.con_coordenadas,
            porcentaje_validado=resultado.porcentaje_validado,
        )
    )
    sesion.commit()

    return resultado


def obtener_ultimo_registro(sesion: Session) -> RegistroValidacion | None:
    """Devuelve la última validación ejecutada, que es el indicador vigente."""
    return sesion.scalars(
        select(RegistroValidacion).order_by(RegistroValidacion.fecha.desc()).limit(1)
    ).first()
