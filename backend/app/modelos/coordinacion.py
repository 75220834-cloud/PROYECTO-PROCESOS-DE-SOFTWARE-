"""Proveedores, servicios y solicitudes de coordinación (Incremento 5).

Cierra dos brechas a la vez:

- **Brecha 5:** *la capacidad y condiciones del proveedor no son verificables al
  decidir.* Se cierra con ``Proveedor``, ``Servicio`` y
  ``DisponibilidadServicio``: quién ofrece qué, con qué capacidad, a qué precio
  y qué días.
- **Brecha 6:** *no existe punto único de coordinación ni registro de lo
  acordado.* Se cierra con ``SolicitudCoordinacion``, que guarda **cada cambio
  de estado con su fecha**. Lo acordado deja de vivir en un WhatsApp.

## Por qué el historial de estados es una tabla y no un campo

Un campo ``estado`` dice dónde está la solicitud **ahora**. La brecha habla de
*registro de lo acordado*, que es otra cosa: hace falta saber cuándo se envió,
cuándo respondió el proveedor y cuánto tardó.

Eso no cabe en un campo. Y sin ello no se puede calcular el indicador del
incremento, que mide justamente cuántas interacciones hacen falta para
confirmar un servicio.

## Sobre los precios, otra vez

Igual que con las tarifas de transporte: **rango, fecha de referencia y
fuente**. Aquí la fuente es el propio proveedor, que es lo más parecido a un
dato verificado que tiene el proyecto —lo publica quien cobra— pero sigue
teniendo fecha, porque un precio de hace dos años no sirve.
"""

from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from app.modelos.itinerario import Itinerario
from app.modelos.usuario import Usuario


class TipoServicio(StrEnum):
    """Qué clase de servicio ofrece un proveedor.

    El conjunto sale de lo que necesita un visitante del valle para completar
    un itinerario: llegar, comer, dormir, entender lo que ve y llevárselo.
    """

    TRANSPORTE = "transporte"
    ALIMENTACION = "alimentacion"
    HOSPEDAJE = "hospedaje"
    GUIADO = "guiado"
    TALLER = "taller"
    ARTESANIA = "artesania"


class EstadoSolicitud(StrEnum):
    """Por dónde va una solicitud de coordinación.

    El orden importa: es el ciclo de vida que el indicador del incremento
    cuenta. ``ENVIADA`` y ``CONFIRMADA`` son los dos extremos que fija la
    verificación del plan de trabajo.
    """

    #: El visitante la mandó y el proveedor aún no la ha visto.
    ENVIADA = "enviada"
    #: El proveedor la leyó y está mirando si puede.
    EN_REVISION = "en_revision"
    #: El proveedor propone cambiar algo (hora, número de personas, precio).
    CONTRAPROPUESTA = "contrapropuesta"
    #: Acuerdo cerrado. Es el estado que persigue el indicador.
    CONFIRMADA = "confirmada"
    #: El proveedor no puede.
    RECHAZADA = "rechazada"
    #: El visitante se echó atrás.
    CANCELADA = "cancelada"


#: Desde qué estado se puede pasar a cuál. Tener esto explícito evita que un
#: endpoint mueva una solicitud a cualquier sitio: una solicitud rechazada no
#: puede volver a estar «en revisión», y una confirmada solo se puede cancelar.
TRANSICIONES_VALIDAS: dict[str, frozenset[str]] = {
    EstadoSolicitud.ENVIADA: frozenset(
        {
            EstadoSolicitud.EN_REVISION,
            EstadoSolicitud.CONFIRMADA,
            EstadoSolicitud.RECHAZADA,
            EstadoSolicitud.CANCELADA,
        }
    ),
    EstadoSolicitud.EN_REVISION: frozenset(
        {
            EstadoSolicitud.CONTRAPROPUESTA,
            EstadoSolicitud.CONFIRMADA,
            EstadoSolicitud.RECHAZADA,
            EstadoSolicitud.CANCELADA,
        }
    ),
    EstadoSolicitud.CONTRAPROPUESTA: frozenset(
        {EstadoSolicitud.CONFIRMADA, EstadoSolicitud.RECHAZADA, EstadoSolicitud.CANCELADA}
    ),
    # Estados finales: de aquí solo se sale cancelando lo confirmado.
    EstadoSolicitud.CONFIRMADA: frozenset({EstadoSolicitud.CANCELADA}),
    EstadoSolicitud.RECHAZADA: frozenset(),
    EstadoSolicitud.CANCELADA: frozenset(),
}


