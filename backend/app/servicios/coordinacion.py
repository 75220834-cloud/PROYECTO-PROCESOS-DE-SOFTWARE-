"""Reglas de la coordinación con proveedores (Incremento 5).

Aquí vive lo que hace que la brecha 6 quede cerrada de verdad y no solo
guardada: **quién puede mover una solicitud, adónde puede moverla, y qué queda
registrado cuando lo hace**.

## Por qué las transiciones no las decide el endpoint

Si cada endpoint pudiera poner cualquier estado, tarde o temprano habría uno
que resucita una solicitud rechazada o que confirma una cancelada. La tabla
``TRANSICIONES_VALIDAS`` del modelo declara el grafo completo y este módulo lo
hace cumplir en un solo sitio.

## Por qué los permisos tampoco

El plan de trabajo pide que *«un proveedor solo vea las solicitudes de sus
servicios»*. Eso no es una comprobación de interfaz: es una regla de negocio, y
si vive en el frontend no existe. Aquí está, y hay pruebas que lo fijan.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.modelos.coordinacion import (
    TRANSICIONES_VALIDAS,
    CambioDeEstado,
    DisponibilidadServicio,
    EstadoSolicitud,
    Proveedor,
    Servicio,
    SolicitudCoordinacion,
)
from app.modelos.usuario import RolUsuario, Usuario


class ErrorDeCoordinacion(Exception):
    """Algo que el visitante o el proveedor pidió y no se puede hacer.

    Se distingue de un fallo del programa: esto es una regla de negocio que no
    se cumple, y quien llama debe convertirlo en una respuesta 4xx con el
    mensaje tal cual, porque el mensaje está escrito para leerse.
    """


class TransicionNoPermitida(ErrorDeCoordinacion):
    """Se intentó mover una solicitud a un estado al que no puede ir."""


class SinPermiso(ErrorDeCoordinacion):
    """Quien lo pide no tiene derecho a tocar esta solicitud."""


# ---------------------------------------------------------------------------
# Quién puede hacer qué
# ---------------------------------------------------------------------------

#: Estados que solo puede provocar el proveedor del servicio (o un operador).
#: El visitante no puede confirmarse a sí mismo una reserva: eso sería volver a
#: no tener acuerdo, que es justo la brecha que se está cerrando.
ESTADOS_DEL_PROVEEDOR = frozenset(
    {
        EstadoSolicitud.EN_REVISION,
        EstadoSolicitud.CONTRAPROPUESTA,
        EstadoSolicitud.CONFIRMADA,
        EstadoSolicitud.RECHAZADA,
    }
)

#: Lo único que puede hacer quien pidió el servicio: echarse atrás.
ESTADOS_DEL_VISITANTE = frozenset({EstadoSolicitud.CANCELADA})

#: Roles que ven y coordinan todas las solicitudes, no solo las suyas.
ROLES_CON_VISION_COMPLETA = frozenset({RolUsuario.OPERADOR, RolUsuario.ADMINISTRADOR})


def proveedor_del_usuario(sesion: Session, usuario: Usuario) -> Proveedor | None:
    """El proveedor que administra este usuario, si administra alguno."""
    return sesion.scalars(
        select(Proveedor).where(Proveedor.usuario_id == usuario.id).limit(1)
    ).first()


def puede_ver_solicitud(
    sesion: Session, solicitud: SolicitudCoordinacion, usuario: Usuario | None
) -> bool:
    """Si este usuario tiene derecho a ver esta solicitud.

    Cuatro casos, y el orden importa:

    1. **Operadores y administradores** ven todo: coordinar es su trabajo.
    2. **Quien la creó** ve la suya.
    3. **El proveedor del servicio** ve las que le llegan, y solo esas.
    4. **Sin cuenta**, nadie ve nada por listado. Las solicitudes anónimas se
       recuperan por identificador, igual que los itinerarios, para que quien
       pidió sin registrarse pueda seguir su estado.
    """
    if usuario is None:
        return False

    if usuario.rol in ROLES_CON_VISION_COMPLETA:
        return True

    if solicitud.usuario_id is not None and solicitud.usuario_id == usuario.id:
        return True

    if usuario.rol == RolUsuario.PROVEEDOR:
        proveedor = proveedor_del_usuario(sesion, usuario)
        return proveedor is not None and solicitud.servicio.proveedor_id == proveedor.id

    return False


def consulta_de_solicitudes_visibles(sesion: Session, usuario: Usuario) -> Select:
    """Consulta con las solicitudes que este usuario puede listar.

    Se devuelve la consulta y no el resultado para que quien llame pueda
    añadirle filtros y paginación sin traerse todo a memoria.
    """
    base = (
        select(SolicitudCoordinacion)
        .options(
            selectinload(SolicitudCoordinacion.servicio).selectinload(Servicio.proveedor),
            selectinload(SolicitudCoordinacion.cambios),
        )
        .order_by(SolicitudCoordinacion.creado_en.desc())
    )

    if usuario.rol in ROLES_CON_VISION_COMPLETA:
        return base

    if usuario.rol == RolUsuario.PROVEEDOR:
        proveedor = proveedor_del_usuario(sesion, usuario)

        if proveedor is None:
            # Un usuario con rol de proveedor pero sin ficha asociada no ve
            # nada. Devolver todo «porque es proveedor» sería el fallo grave.
            return base.where(SolicitudCoordinacion.id.is_(None))

        return base.join(SolicitudCoordinacion.servicio).where(
            Servicio.proveedor_id == proveedor.id
        )

    # Visitantes y gestores: solo lo suyo.
    return base.where(SolicitudCoordinacion.usuario_id == usuario.id)


def _rol_para_el_cambio(
    sesion: Session, solicitud: SolicitudCoordinacion, usuario: Usuario | None, nuevo: str
) -> str:
    """Comprueba que este usuario puede provocar este estado, y devuelve su rol.

    Devolver el rol además de comprobarlo evita que quien llama lo vuelva a
    calcular para guardarlo en el historial.
    """
    if usuario is None:
        # Sin cuenta solo se puede cancelar lo propio, y de eso se encarga
        # quien llama comprobando el identificador de la solicitud.
        if nuevo not in ESTADOS_DEL_VISITANTE:
            raise SinPermiso(
                "Para responder a una solicitud hay que iniciar sesión como el "
                "proveedor del servicio."
            )
        return "visitante"

    if usuario.rol in ROLES_CON_VISION_COMPLETA:
        return usuario.rol

    if nuevo in ESTADOS_DEL_VISITANTE:
        # Cancelar lo puede hacer quien la creó, y también el proveedor si el
        # servicio deja de estar disponible.
        if not puede_ver_solicitud(sesion, solicitud, usuario):
            raise SinPermiso("Esta solicitud no es tuya.")
        return usuario.rol

    if nuevo in ESTADOS_DEL_PROVEEDOR:
        if usuario.rol != RolUsuario.PROVEEDOR:
            raise SinPermiso("Solo el proveedor del servicio puede responder a una solicitud.")

        proveedor = proveedor_del_usuario(sesion, usuario)

        if proveedor is None or solicitud.servicio.proveedor_id != proveedor.id:
            raise SinPermiso("Esta solicitud no es de ninguno de tus servicios.")

        return usuario.rol

    raise SinPermiso("No tienes permiso para hacer ese cambio.")


def cambiar_estado(
    sesion: Session,
    solicitud: SolicitudCoordinacion,
    nuevo_estado: str,
    usuario: Usuario | None = None,
    nota: str | None = None,
    precio_acordado: float | None = None,
) -> CambioDeEstado:
    """Mueve una solicitud de estado y **deja constancia**.

    No hace ``commit``: quien llama decide la transacción.

    Las tres cosas que comprueba, en este orden:

    1. Que la transición esté permitida por el grafo de estados.
    2. Que quien la pide tenga derecho a provocar ese estado.
    3. Que, si se confirma, quede el precio acordado.
    """
    anterior = solicitud.estado

    permitidos = TRANSICIONES_VALIDAS.get(anterior, frozenset())

    if nuevo_estado not in permitidos:
        legibles = ", ".join(sorted(permitidos)) if permitidos else "ninguno"
        raise TransicionNoPermitida(
            f"Una solicitud «{anterior}» no puede pasar a «{nuevo_estado}». "
            f"Desde ahí solo se puede ir a: {legibles}."
        )

    rol = _rol_para_el_cambio(sesion, solicitud, usuario, nuevo_estado)

    solicitud.estado = nuevo_estado

    if nota:
        solicitud.respuesta_proveedor = nota

    if precio_acordado is not None:
        solicitud.precio_acordado_soles = precio_acordado

    cambio = CambioDeEstado(
        solicitud_id=solicitud.id,
        estado_anterior=anterior,
        estado_nuevo=nuevo_estado,
        usuario_id=usuario.id if usuario is not None else None,
        rol_de_quien_cambio=rol,
        nota=nota,
    )

    solicitud.cambios.append(cambio)
    sesion.flush()

    return cambio


# ---------------------------------------------------------------------------
# Disponibilidad: lo que hace verificable la capacidad del proveedor
# ---------------------------------------------------------------------------


def tramos_del_dia(sesion: Session, servicio_id: int, fecha: date) -> list[DisponibilidadServicio]:
    """Tramos en los que un servicio atiende ese día de la semana."""
    return list(
        sesion.scalars(
            select(DisponibilidadServicio)
            .where(
                DisponibilidadServicio.servicio_id == servicio_id,
                DisponibilidadServicio.dia_semana == fecha.weekday(),
            )
            .order_by(DisponibilidadServicio.hora_inicio)
        ).all()
    )


def plazas_ya_comprometidas(sesion: Session, servicio_id: int, fecha: date) -> int:
    """Personas ya comprometidas para ese servicio y esa fecha.

    Cuentan las solicitudes **confirmadas y las que siguen vivas**: una que
    está en revisión todavía puede confirmarse, y prometer su plaza a otro sería
    exactamente el problema que la brecha 5 describe.
    """
    vivas = (
        EstadoSolicitud.ENVIADA,
        EstadoSolicitud.EN_REVISION,
        EstadoSolicitud.CONTRAPROPUESTA,
        EstadoSolicitud.CONFIRMADA,
    )

    filas = sesion.scalars(
        select(SolicitudCoordinacion.numero_personas).where(
            SolicitudCoordinacion.servicio_id == servicio_id,
            SolicitudCoordinacion.fecha_servicio == fecha,
            SolicitudCoordinacion.estado.in_(vivas),
        )
    ).all()

    return sum(filas)


def revisar_disponibilidad(
    sesion: Session,
    servicio: Servicio,
    fecha: date,
    personas: int,
    hora: time | None = None,
    ahora: datetime | None = None,
) -> list[str]:
    """Devuelve los motivos por los que este servicio NO se puede pedir así.

    Lista vacía significa que se puede. Se devuelven **todos** los motivos y no
    el primero, porque decirle a alguien «no hay sitio» y, cuando lo arregla,
    «además llegas tarde», es la clase de trato que hace abandonar un
    formulario.

    Es la comprobación que cierra la brecha 5: *la capacidad y condiciones del
    proveedor no son verificables al decidir*. Ahora lo son, antes de enviar.
    """
    motivos: list[str] = []

    if not servicio.esta_publicado:
        motivos.append("Este servicio no está publicado.")

    if personas > servicio.capacidad_maxima:
        motivos.append(
            f"El servicio atiende como máximo a {servicio.capacidad_maxima} "
            f"persona(s) y se pidieron {personas}."
        )

    # --- Antelación -------------------------------------------------------
    ahora = ahora or datetime.now(UTC)

    # La fecha del servicio se compara a las 00:00 de ese día: es lo más
    # temprano a lo que podría ocurrir, así que si ni eso llega a la antelación
    # mínima, ninguna hora de ese día lo hace.
    momento_servicio = datetime.combine(fecha, hora or time(0, 0), tzinfo=UTC)
    antelacion = momento_servicio - ahora

    if antelacion < timedelta(hours=servicio.antelacion_minima_horas):
        motivos.append(
            f"Este servicio pide al menos {servicio.antelacion_minima_horas} horas "
            "de antelación."
        )

    # --- Día de atención --------------------------------------------------
    tramos = tramos_del_dia(sesion, servicio.id, fecha)

    if not tramos:
        motivos.append(f"El proveedor no atiende los {_nombre_del_dia(fecha.weekday())}.")
    elif hora is not None and not any(t.hora_inicio <= hora <= t.hora_fin for t in tramos):
        horarios = ", ".join(f"{t.hora_inicio:%H:%M}–{t.hora_fin:%H:%M}" for t in tramos)
        motivos.append(f"A esa hora no atiende. Ese día atiende de {horarios}.")

    # --- Cupo -------------------------------------------------------------
    if tramos:
        cupo_del_dia = max(t.cupo for t in tramos)
        comprometidas = plazas_ya_comprometidas(sesion, servicio.id, fecha)

        if comprometidas + personas > cupo_del_dia:
            libres = max(0, cupo_del_dia - comprometidas)
            motivos.append(
                f"Ese día quedan {libres} plaza(s) de {cupo_del_dia} y se pidieron " f"{personas}."
            )

    return motivos


#: Nombres de los días para los mensajes. Van en plural porque siempre se usan
#: como «no atiende los martes».
_DIAS = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábados",
    "domingos",
)


def _nombre_del_dia(dia_semana: int) -> str:
    return _DIAS[dia_semana]
