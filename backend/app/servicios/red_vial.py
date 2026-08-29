"""Cálculo de traslados sobre la red vial del Valle del Mantaro.

Junta las tres piezas del Incremento 4:

1. El **grafo de OpenStreetMap**, descargado una vez y guardado en disco.
2. Las **altitudes** del modelo Copernicus, para calcular pendientes reales.
3. La **función de Tobler**, que convierte pendiente en tiempo de caminata.

## Los dos modos de cálculo, y por qué hay dos

La medición de cobertura (ver
``docs/decisiones/2026-08-29-cobertura-de-openstreetmap-en-el-valle.md``)
encontró que **el 26,1 % de los recursos está a más de 500 m de cualquier vía
registrada**. En esos casos no existe ruta que calcular.

| Situación | Cálculo | Qué se marca |
|---|---|---|
| Ambos extremos sobre la red | Camino más corto sobre el grafo | ``red_vial`` |
| Alguno fuera de la red | Línea recta × 1,26 | ``linea_recta`` |

El factor 1,26 **está medido**, no supuesto: es la mediana del índice de rodeo
sobre 400 pares de recursos donde sí hay red.

Cada tramo lleva su marca, y la interfaz muestra un aviso visible cuando el
cálculo fue estimado. Sin ese aviso el visitante creería que un tiempo estimado
sobre línea recta es un tiempo calculado, y en Chongos Alto eso significa horas
de diferencia.
"""

from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.ia.tiempo_recorrido import calcular_tramo_caminando
from app.modelos.itinerario import OrigenDelCalculo

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
RUTA_DEL_GRAFO = Path(__file__).resolve().parents[2] / "datos" / "red_vial_valle.pickle"

#: Distancia máxima a la que se considera que un punto está «sobre» la red.
#: Sale de la medición de cobertura: 500 m es una caminata de unos 7 minutos
#: por terreno sin vía registrada.
DISTANCIA_MAXIMA_AL_NODO_M = 500.0

#: Índice de rodeo medido sobre la red real del valle: las rutas son un 26 %
#: más largas que la línea recta. Mediana de 400 pares, no una suposición.
#: Ver docs/decisiones/2026-08-29-cobertura-de-openstreetmap-en-el-valle.md
FACTOR_DE_RODEO = 1.26

#: Radio de la Tierra en metros, para la fórmula de Haversine.
RADIO_TERRESTRE_M = 6_371_000.0