class Proveedor(Base):
    """Quien ofrece un servicio: una empresa, una asociación o una persona."""

    __tablename__ = "proveedor"

    id: Mapped[int] = mapped_column(primary_key=True)

    #: Quién administra este proveedor en la plataforma. Nulo mientras el
    #: proveedor exista como ficha de demostración sin cuenta asociada.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    distrito: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    #: Teléfono y correo de contacto. Son los datos que hoy se buscan a mano en
    #: Facebook, y que la brecha 6 quiere tener en un solo sitio.
    telefono: Mapped[str | None] = mapped_column(String(40))
    correo: Mapped[str | None] = mapped_column(String(255))

    descripcion: Mapped[str | None] = mapped_column(Text)

    #: **Marca de dato de demostración.** El proyecto no tiene convenios con
    #: proveedores reales del valle, así que los que hay están inventados para
    #: poder enseñar el flujo. Que esto sea una columna y no un comentario es
    #: deliberado: la interfaz lo muestra y nadie puede confundirse.
    es_demostracion: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    esta_activo: Mapped[bool] = mapped_column(nullable=False, default=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    usuario: Mapped[Usuario | None] = relationship()
    servicios: Mapped[list["Servicio"]] = relationship(
        back_populates="proveedor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Proveedor {self.id} {self.nombre}>"


class Servicio(Base):
    """Algo concreto que un proveedor ofrece, con su capacidad y su precio."""

    __tablename__ = "servicio"

    id: Mapped[int] = mapped_column(primary_key=True)

    proveedor_id: Mapped[int] = mapped_column(
        ForeignKey("proveedor.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: Recurso turístico al que está asociado, si lo está. Un taller de mates
    #: burilados en Cochas se asocia al recurso; un servicio de taxi no.
    recurso_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurso_turistico.id", ondelete="SET NULL"), nullable=True, index=True
    )

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text)

    # --- Capacidad: lo que la brecha 5 quiere hacer verificable -----------
    capacidad_maxima: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duracion_min: Mapped[int | None] = mapped_column(Integer)

    #: Con cuánta antelación hay que avisar. Un almuerzo para veinte no se
    #: improvisa, y hasta ahora el visitante no tenía forma de saberlo.
    antelacion_minima_horas: Mapped[int] = mapped_column(Integer, nullable=False, default=24)

    # --- Precio: rango, fecha y fuente, igual que en el transporte --------
    precio_min_soles: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    precio_max_soles: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    #: Qué incluye el precio: por persona, por grupo, por noche...
    unidad_precio: Mapped[str] = mapped_column(String(24), nullable=False, default="por_persona")
    fecha_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    idiomas: Mapped[str | None] = mapped_column(String(80))
    es_accesible: Mapped[bool] = mapped_column(nullable=False, default=False)

    esta_publicado: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    proveedor: Mapped[Proveedor] = relationship(back_populates="servicios")
    disponibilidades: Mapped[list["DisponibilidadServicio"]] = relationship(
        back_populates="servicio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("precio_max_soles >= precio_min_soles", name="ck_servicio_rango_precio"),
        CheckConstraint("precio_min_soles >= 0", name="ck_servicio_precio_positivo"),
        CheckConstraint("capacidad_maxima > 0", name="ck_servicio_capacidad"),
        CheckConstraint("antelacion_minima_horas >= 0", name="ck_servicio_antelacion"),
        CheckConstraint(
            "tipo IN ('transporte', 'alimentacion', 'hospedaje', 'guiado', 'taller', 'artesania')",
            name="ck_servicio_tipo",
        ),
        CheckConstraint(
            "unidad_precio IN ('por_persona', 'por_grupo', 'por_noche', 'por_hora')",
            name="ck_servicio_unidad",
        ),
    )

    @property
    def precio_medio_soles(self) -> float:
        return float(self.precio_min_soles + self.precio_max_soles) / 2

    def __repr__(self) -> str:
        return f"<Servicio {self.id} {self.nombre} ({self.tipo})>"


class DisponibilidadServicio(Base):
    """Qué días y a qué horas está disponible un servicio, y con qué cupo.

    Se modela por **día de la semana** y no por fecha concreta porque eso es lo
    que un proveedor pequeño puede mantener: «los sábados de 9 a 17». Publicar
    fecha a fecha exigiría que alguien actualizara un calendario todos los
    días, y en cuanto dejara de hacerlo el dato sería peor que no tenerlo.
    """

    __tablename__ = "disponibilidad_servicio"

    id: Mapped[int] = mapped_column(primary_key=True)

    servicio_id: Mapped[int] = mapped_column(
        ForeignKey("servicio.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: 0 es lunes y 6 es domingo, igual que ``date.weekday()`` de Python. Se usa
    #: el mismo convenio que en ``horario_atencion`` para no tener dos.
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)

    #: Cupo de ese tramo. Puede ser menor que la capacidad del servicio: un
    #: restaurante con sitio para 40 puede reservar solo 12 a la plataforma.
    cupo: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    servicio: Mapped[Servicio] = relationship(back_populates="disponibilidades")

    __table_args__ = (
        UniqueConstraint(
            "servicio_id", "dia_semana", "hora_inicio", name="uq_disponibilidad_tramo"
        ),
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_disponibilidad_dia"),
        CheckConstraint("hora_fin > hora_inicio", name="ck_disponibilidad_horas"),
        CheckConstraint("cupo > 0", name="ck_disponibilidad_cupo"),
    )

    def __repr__(self) -> str:
        return f"<Disponibilidad servicio {self.servicio_id} día {self.dia_semana}>"


class SolicitudCoordinacion(Base):
    """Una petición del visitante a un proveedor, con todo lo acordado."""

    __tablename__ = "solicitud_coordinacion"

    id: Mapped[int] = mapped_column(primary_key=True)

    servicio_id: Mapped[int] = mapped_column(
        ForeignKey("servicio.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: Nulo si se pidió sin cuenta. La aplicación funciona sin registro, y
    #: obligar a registrarse justo para coordinar rompería esa promesa.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    #: Itinerario del que sale la solicitud, si sale de uno. Es lo que conecta
    #: el Incremento 5 con el 4: se pide desde el plan, no desde un formulario
    #: suelto.
    itinerario_id: Mapped[int | None] = mapped_column(
        ForeignKey("itinerario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # --- Lo que se pide ---------------------------------------------------
    fecha_servicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_servicio: Mapped[time | None] = mapped_column(Time)
    numero_personas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    #: Cómo contactar a quien pide, porque puede no tener cuenta.
    nombre_contacto: Mapped[str] = mapped_column(String(160), nullable=False)
    telefono_contacto: Mapped[str | None] = mapped_column(String(40))
    correo_contacto: Mapped[str | None] = mapped_column(String(255))

    mensaje: Mapped[str | None] = mapped_column(Text)

    # --- Lo que se acuerda ------------------------------------------------
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EstadoSolicitud.ENVIADA, index=True
    )

    #: Precio finalmente acordado. Nulo mientras no se confirme: antes de eso
    #: solo existe el rango publicado del servicio, que no es un acuerdo.
    precio_acordado_soles: Mapped[float | None] = mapped_column(Numeric(8, 2))

    respuesta_proveedor: Mapped[str | None] = mapped_column(Text)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    servicio: Mapped[Servicio] = relationship()
    usuario: Mapped[Usuario | None] = relationship()
    itinerario: Mapped[Itinerario | None] = relationship()
    cambios: Mapped[list["CambioDeEstado"]] = relationship(
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="CambioDeEstado.ocurrido_en",
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('enviada', 'en_revision', 'contrapropuesta', 'confirmada', "
            "'rechazada', 'cancelada')",
            name="ck_solicitud_estado",
        ),
        CheckConstraint("numero_personas > 0", name="ck_solicitud_personas"),
        CheckConstraint(
            "precio_acordado_soles IS NULL OR precio_acordado_soles >= 0",
            name="ck_solicitud_precio",
        ),
    )

    @property
    def esta_cerrada(self) -> bool:
        """Si ya no admite más cambios de estado por parte del proveedor."""
        return self.estado in (
            EstadoSolicitud.CONFIRMADA,
            EstadoSolicitud.RECHAZADA,
            EstadoSolicitud.CANCELADA,
        )

    @property
    def interacciones(self) -> int:
        """Cuántos movimientos hicieron falta desde el envío.

        **Es el indicador del Incremento 5.** Cuenta los cambios de estado
        registrados: una solicitud que se envía y se confirma sin más vale 1;
        una que pasa por revisión y contrapropuesta vale 3.

        Se cuenta sobre el historial y no sobre un contador porque un contador
        se puede desincronizar, y porque el historial hace falta igual para
        saber cuánto se tardó.
        """
        return len(self.cambios)

    def __repr__(self) -> str:
        return f"<SolicitudCoordinacion {self.id} servicio {self.servicio_id} {self.estado}>"


class CambioDeEstado(Base):
    """Cada movimiento de una solicitud, con quién lo hizo y cuándo.

    **Esto es «el registro de lo acordado» de la brecha 6.** Sin esta tabla, la
    solicitud diría en qué estado está pero no cómo llegó ahí, y volveríamos a
    depender de que alguien se acuerde de lo que se habló por teléfono.
    """

    __tablename__ = "cambio_de_estado"

    id: Mapped[int] = mapped_column(primary_key=True)

    solicitud_id: Mapped[int] = mapped_column(
        ForeignKey("solicitud_coordinacion.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: Nulo en el estado inicial, que no viene de ningún sitio.
    estado_anterior: Mapped[str | None] = mapped_column(String(20))
    estado_nuevo: Mapped[str] = mapped_column(String(20), nullable=False)

    #: Quién lo movió. Nulo si lo hizo alguien sin cuenta.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )
    #: 'visitante', 'proveedor', 'operador'... Se guarda el rol además del
    #: usuario porque el rol de una persona puede cambiar después, y entonces
    #: el registro diría que un cambio lo hizo un rol que no era.
    rol_de_quien_cambio: Mapped[str | None] = mapped_column(String(20))

    nota: Mapped[str | None] = mapped_column(Text)

    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    solicitud: Mapped[SolicitudCoordinacion] = relationship(back_populates="cambios")

    def __repr__(self) -> str:
        return f"<CambioDeEstado {self.estado_anterior} -> {self.estado_nuevo}>"
