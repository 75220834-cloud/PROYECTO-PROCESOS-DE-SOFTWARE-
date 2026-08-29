"""Tabla de preferencias de viaje del visitante.

Esta tabla **es** el Incremento 2 y cierra la brecha 3: *las preferencias del
visitante no se registran ni se usan sistemáticamente*. Antes de esto, lo que
el visitante quería vivía en su cabeza o en una conversación de WhatsApp, y no
entraba nunca al proceso.

Decisión de diseño que gobierna todo el módulo: ``usuario_id`` **puede ser
nulo**. El visitante arma su viaje sin registrarse y solo se le ofrece crear
una cuenta al final, para guardarlo. Obligar a registrarse antes de ver nada
es la forma más rápida de perder al visitante, y el proyecto declara la
accesibilidad del proceso como objetivo.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from app.modelos.usuario import Usuario


class Ritmo(StrEnum):
    """A qué velocidad quiere viajar el visitante.

    Determina cuántas paradas cabe proponer en un día cuando el Incremento 4
    construya el itinerario.
    """

    RELAJADO = "relajado"
    MODERADO = "moderado"
    INTENSO = "intenso"


class Movilidad(StrEnum):
    """Cómo prefiere desplazarse el visitante entre un recurso y otro."""

    CAMINANDO = "caminando"
    TRANSPORTE_PUBLICO = "transporte_publico"
    TAXI = "taxi"
    COMBINADO = "combinado"


class Interes(StrEnum):
    """Los ocho intereses que puede declarar el visitante.

    Se eligieron para que se puedan enlazar con las categorías del inventario
    del MINCETUR en el Incremento 3: no son etiquetas decorativas, son la
    entrada del cálculo de afinidad.
    """

    NATURALEZA = "naturaleza"
    ARQUEOLOGIA = "arqueologia"
    IGLESIAS_CONVENTOS = "iglesias_conventos"
    ARTESANIA = "artesania"
    GASTRONOMIA = "gastronomia"
    FERIAS_FIESTAS = "ferias_fiestas"
    AVENTURA = "aventura"
    FOTOGRAFIA = "fotografia"


class PreferenciaViaje(Base):
    """Lo que un visitante quiere de su viaje por el Valle del Mantaro."""

    __tablename__ = "preferencia_viaje"

    id: Mapped[int] = mapped_column(primary_key=True)

    # NULO a propósito: identifica una preferencia creada sin cuenta.
    # ondelete SET NULL y no CASCADE: si alguien borra su cuenta, sus
    # preferencias se anonimizan en vez de desaparecer, para que los
    # indicadores del proceso no pierdan histórico.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)

    # Numeric y no Float: con dinero, los decimales binarios acumulan errores
    # de redondeo. 10 dígitos con 2 decimales cubren cualquier presupuesto
    # razonable en soles.
    presupuesto_soles: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # ARRAY de PostgreSQL: el visitante marca varios intereses a la vez.
    # Se guarda como arreglo y no como tabla aparte porque siempre se leen
    # todos juntos y nunca se consultan por separado.
    intereses: Mapped[list[str]] = mapped_column(ARRAY(String(40)), nullable=False, default=list)

    movilidad: Mapped[str] = mapped_column(String(24), nullable=False)

    # Accesibilidad para movilidad reducida. No es un adorno: en el Incremento
    # 4 descarta rutas con pendiente o tramos sin acceso.
    requiere_accesibilidad: Mapped[bool] = mapped_column(nullable=False, default=False)

    idioma: Mapped[str] = mapped_column(String(5), nullable=False, default="es")
    ritmo: Mapped[str] = mapped_column(String(16), nullable=False)

    # Distrito desde el que arranca el recorrido cada día. Es el punto de
    # partida del ruteo del Incremento 4.
    distrito_origen: Mapped[str] = mapped_column(String(80), nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped[Usuario | None] = relationship()

    __table_args__ = (
        # Las reglas viven también en la base de datos. Una validación que
        # solo existe en Python se salta con un INSERT manual.
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_preferencia_fechas"),
        CheckConstraint("presupuesto_soles >= 0", name="ck_preferencia_presupuesto"),
        CheckConstraint(
            "movilidad IN ('caminando', 'transporte_publico', 'taxi', 'combinado')",
            name="ck_preferencia_movilidad",
        ),
        CheckConstraint(
            "ritmo IN ('relajado', 'moderado', 'intenso')", name="ck_preferencia_ritmo"
        ),
        CheckConstraint("idioma IN ('es', 'en')", name="ck_preferencia_idioma"),
        CheckConstraint("cardinality(intereses) > 0", name="ck_preferencia_intereses_no_vacios"),
    )

    @property
    def duracion_dias(self) -> int:
        """Días que dura el viaje, contando el primero y el último."""
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __repr__(self) -> str:
        return (
            f"<PreferenciaViaje {self.id} {self.fecha_inicio}..{self.fecha_fin} "
            f"desde {self.distrito_origen} ritmo={self.ritmo}>"
        )


# Constante auxiliar para validar en los esquemas y en las pruebas sin tener
# que repetir la lista en varios sitios.
INTERESES_VALIDOS: frozenset[str] = frozenset(interes.value for interes in Interes)
