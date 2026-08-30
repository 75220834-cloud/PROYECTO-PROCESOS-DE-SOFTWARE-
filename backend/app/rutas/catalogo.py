"""Endpoints del catálogo de recursos turísticos (Incremento 1).

- ``GET /api/recursos``            listado con filtros y paginación
- ``GET /api/recursos/filtros``    valores disponibles para los desplegables
- ``GET /api/recursos/mapa``       GeoJSON para pintar el mapa
- ``GET /api/recursos/{id}``       detalle de un recurso
- ``GET /api/indicadores/catalogo`` indicador del Incremento 1
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, distinct, func, select
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.esquemas.catalogo import (
    ColeccionGeoJSON,
    GeometriaPunto,
    IndicadorCatalogo,
    PaginaDeRecursos,
    RasgoGeoJSON,
    RecursoDetalle,
    RecursoResumen,
    ResumenFiltros,
)
from app.modelos.catalogo import RecursoTuristico
from app.servicios.validacion_catalogo import obtener_ultimo_registro

enrutador = APIRouter(prefix="/api", tags=["catalogo"])

SesionBD = Annotated[Session, Depends(obtener_sesion)]

#: Tope de elementos por página. Evita que una petición pida los 295 recursos
#: con sus descripciones y sature la respuesta.
TAMANO_MAXIMO_DE_PAGINA = 100


def _punto(columna=RecursoTuristico.ubicacion):
    """Convierte la columna geográfica a geometría, que es lo que aceptan ST_X y ST_Y."""
    return cast(columna, Geometry)


def _aplicar_filtros(
    consulta: Select,
    provincia: str | None,
    distrito: str | None,
    categoria: str | None,
    texto: str | None,
    solo_validados: bool,
) -> Select:
    """Añade a la consulta las condiciones de filtrado que vengan informadas.

    Se construye la consulta de forma incremental en vez de escribir SQL a
    mano: SQLAlchemy escapa los valores, así que no hay forma de inyectar SQL
    a través de estos parámetros.
    """
    if provincia:
        consulta = consulta.where(RecursoTuristico.provincia == provincia.strip().upper())

    if distrito:
        consulta = consulta.where(RecursoTuristico.distrito == distrito.strip().upper())

    if categoria:
        consulta = consulta.where(RecursoTuristico.categoria == categoria.strip())

    if texto:
        # unaccent quita las tildes de ambos lados de la comparación: así
        # "concepcion" encuentra "Concepción" y al revés. ilike hace que no
        # distinga mayúsculas.
        patron = f"%{texto.strip()}%"
        consulta = consulta.where(
            func.unaccent(RecursoTuristico.nombre).ilike(func.unaccent(patron))
        )

    if solo_validados:
        consulta = consulta.where(RecursoTuristico.esta_validado.is_(True))

    return consulta


def _a_resumen(recurso: RecursoTuristico, latitud: float | None, longitud: float | None):
    """Convierte una fila de la base de datos al esquema de salida."""
    return RecursoResumen(
        id=recurso.id,
        codigo_mincetur=recurso.codigo_mincetur,
        nombre=recurso.nombre,
        provincia=recurso.provincia,
        distrito=recurso.distrito,
        categoria=recurso.categoria,
        tipo=recurso.tipo,
        latitud=latitud,
        longitud=longitud,
        esta_validado=recurso.esta_validado,
        esta_vigente=recurso.esta_vigente,
        fecha_corte=recurso.fecha_corte,
        foto_url=recurso.foto_url,
    )


@enrutador.get("/recursos", response_model=PaginaDeRecursos, summary="Lista recursos turísticos")
def listar_recursos(
    sesion: SesionBD,
    provincia: str | None = Query(None, description="Nombre de la provincia, sin tildes"),
    distrito: str | None = Query(None, description="Nombre del distrito, sin tildes"),
    categoria: str | None = Query(None, description="Categoría del inventario del MINCETUR"),
    texto: str | None = Query(None, description="Busca en el nombre del recurso"),
    solo_validados: bool = Query(False, description="Devuelve solo los que pasaron la validación"),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(24, ge=1, le=TAMANO_MAXIMO_DE_PAGINA),
) -> PaginaDeRecursos:
    """Devuelve una página de recursos que cumplen los filtros indicados."""
    condiciones = _aplicar_filtros(
        select(RecursoTuristico), provincia, distrito, categoria, texto, solo_validados
    )

    # El total se cuenta sobre la misma consulta filtrada, sin traer las filas.
    total = sesion.scalar(select(func.count()).select_from(condiciones.subquery()))

    punto = _punto()
    consulta = (
        _aplicar_filtros(
            select(
                RecursoTuristico,
                func.ST_Y(punto).label("latitud"),
                func.ST_X(punto).label("longitud"),
            ),
            provincia,
            distrito,
            categoria,
            texto,
            solo_validados,
        )
        .order_by(RecursoTuristico.provincia, RecursoTuristico.nombre)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
    )

    elementos = [
        _a_resumen(recurso, latitud, longitud)
        for recurso, latitud, longitud in sesion.execute(consulta)
    ]

    return PaginaDeRecursos(
        total=total or 0,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
        elementos=elementos,
    )


@enrutador.get(
    "/recursos/filtros", response_model=ResumenFiltros, summary="Valores para los filtros"
)
def obtener_filtros(sesion: SesionBD) -> ResumenFiltros:
    """Devuelve las provincias, distritos y categorías que existen en el catálogo.

    Se sacan de los datos y no de una lista fija en el código: si el
    inventario incorpora una categoría nueva, el filtro aparece solo.
    """

    def valores(columna) -> list[str]:
        return [
            valor
            for (valor,) in sesion.execute(
                select(distinct(columna)).where(columna.is_not(None)).order_by(columna)
            )
        ]

    return ResumenFiltros(
        provincias=valores(RecursoTuristico.provincia),
        distritos=valores(RecursoTuristico.distrito),
        categorias=valores(RecursoTuristico.categoria),
    )


@enrutador.get(
    "/recursos/mapa", response_model=ColeccionGeoJSON, summary="Recursos en formato GeoJSON"
)
def obtener_recursos_para_el_mapa(
    sesion: SesionBD,
    provincia: str | None = Query(None),
    distrito: str | None = Query(None),
    categoria: str | None = Query(None),
    texto: str | None = Query(None),
) -> ColeccionGeoJSON:
    """Devuelve los recursos con coordenadas, listos para pintar en el mapa.

    Solo se incluyen los que tienen ubicación: un marcador sin coordenada no
    se puede dibujar, y ponerlo en el centro del distrito sería inventar.
    """
    punto = _punto()
    consulta = _aplicar_filtros(
        select(
            RecursoTuristico,
            func.ST_Y(punto).label("latitud"),
            func.ST_X(punto).label("longitud"),
        ).where(RecursoTuristico.ubicacion.is_not(None)),
        provincia,
        distrito,
        categoria,
        texto,
        solo_validados=False,
    )

    rasgos = [
        RasgoGeoJSON(
            geometry=GeometriaPunto(coordinates=(longitud, latitud)),
            properties={
                "id": recurso.id,
                "nombre": recurso.nombre,
                "provincia": recurso.provincia,
                "distrito": recurso.distrito,
                "categoria": recurso.categoria,
                "esta_validado": recurso.esta_validado,
            },
        )
        for recurso, latitud, longitud in sesion.execute(consulta)
        if latitud is not None and longitud is not None
    ]

    return ColeccionGeoJSON(features=rasgos)


@enrutador.get(
    "/recursos/{id_recurso}", response_model=RecursoDetalle, summary="Detalle de un recurso"
)
def obtener_recurso(id_recurso: int, sesion: SesionBD) -> RecursoDetalle:
    """Devuelve todos los datos de un recurso, o 404 si no existe."""
    punto = _punto()
    fila = sesion.execute(
        select(
            RecursoTuristico,
            func.ST_Y(punto).label("latitud"),
            func.ST_X(punto).label("longitud"),
        ).where(RecursoTuristico.id == id_recurso)
    ).first()

    if fila is None:
        raise HTTPException(status_code=404, detail={"codigo": "sin_recurso"})

    recurso, latitud, longitud = fila

    return RecursoDetalle(
        **_a_resumen(recurso, latitud, longitud).model_dump(),
        subtipo=recurso.subtipo,
        url_ficha=recurso.url_ficha,
        altitud_msnm=recurso.altitud_msnm,
        descripcion_es=recurso.descripcion_es,
        descripcion_en=recurso.descripcion_en,
        duracion_visita_min=recurso.duracion_visita_min,
        motivos_invalidez=recurso.motivos_invalidez,
    )


@enrutador.get(
    "/indicadores/catalogo",
    response_model=IndicadorCatalogo,
    summary="Indicador del Incremento 1",
)
def obtener_indicador_del_catalogo(sesion: SesionBD) -> IndicadorCatalogo:
    """Devuelve la última validación ejecutada.

    Es el indicador del Incremento 1: *porcentaje de oferta con información
    validada y vigente*. Los números salen de la tabla, no se recalculan al
    vuelo, para que reflejen el estado del catálogo cuando se validó.
    """
    registro = obtener_ultimo_registro(sesion)

    if registro is None:
        raise HTTPException(
            status_code=404,
            detail={"codigo": "catalogo_sin_validar"},
        )

    total = registro.total_recursos or 1  # evita dividir entre cero

    return IndicadorCatalogo(
        fecha=registro.fecha,
        total_recursos=registro.total_recursos,
        validados=registro.validados,
        vigentes=registro.vigentes,
        con_coordenadas=registro.con_coordenadas,
        porcentaje_validado=registro.porcentaje_validado,
        porcentaje_vigente=round(100 * registro.vigentes / total, 2),
        porcentaje_con_coordenadas=round(100 * registro.con_coordenadas / total, 2),
    )
