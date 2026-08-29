"""Endpoints de la recomendación inteligente (Incremento 3).

- ``POST /api/recomendaciones``           recomienda para una preferencia
- ``GET  /api/calendario/{anio}``         festividades del año
- ``GET  /api/calendario/dia/{fecha}``    qué pasa un día concreto
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.esquemas.recomendaciones import (
    AfluenciaEstimada,
    CalendarioPublico,
    FestividadPublica,
    RecomendacionPublica,
    RecursoDescartadoPublico,
    RespuestaRecomendacion,
    SolicitudRecomendacion,
)
from app.ia.afluencia import predecir_afluencia
from app.ia.calendario import calendario_del_anio
from app.modelos.preferencias import PreferenciaViaje
from app.servicios.recomendador import recomendar
from app.utilidades.dependencias import ConfiguracionInyectada, SesionBD, UsuarioOpcional

enrutador = APIRouter(prefix="/api", tags=["recomendaciones"])

#: Cuántos descartes se devuelven como ejemplo. El total va aparte: mandar los
#: 61 recursos sin coordenadas en cada respuesta sería peso muerto.
DESCARTES_DE_EJEMPLO = 10


@enrutador.post(
    "/recomendaciones",
    response_model=RespuestaRecomendacion,
    summary="Recomienda recursos para una preferencia de viaje",
)
def obtener_recomendaciones(
    solicitud: SolicitudRecomendacion,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
    configuracion: ConfiguracionInyectada,
) -> RespuestaRecomendacion:
    """Devuelve los recursos ordenados por afinidad, con su explicación.

    **Funciona sin cuenta**, igual que el asistente de preferencias: si la
    preferencia se creó sin sesión, cualquiera con su identificador puede
    pedir recomendaciones para ella.

    Qué vía se usa lo deciden las variables ``USAR_MODELO_RECOMENDACION`` y
    ``USAR_MODELO_AFLUENCIA`` del ``.env``. El campo ``generado_por`` de la
    respuesta deja constancia de cuál se usó en cada caso.
    """
    preferencia = sesion.get(PreferenciaViaje, solicitud.preferencia_id)

    if preferencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )

    # Misma regla de acceso que en el resto de preferencias: las que tienen
    # dueño solo las ve su dueño, y se responde 404 para no confirmar que
    # existen.
    if preferencia.usuario_id is not None and (
        usuario is None or preferencia.usuario_id != usuario.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )

    resultado = recomendar(
        sesion,
        preferencia,
        usar_modelo_recomendacion=configuracion.usar_modelo_recomendacion,
        usar_modelo_afluencia=configuracion.usar_modelo_afluencia,
        limite=solicitud.limite,
    )

    return RespuestaRecomendacion(
        preferencia_id=preferencia.id,
        fecha_de_referencia=preferencia.fecha_inicio,
        generado_por=resultado.generado_por,
        total_evaluados=resultado.total_evaluados,
        total_recomendados=len(resultado.recomendaciones),
        total_descartados=len(resultado.descartados),
        recomendaciones=[
            RecomendacionPublica(
                recurso_id=r.recurso_id,
                nombre=r.nombre,
                provincia=r.provincia,
                distrito=r.distrito,
                categoria=r.categoria,
                latitud=r.latitud,
                longitud=r.longitud,
                distancia_km=r.distancia_km,
                puntaje_afinidad=r.puntaje_afinidad,
                puntaje_relativo=r.puntaje_relativo,
                terminos_decisivos=r.terminos_decisivos,
                intereses_cubiertos=r.intereses_cubiertos,
                afluencia=AfluenciaEstimada(
                    nivel=r.afluencia.nivel.value,
                    motivo=r.afluencia.motivo,
                    festividades=r.afluencia.festividades,
                    calculado_por=r.afluencia.calculado_por,
                ),
                generado_por=r.generado_por,
            )
            for r in resultado.recomendaciones
        ],
        descartados=[
            RecursoDescartadoPublico(recurso_id=d.recurso_id, nombre=d.nombre, motivo=d.motivo)
            for d in resultado.descartados[:DESCARTES_DE_EJEMPLO]
        ],
        avisos=resultado.avisos,
    )


@enrutador.get(
    "/calendario/dia/{fecha}",
    summary="Qué ocurre un día concreto en el valle",
)
def consultar_dia(
    fecha: date,
    configuracion: ConfiguracionInyectada,
    distrito: str = Query("HUANCAYO", description="Distrito sobre el que consultar"),
) -> dict:
    """Devuelve la afluencia esperada y las fiestas activas de un día.

    Alimenta la etiqueta «hoy hay fiesta en X» de la interfaz.
    """
    prediccion = predecir_afluencia(
        fecha, distrito, usar_modelo=configuracion.usar_modelo_afluencia
    )

    return {
        "fecha": fecha,
        "distrito": distrito.upper(),
        "afluencia": {
            "nivel": prediccion.nivel.value,
            "motivo": prediccion.motivo,
            "festividades": prediccion.festividades,
            "calculado_por": prediccion.calculado_por,
        },
    }


@enrutador.get(
    "/calendario/{anio}",
    response_model=CalendarioPublico,
    summary="Festividades del Valle del Mantaro en un año",
)
def consultar_calendario(anio: int) -> CalendarioPublico:
    """Devuelve todas las fiestas del año, móviles y fijas.

    Las móviles se calculan con el algoritmo de la Pascua, así que este
    endpoint responde correctamente para cualquier año, pasado o futuro, sin
    tener que cargar nada previamente.
    """
    if not 2000 <= anio <= 2100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El año debe estar entre 2000 y 2100",
        )

    festividades = calendario_del_anio(anio)

    return CalendarioPublico(
        anio=anio,
        total=len(festividades),
        festividades=[
            FestividadPublica(
                nombre=f.nombre,
                fecha_inicio=f.fecha_inicio,
                fecha_fin=f.fecha_fin,
                tipo=f.tipo.value,
                distritos=list(f.distritos),
                es_movil=f.es_movil,
                fuente=f.fuente,
            )
            for f in festividades
        ],
    )
