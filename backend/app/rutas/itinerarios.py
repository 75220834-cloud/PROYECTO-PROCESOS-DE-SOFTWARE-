"""Endpoints del itinerario geoespacial (Incremento 4).

- ``POST /api/itinerarios``                   arma el itinerario de un día
- ``POST /api/itinerarios/reordenar``         recalcula tras arrastrar paradas
- ``GET  /api/itinerarios/{id}``              recupera uno guardado
- ``GET  /api/itinerarios``                   lista los del usuario

Igual que el resto del sistema, **funciona sin cuenta**: quien tenga el
identificador de una preferencia sin dueño puede armar su itinerario. Es la
decisión registrada en ``docs/decisiones/2026-08-29-la-aplicacion-funciona-sin-cuenta.md``.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.esquemas.itinerarios import (
    ParadaPublica,
    RespuestaItinerario,
    SolicitudItinerario,
    SolicitudReordenar,
    TrasladoPublico,
)
from app.modelos.itinerario import Itinerario
from app.modelos.preferencias import PreferenciaViaje
from app.servicios.recomendador import recomendar
from app.servicios.ruteo import (
    HORA_FIN_PREDETERMINADA,
    HORA_INICIO_PREDETERMINADA,
    ItinerarioCalculado,
    construir_itinerario,
    construir_itinerario_en_orden,
    guardar_itinerario,
    titulo_por_defecto,
)
from app.utilidades.dependencias import ConfiguracionInyectada, SesionBD, UsuarioOpcional

enrutador = APIRouter(prefix="/api/itinerarios", tags=["itinerarios"])

#: Cuántas recomendaciones se piden antes de rutear. El optimizador se queda
#: con las 20 mejores; pedir 40 le da margen para descartar las que no encajan
#: en el horario o el presupuesto sin quedarse corto de candidatos.
RECOMENDACIONES_A_CONSIDERAR = 40


def _preferencia_accesible(sesion: SesionBD, preferencia_id: int, usuario) -> PreferenciaViaje:
    """Busca una preferencia comprobando que quien la pide puede verla.

    Las preferencias con dueño solo las ve su dueño. Se responde 404 y no 403
    para no confirmar que existe una preferencia ajena: un 403 le diría a
    cualquiera que ese identificador es válido.
    """
    preferencia = sesion.get(PreferenciaViaje, preferencia_id)

    hay_acceso = preferencia is not None and (
        preferencia.usuario_id is None
        or (usuario is not None and preferencia.usuario_id == usuario.id)
    )

    if not hay_acceso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )

    return preferencia  # type: ignore[return-value]


def _fecha_del_itinerario(preferencia: PreferenciaViaje, pedida: date | None) -> date:
    """Decide qué día se planifica y comprueba que cae dentro del viaje."""
    if pedida is None:
        return preferencia.fecha_inicio

    if not preferencia.fecha_inicio <= pedida <= preferencia.fecha_fin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"La fecha {pedida} está fuera del viaje, que va del "
                f"{preferencia.fecha_inicio} al {preferencia.fecha_fin}"
            ),
        )

    return pedida


def _a_respuesta(
    calculado: ItinerarioCalculado,
    preferencia: PreferenciaViaje,
    fecha: date,
    titulo: str,
    itinerario_id: int | None,
) -> RespuestaItinerario:
    """Convierte el resultado del ruteo en la respuesta pública."""
    return RespuestaItinerario(
        itinerario_id=itinerario_id,
        preferencia_id=preferencia.id,
        fecha=fecha,
        titulo=titulo,
        generado_por=calculado.generado_por,
        paradas=[
            ParadaPublica(
                orden=parada.orden,
                recurso_id=parada.candidato.recurso_id,
                nombre=parada.candidato.nombre,
                distrito=parada.candidato.distrito,
                categoria=parada.candidato.categoria,
                latitud=parada.candidato.latitud,
                longitud=parada.candidato.longitud,
                altitud_msnm=(
                    round(parada.candidato.altitud_m)
                    if parada.candidato.altitud_m is not None
                    else None
                ),
                hora_llegada=parada.hora_llegada,
                hora_salida=parada.hora_salida,
                duracion_visita_min=parada.candidato.duracion_visita_min,
                puntaje_relativo=parada.candidato.puntaje_relativo,
                traslado=(
                    TrasladoPublico(
                        modo=parada.traslado.modo,
                        minutos=parada.traslado.minutos,
                        distancia_km=parada.traslado.distancia_km,
                        desnivel_m=parada.traslado.desnivel_m,
                        precio_min_soles=parada.traslado.precio_min_soles,
                        precio_max_soles=parada.traslado.precio_max_soles,
                        es_estimado=parada.traslado.es_estimado,
                        fuente=parada.traslado.fuente,
                        fecha_referencia=parada.traslado.fecha_referencia,
                        origen_del_calculo=parada.traslado.origen_del_calculo,
                        trazado=parada.traslado.trazado,
                    )
                    if parada.traslado is not None
                    else None
                ),
            )
            for parada in calculado.paradas
        ],
        tiempo_total_min=calculado.tiempo_total_min,
        costo_min_soles=calculado.costo_min_soles,
        costo_max_soles=calculado.costo_max_soles,
        distancia_total_km=calculado.distancia_total_km,
        subida_total_m=calculado.subida_total_m,
        esfuerzo=calculado.esfuerzo,
        hay_tramos_estimados=calculado.hay_tramos_estimados,
        avisos=calculado.avisos,
    )


@enrutador.post(
    "",
    response_model=RespuestaItinerario,
    summary="Arma el itinerario de un día para una preferencia",
)
def armar_itinerario(
    solicitud: SolicitudItinerario,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
    configuracion: ConfiguracionInyectada,
) -> RespuestaItinerario:
    """Recomienda, ordena y horaria las paradas de un día.

    Qué vía se usa lo decide ``USAR_MODELO_RECOMENDACION`` del ``.env``: con
    ``true`` optimiza con OR-Tools, con ``false`` usa el vecino más cercano. El
    campo ``generado_por`` de la respuesta deja constancia de cuál fue.
    """
    preferencia = _preferencia_accesible(sesion, solicitud.preferencia_id, usuario)
    fecha = _fecha_del_itinerario(preferencia, solicitud.fecha)

    recomendacion = recomendar(
        sesion,
        preferencia,
        usar_modelo_recomendacion=configuracion.usar_modelo_recomendacion,
        usar_modelo_afluencia=configuracion.usar_modelo_afluencia,
        limite=RECOMENDACIONES_A_CONSIDERAR,
    )

    calculado = construir_itinerario(
        sesion,
        preferencia,
        recomendacion.recomendaciones,
        fecha,
        usar_modelo=configuracion.usar_modelo_recomendacion,
        hora_inicio=solicitud.hora_inicio or HORA_INICIO_PREDETERMINADA,
        hora_fin=solicitud.hora_fin or HORA_FIN_PREDETERMINADA,
    )

    titulo = solicitud.titulo or titulo_por_defecto(calculado.paradas, fecha)

    itinerario_id = None
    if solicitud.guardar and calculado.paradas:
        itinerario = guardar_itinerario(
            sesion, preferencia, calculado, fecha, titulo, preferencia.usuario_id
        )
        sesion.commit()
        itinerario_id = itinerario.id

    return _a_respuesta(calculado, preferencia, fecha, titulo, itinerario_id)


@enrutador.post(
    "/reordenar",
    response_model=RespuestaItinerario,
    summary="Recalcula el itinerario con el orden que eligió el visitante",
)
def reordenar_itinerario(
    solicitud: SolicitudReordenar,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
    configuracion: ConfiguracionInyectada,
) -> RespuestaItinerario:
    """Rehace horarios, traslados y totales respetando el orden pedido.

    **No reoptimiza.** Si el visitante arrastró una parada al primer puesto, se
    queda en el primer puesto. Lo que se recalcula son las consecuencias: a qué
    hora se llega a cada sitio, cuánto cuesta llegar y si el día sigue cabiendo.
    """
    preferencia = _preferencia_accesible(sesion, solicitud.preferencia_id, usuario)
    fecha = _fecha_del_itinerario(preferencia, solicitud.fecha)

    recomendacion = recomendar(
        sesion,
        preferencia,
        usar_modelo_recomendacion=configuracion.usar_modelo_recomendacion,
        usar_modelo_afluencia=configuracion.usar_modelo_afluencia,
        limite=RECOMENDACIONES_A_CONSIDERAR,
    )

    calculado = construir_itinerario_en_orden(
        sesion,
        preferencia,
        recomendacion.recomendaciones,
        fecha,
        solicitud.recursos_en_orden,
        hora_inicio=solicitud.hora_inicio or HORA_INICIO_PREDETERMINADA,
        hora_fin=solicitud.hora_fin or HORA_FIN_PREDETERMINADA,
    )

    titulo = solicitud.titulo or titulo_por_defecto(calculado.paradas, fecha)

    itinerario_id = None
    if solicitud.guardar and calculado.paradas:
        itinerario = guardar_itinerario(
            sesion, preferencia, calculado, fecha, titulo, preferencia.usuario_id
        )
        sesion.commit()
        itinerario_id = itinerario.id

    return _a_respuesta(calculado, preferencia, fecha, titulo, itinerario_id)


@enrutador.get(
    "",
    summary="Lista los itinerarios guardados del usuario",
)
def listar_itinerarios(
    sesion: SesionBD,
    usuario: UsuarioOpcional,
    limite: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    """Devuelve los itinerarios del usuario que ha iniciado sesión.

    Sin cuenta devuelve una lista vacía: un itinerario sin dueño no se puede
    recuperar por listado, solo por su identificador. Devolver todos los
    anónimos convertiría la lista en el historial de viaje de desconocidos.
    """
    if usuario is None:
        return []

    itinerarios = sesion.scalars(
        select(Itinerario)
        .where(Itinerario.usuario_id == usuario.id)
        .order_by(Itinerario.fecha.desc(), Itinerario.id.desc())
        .limit(limite)
    ).all()

    return [
        {
            "id": itinerario.id,
            "titulo": itinerario.titulo,
            "fecha": itinerario.fecha,
            "estado": itinerario.estado,
            "generado_por": itinerario.generado_por,
            "total_paradas": len(itinerario.paradas),
            "tiempo_total_min": itinerario.tiempo_total_min,
            "costo_total_soles": itinerario.costo_total_soles,
            "distancia_total_km": itinerario.distancia_total_km,
            "desnivel_total_m": itinerario.desnivel_total_m,
        }
        for itinerario in itinerarios
    ]


@enrutador.get(
    "/{itinerario_id}",
    summary="Recupera un itinerario guardado",
)
def consultar_itinerario(
    itinerario_id: int,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
) -> dict:
    """Devuelve un itinerario guardado con sus paradas.

    Los itinerarios sin dueño son accesibles por identificador, igual que las
    preferencias sin cuenta: es lo que permite compartir un plan con quien va a
    viajar contigo sin obligarle a registrarse.
    """
    itinerario = sesion.get(Itinerario, itinerario_id)

    hay_acceso = itinerario is not None and (
        itinerario.usuario_id is None
        or (usuario is not None and itinerario.usuario_id == usuario.id)
    )

    if not hay_acceso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un itinerario con ese identificador",
        )

    assert itinerario is not None  # ya lo comprobó hay_acceso

    return {
        "id": itinerario.id,
        "preferencia_id": itinerario.preferencia_id,
        "titulo": itinerario.titulo,
        "fecha": itinerario.fecha,
        "estado": itinerario.estado,
        "generado_por": itinerario.generado_por,
        "tiempo_total_min": itinerario.tiempo_total_min,
        "costo_total_soles": itinerario.costo_total_soles,
        "distancia_total_km": itinerario.distancia_total_km,
        "desnivel_total_m": itinerario.desnivel_total_m,
        "avisos": itinerario.avisos.split("\n") if itinerario.avisos else [],
        "paradas": [
            {
                "orden": parada.orden,
                "recurso_id": parada.recurso_id,
                "nombre": parada.recurso.nombre,
                "distrito": parada.recurso.distrito,
                "altitud_msnm": parada.recurso.altitud_msnm,
                "hora_llegada": parada.hora_llegada,
                "hora_salida": parada.hora_salida,
                "modo_traslado": parada.modo_traslado,
                "tiempo_traslado_min": parada.tiempo_traslado_min,
                "distancia_traslado_km": parada.distancia_traslado_km,
                "costo_traslado_min_soles": parada.costo_traslado_min_soles,
                "costo_traslado_max_soles": parada.costo_traslado_max_soles,
                "origen_del_calculo": parada.origen_del_calculo,
            }
            for parada in itinerario.paradas
        ],
    }
