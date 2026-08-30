"""Si un recurso está «en temporada» para las fechas de un viaje.

## El problema que resuelve

36 de los 295 recursos del catálogo **son fiestas**: la Tunantada, el Carnaval
Jaujino, la Fiesta del Tayta Niño. Hasta ahora el sistema los trataba como si
fueran una plaza o un mirador —algo que está ahí todo el año— y podía meter la
Tunantada en un itinerario de mayo. La Tunantada es del 18 al 20 de enero.

No es un detalle estético: es proponerle a alguien que viaje a un pueblo a ver
algo que no va a estar.

## Por qué solo se comparan meses

Las fichas del MINCETUR dan la fecha en prosa, y muchas veces esa prosa no se
puede convertir en un rango exacto sin inventar:

- «el último domingo de enero»
- «fecha móvil entre marzo y abril»
- «el primer domingo de octubre»

Convertirlas a días concretos exigiría calcular el calendario litúrgico de
cada año y adivinar a qué se refieren las que no lo dicen. Comparar meses es
grueso, pero es **cierto**: si la fiesta es de enero y el viaje es de mayo, no
coincide, y eso basta para avisar.

## Qué se hace con el resultado

**No se esconde el recurso.** Se enseña con su fecha y un aviso en rojo de que
no cae dentro del viaje. Esconderlo dejaría al visitante sin saber que esa
fiesta existe; enseñarlo con su fecha le permite mover el viaje si le interesa.
"""

from __future__ import annotations

from datetime import date


def meses_del_viaje(inicio: date, fin: date) -> set[int]:
    """Los meses que toca un viaje, del 1 al 12.

    Un viaje del 28 de enero al 2 de febrero toca los dos meses, y hay que
    contar los dos: una fiesta de febrero sí cae dentro de ese viaje.
    """
    if fin < inicio:
        inicio, fin = fin, inicio

    meses: set[int] = set()
    anio, mes = inicio.year, inicio.month

    # Se avanza mes a mes en vez de restar fechas para que un viaje que cruza
    # el fin de año —diciembre a enero— no se salte nada.
    while (anio, mes) <= (fin.year, fin.month):
        meses.add(mes)
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)

    return meses


def esta_en_temporada(
    meses_de_celebracion: list[int] | None,
    meses_del_viaje_: set[int],
) -> bool | None:
    """Si la fiesta cae dentro del viaje.

    Devuelve:

    - ``None`` cuando **no aplica**: el recurso no es una fiesta, o su ficha no
      precisa cuándo se celebra. Se distingue de ``False`` a propósito: «no
      sabemos» y «sabemos que no» son cosas distintas, y avisar en rojo de algo
      que no sabemos sería mentir.
    - ``True`` si algún mes de la fiesta cae dentro del viaje.
    - ``False`` si ninguno.
    """
    if not meses_de_celebracion:
        return None

    return bool(set(meses_de_celebracion) & meses_del_viaje_)
