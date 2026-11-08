"""Carga y construccion de la red vial: todo lo que toca el mundo exterior.

Este modulo es un **adaptador de salida**. Hace tres cosas que el dominio no
puede hacer sin dejar de ser dominio: descarga el grafo de OpenStreetMap, lee
las altitudes por un puerto, y guarda y recupera el resultado del disco.

El calculo -buscar caminos, medir pendientes, estimar tiempos- vive en
``src.domain.red_vial`` y no sabe nada de esto.
"""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path

from src.domain.red_vial import RedVial
from src.ports.elevacion import FuenteDeAltitud

#: Dónde se guarda el grafo ya preparado, con altitudes incluidas. Se guarda
#: procesado y no crudo para no repetir en cada arranque un trabajo de minutos.
#:
#: SEGURIDAD — por qué aquí sí se usa ``pickle``. Deserializar un pickle
#: ejecuta código, así que solo es aceptable con archivos de origen conocido.
#: Este archivo lo escribe ``construir_y_guardar`` en la misma máquina, no se
#: descarga de ningún sitio y no se sube al repositorio (está en .gitignore).
#: Se usa pickle y no JSON porque un grafo de NetworkX con 40 000 nodos no es
#: un objeto serializable a JSON sin reconstruirlo entero a mano.
#: **Nunca cargar aquí un archivo recibido de un tercero.**
#:
#: Son ``parents[3]`` y no ``parents[2]`` porque este archivo bajo dos niveles
#: al pasar de ``src/servicios/`` a ``src/adapters/outbound/``. La ruta
#: resultante es la misma de siempre: ``backend/datos/``.
RUTA_DEL_GRAFO = Path(__file__).resolve().parents[3] / "datos" / "red_vial_valle.pickle"


# ---------------------------------------------------------------------------
# Carga y construcción
# ---------------------------------------------------------------------------


def construir_y_guardar(
    limites: tuple[float, float, float, float],
    fuente_de_altitud: FuenteDeAltitud,
) -> RedVial:
    """Descarga la red, le pega las altitudes y la guarda en disco.

    Es la operación cara: minutos de descarga y de muestreo. Se ejecuta una vez
    con ``python -m src.utilidades.preparar_red_vial``.

    La fuente de altitud llega **por parámetro** y no se construye aquí. Quien
    llama decide si es el modelo de Copernicus o un diccionario de prueba, y es
    también quien abre y cierra sus archivos: esta función solo pregunta.
    """
    import osmnx as ox

    ox.settings.log_console = False
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(Path("datos") / "cache_osm")
    ox.settings.requests_timeout = 600

    grafo = ox.graph_from_bbox(bbox=limites, network_type="all", simplify=True)

    altitudes: dict[int, float] = {}
    for nodo, datos in grafo.nodes(data=True):
        altitud = fuente_de_altitud.altitud(datos["y"], datos["x"])
        if altitud is not None:
            altitudes[nodo] = altitud

    RUTA_DEL_GRAFO.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_DEL_GRAFO.open("wb") as archivo:
        pickle.dump({"grafo": grafo, "altitudes": altitudes}, archivo)

    return RedVial(grafo, altitudes)


@lru_cache(maxsize=1)
def obtener_red_vial() -> RedVial | None:
    """Devuelve la red vial ya preparada, o ``None`` si no se ha construido.

    ``lru_cache`` hace que se cargue del disco una sola vez por proceso. Sin
    eso, cada petición leería cien megas de grafo.

    Devuelve ``None`` en vez de fallar cuando no existe el archivo: el sistema
    tiene que poder arrancar sin la red y decir que el ruteo no está
    disponible, en lugar de no arrancar.
    """
    if not RUTA_DEL_GRAFO.exists():
        return None

    with RUTA_DEL_GRAFO.open("rb") as archivo:
        datos = pickle.load(archivo)

    return RedVial(datos["grafo"], datos["altitudes"])
