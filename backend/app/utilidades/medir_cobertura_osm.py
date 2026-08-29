"""Mide la cobertura real de OpenStreetMap en el Valle del Mantaro.

El plan de trabajo lo exige **antes** de comprometer el ruteo del Incremento 4:
si un distrito tiene poca red vial registrada, el sistema no puede fingir que
calcula rutas reales allí y debe degradar a distancia en línea recta,
diciéndolo en la interfaz.

Qué se mide, y por qué eso y no otra cosa:

1. **Distancia de cada recurso al nodo de la red más cercano.** Es la pregunta
   que de verdad importa para rutear: si un recurso está a 3 km de la carretera
   más próxima registrada, ninguna ruta calculada sobre esa red llega hasta él.
2. **Nodos y aristas cerca de los recursos de cada distrito.** Da la densidad
   de la red donde se va a rutear, que no es lo mismo que la densidad media del
   distrito entero.

Se ejecuta desde ``backend/``:

    python -m app.utilidades.medir_cobertura_osm
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import osmnx as ox
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select

from app.base_datos import FabricaDeSesiones
from app.modelos.catalogo import RecursoTuristico

#: Dónde se guarda el resultado. Es evidencia del proyecto, no un cálculo
#: pasajero: la decisión de degradar a línea recta se apoya en estos números.
RUTA_DEL_INFORME = Path(__file__).resolve().parents[2] / "datos" / "cobertura_osm.json"

#: Radio alrededor de los recursos de un distrito dentro del cual se cuentan
#: nodos y aristas. Tres kilómetros es el orden de magnitud de un traslado a
#: pie entre recursos cercanos.
RADIO_DE_CONTEO_M = 3000

#: A partir de esta distancia al nodo más cercano, se considera que el recurso
#: NO está conectado a la red y hay que degradar a línea recta para llegar a él.
#: 500 m es una caminata de unos 7 minutos por terreno sin vía registrada.
UMBRAL_DE_DESCONEXION_M = 500

#: Margen que se añade al rectángulo de los recursos antes de descargar, para
#: que la red no quede cortada justo en el borde.
MARGEN_GRADOS = 0.05


@dataclass
class CoberturaDeDistrito:
    """Lo que se sabe de la red vial alrededor de los recursos de un distrito."""

    distrito: str
    provincia: str
    recursos: int
    nodos_cerca: int
    aristas_cerca: int
    distancia_mediana_m: float
    distancia_maxima_m: float
    recursos_desconectados: int

    @property
    def porcentaje_conectado(self) -> float:
        if self.recursos == 0:
            return 0.0
        return round(100 * (self.recursos - self.recursos_desconectados) / self.recursos, 1)

    @property
    def veredicto(self) -> str:
        """Qué se puede hacer con este distrito en el ruteo.

        - **buena**: todos sus recursos están sobre la red; se rutea de verdad.
        - **parcial**: alguno queda fuera; se rutea lo que se pueda y se avisa.
        - **pobre**: la mayoría queda fuera; se degrada a línea recta.
        """
        if self.recursos_desconectados == 0 and self.nodos_cerca >= 50:
            return "buena"
        if self.porcentaje_conectado >= 60:
            return "parcial"
        return "pobre"


def descargar_red_del_valle(limites: tuple[float, float, float, float]):
    """Descarga la red vial transitable del rectángulo indicado.

    Se pide ``network_type="all"`` y no ``"drive"`` porque en el valle muchos
    recursos se alcanzan por caminos de herradura y sendas que no admiten
    coche pero sí se caminan, y el ruteo los necesita.
    """
    ox.settings.log_console = False
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(Path("datos") / "cache_osm")
    ox.settings.requests_timeout = 600

    oeste, sur, este, norte = limites

    print(f"  Rectángulo: {sur:.3f}..{norte:.3f} lat, {oeste:.3f}..{este:.3f} lon")
    print("  Descargando de Overpass (puede tardar varios minutos)...")

    inicio = time.time()
    grafo = ox.graph_from_bbox(bbox=limites, network_type="all", simplify=True)

    print(f"  Descargada en {time.time() - inicio:.0f}s")
    print(f"    nodos  : {grafo.number_of_nodes():,}")
    print(f"    aristas: {grafo.number_of_edges():,}")

    return grafo


def medir() -> list[CoberturaDeDistrito]:
    """Mide la cobertura y devuelve una fila por distrito."""
    punto = cast(RecursoTuristico.ubicacion, Geometry)

    with FabricaDeSesiones() as sesion:
        filas = sesion.execute(
            select(
                RecursoTuristico.provincia,
                RecursoTuristico.distrito,
                func.ST_Y(punto),
                func.ST_X(punto),
            ).where(RecursoTuristico.ubicacion.is_not(None))
        ).all()

    if not filas:
        raise RuntimeError(
            "No hay recursos georreferenciados. Ejecuta antes "
            "python -m app.utilidades.cargar_catalogo"
        )

    latitudes = [f[2] for f in filas]
    longitudes = [f[3] for f in filas]

    limites = (
        min(longitudes) - MARGEN_GRADOS,
        min(latitudes) - MARGEN_GRADOS,
        max(longitudes) + MARGEN_GRADOS,
        max(latitudes) + MARGEN_GRADOS,
    )

    print(f"  Recursos georreferenciados: {len(filas)}")
    grafo = descargar_red_del_valle(limites)

    # Se proyecta a metros. Sin esto las distancias saldrían en grados, que no
    # son comparables entre sí: un grado de longitud mide distinto según la
    # latitud.
    print("  Proyectando la red a coordenadas métricas...")
    grafo_proyectado = ox.project_graph(grafo)

    return _medir_por_distrito(filas, grafo_proyectado)


def _medir_por_distrito(filas, grafo_proyectado) -> list[CoberturaDeDistrito]:
    """Calcula las métricas agrupando por distrito."""
    import geopandas as gpd
    from shapely.geometry import Point

    crs_metrico = grafo_proyectado.graph["crs"]

    # Los recursos se proyectan al mismo sistema métrico que la red.
    puntos = gpd.GeoSeries(
        [Point(lon, lat) for _, _, lat, lon in filas], crs="EPSG:4326"
    ).to_crs(crs_metrico)

    print("  Calculando distancias al nodo más cercano...")
    nodos, distancias = ox.nearest_nodes(
        grafo_proyectado,
        X=[p.x for p in puntos],
        Y=[p.y for p in puntos],
        return_dist=True,
    )

    # Posición de cada nodo de la red, para contar los que caen cerca.
    nodos_gdf = ox.graph_to_gdfs(grafo_proyectado, edges=False)

    por_distrito: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (provincia, distrito, _, _), distancia in zip(filas, distancias, strict=True):
        por_distrito[(provincia, distrito)].append(float(distancia))

    resultados: list[CoberturaDeDistrito] = []

    print("  Contando nodos y aristas alrededor de cada distrito...")
    for (provincia, distrito), distancias_del_distrito in sorted(por_distrito.items()):
        indices = [
            i
            for i, (p, d, _, _) in enumerate(filas)
            if p == provincia and d == distrito
        ]
        puntos_del_distrito = puntos.iloc[indices]

        # Nodos dentro del radio de cualquiera de sus recursos.
        area = puntos_del_distrito.buffer(RADIO_DE_CONTEO_M).union_all()
        dentro = nodos_gdf[nodos_gdf.geometry.within(area)]

        subgrafo = grafo_proyectado.subgraph(dentro.index)

        ordenadas = sorted(distancias_del_distrito)
        mediana = ordenadas[len(ordenadas) // 2]

        resultados.append(
            CoberturaDeDistrito(
                distrito=distrito,
                provincia=provincia,
                recursos=len(distancias_del_distrito),
                nodos_cerca=len(dentro),
                aristas_cerca=subgrafo.number_of_edges(),
                distancia_mediana_m=round(mediana, 1),
                distancia_maxima_m=round(max(distancias_del_distrito), 1),
                recursos_desconectados=sum(
                    1 for d in distancias_del_distrito if d > UMBRAL_DE_DESCONEXION_M
                ),
            )
        )

    return resultados


def main() -> int:
    print("=" * 92)
    print("COBERTURA DE OPENSTREETMAP EN EL VALLE DEL MANTARO")
    print("=" * 92)

    resultados = medir()

    print()
    print("=" * 92)
    print(
        f"{'DISTRITO':<24} {'PROVINCIA':<12} {'REC':>4} {'NODOS':>7} {'ARISTAS':>8} "
        f"{'MEDIANA':>8} {'MAXIMA':>8} {'DESCON':>7}  VEREDICTO"
    )
    print("=" * 92)

    for c in sorted(resultados, key=lambda x: (x.veredicto != "pobre", x.distrito)):
        print(
            f"{c.distrito[:23]:<24} {c.provincia[:11]:<12} {c.recursos:>4} "
            f"{c.nodos_cerca:>7} {c.aristas_cerca:>8} "
            f"{c.distancia_mediana_m:>7.0f}m {c.distancia_maxima_m:>7.0f}m "
            f"{c.recursos_desconectados:>7}  {c.veredicto}"
        )

    print("=" * 92)

    total_recursos = sum(c.recursos for c in resultados)
    total_desconectados = sum(c.recursos_desconectados for c in resultados)
    por_veredicto = defaultdict(int)
    for c in resultados:
        por_veredicto[c.veredicto] += 1

    print()
    print("RESUMEN")
    print(f"  Distritos evaluados          : {len(resultados)}")
    print(f"  Recursos georreferenciados   : {total_recursos}")
    print(
        f"  Recursos sobre la red        : {total_recursos - total_desconectados} "
        f"({100 * (total_recursos - total_desconectados) / total_recursos:.1f} %)"
    )
    print(f"  Recursos a más de {UMBRAL_DE_DESCONEXION_M} m       : {total_desconectados}")
    print()
    print(f"  Distritos con cobertura buena  : {por_veredicto['buena']}")
    print(f"  Distritos con cobertura parcial: {por_veredicto['parcial']}")
    print(f"  Distritos con cobertura pobre  : {por_veredicto['pobre']}")

    RUTA_DEL_INFORME.parent.mkdir(parents=True, exist_ok=True)
    RUTA_DEL_INFORME.write_text(
        json.dumps(
            {
                "medido_en": time.strftime("%Y-%m-%d %H:%M"),
                "umbral_de_desconexion_m": UMBRAL_DE_DESCONEXION_M,
                "radio_de_conteo_m": RADIO_DE_CONTEO_M,
                "distritos": [
                    {**asdict(c), "veredicto": c.veredicto,
                     "porcentaje_conectado": c.porcentaje_conectado}
                    for c in resultados
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"  Informe guardado en {RUTA_DEL_INFORME}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
