"""Carga prestadores REALES del directorio oficial del MINCETUR.

    python -m app.utilidades.cargar_prestadores

## De dónde salen

Del **Directorio Nacional de Prestadores de Servicios Turísticos
Calificados**, que el MINCETUR publica en la Plataforma Nacional de Datos
Abiertos con licencia *Open Data Commons Attribution*. Son tres archivos:
hospedajes, agencias de viaje y restaurantes calificados.

## Por qué esto no es lo mismo que inventarlos, ni que copiarlos de la web

Son empresas que **se certificaron voluntariamente ante el Estado** y cuyos
datos el Estado **publica**: razón social, RUC, dirección, teléfono, categoría
y número de certificado. Usarlos es exactamente el mismo acto que usar el
inventario de recursos turísticos, que es de dónde salen los 295 atractivos.

Lo que **no** significa es que tengan ningún trato con este proyecto. La
interfaz lo dice con esas palabras: *certificado por el MINCETUR, sin convenio
con este proyecto*. Y por eso tampoco se les inventa capacidad ni horarios:
esos datos no están publicados, y ponerles un número sería justo lo que este
proyecto dice no hacer.

## Qué pasa con los de demostración

**Se quedan.** No por comodidad: sin ellos no hay ninguna cuenta de proveedor
que pueda entrar y confirmar una solicitud, y el ciclo completo —pedir,
responder, confirmar, registrar— dejaría de poderse enseñar. Ese ciclo es lo
que cierran las brechas 5 y 6 y lo que mide el indicador 5.

Los reales sirven para encontrar y contactar; los de demostración, para
enseñar el proceso. Cada grupo va marcado y separado en la interfaz.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.base_datos import FabricaDeSesiones
from app.modelos.coordinacion import Proveedor

#: Los tres archivos del directorio, con la clase de servicio que representan.
#:
#: Las direcciones son las que publica la Plataforma Nacional de Datos
#: Abiertos. Se dejan escritas aquí y no en el `.env` porque no son secretos ni
#: configuración: son parte de la procedencia del dato, y esconderlas haría más
#: difícil comprobar de dónde salió cada prestador.
ARCHIVOS = {
    "hospedajes": "https://www.mincetur.gob.pe/Datos_abiertos/DGPDT/Establecimientos_hospedajes_calificados.csv",
    "agencias": "https://www.mincetur.gob.pe/Datos_abiertos/DGPDT/Agencias_de_viajes_y_turismo.csv",
    "restaurantes": "https://www.mincetur.gob.pe/Datos_abiertos/DGPDT/Restaurantes_calificados.csv",
}

#: Las cuatro provincias de la Ruta del Valle del Mantaro. Es el mismo recorte
#: que hace `cargar_catalogo`, para que el catálogo y los prestadores hablen
#: del mismo territorio.
PROVINCIAS_DE_LA_RUTA = {"HUANCAYO", "CONCEPCION", "JAUJA", "CHUPACA"}

FUENTE = "Directorio Nacional de Prestadores de Servicios Turísticos Calificados, MINCETUR"

#: Dónde se guardan los CSV descargados. Bajo `datos/`, que está ignorado.
CARPETA = Path(__file__).resolve().parents[2] / "datos" / "prestadores"


def _sin_tildes(texto: str) -> str:
    """Quita las tildes para poder comparar provincias.

    El directorio escribe «JUNÍN» con tilde y las provincias a veces también.
    Es el mismo problema que tuvo el asistente con «CONCEPCIÓN».
    """
    import unicodedata

    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _valor(fila: dict[str, str], *nombres: str) -> str | None:
    """El primer campo con contenido de entre varios nombres posibles.

    Los tres archivos llaman a las mismas cosas de forma distinta: el de
    restaurantes usa ``DES_PROV`` y los otros dos ``PROVINCIA``. En vez de
    escribir tres lectores casi iguales, se prueban los nombres por orden.
    """
    for nombre in nombres:
        valor = (fila.get(nombre) or "").strip()

        if valor and valor not in ("-", "--"):
            return valor

    return None


def _telefono(fila: dict[str, str]) -> str | None:
    """El primer teléfono que traiga la fila.

    El directorio reparte hasta cuatro teléfonos en columnas distintas y casi
    nunca están todas llenas; a menudo el único que hay está en ``TELEF4``.
    """
    return _valor(fila, "TELEF1", "TELEF2", "TELEF3", "TELEF4")


def _direccion(fila: dict[str, str]) -> str | None:
    """Reconstruye la dirección, que viene partida en cuatro columnas."""
    partes = [
        _valor(fila, "VIA"),
        _valor(fila, "DES_VIA"),
        _valor(fila, "NUMERO"),
        _valor(fila, "INTERIOR"),
    ]
    junta = " ".join(parte for parte in partes if parte)

    return junta or None


def _fecha_de_corte(fila: dict[str, str]) -> date | None:
    """La fecha de corte del archivo, que viene como ``20260829``."""
    crudo = _valor(fila, "FECHA_CORTE")

    if not crudo:
        return None

    try:
        return datetime.strptime(crudo, "%Y%m%d").date()
    except ValueError:
        return None


def descargar(nombre: str, url: str) -> Path:
    """Baja un archivo del directorio, o usa el que ya esté en disco."""
    destino = CARPETA / f"{nombre}.csv"

    if destino.exists():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=120.0, follow_redirects=True) as cliente:
        respuesta = cliente.get(url)
        respuesta.raise_for_status()
        destino.write_bytes(respuesta.content)

    return destino


def leer(ruta: Path) -> Iterator[dict[str, str]]:
    """Lee un CSV del directorio.

    Viene en *latin-1*, no en UTF-8: abrirlo como UTF-8 falla en la primera
    tilde. Se detecta el separador leyendo la primera línea porque los tres
    archivos no usan el mismo.
    """
    with ruta.open(encoding="latin-1", newline="") as archivo:
        primera = archivo.readline()
        archivo.seek(0)

        yield from csv.DictReader(archivo, delimiter=";" if ";" in primera else ",")


def es_de_la_ruta(fila: dict[str, str]) -> bool:
    """Si el prestador está en una de las cuatro provincias del valle."""
    departamento = _valor(fila, "DEPARTAMENTO", "DES_DEPA") or ""
    provincia = _valor(fila, "PROVINCIA", "DES_PROV") or ""

    return (
        "JUNIN" in _sin_tildes(departamento).upper()
        and _sin_tildes(provincia).upper().strip() in PROVINCIAS_DE_LA_RUTA
    )


def a_proveedor(fila: dict[str, str], clase_por_defecto: str) -> Proveedor | None:
    """Convierte una fila del directorio en un proveedor.

    Devuelve ``None`` si le falta lo imprescindible. Un prestador sin RUC no se
    puede identificar para no duplicarlo, y uno sin nombre no se puede enseñar.
    """
    ruc = _valor(fila, "RUC")
    nombre = _valor(fila, "NOMBRE_COMERCIAL", "RAZON_SOCIAL")

    if not (ruc and nombre):
        return None

    return Proveedor(
        usuario_id=None,  # nadie los administra: se les contacta directamente
        nombre=nombre,
        distrito=(_valor(fila, "DISTRITO", "DES_DIST") or "").upper() or "SIN DISTRITO",
        telefono=_telefono(fila),
        correo=_valor(fila, "E_MAIL"),
        descripcion=None,  # el directorio no publica descripción, y no se inventa
        es_demostracion=False,
        ruc=ruc,
        direccion=_direccion(fila),
        pagina_web=_valor(fila, "PAGINA_WEB"),
        clase=_valor(fila, "CLASE") or clase_por_defecto,
        categoria=_valor(fila, "CATEGORIA"),
        certificado=_valor(fila, "NRO_CERTIFICADO"),
        fuente=FUENTE,
        fecha_corte=_fecha_de_corte(fila),
        esta_activo=True,
    )


def cargar(sesion: Session) -> dict[str, int]:
    """Carga los tres archivos y devuelve cuántos entraron de cada uno.

    Es idempotente: identifica cada prestador por su RUC, así que volver a
    ejecutarlo actualiza en vez de duplicar. Lo mismo que hace
    `cargar_catalogo` con el código del MINCETUR.

    **Un mismo RUC puede aparecer en dos archivos**: hay hoteles del valle que
    también tienen restaurante calificado, y el Estado los registra en los dos
    directorios. No son dos negocios, es uno con dos certificaciones, así que
    se guarda una sola ficha y se juntan las clases —«Hostal · Restaurante»—.
    Quedarse con la última sería esconder la mitad de lo que ese negocio hace.
    """
    resumen: dict[str, int] = {}

    # Los que ya se vieron en esta ejecución. Consultar solo la base no basta:
    # los añadidos aún no están confirmados y no aparecerían en la consulta.
    vistos: dict[str, Proveedor] = {}

    for nombre, url in ARCHIVOS.items():
        ruta = descargar(nombre, url)
        clase_por_defecto = {"hospedajes": "Hospedaje", "restaurantes": "Restaurante"}.get(
            nombre, "Agencia de viajes"
        )

        nuevos = actualizados = repetidos = 0

        for fila in leer(ruta):
            if not es_de_la_ruta(fila):
                continue

            candidato = a_proveedor(fila, clase_por_defecto)

            if candidato is None:
                continue

            ya_en_esta_vuelta = vistos.get(candidato.ruc)

            if ya_en_esta_vuelta is not None:
                _juntar_clases(ya_en_esta_vuelta, candidato.clase)
                repetidos += 1
                continue

            existente = sesion.scalar(select(Proveedor).where(Proveedor.ruc == candidato.ruc))

            if existente is None:
                sesion.add(candidato)
                vistos[candidato.ruc] = candidato
                nuevos += 1
                continue

            for campo in (
                "nombre",
                "distrito",
                "telefono",
                "correo",
                "direccion",
                "pagina_web",
                "clase",
                "categoria",
                "certificado",
                "fuente",
                "fecha_corte",
            ):
                setattr(existente, campo, getattr(candidato, campo))

            vistos[candidato.ruc] = existente
            actualizados += 1

        resumen[nombre] = nuevos
        resumen[f"{nombre}_actualizados"] = actualizados
        resumen[f"{nombre}_repetidos"] = repetidos

    sesion.commit()

    return resumen


def _juntar_clases(proveedor: Proveedor, otra: str | None) -> None:
    """Añade otra clase a un prestador que ya estaba, sin repetirla."""
    if not otra:
        return

    clases = [c.strip() for c in (proveedor.clase or "").split("·") if c.strip()]

    if otra not in clases:
        clases.append(otra)

    proveedor.clase = " · ".join(clases)[:80]


def principal(argumentos: list[str] | None = None) -> int:
    """Punto de entrada del guion."""
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.parse_args(argumentos)

    with FabricaDeSesiones() as sesion:
        resumen = cargar(sesion)

        print("Prestadores reales del directorio del MINCETUR")
        print(f"  Provincias de la ruta : {', '.join(sorted(PROVINCIAS_DE_LA_RUTA))}")
        print()

        for nombre in ARCHIVOS:
            print(
                f"  {nombre:14} nuevos: {resumen.get(nombre, 0):4}"
                f"   actualizados: {resumen.get(f'{nombre}_actualizados', 0):4}"
                f"   ya estaban en otro archivo: {resumen.get(f'{nombre}_repetidos', 0):3}"
            )

        cuantos = lambda de_demostracion: sesion.scalar(  # noqa: E731
            select(func.count())
            .select_from(Proveedor)
            .where(Proveedor.es_demostracion.is_(de_demostracion))
        )
        reales, demostracion = cuantos(False), cuantos(True)

        print()
        print(f"  En la base: {reales} reales · {demostracion} de demostración")
        print()
        print("  Los reales están CERTIFICADOS por el MINCETUR pero NO tienen")
        print("  convenio con este proyecto. La interfaz lo dice.")

    return 0


if __name__ == "__main__":
    sys.exit(principal())
