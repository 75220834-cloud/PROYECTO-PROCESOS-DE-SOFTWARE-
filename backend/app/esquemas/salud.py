"""Esquemas de la respuesta del endpoint de salud.

Un esquema de Pydantic describe la forma exacta de los datos que entran o
salen de la API. FastAPI lo usa para validar, para serializar a JSON y para
generar la documentacion automatica en /docs.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Un componente puede estar operativo, caido, o no configurado todavia.
EstadoComponente = Literal["operativo", "no_disponible"]


class SaludComponente(BaseModel):
    """Estado de uno de los componentes de los que depende la plataforma."""

    estado: EstadoComponente
    detalle: str = Field(description="Version, mensaje de error o dato util para diagnosticar")


class SaludGeneral(BaseModel):
    """Respuesta completa de GET /api/salud."""

    aplicacion: str
    version: str
    entorno: str
    estado_general: Literal["operativo", "degradado"] = Field(
        description="Es 'degradado' si algun componente no responde"
    )
    api: SaludComponente
    base_datos: SaludComponente
    ollama: SaludComponente
