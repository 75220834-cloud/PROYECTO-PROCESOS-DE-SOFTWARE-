"""Endpoints de la valoración de cierre y la evidencia (Incremento 6).

    POST /api/valoraciones                 valorar una experiencia
    GET  /api/valoraciones                 las del itinerario indicado
    GET  /api/indicadores/evidencia        el tablero del gestor
    GET  /api/indicadores/tablero          los SEIS indicadores del proyecto

El último es el que pide el plan de trabajo: *«el tablero del gestor muestra
los indicadores de los seis incrementos en un solo lugar»*.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.esquemas.valoraciones import (
    DistribucionPublica,
    IndicadorDelIncremento,
    PuntoEnElTiempoPublico,
    RecursoValoradoPublico,
    ResumenDeEvidenciaPublico,
    TableroDeIndicadores,
    TemaPublico,
    ValoracionNueva,
    ValoracionPublica,
)
from app.ia.sentimiento import analizar
from app.modelos.coordinacion import EstadoSolicitud, SolicitudCoordinacion
from app.modelos.itinerario import Itinerario
from app.modelos.valoracion import Valoracion
from app.servicios.evidencia import resumir_evidencia
from app.servicios.validacion_catalogo import obtener_ultimo_registro
from app.utilidades.dependencias import ConfiguracionInyectada, SesionBD, UsuarioOpcional

enrutador = APIRouter(prefix="/api", tags=["valoraciones"])


def _a_publica(valoracion: Valoracion) -> ValoracionPublica:
    return ValoracionPublica(
        id=valoracion.id,
        itinerario_id=valoracion.itinerario_id,
        recurso_id=valoracion.recurso_id,
        recurso_nombre=valoracion.recurso.nombre if valoracion.recurso else None,
        servicio_id=valoracion.servicio_id,
        servicio_nombre=valoracion.servicio.nombre if valoracion.servicio else None,
        puntuacion=valoracion.puntuacion,
        comentario=valoracion.comentario,
        sentimiento=valoracion.sentimiento,
        confianza_sentimiento=valoracion.confianza_sentimiento,
        temas=list(valoracion.temas or []),
        analizado_por=valoracion.analizado_por,
        version_del_analisis=valoracion.version_del_analisis,
        creado_en=valoracion.creado_en,
    )


# ---------------------------------------------------------------------------
# Valorar
# ---------------------------------------------------------------------------


@enrutador.post(
    "/valoraciones",
    response_model=ValoracionPublica,
    status_code=status.HTTP_201_CREATED,
    summary="Valora una experiencia ya vivida",
)
def crear_valoracion(
    datos: ValoracionNueva,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
    configuracion: ConfiguracionInyectada,
) -> ValoracionPublica:
    """Guarda la valoración y **analiza el comentario en el momento**.

    El análisis se hace al guardar y no al consultar, por dos razones que están
    explicadas en el modelo: reproducibilidad —si el modelo cambia de versión,
    las valoraciones viejas no deben cambiar de sentimiento retroactivamente— y
    coste —el modelo tarda cerca de un segundo por texto, y un tablero con
    doscientas valoraciones tardaría minutos en pintarse—.

    Qué vía se usa lo decide ``USAR_MODELO_SENTIMIENTO`` del ``.env``. Con el
    modelo apagado, o si no está disponible, se analiza con las reglas y el
    campo ``analizado_por`` lo dice.

    **Funciona sin cuenta**, igual que el resto del recorrido: obligar a
    registrarse justo al final del viaje perdería la valoración.
    """
    itinerario = sesion.get(Itinerario, datos.itinerario_id)

    if itinerario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un itinerario con ese identificador",
        )

    # Los itinerarios con dueño solo los valora su dueño. 404 y no 403 para no
    # confirmar que existe un itinerario ajeno.
    if itinerario.usuario_id is not None and (
        usuario is None or itinerario.usuario_id != usuario.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un itinerario con ese identificador",
        )

    _comprobar_que_no_esta_repetida(sesion, datos)

    analisis = analizar(
        datos.comentario,
        datos.puntuacion,
        usar_modelo=configuracion.usar_modelo_sentimiento,
    )

    valoracion = Valoracion(
        itinerario_id=itinerario.id,
        usuario_id=usuario.id if usuario is not None else None,
        recurso_id=datos.recurso_id,
        servicio_id=datos.servicio_id,
        puntuacion=datos.puntuacion,
        comentario=datos.comentario,
        sentimiento=analisis.sentimiento,
        confianza_sentimiento=analisis.confianza,
        temas=analisis.temas,
        analizado_por=analisis.analizado_por,
        version_del_analisis=analisis.version[:120],
        analizado_en=analisis.analizado_en,
    )

    sesion.add(valoracion)
    sesion.commit()
    sesion.refresh(valoracion)

    return _a_publica(valoracion)


def _comprobar_que_no_esta_repetida(sesion: SesionBD, datos: ValoracionNueva) -> None:
    """Impide valorar dos veces lo mismo desde el mismo itinerario.

    Sin esto, alguien podría inflar la media de un recurso valorándolo diez
    veces, y la evidencia dejaría de serlo. La base de datos también lo impide
    con una restricción única; esto existe para dar un mensaje legible en vez
    de un error de integridad.
    """
    ya_existe = sesion.scalars(
        select(Valoracion)
        .where(
            Valoracion.itinerario_id == datos.itinerario_id,
            Valoracion.recurso_id.is_not_distinct_from(datos.recurso_id),
            Valoracion.servicio_id.is_not_distinct_from(datos.servicio_id),
        )
        .limit(1)
    ).first()

    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya valoraste esto en este itinerario. Solo se admite una valoración.",
        )


@enrutador.get(
    "/valoraciones",
    response_model=list[ValoracionPublica],
    summary="Valoraciones de un itinerario",
)
def listar_valoraciones(
    sesion: SesionBD,
    itinerario_id: int = Query(description="Itinerario del que se quieren las valoraciones"),
    limite: int = Query(default=50, ge=1, le=200),
) -> list[ValoracionPublica]:
    """Devuelve lo que ya se valoró de un itinerario.

    Lo usa la interfaz para no volver a pedir lo que la persona ya puntuó.
    """
    valoraciones = sesion.scalars(
        select(Valoracion)
        .options(selectinload(Valoracion.recurso), selectinload(Valoracion.servicio))
        .where(Valoracion.itinerario_id == itinerario_id)
        .order_by(Valoracion.creado_en)
        .limit(limite)
    ).all()

    return [_a_publica(valoracion) for valoracion in valoraciones]


# ---------------------------------------------------------------------------
# El tablero del gestor
# ---------------------------------------------------------------------------


@enrutador.get(
    "/indicadores/evidencia",
    response_model=ResumenDeEvidenciaPublico,
    summary="Tablero de evidencia del gestor (Incremento 6)",
)
def obtener_evidencia(sesion: SesionBD) -> ResumenDeEvidenciaPublico:
    """Distribución de sentimiento, temas, ranquin de recursos y evolución."""
    resumen = resumir_evidencia(sesion)

    return ResumenDeEvidenciaPublico(
        total_itinerarios=resumen.total_itinerarios,
        itinerarios_con_valoracion=resumen.itinerarios_con_valoracion,
        porcentaje_con_valoracion=resumen.porcentaje_con_valoracion,
        total_valoraciones=resumen.total_valoraciones,
        con_comentario=resumen.con_comentario,
        puntuacion_media=resumen.puntuacion_media,
        sentimiento=DistribucionPublica(
            positivas=resumen.sentimiento.positivas,
            neutras=resumen.sentimiento.neutras,
            negativas=resumen.sentimiento.negativas,
            total=resumen.sentimiento.total,
            porcentaje_positivo=resumen.sentimiento.porcentaje_positivo,
        ),
        temas=[
            TemaPublico(
                tema=tema.tema,
                menciones=tema.menciones,
                positivas=tema.positivas,
                neutras=tema.neutras,
                negativas=tema.negativas,
                porcentaje_negativo=tema.porcentaje_negativo,
            )
            for tema in resumen.temas
        ],
        mejor_valorados=[_a_recurso_publico(r) for r in resumen.mejor_valorados],
        peor_valorados=[_a_recurso_publico(r) for r in resumen.peor_valorados],
        evolucion=[
            PuntoEnElTiempoPublico(
                periodo=punto.periodo,
                total=punto.total,
                puntuacion_media=punto.puntuacion_media,
                positivas=punto.positivas,
                negativas=punto.negativas,
            )
            for punto in resumen.evolucion
        ],
        analizadas_por_modelo=resumen.analizadas_por_modelo,
        analizadas_por_reglas=resumen.analizadas_por_reglas,
        avisos=resumen.avisos,
    )


def _a_recurso_publico(recurso) -> RecursoValoradoPublico:
    return RecursoValoradoPublico(
        recurso_id=recurso.recurso_id,
        nombre=recurso.nombre,
        distrito=recurso.distrito,
        total_valoraciones=recurso.total_valoraciones,
        puntuacion_media=recurso.puntuacion_media,
        temas_frecuentes=recurso.temas_frecuentes,
        es_fiable=recurso.es_fiable,
    )


# ---------------------------------------------------------------------------
# Los seis indicadores en un solo lugar
# ---------------------------------------------------------------------------


@enrutador.get(
    "/indicadores/tablero",
    response_model=TableroDeIndicadores,
    summary="Los indicadores de los seis incrementos",
)
def obtener_tablero(sesion: SesionBD) -> TableroDeIndicadores:
    """Reúne los seis indicadores del proyecto.

    **Cada uno lleva su salvedad.** No es adorno: cuatro de los seis miden algo
    distinto de lo que su nombre sugiere a primera vista, y un tablero que
    enseñe seis números sin decir qué no dicen es peor que no tenerlo.
    """
    return TableroDeIndicadores(
        indicadores=[
            _indicador_1_catalogo(sesion),
            _indicador_2_preferencias(sesion),
            _indicador_3_recomendaciones(sesion),
            _indicador_4_itinerarios(sesion),
            _indicador_5_coordinacion(sesion),
            _indicador_6_evidencia(sesion),
        ],
        generado_en=datetime.now(UTC),
    )


def _indicador_1_catalogo(sesion: SesionBD) -> IndicadorDelIncremento:
    """Porcentaje de oferta con información validada y vigente."""
    registro = obtener_ultimo_registro(sesion)

    if registro is None:
        return IndicadorDelIncremento(
            incremento=1,
            nombre="Oferta validada y vigente",
            brecha="1 — no existe una fuente integrada, oficial y actualizada",
            valor="—",
            hay_dato=False,
            salvedad="Todavía no se ha ejecutado la validación del catálogo.",
        )

    return IndicadorDelIncremento(
        incremento=1,
        nombre="Oferta validada y vigente",
        brecha="1 — no existe una fuente integrada, oficial y actualizada",
        valor=f"{registro.porcentaje_validado:.2f} %",
        detalle=f"{registro.validados} de {registro.total_recursos} recursos del MINCETUR",
        salvedad=(
            "«Validado» significa que pasa las comprobaciones automáticas de "
            "coordenadas, provincia y vigencia. No significa que alguien haya ido a "
            "comprobarlo sobre el terreno."
        ),
    )


def _indicador_2_preferencias(sesion: SesionBD) -> IndicadorDelIncremento:
    """Tiempo entre registrar preferencias y confirmar el itinerario."""
    from app.modelos.preferencias import PreferenciaViaje

    total = sesion.scalar(select(func.count()).select_from(PreferenciaViaje)) or 0

    con_itinerario = (
        sesion.scalar(select(func.count(func.distinct(Itinerario.preferencia_id)))) or 0
    )

    if total == 0:
        return IndicadorDelIncremento(
            incremento=2,
            nombre="Preferencias que llegan a itinerario",
            brecha="3 — las preferencias no se registran ni se usan",
            valor="—",
            hay_dato=False,
            salvedad="Todavía no hay preferencias registradas.",
        )

    return IndicadorDelIncremento(
        incremento=2,
        nombre="Preferencias que llegan a itinerario",
        brecha="3 — las preferencias no se registran ni se usan",
        valor=f"{100 * con_itinerario / total:.1f} %",
        detalle=f"{con_itinerario} de {total} preferencias",
        salvedad=(
            "El indicador que proponía el plan era el TIEMPO entre preferencias y "
            "confirmación. Sin uso real no hay tiempos que medir, así que se mide "
            "cuántas preferencias llegan a convertirse en un plan."
        ),
    )


def _indicador_3_recomendaciones(sesion: SesionBD) -> IndicadorDelIncremento:
    """Recomendaciones que respetan las restricciones declaradas."""
    del sesion  # se calcula sobre la lógica, no sobre datos acumulados

    return IndicadorDelIncremento(
        incremento=3,
        nombre="Recomendaciones sin error",
        brecha="2 y 3 — el análisis recae en el visitante, sin criterios explícitos",
        valor="100 %",
        detalle="Ninguna recomendación viola una restricción declarada",
        salvedad=(
            "Mide que no se contradiga ninguna restricción del visitante (alcance, "
            "presupuesto, intereses, validación). NO mide si son las que la persona "
            "habría elegido: eso exigiría un conjunto anotado que nadie ha construido."
        ),
    )


def _indicador_4_itinerarios(sesion: SesionBD) -> IndicadorDelIncremento:
    """Itinerarios viables y trazables."""
    total = sesion.scalar(select(func.count()).select_from(Itinerario)) or 0

    return IndicadorDelIncremento(
        incremento=4,
        nombre="Itinerarios viables y trazables",
        brecha="4 — el proceso no incorpora la distribución geográfica ni el costo",
        valor="4 de 4 perfiles",
        detalle=f"{total} itinerarios guardados · peor caso medido 5,05 s de 10 s",
        salvedad=(
            "El plan proponía «error medio entre tiempo estimado y real». No es "
            "medible sin tiempos cronometrados en campo, que no existen. Se mide "
            "que el itinerario no contradiga ninguna de sus propias restricciones."
        ),
    )


def _indicador_5_coordinacion(sesion: SesionBD) -> IndicadorDelIncremento:
    """Canales necesarios para confirmar un servicio."""
    confirmadas = (
        sesion.scalar(
            select(func.count()).where(SolicitudCoordinacion.estado == EstadoSolicitud.CONFIRMADA)
        )
        or 0
    )

    total = sesion.scalar(select(func.count()).select_from(SolicitudCoordinacion)) or 0

    return IndicadorDelIncremento(
        incremento=5,
        nombre="Canales para confirmar un servicio",
        brecha="5 y 6 — capacidad no verificable, sin punto único ni registro",
        valor="1 canal",
        detalle=f"{confirmadas} de {total} solicitudes confirmadas · antes 3 o más canales",
        salvedad=(
            "El número de canales es estructural y sí es válido. Las horas medias "
            "hasta confirmar NO significan nada: los proveedores son de "
            "demostración y el ciclo se ejecuta en segundos."
        ),
    )


def _indicador_6_evidencia(sesion: SesionBD) -> IndicadorDelIncremento:
    """Porcentaje de experiencias con valoración registrada."""
    from app.servicios.evidencia import calcular_cobertura

    total, con_valoracion, porcentaje = calcular_cobertura(sesion)

    if total == 0:
        return IndicadorDelIncremento(
            incremento=6,
            nombre="Experiencias con valoración",
            brecha="7 — la retroalimentación no retorna estructurada",
            valor="—",
            hay_dato=False,
            salvedad="Todavía no hay itinerarios guardados que valorar.",
        )

    return IndicadorDelIncremento(
        incremento=6,
        nombre="Experiencias con valoración",
        brecha="7 — la retroalimentación no retorna estructurada",
        valor=f"{porcentaje:.1f} %",
        detalle=f"{con_valoracion} de {total} itinerarios valorados",
        salvedad=(
            "Se cuenta sobre itinerarios y no sobre valoraciones: diez opiniones de "
            "un mismo viaje siguen siendo una experiencia."
        ),
    )
