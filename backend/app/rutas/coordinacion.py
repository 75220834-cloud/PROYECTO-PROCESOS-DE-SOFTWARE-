"""Endpoints del canal único de coordinación (Incremento 5).

    GET  /api/servicios                        catálogo de servicios ofrecidos
    GET  /api/servicios/{id}                   ficha de un servicio
    POST /api/servicios/{id}/disponibilidad    ¿se puede pedir así?
    POST /api/servicios                        publicar (solo proveedor)
    POST /api/servicios/{id}/tramos            publicar disponibilidad

    POST /api/solicitudes                      pedir un servicio
    GET  /api/solicitudes                      las que puedo ver
    GET  /api/solicitudes/{id}                 una, con su historial
    POST /api/solicitudes/{id}/estado          moverla de estado

    GET  /api/indicadores/coordinacion         el indicador del incremento

**El punto de todo esto es que sea UN solo sitio.** La brecha 6 dice que no
existe punto único de coordinación ni registro de lo acordado; el registro está
en el historial de estados, y el punto único es que estas rutas son las únicas
por las que se coordina.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.esquemas.coordinacion import (
    CambioDeEstadoPublico,
    CambioSolicitado,
    ConsultaDisponibilidad,
    ProveedorPublico,
    RespuestaDisponibilidad,
    ResumenDeCoordinacion,
    ServicioNuevo,
    ServicioPublico,
    SolicitudNueva,
    SolicitudPublica,
    TramoDisponible,
    TramoNuevo,
)
from app.modelos.coordinacion import (
    CambioDeEstado,
    DisponibilidadServicio,
    EstadoSolicitud,
    Proveedor,
    Servicio,
    SolicitudCoordinacion,
)
from app.modelos.usuario import RolUsuario
from app.servicios.coordinacion import (
    ErrorDeCoordinacion,
    SinPermiso,
    cambiar_estado,
    consulta_de_solicitudes_visibles,
    plazas_ya_comprometidas,
    proveedor_del_usuario,
    puede_ver_solicitud,
    revisar_disponibilidad,
    tramos_del_dia,
)
from app.utilidades.dependencias import SesionBD, UsuarioOpcional, UsuarioRequerido

enrutador = APIRouter(prefix="/api", tags=["coordinación"])


# ---------------------------------------------------------------------------
# Conversión a los esquemas públicos
# ---------------------------------------------------------------------------


def _a_proveedor_publico(proveedor: Proveedor) -> ProveedorPublico:
    return ProveedorPublico(
        id=proveedor.id,
        nombre=proveedor.nombre,
        distrito=proveedor.distrito,
        telefono=proveedor.telefono,
        correo=proveedor.correo,
        descripcion=proveedor.descripcion,
        es_demostracion=proveedor.es_demostracion,
    )


def _a_servicio_publico(servicio: Servicio) -> ServicioPublico:
    return ServicioPublico(
        id=servicio.id,
        nombre=servicio.nombre,
        tipo=servicio.tipo,
        descripcion=servicio.descripcion,
        proveedor=_a_proveedor_publico(servicio.proveedor),
        recurso_id=servicio.recurso_id,
        capacidad_maxima=servicio.capacidad_maxima,
        duracion_min=servicio.duracion_min,
        antelacion_minima_horas=servicio.antelacion_minima_horas,
        precio_min_soles=servicio.precio_min_soles,
        precio_max_soles=servicio.precio_max_soles,
        unidad_precio=servicio.unidad_precio,
        fecha_referencia=servicio.fecha_referencia,
        idiomas=servicio.idiomas,
        es_accesible=servicio.es_accesible,
        disponibilidad=[
            TramoDisponible(
                dia_semana=tramo.dia_semana,
                hora_inicio=tramo.hora_inicio,
                hora_fin=tramo.hora_fin,
                cupo=tramo.cupo,
            )
            for tramo in sorted(
                servicio.disponibilidades, key=lambda t: (t.dia_semana, t.hora_inicio)
            )
        ],
    )


def _a_solicitud_publica(solicitud: SolicitudCoordinacion) -> SolicitudPublica:
    return SolicitudPublica(
        id=solicitud.id,
        servicio_id=solicitud.servicio_id,
        servicio_nombre=solicitud.servicio.nombre,
        proveedor_nombre=solicitud.servicio.proveedor.nombre,
        proveedor_telefono=solicitud.servicio.proveedor.telefono,
        proveedor_es_demostracion=solicitud.servicio.proveedor.es_demostracion,
        itinerario_id=solicitud.itinerario_id,
        fecha_servicio=solicitud.fecha_servicio,
        hora_servicio=solicitud.hora_servicio,
        numero_personas=solicitud.numero_personas,
        nombre_contacto=solicitud.nombre_contacto,
        telefono_contacto=solicitud.telefono_contacto,
        correo_contacto=solicitud.correo_contacto,
        mensaje=solicitud.mensaje,
        estado=solicitud.estado,
        precio_acordado_soles=solicitud.precio_acordado_soles,
        respuesta_proveedor=solicitud.respuesta_proveedor,
        precio_min_soles=solicitud.servicio.precio_min_soles,
        precio_max_soles=solicitud.servicio.precio_max_soles,
        creado_en=solicitud.creado_en,
        actualizado_en=solicitud.actualizado_en,
        interacciones=solicitud.interacciones,
        historial=[
            CambioDeEstadoPublico(
                estado_anterior=cambio.estado_anterior,
                estado_nuevo=cambio.estado_nuevo,
                rol_de_quien_cambio=cambio.rol_de_quien_cambio,
                nota=cambio.nota,
                ocurrido_en=cambio.ocurrido_en,
            )
            for cambio in solicitud.cambios
        ],
    )


def _buscar_servicio(sesion: SesionBD, servicio_id: int) -> Servicio:
    servicio = sesion.scalars(
        select(Servicio)
        .options(
            selectinload(Servicio.proveedor),
            selectinload(Servicio.disponibilidades),
        )
        .where(Servicio.id == servicio_id)
    ).first()

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un servicio con ese identificador",
        )

    return servicio


# ---------------------------------------------------------------------------
# Catálogo de servicios — cierra la brecha 5
# ---------------------------------------------------------------------------


@enrutador.get(
    "/servicios",
    response_model=list[ServicioPublico],
    summary="Servicios ofrecidos por los proveedores",
)
def listar_servicios(
    sesion: SesionBD,
    tipo: str | None = Query(default=None, description="Filtrar por tipo de servicio"),
    distrito: str | None = Query(default=None, description="Filtrar por distrito"),
    recurso_id: int | None = Query(default=None, description="Servicios de un recurso"),
    limite: int = Query(default=50, ge=1, le=200),
) -> list[ServicioPublico]:
    """Devuelve los servicios publicados, con su capacidad y su precio.

    **Es lo que cierra la brecha 5**: hasta ahora, saber si un proveedor podía
    atender a doce personas un sábado exigía llamar. Aquí está escrito.
    """
    consulta = (
        select(Servicio)
        .options(selectinload(Servicio.proveedor), selectinload(Servicio.disponibilidades))
        .join(Servicio.proveedor)
        .where(Servicio.esta_publicado.is_(True), Proveedor.esta_activo.is_(True))
        .order_by(Servicio.tipo, Servicio.nombre)
        .limit(limite)
    )

    if tipo:
        consulta = consulta.where(Servicio.tipo == tipo)

    if distrito:
        consulta = consulta.where(Proveedor.distrito == distrito.upper())

    if recurso_id is not None:
        consulta = consulta.where(Servicio.recurso_id == recurso_id)

    return [_a_servicio_publico(servicio) for servicio in sesion.scalars(consulta)]


@enrutador.get(
    "/servicios/{servicio_id}",
    response_model=ServicioPublico,
    summary="Ficha de un servicio",
)
def consultar_servicio(servicio_id: int, sesion: SesionBD) -> ServicioPublico:
    return _a_servicio_publico(_buscar_servicio(sesion, servicio_id))


@enrutador.post(
    "/servicios/{servicio_id}/disponibilidad",
    response_model=RespuestaDisponibilidad,
    summary="Comprueba si un servicio se puede pedir para esa fecha",
)
def comprobar_disponibilidad(
    servicio_id: int, consulta: ConsultaDisponibilidad, sesion: SesionBD
) -> RespuestaDisponibilidad:
    """Responde si se puede pedir, y si no, **todos** los motivos.

    Se consulta antes de enviar la solicitud para que el visitante no descubra
    que no hay sitio después de rellenar el formulario entero.
    """
    servicio = _buscar_servicio(sesion, servicio_id)

    motivos = revisar_disponibilidad(
        sesion,
        servicio,
        consulta.fecha,
        consulta.numero_personas,
        consulta.hora,
    )

    tramos = tramos_del_dia(sesion, servicio.id, consulta.fecha)
    libres = None

    if tramos:
        cupo = max(tramo.cupo for tramo in tramos)
        libres = max(0, cupo - plazas_ya_comprometidas(sesion, servicio.id, consulta.fecha))

    return RespuestaDisponibilidad(
        servicio_id=servicio.id,
        fecha=consulta.fecha,
        numero_personas=consulta.numero_personas,
        hay_disponibilidad=not motivos,
        motivos=motivos,
        plazas_libres=libres,
    )


# ---------------------------------------------------------------------------
# Publicación de servicios — panel del proveedor
# ---------------------------------------------------------------------------


def _proveedor_del_que_pide(sesion: SesionBD, usuario) -> Proveedor:
    """El proveedor que administra quien hace la petición, o error 403."""
    if usuario.rol != RolUsuario.PROVEEDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los proveedores pueden publicar servicios",
        )

    proveedor = proveedor_del_usuario(sesion, usuario)

    if proveedor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tu cuenta tiene rol de proveedor pero no está asociada a ninguna "
                "ficha de proveedor. Pide a un administrador que la asocie."
            ),
        )

    return proveedor


@enrutador.post(
    "/servicios",
    response_model=ServicioPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Publica un servicio nuevo",
)
def publicar_servicio(
    datos: ServicioNuevo, sesion: SesionBD, usuario: UsuarioRequerido
) -> ServicioPublico:
    proveedor = _proveedor_del_que_pide(sesion, usuario)

    servicio = Servicio(proveedor_id=proveedor.id, **datos.model_dump())

    sesion.add(servicio)
    sesion.commit()
    sesion.refresh(servicio)

    return _a_servicio_publico(servicio)


@enrutador.post(
    "/servicios/{servicio_id}/tramos",
    response_model=ServicioPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Publica un tramo de disponibilidad",
)
def publicar_tramo(
    servicio_id: int, datos: TramoNuevo, sesion: SesionBD, usuario: UsuarioRequerido
) -> ServicioPublico:
    proveedor = _proveedor_del_que_pide(sesion, usuario)
    servicio = _buscar_servicio(sesion, servicio_id)

    if servicio.proveedor_id != proveedor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese servicio no es tuyo",
        )

    sesion.add(DisponibilidadServicio(servicio_id=servicio.id, **datos.model_dump()))
    sesion.commit()
    sesion.refresh(servicio)

    return _a_servicio_publico(servicio)


# ---------------------------------------------------------------------------
# Solicitudes — cierra la brecha 6
# ---------------------------------------------------------------------------


@enrutador.post(
    "/solicitudes",
    response_model=SolicitudPublica,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita un servicio a su proveedor",
)
def crear_solicitud(
    datos: SolicitudNueva, sesion: SesionBD, usuario: UsuarioOpcional
) -> SolicitudPublica:
    """Crea la solicitud y **registra su primer estado**.

    Funciona sin cuenta, igual que el resto del recorrido del visitante: por
    eso se piden nombre y contacto en el propio formulario.

    Se comprueba la disponibilidad antes de crearla. Aceptar una solicitud que
    ya se sabe imposible sería hacerle perder el tiempo a las dos partes.
    """
    servicio = _buscar_servicio(sesion, datos.servicio_id)

    motivos = revisar_disponibilidad(
        sesion,
        servicio,
        datos.fecha_servicio,
        datos.numero_personas,
        datos.hora_servicio,
    )

    if motivos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "El servicio no está disponible así", "motivos": motivos},
        )

    solicitud = SolicitudCoordinacion(
        servicio_id=servicio.id,
        usuario_id=usuario.id if usuario is not None else None,
        itinerario_id=datos.itinerario_id,
        fecha_servicio=datos.fecha_servicio,
        hora_servicio=datos.hora_servicio,
        numero_personas=datos.numero_personas,
        nombre_contacto=datos.nombre_contacto,
        telefono_contacto=datos.telefono_contacto,
        correo_contacto=datos.correo_contacto,
        mensaje=datos.mensaje,
        estado=EstadoSolicitud.ENVIADA,
    )

    sesion.add(solicitud)
    sesion.flush()

    # El primer movimiento del historial. Sin él, una solicitud confirmada de
    # un golpe tendría cero interacciones registradas y el indicador mentiría.
    solicitud.cambios.append(
        CambioDeEstado(
            solicitud_id=solicitud.id,
            estado_anterior=None,
            estado_nuevo=EstadoSolicitud.ENVIADA,
            usuario_id=usuario.id if usuario is not None else None,
            rol_de_quien_cambio=usuario.rol if usuario is not None else "visitante",
        )
    )

    sesion.commit()
    sesion.refresh(solicitud)

    return _a_solicitud_publica(solicitud)


@enrutador.get(
    "/solicitudes",
    response_model=list[SolicitudPublica],
    summary="Solicitudes que puedes ver",
)
def listar_solicitudes(
    sesion: SesionBD,
    usuario: UsuarioRequerido,
    estado: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
) -> list[SolicitudPublica]:
    """Devuelve las solicitudes según el rol de quien pregunta.

    - **Operador y administrador:** todas.
    - **Proveedor:** solo las de sus servicios.
    - **Visitante y gestor:** solo las suyas.

    Exige sesión: sin cuenta no hay listado, porque no habría forma de saber
    cuáles son «las tuyas» sin enseñar las de otros.
    """
    consulta = consulta_de_solicitudes_visibles(sesion, usuario).limit(limite)

    if estado:
        consulta = consulta.where(SolicitudCoordinacion.estado == estado)

    return [_a_solicitud_publica(solicitud) for solicitud in sesion.scalars(consulta)]


@enrutador.get(
    "/solicitudes/{solicitud_id}",
    response_model=SolicitudPublica,
    summary="Una solicitud con su historial completo",
)
def consultar_solicitud(
    solicitud_id: int, sesion: SesionBD, usuario: UsuarioOpcional
) -> SolicitudPublica:
    """Devuelve la solicitud y **todo lo que le ha pasado**.

    Las solicitudes creadas sin cuenta son accesibles por identificador, igual
    que los itinerarios: es lo que permite a quien pidió sin registrarse seguir
    el estado de lo que pidió.
    """
    solicitud = sesion.scalars(
        select(SolicitudCoordinacion)
        .options(
            selectinload(SolicitudCoordinacion.servicio).selectinload(Servicio.proveedor),
            selectinload(SolicitudCoordinacion.cambios),
        )
        .where(SolicitudCoordinacion.id == solicitud_id)
    ).first()

    hay_acceso = solicitud is not None and (
        solicitud.usuario_id is None or puede_ver_solicitud(sesion, solicitud, usuario)
    )

    if not hay_acceso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una solicitud con ese identificador",
        )

    assert solicitud is not None  # ya lo comprobó hay_acceso

    return _a_solicitud_publica(solicitud)


@enrutador.post(
    "/solicitudes/{solicitud_id}/estado",
    response_model=SolicitudPublica,
    summary="Mueve una solicitud de estado",
)
def mover_solicitud(
    solicitud_id: int,
    cambio: CambioSolicitado,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
) -> SolicitudPublica:
    """Cambia el estado y deja constancia de quién lo hizo y cuándo.

    Las reglas viven en ``servicios/coordinacion.py``, no aquí: qué
    transiciones son válidas y quién puede provocarlas son reglas de negocio, y
    repartirlas entre los endpoints sería garantizar que algún día no
    coincidan.
    """
    solicitud = sesion.scalars(
        select(SolicitudCoordinacion)
        .options(
            selectinload(SolicitudCoordinacion.servicio).selectinload(Servicio.proveedor),
            selectinload(SolicitudCoordinacion.cambios),
        )
        .where(SolicitudCoordinacion.id == solicitud_id)
    ).first()

    if solicitud is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una solicitud con ese identificador",
        )

    # Confirmar sin precio dejaría un acuerdo sin la única cifra que importa.
    if (
        cambio.nuevo_estado == EstadoSolicitud.CONFIRMADA
        and cambio.precio_acordado_soles is None
        and solicitud.precio_acordado_soles is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Para confirmar hay que indicar el precio acordado",
        )

    try:
        cambiar_estado(
            sesion,
            solicitud,
            cambio.nuevo_estado,
            usuario=usuario,
            nota=cambio.nota,
            precio_acordado=(
                float(cambio.precio_acordado_soles)
                if cambio.precio_acordado_soles is not None
                else None
            ),
        )
    except SinPermiso as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ErrorDeCoordinacion as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    sesion.commit()
    sesion.refresh(solicitud)

    return _a_solicitud_publica(solicitud)


# ---------------------------------------------------------------------------
# El indicador del incremento
# ---------------------------------------------------------------------------


@enrutador.get(
    "/indicadores/coordinacion",
    response_model=ResumenDeCoordinacion,
    summary="Indicador del Incremento 5",
)
def indicador_de_coordinacion(sesion: SesionBD) -> ResumenDeCoordinacion:
    """Cuántas interacciones hacen falta para confirmar un servicio.

    Se calcula sobre lo registrado, no sobre una estimación. Si todavía no hay
    ninguna solicitud confirmada, las medias van a ``null`` y no a cero: una
    media de cero casos no es cero, es que no hay dato.
    """
    por_estado = dict(
        sesion.execute(
            select(SolicitudCoordinacion.estado, func.count()).group_by(
                SolicitudCoordinacion.estado
            )
        ).all()
    )

    total = sum(por_estado.values())
    confirmadas = por_estado.get(EstadoSolicitud.CONFIRMADA.value, 0)
    rechazadas = por_estado.get(EstadoSolicitud.RECHAZADA.value, 0)

    solicitudes_confirmadas = list(
        sesion.scalars(
            select(SolicitudCoordinacion)
            .options(selectinload(SolicitudCoordinacion.cambios))
            .where(SolicitudCoordinacion.estado == EstadoSolicitud.CONFIRMADA)
        ).all()
    )

    interacciones_medias = None
    horas_medias = None

    if solicitudes_confirmadas:
        interacciones_medias = round(
            sum(s.interacciones for s in solicitudes_confirmadas) / len(solicitudes_confirmadas),
            2,
        )

        duraciones = [
            (s.cambios[-1].ocurrido_en - s.cambios[0].ocurrido_en).total_seconds() / 3600
            for s in solicitudes_confirmadas
            if len(s.cambios) >= 2
        ]

        if duraciones:
            horas_medias = round(sum(duraciones) / len(duraciones), 2)

    return ResumenDeCoordinacion(
        total_solicitudes=total,
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        pendientes=total - confirmadas - rechazadas,
        interacciones_medias_hasta_confirmar=interacciones_medias,
        horas_medias_hasta_confirmar=horas_medias,
    )


@enrutador.get(
    "/proveedores/mio",
    response_model=ProveedorPublico,
    summary="La ficha de proveedor de quien ha iniciado sesión",
)
def mi_proveedor(sesion: SesionBD, usuario: UsuarioRequerido) -> ProveedorPublico:
    """Devuelve el proveedor que administra el usuario actual.

    Lo usa el panel para saber si hay algo que gestionar antes de pintarlo.
    """
    proveedor = proveedor_del_usuario(sesion, usuario)

    if proveedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tu cuenta no administra ninguna ficha de proveedor",
        )

    return _a_proveedor_publico(proveedor)


@enrutador.get(
    "/proveedores/mio/servicios",
    response_model=list[ServicioPublico],
    summary="Los servicios del proveedor de quien ha iniciado sesión",
)
def mis_servicios(sesion: SesionBD, usuario: UsuarioRequerido) -> list[ServicioPublico]:
    """Incluye los NO publicados: el proveedor tiene que poder ver sus borradores."""
    proveedor = _proveedor_del_que_pide(sesion, usuario)

    servicios = sesion.scalars(
        select(Servicio)
        .options(selectinload(Servicio.proveedor), selectinload(Servicio.disponibilidades))
        .where(Servicio.proveedor_id == proveedor.id)
        .order_by(Servicio.nombre)
    ).all()

    return [_a_servicio_publico(servicio) for servicio in servicios]


@enrutador.get(
    "/servicios/{servicio_id}/plazas",
    summary="Plazas libres de un servicio en una fecha",
)
def plazas_libres(servicio_id: int, fecha: date, sesion: SesionBD) -> dict:
    """Cuánto cupo queda ese día, contando lo ya comprometido."""
    servicio = _buscar_servicio(sesion, servicio_id)
    tramos = tramos_del_dia(sesion, servicio.id, fecha)

    if not tramos:
        return {"servicio_id": servicio.id, "fecha": fecha, "atiende": False, "libres": 0}

    cupo = max(tramo.cupo for tramo in tramos)
    comprometidas = plazas_ya_comprometidas(sesion, servicio.id, fecha)

    return {
        "servicio_id": servicio.id,
        "fecha": fecha,
        "atiende": True,
        "cupo": cupo,
        "comprometidas": comprometidas,
        "libres": max(0, cupo - comprometidas),
    }
