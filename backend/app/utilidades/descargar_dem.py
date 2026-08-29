"""Descarga las teselas de elevación que cubren el Valle del Mantaro.

Se ejecuta una sola vez desde ``backend/``:

    python -m app.utilidades.descargar_dem

Después el cálculo de pendientes funciona sin internet, que es lo que exige la
restricción de conectividad limitada del proyecto.
"""

from __future__ import annotations

import time

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select

from app.base_datos import FabricaDeSesiones
from app.modelos.catalogo import RecursoTuristico
from app.servicios.elevacion import (
    MuestreadorDeAltitud,
    descargar_tesela,
    nombre_de_tesela,
    ruta_local_de_tesela,
    teselas_necesarias,
)

#: Altitudes verificadas en CONTEXTO_PROYECTO.md, sección 9. Sirven para
#: comprobar que el modelo descargado da valores creíbles antes de fiarse de
#: él para calcular pendientes.
ALTITUDES_DE_REFERENCIA = [
    ("Plaza Constitución, Huancayo", -12.0681, -75.2100, 3250),
    ("Plaza de Armas, Jauja", -11.7756, -75.4989, 3390),
    ("Plaza de Chupaca", -12.0592, -75.2867, 3263),
    ("Convento de Santa Rosa de Ocopa", -11.8740, -75.2944, 3360),
]

#: Cuánto se admite que se desvíe el modelo de la altitud publicada. GLO-30 es
#: un modelo de superficie con celda de 30 m: en zona urbana incluye tejados, y
#: las altitudes publicadas suelen ser de un punto concreto de la plaza.
TOLERANCIA_M = 60


def main() -> int:
    print("=" * 74)
    print("MODELO DE ELEVACIÓN COPERNICUS GLO-30")
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

    limites = (min(longitudes), min(latitudes), max(longitudes), max(latitudes))
    centros = teselas_necesarias(limites)

    print(f"  Recursos a cubrir : {len(filas)}")
    print(f"  Teselas necesarias: {len(centros)}")
    print()

    for latitud, longitud in centros:
        etiqueta_lat, etiqueta_lon = nombre_de_tesela(latitud, longitud)
        destino = ruta_local_de_tesela(latitud, longitud)

        if destino.exists():
            tamano = destino.stat().st_size / 1_048_576
            print(f"  ya estaba  {etiqueta_lat}/{etiqueta_lon}   {tamano:.1f} MB")
            continue

        print(f"  descargando {etiqueta_lat}/{etiqueta_lon} ...", end="", flush=True)
        inicio = time.time()

        try:
            ruta = descargar_tesela(latitud, longitud)
            tamano = ruta.stat().st_size / 1_048_576
            print(f" {tamano:.1f} MB en {time.time() - inicio:.0f}s")
        except Exception as error:  # noqa: BLE001
            print(f" FALLÓ: {type(error).__name__}: {str(error)[:80]}")

    print()
    print("=" * 74)
    print("COMPROBACIÓN CONTRA ALTITUDES PUBLICADAS")
    print("=" * 74)

    fallos = 0

    with MuestreadorDeAltitud() as muestreador:
        for nombre, latitud, longitud, publicada in ALTITUDES_DE_REFERENCIA:
            medida = muestreador.altitud(latitud, longitud)

            if medida is None:
                print(f"  SIN DATO  {nombre}")
                fallos += 1
                continue

            diferencia = medida - publicada
            correcta = abs(diferencia) <= TOLERANCIA_M
            if not correcta:
                fallos += 1

            print(
                f"  {'OK   ' if correcta else 'FALLA'} {nombre[:38]:<40} "
                f"modelo {medida:>6.0f} m   publicada {publicada} m   "
                f"diferencia {diferencia:+.0f} m"
            )

        print()
        print(
            f"  Dentro de la tolerancia de ±{TOLERANCIA_M} m: "
            f"{len(ALTITUDES_DE_REFERENCIA) - fallos} de {len(ALTITUDES_DE_REFERENCIA)}"
        )

        print()
        print("=" * 74)
        print("ALTITUD DE LOS RECURSOS DEL CATÁLOGO")
        print("=" * 74)

        # Se guarda la altitud de cada recurso en el catálogo. La columna
        # existía desde la Fase 1 pero estaba vacía: el inventario del MINCETUR
        # no publica altitudes, así que hasta ahora no había con qué llenarla.
        print("  Guardando la altitud de cada recurso en el catálogo...")

        with FabricaDeSesiones() as sesion:
            recursos = sesion.scalars(
                select(RecursoTuristico).where(RecursoTuristico.ubicacion.is_not(None))
            ).all()

            coordenadas = sesion.execute(
                select(RecursoTuristico.id, func.ST_Y(punto), func.ST_X(punto)).where(
                    RecursoTuristico.ubicacion.is_not(None)
                )
            ).all()

            por_id = {
                id_recurso: muestreador.altitud(lat, lon) for id_recurso, lat, lon in coordenadas
            }

            actualizados = 0
            for recurso in recursos:
                altitud = por_id.get(recurso.id)
                if altitud is not None:
                    recurso.altitud_msnm = round(altitud)
                    actualizados += 1

            sesion.commit()

        print(f"  Altitud guardada en {actualizados} recursos")
        print()

        altitudes = [
            a for a in muestreador.altitudes([(lat, lon) for lat, lon in filas]) if a is not None
        ]

        if altitudes:
            altitudes.sort()
            print(f"  Recursos con altitud : {len(altitudes)} de {len(filas)}")
            print(f"  Mínima               : {altitudes[0]:.0f} m")
            print(f"  Mediana              : {altitudes[len(altitudes) // 2]:.0f} m")
            print(f"  Máxima               : {altitudes[-1]:.0f} m")
            print()
            print("  El valle está entre 3 240 y 3 400 m; los recursos por encima")
            print("  de eso son de la puna y las alturas circundantes.")

    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
