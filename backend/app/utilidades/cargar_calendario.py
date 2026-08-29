"""Vuelca el calendario festivo calculado en la tabla ``festividad``.

Se ejecuta desde ``backend/``:

    python -m app.utilidades.cargar_calendario --desde 2026 --hasta 2028

Es idempotente: la restricción de unicidad sobre (nombre, fecha_inicio,
distrito) impide duplicar al volver a ejecutarlo.

**Hay que ejecutarlo una vez por cada año que se quiera tener cargado.** Las
fiestas móviles cambian de fecha cada año, así que no basta con cargarlas una
vez y olvidarse. El código de ``app/ia/calendario.py`` las calcula al vuelo
para las predicciones; la tabla existe para poder consultarlas en SQL y para
que un gestor pueda añadir fiestas locales que no estén en la lista.
"""

from __future__ import annotations

import argparse
from datetime import date

from sqlalchemy import select

from app.base_datos import FabricaDeSesiones
from app.ia.calendario import calendario_del_anio
from app.modelos.afluencia import Festividad


def cargar_anio(sesion, anio: int) -> tuple[int, int]:
    """Carga las fiestas de un año. Devuelve (insertadas, ya existentes)."""
    insertadas = 0
    existentes = 0

    for festividad in calendario_del_anio(anio):
        # Una fiesta sin distritos declarados se guarda como una sola fila con
        # distrito nulo, que significa «todo el valle». Una con varios
        # distritos se guarda una vez por distrito, para poder consultarla.
        distritos: tuple[str | None, ...] = festividad.distritos or (None,)

        for distrito in distritos:
            ya_esta = sesion.scalars(
                select(Festividad).where(
                    Festividad.nombre == festividad.nombre,
                    Festividad.fecha_inicio == festividad.fecha_inicio,
                    (
                        Festividad.distrito.is_(distrito)
                        if distrito is None
                        else Festividad.distrito == distrito
                    ),
                )
            ).first()

            if ya_esta is not None:
                existentes += 1
                continue

            sesion.add(
                Festividad(
                    nombre=festividad.nombre,
                    distrito=distrito,
                    fecha_inicio=festividad.fecha_inicio,
                    fecha_fin=festividad.fecha_fin,
                    es_movil=festividad.es_movil,
                    tipo=festividad.tipo.value,
                    fuente=festividad.fuente,
                )
            )
            insertadas += 1

    sesion.commit()
    return insertadas, existentes


def main() -> int:
    anio_actual = date.today().year

    analizador = argparse.ArgumentParser(
        description="Carga el calendario festivo del Valle del Mantaro en la base de datos."
    )
    analizador.add_argument("--desde", type=int, default=anio_actual)
    analizador.add_argument("--hasta", type=int, default=anio_actual + 2)
    argumentos = analizador.parse_args()

    print("=" * 70)
    print("CALENDARIO FESTIVO DEL VALLE DEL MANTARO")
    print("=" * 70)

    total_insertadas = 0

    with FabricaDeSesiones() as sesion:
        for anio in range(argumentos.desde, argumentos.hasta + 1):
            insertadas, existentes = cargar_anio(sesion, anio)
            total_insertadas += insertadas
            print(f"  {anio}:  {insertadas:>3} insertadas   {existentes:>3} ya existían")

        print()
        print("  Fiestas móviles cargadas (calculadas con el algoritmo de la Pascua):")

        moviles = sesion.scalars(
            select(Festividad)
            .where(Festividad.es_movil.is_(True))
            .order_by(Festividad.fecha_inicio)
        ).all()

        for festividad in moviles:
            rango = (
                f"{festividad.fecha_inicio}"
                if festividad.fecha_inicio == festividad.fecha_fin
                else f"{festividad.fecha_inicio} a {festividad.fecha_fin}"
            )
            print(f"    {festividad.nombre:<18} {rango}")

    print()
    print(f"  Total insertadas en esta ejecución: {total_insertadas}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
