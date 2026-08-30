"""Esquemas de la valoración de cierre y la evidencia (Incremento 6)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modelos.valoracion import PUNTUACION_MAXIMA, PUNTUACION_MINIMA

SentimientoLiteral = Literal["positivo", "neutro", "negativo"]

TemaLiteral = Literal[
    "limpieza",
    "atencion",
    "precio",
    "acceso",
    "senalizacion",
    "seguridad",
    "comida",
    "paisaje",
    "infraestructura",
]


class ValoracionNueva(BaseModel):
    """Lo que el visitante manda al cerrar su itinerario."""

    itinerario_id: int

    puntuacion: int = Field(ge=PUNTUACION_MINIMA, le=PUNTUACION_MAXIMA)
    comentario: str | None = Field(default=None, max_length=4000)

    #: Recurso concreto, si se valora uno. Nulo si es del día completo.
    recurso_id: int | None = None
    #: Servicio coordinado, si se valora uno. Es lo que enlaza con el
    #: Incremento 5: se puede valorar el almuerzo que se reservó.
    servicio_id: int | None = None


class ValoracionPublica(BaseModel):
    """Una valoración con lo que la persona puso y lo que el sistema entendió."""

    id: int
    itinerario_id: int
    recurso_id: int | None = None
    recurso_nombre: str | None = None
    servicio_id: int | None = None
    servicio_nombre: str | None = None

    # --- Lo que la persona puso -------------------------------------------
    puntuacion: int
    comentario: str | None = None

    # --- Lo que el sistema entendió ---------------------------------------
    #: Nulo si no había comentario que leer: una puntuación sola no tiene
    #: sentimiento, tiene número.
    sentimiento: SentimientoLiteral | None = None
    confianza_sentimiento: float | None = None
    temas: list[str] = Field(default_factory=list)

    #: `modelo` o `reglas`. La trazabilidad de la regla de oro de la IA.
    analizado_por: Literal["modelo", "reglas"] | None = None
    version_del_analisis: str | None = None

    creado_en: datetime


class DistribucionPublica(BaseModel):
    """Cuántas valoraciones hay de cada signo."""

    positivas: int
    neutras: int
    negativas: int
    total: int
    #: Nulo si no hay valoraciones: un porcentaje de cero casos no es cero.
    porcentaje_positivo: float | None = None


class TemaPublico(BaseModel):
    """Cuánto se menciona un tema, y con qué signo."""

    tema: str
    menciones: int
    positivas: int
    neutras: int
    negativas: int
    #: El número que dice DÓNDE actuar: un tema muy mencionado y negativo es un
    #: problema; uno muy mencionado y positivo es una fortaleza.
    porcentaje_negativo: float | None = None


class RecursoValoradoPublico(BaseModel):
    """Un recurso con su valoración media."""

    recurso_id: int
    nombre: str
    distrito: str
    total_valoraciones: int
    puntuacion_media: float
    temas_frecuentes: list[str] = Field(default_factory=list)
    #: `false` cuando tiene menos valoraciones de las que hacen falta para que
    #: la media signifique algo. La interfaz lo marca en vez de esconderlo.
    es_fiable: bool


class PuntoEnElTiempoPublico(BaseModel):
    """La media de un mes, para dibujar la evolución."""

    periodo: str
    total: int
    puntuacion_media: float
    positivas: int
    negativas: int


class ResumenDeEvidenciaPublico(BaseModel):
    """Todo lo que el tablero del gestor necesita."""

    # --- El indicador del Incremento 6 ------------------------------------
    total_itinerarios: int
    itinerarios_con_valoracion: int
    porcentaje_con_valoracion: float

    total_valoraciones: int
    con_comentario: int
    puntuacion_media: float | None = None

    sentimiento: DistribucionPublica
    temas: list[TemaPublico] = Field(default_factory=list)

    mejor_valorados: list[RecursoValoradoPublico] = Field(default_factory=list)
    peor_valorados: list[RecursoValoradoPublico] = Field(default_factory=list)

    evolucion: list[PuntoEnElTiempoPublico] = Field(default_factory=list)

    analizadas_por_modelo: int
    analizadas_por_reglas: int

    #: Avisos sobre la fiabilidad de lo que se está mostrando. Un tablero que no
    #: dice cuándo sus números son frágiles invita a decidir sobre nada.
    avisos: list[str] = Field(default_factory=list)


class IndicadorDelIncremento(BaseModel):
    """Un indicador cualquiera, en la forma en que lo muestra el tablero.

    Existe para que los seis incrementos se puedan enseñar juntos aunque cada
    uno mida algo distinto. El campo ``valor`` es un texto y no un número
    porque algunos son porcentajes, otros conteos y otros medias, y forzarlos
    todos a `float` obligaría a la interfaz a saber cuál es cuál.
    """

    incremento: int
    nombre: str
    #: Qué brecha del análisis cierra.
    brecha: str
    valor: str
    #: Contexto para entender el valor. Por ejemplo «234 de 295 recursos».
    detalle: str | None = None
    #: `null` cuando el indicador todavía no se puede medir. Se distingue de
    #: cero: cero es una medición, `null` es la ausencia de una.
    hay_dato: bool = True
    #: Lo que este indicador NO dice. Va en el propio dato para que no se pueda
    #: leer el número sin su salvedad.
    salvedad: str | None = None


class TableroDeIndicadores(BaseModel):
    """Los seis indicadores del proyecto en un solo lugar."""

    indicadores: list[IndicadorDelIncremento] = Field(default_factory=list)
    generado_en: datetime
