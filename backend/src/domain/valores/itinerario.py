"""Objetos de valor de itinerario.

Viven en el dominio y no en los modelos de SQLAlchemy porque no son una forma
de guardar datos: son parte de las reglas. El ORM los importa desde aqui, de
modo que la dependencia apunta hacia adentro.
"""

from __future__ import annotations

from enum import StrEnum


class EstadoItinerario(StrEnum):
    """En qué punto del proceso está un itinerario."""

    BORRADOR = "borrador"
    GUARDADO = "guardado"
    CONFIRMADO = "confirmado"
    COMPLETADO = "completado"


class OrigenDelCalculo(StrEnum):
    """Cómo se calculó un tramo, y por tanto cuánto fiarse de él.

    Es la distinción que exige la medición de cobertura de OSM: en los
    distritos donde no hay red vial registrada, el tiempo es una estimación
    sobre línea recta y **el visitante tiene que saberlo**.
    """

    #: Ruta calculada sobre el grafo real de OpenStreetMap.
    RED_VIAL = "red_vial"
    #: Línea recta corregida por el factor de rodeo medido (1,26).
    LINEA_RECTA = "linea_recta"
