"""Guion de línea de comandos para cargar y validar el catálogo.

Se ejecuta desde ``backend/`` con el entorno virtual activado:

    python -m app.utilidades.cargar_catalogo

O indicando otro archivo:

    python -m app.utilidades.cargar_catalogo --archivo ruta/al/inventario.csv

Hace dos cosas en orden: importa el inventario del MINCETUR y después ejecuta
la validación, que es la que produce el indicador del Incremento 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.base_datos import FabricaDeSesiones
from app.servicios.catalogo import importar_inventario
from app.servicios.validacion_catalogo import validar_catalogo

#: Ubicación por omisión del inventario descargado del MINCETUR.
RUTA_POR_OMISION = (
    Path(__file__).resolve().parents[2] / "datos" / "crudos" / "Inventario_recursos_turisticos.csv"
)


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Importa el inventario del MINCETUR y valida el catálogo."
    )
    analizador.add_argument(
        "--archivo",
        type=Path,
        default=RUTA_POR_OMISION,
        help="Ruta del CSV del inventario. Por omisión, backend/datos/crudos/.",
    )
    argumentos = analizador.parse_args()

    if not argumentos.archivo.exists():
        print(f"ERROR: no se encontró el archivo {argumentos.archivo}", file=sys.stderr)
        print(
            "Descárgalo de "
            "https://www.mincetur.gob.pe/Datos_abiertos/DGET/Inventario_recursos_turisticos.csv "
            "y colócalo en backend/datos/crudos/",
            file=sys.stderr,
        )
        return 1

    with FabricaDeSesiones() as sesion:
        print("=" * 70)
        print("IMPORTACIÓN DEL INVENTARIO DEL MINCETUR")
        print("=" * 70)

        importacion = importar_inventario(sesion, argumentos.archivo)

        print(f"  Archivo                        : {argumentos.archivo.name}")
        print(f"  Codificación detectada         : {importacion.codificacion_detectada}")
        print(f"  Filas en el archivo nacional   : {importacion.filas_en_el_archivo:,}")
        print(f"  Filas de la región Junín       : {importacion.filas_de_junin:,}")
        print(f"  Filas de las 4 provincias      : {importacion.filas_de_la_ruta:,}")
        print(f"  Recursos insertados            : {importacion.insertados}")
        print(f"  Recursos actualizados          : {importacion.actualizados}")
        print(f"  Sin coordenadas en la fuente   : {importacion.sin_coordenadas}")

        if importacion.coordenadas_estaban_intercambiadas:
            print("  Columnas lat/lon               : INTERCAMBIADAS en la fuente, corregidas")

        for advertencia in importacion.advertencias:
            print(f"  AVISO: {advertencia}")

        print()
        print("=" * 70)
        print("VALIDACIÓN DEL CATÁLOGO  —  indicador del Incremento 1")
        print("=" * 70)

        validacion = validar_catalogo(sesion)

        print(f"  Total de recursos              : {validacion.total_recursos}")
        print(f"  Validados                      : {validacion.validados}")
        print(f"  Vigentes                       : {validacion.vigentes}")
        print(f"  Con coordenadas                : {validacion.con_coordenadas}")
        print(f"  PORCENTAJE VALIDADO            : {validacion.porcentaje_validado} %")

        if validacion.motivos_frecuentes:
            print()
            print("  Motivos de rechazo, por frecuencia:")
            for motivo, cantidad in validacion.motivos_frecuentes.items():
                print(f"    {cantidad:>4}  {motivo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