def distancia_en_linea_recta_m(
    latitud_a: float, longitud_a: float, latitud_b: float, longitud_b: float
) -> float:
    """Distancia sobre la superficie terrestre entre dos puntos, en metros.

    Usa la fórmula de Haversine, que trata la Tierra como una esfera. El error
    frente a un elipsoide es de unas décimas de por ciento, despreciable frente
    a la incertidumbre del propio factor de rodeo.
    """
    lat_a, lon_a, lat_b, lon_b = map(math.radians, (latitud_a, longitud_a, latitud_b, longitud_b))

    diferencia_lat = lat_b - lat_a
    diferencia_lon = lon_b - lon_a

    a = (
        math.sin(diferencia_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(diferencia_lon / 2) ** 2
    )

    return 2 * RADIO_TERRESTRE_M * math.asin(math.sqrt(a))


@dataclass
class BusquedaDeCamino:
    """Resultado de buscar una ruta: el camino, y si había red donde buscarla.

    ``hay_cobertura`` existe para no confundir dos cosas muy distintas: que no
    haya camino porque los puntos están en el mismo sitio, y que no lo haya
    porque OpenStreetMap no conoce esa zona. Solo la segunda merece un aviso.
    """

    camino: list[int] | None
    recta_m: float
    hay_cobertura: bool


@dataclass
class Traslado:
    """Un desplazamiento entre dos puntos, con todo lo que hace falta saber."""

    distancia_m: float
    minutos: float
    desnivel_m: float
    #: Solo la subida. Es lo que determina el esfuerzo del día.
    subida_m: float
    origen_del_calculo: str
    #: Coordenadas del camino, para dibujarlo en el mapa. Vacío si es estimado.
    trazado: list[tuple[float, float]]

    @property
    def es_estimado(self) -> bool:
        return self.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA


class RedVial:
    """El grafo de la red vial del valle, con altitudes.

    Se carga una vez y se reutiliza: construirlo desde cero lleva minutos, y
    hacerlo en cada petición dejaría la API inservible.
    """

    def __init__(self, grafo, altitudes: dict[int, float]) -> None:
        self._grafo = grafo
        self._altitudes = altitudes
        self._sin_direccion = None

    @property
    def grafo(self):
        return self._grafo

    @property
    def sin_direccion(self):
        """Grafo no dirigido: a pie se puede ir en ambos sentidos.

        Se calcula la primera vez que se pide y se guarda, porque convertirlo
        es caro y se necesita en cada cálculo de ruta.
        """
        if self._sin_direccion is None:
            import networkx as nx

            self._sin_direccion = nx.Graph(self._grafo)

        return self._sin_direccion

    def nodo_mas_cercano(self, latitud: float, longitud: float) -> tuple[int, float]:
        """Devuelve el nodo más cercano a un punto y su distancia en metros."""
        import osmnx as ox

        nodo, distancia = ox.nearest_nodes(self._grafo, X=longitud, Y=latitud, return_dist=True)
        return int(nodo), float(distancia)

    def altitud_del_nodo(self, nodo: int) -> float | None:
        return self._altitudes.get(nodo)

    def calcular_traslado_caminando(
        self,
        latitud_origen: float,
        longitud_origen: float,
        altitud_origen: float | None,
        latitud_destino: float,
        longitud_destino: float,
        altitud_destino: float | None,
    ) -> Traslado:
        """Calcula un traslado a pie entre dos puntos.

        Intenta la ruta real sobre la red; si alguno de los extremos está
        demasiado lejos de ella, cae a línea recta corregida y lo marca.
        """
        busqueda = self.buscar_camino(
            latitud_origen, longitud_origen, latitud_destino, longitud_destino
        )

        if busqueda.camino is None:
            return self._traslado_en_linea_recta(
                busqueda.recta_m,
                altitud_origen,
                altitud_destino,
                busqueda.hay_cobertura,
            )

        return self._traslado_por_la_red(busqueda.camino, altitud_origen, altitud_destino)

    def buscar_camino(
        self,
        latitud_origen: float,
        longitud_origen: float,
        latitud_destino: float,
        longitud_destino: float,
    ) -> BusquedaDeCamino:
        """Camino mínimo sobre la red entre dos puntos.

        Devuelve un camino nulo en tres casos distintos, y la diferencia entre
        ellos **importa para lo que se le dice al visitante**:

        - alguno de los extremos está a más de 500 m de cualquier vía: no hay
          cobertura, el tiempo es una estimación y hay que avisar;
        - los dos caen sobre el mismo nodo: están prácticamente en el mismo
          sitio y no hay tramo que recorrer. Sí hay cobertura, y avisar de una
          estimación aquí sería alarmar sin motivo;
        - la red está partida entre los dos: hay cobertura en ambos extremos
          pero no existe camino. Se avisa, porque el tiempo no se conoce.

        La usan tanto la caminata como los traslados motorizados: el grafo se
        descargó con ``network_type="all"``, así que contiene las carreteras
        además de los caminos peatonales.
        """
        recta_m = distancia_en_linea_recta_m(
            latitud_origen, longitud_origen, latitud_destino, longitud_destino
        )

        nodo_origen, distancia_origen = self.nodo_mas_cercano(latitud_origen, longitud_origen)
        nodo_destino, distancia_destino = self.nodo_mas_cercano(latitud_destino, longitud_destino)

        hay_cobertura = (
            distancia_origen <= DISTANCIA_MAXIMA_AL_NODO_M
            and distancia_destino <= DISTANCIA_MAXIMA_AL_NODO_M
        )

        if not hay_cobertura:
            return BusquedaDeCamino(None, recta_m, hay_cobertura=False)

        if nodo_origen == nodo_destino:
            # Mismo nodo: los dos puntos están sobre la red, solo que en el
            # mismo sitio. La línea recta ES la distancia correcta.
            return BusquedaDeCamino(None, recta_m, hay_cobertura=True)

        try:
            import networkx as nx

            camino = nx.shortest_path(
                self.sin_direccion, nodo_origen, nodo_destino, weight="length"
            )
        except Exception:  # noqa: BLE001 - red partida entre los dos extremos
            return BusquedaDeCamino(None, recta_m, hay_cobertura=False)

        return BusquedaDeCamino(camino, recta_m, hay_cobertura=True)

    def longitud_del_camino_m(self, camino: list[int]) -> tuple[float, list[tuple[float, float]]]:
        """Longitud de un camino en metros y sus coordenadas para dibujarlo.

        Es lo que necesita un traslado motorizado: la distancia por carretera,
        sin aplicar Tobler, porque a quien sube la cuesta es al motor.
        """
        nodos = self._grafo.nodes

        total = 0.0
        trazado: list[tuple[float, float]] = []

        for indice in range(len(camino) - 1):
            actual, siguiente = camino[indice], camino[indice + 1]
            total += self._longitud_de_arista(actual, siguiente)
            trazado.append((nodos[actual]["y"], nodos[actual]["x"]))

        if camino:
            ultimo = camino[-1]
            trazado.append((nodos[ultimo]["y"], nodos[ultimo]["x"]))

        return total, trazado

    def _longitud_de_arista(self, actual: int, siguiente: int) -> float:
        """Longitud en metros del arco más corto entre dos nodos contiguos."""
        datos = self._grafo.get_edge_data(actual, siguiente)
        if datos is None:
            datos = self._grafo.get_edge_data(siguiente, actual) or {}

        # Puede haber varias aristas paralelas; se toma la más corta.
        return min((arista.get("length", 0.0) for arista in datos.values()), default=0.0)

    def _traslado_por_la_red(
        self,
        camino: list[int],
        altitud_origen: float | None,
        altitud_destino: float | None,
    ) -> Traslado:
        """Suma los tramos del camino, aplicando Tobler a cada uno.

        Se calcula tramo a tramo y no de una vez sobre el total porque la
        pendiente **no es lineal**: subir 100 m en un tramo y bajarlos en el
        siguiente no es lo mismo que recorrer los dos en llano, y sumar los
        desniveles daría cero.
        """
        nodos = self._grafo.nodes

        distancia_total = 0.0
        minutos_total = 0.0
        subida_total = 0.0
        trazado: list[tuple[float, float]] = []

        for indice in range(len(camino) - 1):
            actual, siguiente = camino[indice], camino[indice + 1]

            longitud = self._longitud_de_arista(actual, siguiente)

            altitud_a = self._altitudes.get(actual)
            altitud_b = self._altitudes.get(siguiente)

            tramo = calcular_tramo_caminando(longitud, altitud_a, altitud_b)

            distancia_total += tramo.distancia_m
            minutos_total += tramo.minutos
            if tramo.desnivel_m > 0:
                subida_total += tramo.desnivel_m

            trazado.append((nodos[actual]["y"], nodos[actual]["x"]))

        if camino:
            ultimo = camino[-1]
            trazado.append((nodos[ultimo]["y"], nodos[ultimo]["x"]))

        desnivel_neto = (
            (altitud_destino - altitud_origen)
            if altitud_origen is not None and altitud_destino is not None
            else 0.0
        )

        return Traslado(
            distancia_m=round(distancia_total, 1),
            minutos=round(minutos_total, 1),
            desnivel_m=round(desnivel_neto, 1),
            subida_m=round(subida_total, 1),
            origen_del_calculo=OrigenDelCalculo.RED_VIAL,
            trazado=trazado,
        )

    def _traslado_en_linea_recta(
        self,
        distancia_recta_m: float,
        altitud_origen: float | None,
        altitud_destino: float | None,
        hay_cobertura: bool = False,
    ) -> Traslado:
        """Estima el traslado cuando no hay red que recorrer.

        Se corrige la línea recta por el factor de rodeo medido. El desnivel sí
        se conoce —el modelo de elevación cubre todo el valle—, así que Tobler
        sigue aplicándose y el tiempo no es una regla de tres.

        Con ``hay_cobertura=True`` no se aplica el factor de rodeo ni se marca
        como estimado: es el caso de dos puntos que caen sobre el mismo nodo,
        donde la línea recta es la distancia correcta y no una aproximación.
        """
        if hay_cobertura:
            tramo_directo = calcular_tramo_caminando(
                distancia_recta_m, altitud_origen, altitud_destino
            )
            return Traslado(
                distancia_m=round(distancia_recta_m, 1),
                minutos=round(tramo_directo.minutos, 1),
                desnivel_m=tramo_directo.desnivel_m,
                subida_m=max(0.0, tramo_directo.desnivel_m),
                origen_del_calculo=OrigenDelCalculo.RED_VIAL,
                trazado=[],
            )

        distancia_corregida = distancia_recta_m * FACTOR_DE_RODEO

        tramo = calcular_tramo_caminando(distancia_corregida, altitud_origen, altitud_destino)

        return Traslado(
            distancia_m=round(distancia_corregida, 1),
            minutos=round(tramo.minutos, 1),
            desnivel_m=tramo.desnivel_m,
            subida_m=max(0.0, tramo.desnivel_m),
            origen_del_calculo=OrigenDelCalculo.LINEA_RECTA,
            trazado=[],
        )


# ---------------------------------------------------------------------------
# Carga y construcción
# ---------------------------------------------------------------------------


def construir_y_guardar(limites: tuple[float, float, float, float]) -> RedVial:
    """Descarga la red, le pega las altitudes y la guarda en disco.

    Es la operación cara: minutos de descarga y de muestreo. Se ejecuta una vez
    con ``python -m app.utilidades.preparar_red_vial``.
    """
    import osmnx as ox

    from app.servicios.elevacion import MuestreadorDeAltitud

    ox.settings.log_console = False
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(Path("datos") / "cache_osm")
    ox.settings.requests_timeout = 600

    grafo = ox.graph_from_bbox(bbox=limites, network_type="all", simplify=True)

    altitudes: dict[int, float] = {}
    with MuestreadorDeAltitud() as muestreador:
        for nodo, datos in grafo.nodes(data=True):
            altitud = muestreador.altitud(datos["y"], datos["x"])
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
