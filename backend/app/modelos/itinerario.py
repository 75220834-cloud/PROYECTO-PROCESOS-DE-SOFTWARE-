"""Itinerarios y sus paradas (Incremento 4).

Un itinerario es el resultado de resolver, para una preferencia concreta, qué
recursos visitar, **en qué orden**, a qué hora, cómo desplazarse entre ellos y
cuánto cuesta. Es lo que cierra la brecha 4: *el proceso no incorporaba la
distribución geográfica ni el tiempo y costo de desplazamiento*.
"""

from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from app.modelos.catalogo import RecursoTuristico
from app.modelos.preferencias import PreferenciaViaje
from app.modelos.usuario import Usuario


class EstadoItinerario(StrEnum):
    """En qué punto del proceso está un itinerario."""

    BORRADOR = "borrador"
    GUARDADO = "guardado"
    CONFIRMADO = "confirmado"
    COMPLETADO = "completado"


class OrigenDelCalculo(StrEnum):
    """Cómo se calculó un tramo, y por tanto cuánto fiarse de él.

    Es la distinción que exige la medición de cobertura de OSM: en los
    distritos donde no hay red vial registrada, el tiempo es una estimación
    sobre línea recta y **el visitante tiene que saberlo**.
    """

    #: Ruta calculada sobre el grafo real de OpenStreetMap.
    RED_VIAL = "red_vial"
    #: Línea recta corregida por el factor de rodeo medido (1,26).
    LINEA_RECTA = "linea_recta"


class Itinerario(Base):
    """Un recorrido completo, con sus paradas y sus totales."""

    __tablename__ = "itinerario"

    id: Mapped[int] = mapped_column(primary_key=True)

    preferencia_id: Mapped[int] = mapped_column(
        ForeignKey("preferencia_viaje.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Nulo si se armó sin cuenta, igual que las preferencias.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)

    #: Día concreto que cubre este itinerario. Un viaje de tres días son tres
    #: itinerarios, no uno con todo dentro: cada día se optimiza por separado
    #: porque el visitante duerme entre medias.
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Totales -----------------------------------------------------------
    tiempo_total_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    costo_total_soles: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    distancia_total_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    #: Solo la subida, no el desnivel neto. Bajar lo que se subió no descansa
    #: las piernas, y es lo que determina lo duro que resulta el día.
    desnivel_total_m: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    estado: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EstadoItinerario.BORRADOR
    )

    #: 'modelo' (optimización VRPTW con OR-Tools) o 'reglas' (vecino más
    #: cercano). Es la trazabilidad que exige la regla de oro de la IA del
    #: proyecto, y aparece en la interfaz.
    generado_por: Mapped[str] = mapped_column(String(16), nullable=False, default="modelo")

    #: Avisos que hay que mostrar: tramos estimados, altitud, esfuerzo del día.
    #:
    #: Se guardan como JSONB —una lista de ``{codigo, parametros}``— y no como
    #: texto concatenado, porque desde la Fase 7 un aviso **es un dato**: se
    #: puede contar cuántos itinerarios avisaron de altitud sin buscar
    #: subcadenas, y la interfaz lo redacta en el idioma del visitante. Ver
    #: `servicios/avisos.py` para el razonamiento completo.
    avisos: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    preferencia: Mapped[PreferenciaViaje] = relationship()
    usuario: Mapped[Usuario | None] = relationship()
    paradas: Mapped[list["ParadaItinerario"]] = relationship(
        back_populates="itinerario",
        cascade="all, delete-orphan",
        order_by="ParadaItinerario.orden",
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('borrador', 'guardado', 'confirmado', 'completado')",
            name="ck_itinerario_estado",
        ),
        CheckConstraint("generado_por IN ('modelo', 'reglas')", name="ck_itinerario_generado_por"),
        CheckConstraint("tiempo_total_min >= 0", name="ck_itinerario_tiempo"),
        CheckConstraint("costo_total_soles >= 0", name="ck_itinerario_costo"),
    )

    def __repr__(self) -> str:
        return f"<Itinerario {self.id} {self.fecha} {len(self.paradas)} paradas>"


class ParadaItinerario(Base):
    """Una visita dentro de un itinerario, y cómo se llegó hasta ella."""

    __tablename__ = "parada_itinerario"

    id: Mapped[int] = mapped_column(primary_key=True)

    itinerario_id: Mapped[int] = mapped_column(
        ForeignKey("itinerario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recurso_id: Mapped[int] = mapped_column(
        ForeignKey("recurso_turistico.id", ondelete="CASCADE"), nullable=False
    )

    orden: Mapped[int] = mapped_column(Integer, nullable=False)

    hora_llegada: Mapped[time] = mapped_column(Time, nullable=False)
    hora_salida: Mapped[time] = mapped_column(Time, nullable=False)

    # --- El traslado DESDE la parada anterior hasta esta --------------------
    # Van en la parada de destino y no en una tabla de tramos aparte porque
    # siempre se leen juntos: la interfaz muestra «llegar aquí costó X».
    modo_traslado: Mapped[str | None] = mapped_column(String(16))
    tiempo_traslado_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distancia_traslado_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    desnivel_traslado_m: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    costo_traslado_min_soles: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=0
    )
    costo_traslado_max_soles: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=0
    )

    #: 'red_vial' o 'linea_recta'. Determina si la interfaz muestra el aviso de
    #: tramo estimado.
    origen_del_calculo: Mapped[str] = mapped_column(
        String(16), nullable=False, default=OrigenDelCalculo.RED_VIAL
    )

    #: Afluencia esperada en este recurso ese día: 'bajo', 'medio' o 'alto'.
    afluencia_estimada: Mapped[str | None] = mapped_column(String(8))

    itinerario: Mapped[Itinerario] = relationship(back_populates="paradas")
    recurso: Mapped[RecursoTuristico] = relationship()

    __table_args__ = (
        UniqueConstraint("itinerario_id", "orden", name="uq_parada_itinerario_orden"),
        CheckConstraint("orden >= 0", name="ck_parada_orden"),
        CheckConstraint("hora_salida >= hora_llegada", name="ck_parada_horas"),
        CheckConstraint(
            "modo_traslado IS NULL OR modo_traslado IN "
            "('caminando', 'combi', 'colectivo', 'taxi')",
            name="ck_parada_modo",
        ),
        CheckConstraint(
            "origen_del_calculo IN ('red_vial', 'linea_recta')",
            name="ck_parada_origen_calculo",
        ),
    )

    @property
    def minutos_de_visita(self) -> int:
        """Cuánto se queda el visitante en esta parada."""
        llegada = self.hora_llegada.hour * 60 + self.hora_llegada.minute
        salida = self.hora_salida.hour * 60 + self.hora_salida.minute
        return salida - llegada

    def __repr__(self) -> str:
        return (
            f"<ParadaItinerario {self.orden}: recurso {self.recurso_id} a las {self.hora_llegada}>"
        )
