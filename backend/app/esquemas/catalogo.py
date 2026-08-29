"""Esquemas de entrada y salida del catálogo de recursos turísticos."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RecursoResumen(BaseModel):
    """Datos de un recurso para el listado en tarjetas.

    Se devuelve una versión reducida a propósito: el listado puede traer
    cientos de recursos y mandar la descripción completa de cada uno haría la
    respuesta innecesariamente pesada.
    """

    id: int
    codigo_mincetur: str
    nombre: str
    provincia: str
    distrito: str
    categoria: str | None = None
    tipo: str | None = None

    latitud: float | None = None
    longitud: float | None = None

    esta_validado: bool
    esta_vigente: bool
    fecha_corte: date | None = None

    foto_url: str | None = None


class RecursoDetalle(RecursoResumen):
    """Todos los datos de un recurso, para la página de detalle."""

    subtipo: str | None = None
    url_ficha: str | None = None
    altitud_msnm: int | None = None
    descripcion_es: str | None = None
    descripcion_en: str | None = None
    duracion_visita_min: int | None = None
    motivos_invalidez: str | None = None


class PaginaDeRecursos(BaseModel):
    """Una página del listado de recursos.

    Se devuelve el total además de los elementos para que el frontend pueda
    dibujar el paginador sin tener que pedir el conteo aparte.
    """

    total: int = Field(description="Recursos que cumplen los filtros, no solo los de esta página")
    pagina: int
    tamano_pagina: int
    elementos: list[RecursoResumen]


class GeometriaPunto(BaseModel):
    """Geometría de un punto en formato GeoJSON."""

    type: Literal["Point"] = "Point"
    # GeoJSON exige el orden [longitud, latitud]. Es al revés de como se dice
    # en el habla común ("latitud y longitud"), y es un error frecuente.
    coordinates: tuple[float, float]


class RasgoGeoJSON(BaseModel):
    """Un recurso turístico expresado como rasgo («feature») de GeoJSON."""

    type: Literal["Feature"] = "Feature"
    geometry: GeometriaPunto
    properties: dict[str, Any]


class ColeccionGeoJSON(BaseModel):
    """Colección de rasgos GeoJSON, lista para pintar en el mapa.

    Se usa GeoJSON y no un formato propio porque es el estándar que entienden
    Leaflet y prácticamente cualquier herramienta geográfica, sin conversión.
    """

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[RasgoGeoJSON]


class IndicadorCatalogo(BaseModel):
    """Indicador del Incremento 1: oferta con información validada y vigente."""

    fecha: datetime
    total_recursos: int
    validados: int
    vigentes: int
    con_coordenadas: int
    porcentaje_validado: float

    # Se añaden los porcentajes derivados para que el frontend no tenga que
    # calcularlos, y así el número que se muestra sea siempre el mismo que el
    # que se guardó.
    porcentaje_vigente: float
    porcentaje_con_coordenadas: float


class ResumenFiltros(BaseModel):
    """Valores disponibles para poblar los desplegables de filtro."""

    provincias: list[str]
    distritos: list[str]
    categorias: list[str]
