"""Objetos de valor de coordinacion.

Viven en el dominio y no en los modelos de SQLAlchemy porque no son una forma
de guardar datos: son parte de las reglas. El ORM los importa desde aqui, de
modo que la dependencia apunta hacia adentro.
"""

from __future__ import annotations

from enum import StrEnum


class TipoServicio(StrEnum):
    """Qué clase de servicio ofrece un proveedor.

    El conjunto sale de lo que necesita un visitante del valle para completar
    un itinerario: llegar, comer, dormir, entender lo que ve y llevárselo.
    """

    TRANSPORTE = "transporte"
    ALIMENTACION = "alimentacion"
    HOSPEDAJE = "hospedaje"
    GUIADO = "guiado"
    TALLER = "taller"
    ARTESANIA = "artesania"


class EstadoSolicitud(StrEnum):
    """Por dónde va una solicitud de coordinación.

    El orden importa: es el ciclo de vida que el indicador del incremento
    cuenta. ``ENVIADA`` y ``CONFIRMADA`` son los dos extremos que fija la
    verificación del plan de trabajo.
    """

    #: El visitante la mandó y el proveedor aún no la ha visto.
    ENVIADA = "enviada"
    #: El proveedor la leyó y está mirando si puede.
    EN_REVISION = "en_revision"
    #: El proveedor propone cambiar algo (hora, número de personas, precio).
    CONTRAPROPUESTA = "contrapropuesta"
    #: Acuerdo cerrado. Es el estado que persigue el indicador.
    CONFIRMADA = "confirmada"
    #: El proveedor no puede.
    RECHAZADA = "rechazada"
    #: El visitante se echó atrás.
    CANCELADA = "cancelada"
