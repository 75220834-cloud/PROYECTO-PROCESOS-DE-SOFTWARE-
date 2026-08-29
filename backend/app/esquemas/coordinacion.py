"""Esquemas de la coordinación con proveedores (Incremento 5)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TipoServicioLiteral = Literal[
    "transporte", "alimentacion", "hospedaje", "guiado", "taller", "artesania"
]

EstadoLiteral = Literal[
    "enviada", "en_revision", "contrapropuesta", "confirmada", "rechazada", "cancelada"
]


class ProveedorPublico(BaseModel):
    """Quién ofrece el servicio."""

    id: int
    nombre: str
    distrito: str
    telefono: str | None = None
    correo: str | None = None
    descripcion: str | None = None

    #: ``true`` cuando el proveedor es inventado para poder enseñar el flujo.
    #: La interfaz lo muestra: nadie debe llamar a un teléfono de demostración
    #: creyendo que va a contestar alguien.
    es_demostracion: bool


class TramoDisponible(BaseModel):
    """Un tramo horario en el que el servicio atiende."""

    #: 0 es lunes y 6 es domingo, igual que ``date.weekday()``.
    dia_semana: int = Field(ge=0, le=6)
    hora_inicio: time
    hora_fin: time
    cupo: int


class ServicioPublico(BaseModel):
    """Un servicio publicado, con lo que hace falta para decidir si sirve."""

    id: int
    nombre: str
    tipo: TipoServicioLiteral
    descripcion: str | None = None

    proveedor: ProveedorPublico

    recurso_id: int | None = None

    # --- Lo que hace verificable la capacidad (brecha 5) ------------------
    capacidad_maxima: int
    duracion_min: int | None = None
    antelacion_minima_horas: int

    # --- Precio: rango y fecha, nunca un numero solo ---------------------
    precio_min_soles: Decimal
    precio_max_soles: Decimal
    unidad_precio: Literal["por_persona", "por_grupo", "por_noche", "por_hora"]
    fecha_referencia: date

    idiomas: str | None = None
    es_accesible: bool

    disponibilidad: list[TramoDisponible] = Field(default_factory=list)


class ConsultaDisponibilidad(BaseModel):
    """Pregunta si un servicio se puede pedir para una fecha y unas personas."""

    fecha: date
    numero_personas: int = Field(ge=1, le=200)
    hora: time | None = None


class RespuestaDisponibilidad(BaseModel):
    """Si se puede pedir, y si no, todos los motivos.

    Se devuelven **todos** los motivos y no solo el primero: decirle a alguien
    «no hay sitio» y, cuando lo arregla, «además llegas tarde», es la clase de
    trato que hace abandonar un formulario.
    """

    servicio_id: int
    fecha: date
    numero_personas: int
    hay_disponibilidad: bool
    motivos: list[str] = Field(default_factory=list)
    plazas_libres: int | None = None


class SolicitudNueva(BaseModel):
    """Lo que el visitante manda al proveedor."""

    servicio_id: int
    fecha_servicio: date
    hora_servicio: time | None = None
    numero_personas: int = Field(ge=1, le=200)

    nombre_contacto: str = Field(min_length=2, max_length=160)
    telefono_contacto: str | None = Field(default=None, max_length=40)
    correo_contacto: str | None = Field(default=None, max_length=255)

    mensaje: str | None = Field(default=None, max_length=2000)

    #: Itinerario del que sale, si sale de uno. Es lo que conecta este
    #: incremento con el anterior.
    itinerario_id: int | None = None

    @field_validator("telefono_contacto", "correo_contacto")
    @classmethod
    def _sin_espacios_sobrantes(cls, valor: str | None) -> str | None:
        return valor.strip() if valor else None


class CambioDeEstadoPublico(BaseModel):
    """Un movimiento de la solicitud, con quién lo hizo y cuándo.

    Es la pieza que cierra la brecha 6: sin el historial, la solicitud diría en
    qué estado está pero no cómo llegó ahí.
    """

    estado_anterior: str | None = None
    estado_nuevo: str
    rol_de_quien_cambio: str | None = None
    nota: str | None = None
    ocurrido_en: datetime


class SolicitudPublica(BaseModel):
    """Una solicitud con todo lo acordado y todo lo ocurrido."""

    id: int
    servicio_id: int
    servicio_nombre: str
    proveedor_nombre: str
    proveedor_telefono: str | None = None
    proveedor_es_demostracion: bool

    itinerario_id: int | None = None

    fecha_servicio: date
    hora_servicio: time | None = None
    numero_personas: int

    nombre_contacto: str
    telefono_contacto: str | None = None
    correo_contacto: str | None = None
    mensaje: str | None = None

    estado: EstadoLiteral
    precio_acordado_soles: Decimal | None = None
    respuesta_proveedor: str | None = None

    #: Rango publicado del servicio. Se manda junto al precio acordado para
    #: que se vea si lo acordado cae dentro de lo que se anunciaba.
    precio_min_soles: Decimal
    precio_max_soles: Decimal

    creado_en: datetime
    actualizado_en: datetime

    #: Cuántos movimientos hubo. **Es el indicador del Incremento 5.**
    interacciones: int

    historial: list[CambioDeEstadoPublico] = Field(default_factory=list)


class CambioSolicitado(BaseModel):
    """Lo que un proveedor (o el visitante) pide hacer con una solicitud."""

    nuevo_estado: EstadoLiteral
    nota: str | None = Field(default=None, max_length=2000)

    #: Obligatorio al confirmar: un acuerdo sin precio no es un acuerdo.
    precio_acordado_soles: Decimal | None = Field(default=None, ge=0)


class ServicioNuevo(BaseModel):
    """Lo que un proveedor publica."""

    nombre: str = Field(min_length=3, max_length=200)
    tipo: TipoServicioLiteral
    descripcion: str | None = Field(default=None, max_length=2000)

    recurso_id: int | None = None

    capacidad_maxima: int = Field(ge=1, le=500)
    duracion_min: int | None = Field(default=None, ge=1, le=10_080)
    antelacion_minima_horas: int = Field(default=24, ge=0, le=8_760)

    precio_min_soles: Decimal = Field(ge=0)
    precio_max_soles: Decimal = Field(ge=0)
    unidad_precio: Literal["por_persona", "por_grupo", "por_noche", "por_hora"] = "por_persona"
    fecha_referencia: date

    idiomas: str | None = Field(default=None, max_length=80)
    es_accesible: bool = False
    esta_publicado: bool = True

    @field_validator("precio_max_soles")
    @classmethod
    def _el_maximo_no_puede_ser_menor(cls, maximo: Decimal, info) -> Decimal:
        minimo = info.data.get("precio_min_soles")

        if minimo is not None and maximo < minimo:
            raise ValueError("El precio máximo no puede ser menor que el mínimo")

        return maximo


class TramoNuevo(BaseModel):
    """Un tramo de disponibilidad que publica el proveedor."""

    dia_semana: int = Field(ge=0, le=6)
    hora_inicio: time
    hora_fin: time
    cupo: int = Field(ge=1, le=500)

    @field_validator("hora_fin")
    @classmethod
    def _el_fin_va_despues(cls, fin: time, info) -> time:
        inicio = info.data.get("hora_inicio")

        if inicio is not None and fin <= inicio:
            raise ValueError("La hora de fin tiene que ser posterior a la de inicio")

        return fin


class ResumenDeCoordinacion(BaseModel):
    """El indicador del Incremento 5, calculado sobre lo que hay registrado."""

    total_solicitudes: int
    confirmadas: int
    rechazadas: int
    pendientes: int

    #: Media de cambios de estado hasta confirmar. **Es el indicador.** Nulo si
    #: todavía no se ha confirmado ninguna: una media de cero solicitudes no es
    #: cero, es que no hay dato.
    interacciones_medias_hasta_confirmar: float | None = None

    #: Horas medias entre el envío y la confirmación. Nulo por lo mismo.
    horas_medias_hasta_confirmar: float | None = None

    #: Cuántos canales distintos hace falta usar. Es 1 por construcción, y es
    #: justo lo que mide la brecha 6: antes eran teléfono, Facebook y WhatsApp.
    canales_para_confirmar: int = 1
