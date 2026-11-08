"""Altitud del terreno a partir del modelo de elevación Copernicus GLO-30.

Es lo que alimenta la función de Tobler: sin altitudes no hay pendientes, y sin
pendientes el tiempo de caminata sería el mismo cuesta arriba que en llano.

## Qué es Copernicus GLO-30

Un modelo digital de superficie del programa Copernicus de la Unión Europea,
con una celda de **30 metros**, derivado de la misión radar TanDEM-X. Es de
acceso libre y está publicado en AWS Open Data.

Se eligió frente a las alternativas por tres motivos:

- **SRTM** (30 m, NASA) tiene huecos en zonas de montaña escarpada, justo donde
  más importa aquí.
- **ASTER GDEM** (30 m) tiene más ruido y artefactos en nubes.
- **Los servicios de elevación por API** (Google, Open-Elevation) son de pago o
  poco fiables, y exigen internet en cada consulta. El proyecto declara la
  conectividad limitada como restricción.

Las teselas se descargan una vez y se guardan en ``backend/datos/dem/``. A
partir de ahí el cálculo es local y funciona sin internet.

## Precisión y sus límites

GLO-30 es un modelo de **superficie**, no de terreno: incluye la altura de
edificios y árboles. En el centro de Huancayo eso puede añadir algunos metros
de error. Para calcular pendientes de caminata entre recursos separados
cientos de metros, ese error es despreciable; para nada más fino, no serviría.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import httpx

#: Dónde se guardan las teselas descargadas.
CARPETA_DEM = Path(__file__).resolve().parents[2] / "datos" / "dem"

#: Plantilla de la URL en AWS Open Data.
URL_PLANTILLA = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM/"
    "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM.tif"
)


def nombre_de_tesela(latitud: float, longitud: float) -> tuple[str, str]:
    """Devuelve el identificador de la tesela que contiene un punto.

    Las teselas de Copernicus cubren un grado por un grado y se nombran por su
    esquina **suroeste**. Por eso se usa ``floor`` y no un redondeo: el punto
    (−12,5, −75,5) pertenece a la tesela S13/W076, que va de −13 a −12 y de
    −76 a −75.
    """
    grado_lat = math.floor(latitud)
    grado_lon = math.floor(longitud)

    etiqueta_lat = f"{'S' if grado_lat < 0 else 'N'}{abs(grado_lat):02d}"
    etiqueta_lon = f"{'W' if grado_lon < 0 else 'E'}{abs(grado_lon):03d}"

    return etiqueta_lat, etiqueta_lon


def ruta_local_de_tesela(latitud: float, longitud: float) -> Path:
    """Dónde se guarda localmente la tesela de un punto."""
    etiqueta_lat, etiqueta_lon = nombre_de_tesela(latitud, longitud)
    return CARPETA_DEM / f"Copernicus_DSM_COG_10_{etiqueta_lat}_00_{etiqueta_lon}_00_DEM.tif"


def descargar_tesela(latitud: float, longitud: float) -> Path:
    """Descarga la tesela que contiene el punto, si no está ya.

    Devuelve la ruta local. Es idempotente: si el archivo existe, no lo vuelve
    a bajar.
    """
    destino = ruta_local_de_tesela(latitud, longitud)

    if destino.exists() and destino.stat().st_size > 0:
        return destino

    etiqueta_lat, etiqueta_lon = nombre_de_tesela(latitud, longitud)
    url = URL_PLANTILLA.format(lat=etiqueta_lat, lon=etiqueta_lon)

    destino.parent.mkdir(parents=True, exist_ok=True)

    # Se descarga a un archivo temporal y se renombra al final: así una
    # descarga interrumpida no deja una tesela a medias que parezca completa.
    temporal = destino.with_suffix(".parcial")

    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as respuesta:
        respuesta.raise_for_status()
        with temporal.open("wb") as archivo:
            for bloque in respuesta.iter_bytes(chunk_size=1 << 20):
                archivo.write(bloque)

    temporal.replace(destino)
    return destino


@dataclass
class MuestreadorDeAltitud:
    """Consulta altitudes en las teselas descargadas.

    Mantiene abiertas las teselas que va usando, porque abrir un archivo GeoTIFF
    por cada consulta sería lentísimo cuando hay que muestrear miles de nodos.
    """

    _teselas: dict[tuple[str, str], object] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._teselas = {}

    def _obtener_tesela(self, latitud: float, longitud: float):
        clave = nombre_de_tesela(latitud, longitud)

        if clave not in self._teselas:
            import rasterio

            ruta = ruta_local_de_tesela(latitud, longitud)
            if not ruta.exists():
                self._teselas[clave] = None
            else:
                self._teselas[clave] = rasterio.open(ruta)

        return self._teselas[clave]

    def altitud(self, latitud: float, longitud: float) -> float | None:
        """Altitud del terreno en metros, o ``None`` si no hay dato.

        Devolver ``None`` y no un cero es deliberado: cero metros sobre el nivel
        del mar es una altitud válida en la costa, y confundirla con «no lo sé»
        haría que un tramo sin datos pareciera una bajada de 3 250 m.
        """
        tesela = self._obtener_tesela(latitud, longitud)

        if tesela is None:
            return None

        try:
            valor = next(tesela.sample([(longitud, latitud)]))[0]
        except (StopIteration, IndexError, ValueError):
            return None

        # El valor de «sin dato» del modelo. Comparar con el declarado en el
        # archivo en vez de con un número fijo.
        if tesela.nodata is not None and valor == tesela.nodata:
            return None

        # Copernicus usa valores muy negativos para el mar y para huecos.
        if valor is None or float(valor) < -400:
            return None

        return float(valor)

    def altitudes(self, puntos: list[tuple[float, float]]) -> list[float | None]:
        """Altitud de varios puntos ``(latitud, longitud)`` de una vez."""
        return [self.altitud(lat, lon) for lat, lon in puntos]

    def cerrar(self) -> None:
        for tesela in self._teselas.values():
            if tesela is not None:
                tesela.close()
        self._teselas.clear()

    def __enter__(self) -> MuestreadorDeAltitud:
        return self

    def __exit__(self, *_) -> None:
        self.cerrar()


def teselas_necesarias(
    limites: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    """Puntos representativos de cada tesela que cubre un rectángulo.

    ``limites`` es ``(oeste, sur, este, norte)``.
    """
    oeste, sur, este, norte = limites

    puntos: list[tuple[float, float]] = []

    for grado_lat in range(math.floor(sur), math.floor(norte) + 1):
        for grado_lon in range(math.floor(oeste), math.floor(este) + 1):
            # Se toma el centro de la tesela como punto representativo.
            puntos.append((grado_lat + 0.5, grado_lon + 0.5))

    return puntos
