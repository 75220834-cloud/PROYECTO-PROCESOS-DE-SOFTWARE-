"""Prepara el grafo de la red vial del valle y lo guarda listo para usar.

Se ejecuta una sola vez desde ``backend/``:

    python -m app.utilidades.preparar_red_vial

Junta lo que ya se descargó por separado —la red de OpenStreetMap y las
teselas de elevación de Copernicus— en un solo archivo con el grafo y la
altitud de cada nodo. A partir de ahí, el ruteo funciona sin internet y sin
volver a muestrear nada.

El archivo resultante NO se sube al repositorio: pesa cientos de megas y se
reconstruye con este comando.
"""

from __future__ import annotations

import time

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select

from app.base_datos import FabricaDeSesiones
from app.modelos.catalogo import RecursoTuristico
from app.servicios.red_vial import RUTA_DEL_GRAFO, construir_y_guardar

#: Margen que se añade al rectángulo de los recursos, en grados. Sin él, un
#: recurso pegado al borde se quedaría sin las vías que lo conectan con el
#: resto. 0,05° son unos 5,5 km. Es el mismo valor que usó la medición de
#: cobertura, para que el grafo sea exactamente el que se midió.
MARGEN_GRADOS = 0.05


def main() -> int:
    print("=" * 74)
    print("PREPARACIÓN DE LA RED VIAL DEL VALLE DEL MANTARO")
    print("=" * 74)

    punto = cast(RecursoTuristico.ubicacion, Geometry)

    with FabricaDeSesiones() as sesion:
        filas = sesion.execute(
            select(func.ST_Y(punto), func.ST_X(punto)).where(
                RecursoTuristico.ubicacion.is_not(None)
            )
        ).all()

    if not filas:
        print("No hay recursos georreferenciados. Ejecuta antes cargar_catalogo.")
        return 1

    latitudes = [f[0] for f in filas]
    longitudes = [f[1] for f in filas]

    limites = (
        min(longitudes) - MARGEN_GRADOS,
        min(latitudes) - MARGEN_GRADOS,
        max(longitudes) + MARGEN_GRADOS,
        max(latitudes) + MARGEN_GRADOS,
    )

    print(f"  Recursos georreferenciados : {len(filas)}")
    print(
        f"  Rectángulo                 : "
        f"lat {limites[1]:.4f} a {limites[3]:.4f}, "
        f"lon {limites[0]:.4f} a {limites[2]:.4f}"
    )
    print()
    print("  Construyendo el grafo y muestreando altitudes...")
    print("  (la red ya está en caché; lo lento ahora es muestrear 40 000 nodos)")

    inicio = time.time()
    red = construir_y_guardar(limites)
    tardanza = time.time() - inicio

    nodos = red.grafo.number_of_nodes()
    aristas = red.grafo.number_of_edges()
    con_altitud = sum(1 for nodo in red.grafo.nodes if red.altitud_del_nodo(nodo) is not None)

    tamano_mb = RUTA_DEL_GRAFO.stat().st_size / 1_048_576

    print()
    print("=" * 74)
    print("RESULTADO")
    print("=" * 74)
    print(f"  Nodos              : {nodos:,}")
    print(f"  Aristas            : {aristas:,}")
    print(f"  Nodos con altitud  : {con_altitud:,} ({con_altitud / nodos:.1%})")
    print(f"  Archivo            : {RUTA_DEL_GRAFO.name}  ({tamano_mb:.1f} MB)")
    print(f"  Tardanza           : {tardanza:.0f} s")

    if con_altitud < nodos:
        print()
        print(f"  AVISO: {nodos - con_altitud:,} nodos se quedaron sin altitud.")
        print("  Los tramos que los usen se calcularán como si fueran llanos.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
