"""Objetos de valor de preferencias.

Viven en el dominio y no en los modelos de SQLAlchemy porque no son una forma
de guardar datos: son parte de las reglas. El ORM los importa desde aqui, de
modo que la dependencia apunta hacia adentro.
"""

from __future__ import annotations

from enum import StrEnum


class Ritmo(StrEnum):
    """A qué velocidad quiere viajar el visitante.

    Determina cuántas paradas cabe proponer en un día cuando el Incremento 4
    construya el itinerario.
    """

    RELAJADO = "relajado"
    MODERADO = "moderado"
    INTENSO = "intenso"


class Movilidad(StrEnum):
    """Cómo prefiere desplazarse el visitante entre un recurso y otro."""

    CAMINANDO = "caminando"
    TRANSPORTE_PUBLICO = "transporte_publico"
    TAXI = "taxi"
    COMBINADO = "combinado"


class Interes(StrEnum):
    """Los ocho intereses que puede declarar el visitante.

    Se eligieron para que se puedan enlazar con las categorías del inventario
    del MINCETUR en el Incremento 3: no son etiquetas decorativas, son la
    entrada del cálculo de afinidad.
    """

    NATURALEZA = "naturaleza"
    ARQUEOLOGIA = "arqueologia"
    IGLESIAS_CONVENTOS = "iglesias_conventos"
    ARTESANIA = "artesania"
    GASTRONOMIA = "gastronomia"
    FERIAS_FIESTAS = "ferias_fiestas"
    AVENTURA = "aventura"
    FOTOGRAFIA = "fotografia"
