"""Esquemas de la recomendación inteligente (Incremento 3)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SolicitudRecomendacion(BaseModel):
    """Petición de recomendaciones para una preferencia ya guardada."""

    preferencia_id: int
    limite: int = Field(default=20, ge=1, le=60)


class AfluenciaEstimada(BaseModel):
    """Cuánta gente se espera, y por qué.

    El motivo no es decorativo: sin él, «mucha gente» es una afirmación que el
    visitante no puede comprobar ni discutir.
    """

    nivel: Literal["bajo", "medio", "alto"]
    motivo: str
    festividades: list[str] = Field(default_factory=list)
    calculado_por: Literal["modelo", "reglas"]


class RecomendacionPublica(BaseModel):
    """Un recurso recomendado, con la explicación de por qué lo fue."""

    recurso_id: int
    nombre: str
    provincia: str
    distrito: str
    categoria: str | None = None

    latitud: float | None = None
    longitud: float | None = None
    distancia_km: float | None = None

    #: Entre 0 y 1. Es la similitud coseno en bruto. Se expone para poder
    #: auditar el cálculo, no para mostrarla: no significa nada por sí sola.
    puntaje_afinidad: float

    #: De 0 a 100, tomando como 100 el mejor resultado de esta misma búsqueda.
    #: Es lo que se muestra al visitante. **No es una probabilidad ni un
    #: porcentaje absoluto**: dice cuánto encaja este recurso comparado con el
    #: que mejor encaja de los encontrados.
    puntaje_relativo: int

    #: Los términos que más pesaron en el puntaje. Es lo que hace auditable la
    #: recomendación: el visitante puede ver qué palabras la provocaron.
    terminos_decisivos: list[str] = Field(default_factory=list)

    #: Qué intereses declarados satisface este recurso.
    intereses_cubiertos: list[str] = Field(default_factory=list)

    afluencia: AfluenciaEstimada

    #: 'modelo' o 'reglas'. Trazabilidad de la regla de oro de la IA.
    generado_por: Literal["modelo", "reglas"]


class RecursoDescartadoPublico(BaseModel):
    """Un recurso que no pasó los filtros duros, con su motivo."""

    recurso_id: int
    nombre: str
    motivo: str


class RespuestaRecomendacion(BaseModel):
    """Todo lo que devuelve una recomendación.

    Incluye a propósito lo que se descartó y por qué: es lo que permite
    explicarle al visitante por qué no ve un sitio que esperaba, y lo que
    convierte el proceso en auditable en vez de en una caja negra.
    """

    preferencia_id: int
    fecha_de_referencia: date

    generado_por: Literal["modelo", "reglas"]
    total_evaluados: int
    total_recomendados: int
    total_descartados: int

    recomendaciones: list[RecomendacionPublica]

    #: Se limita la lista de descartes: son decenas y el frontend solo muestra
    #: un resumen. El conteo completo va en total_descartados.
    descartados: list[RecursoDescartadoPublico] = Field(default_factory=list)

    avisos: list[str] = Field(default_factory=list)


class FestividadPublica(BaseModel):
    """Una festividad del calendario del valle."""

    nombre: str
    fecha_inicio: date
    fecha_fin: date
    tipo: str
    distritos: list[str] = Field(default_factory=list)
    es_movil: bool
    fuente: str


class CalendarioPublico(BaseModel):
    """Las festividades de un año."""

    anio: int
    total: int
    festividades: list[FestividadPublica]
