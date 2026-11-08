"""Objetos de valor de transporte.

Viven en el dominio y no en los modelos de SQLAlchemy porque no son una forma
de guardar datos: son parte de las reglas. El ORM los importa desde aqui, de
modo que la dependencia apunta hacia adentro.
"""

from __future__ import annotations

from enum import StrEnum


class ModoTransporte(StrEnum):
    """Cómo se cubre un traslado entre dos puntos."""

    CAMINANDO = "caminando"
    COMBI = "combi"
    COLECTIVO = "colectivo"
    TAXI = "taxi"
