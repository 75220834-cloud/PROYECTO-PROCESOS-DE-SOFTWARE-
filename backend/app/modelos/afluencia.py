"""Tablas del calendario festivo y de la afluencia histórica (Incremento 3).

**Por qué existe la tabla `festividad` si el calendario se calcula en código.**
Son dos cosas distintas y complementarias:

- ``app/ia/calendario.py`` es la **fuente de verdad** de las fiestas conocidas.
  Calcula las móviles con el algoritmo de la Pascua y conoce las fijas
  documentadas. No se puede editar sin tocar el código, que es justo lo que se
  quiere de un dato que debe ser reproducible.
- Esta tabla guarda esas fiestas **materializadas por año**, más las que un
  gestor municipal añada. El valle tiene fiestas patronales distrito por
  distrito que ninguna lista escrita a mano va a cubrir entera; sin la tabla,
  añadir una exigiría desplegar código.

El guion ``app.utilidades.cargar_calendario`` vuelca el calendario calculado
en la tabla, y es idempotente.
"""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from app.modelos.catalogo import RecursoTuristico


class Festividad(Base):
    """Una celebración con fecha, ámbito y origen documentado."""

    __tablename__ = "festividad"

    id: Mapped[int] = mapped_column(primary_key=True)

    nombre: Mapped[str] = mapped_column(String(160), nullable=False)

    # Nulos significan «afecta a todo el valle»: es el caso de los feriados
    # nacionales y de la Fiesta de Santiago, que se celebra en unos 28
    # distritos a la vez.
    provincia: Mapped[str | None] = mapped_column(String(80), index=True)
    distrito: Mapped[str | None] = mapped_column(String(80), index=True)

    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)

    # Marca si la fecha se calculó a partir de la Pascua. Sirve para saber qué
    # filas hay que regenerar cada año y cuáles no.
    es_movil: Mapped[bool] = mapped_column(nullable=False, default=False)

    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    # De dónde sale el dato. Sin fuente, una fiesta es un rumor.
    fuente: Mapped[str | None] = mapped_column(Text)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_festividad_fechas"),
        CheckConstraint(
            "tipo IN ('religiosa', 'costumbrista', 'civica', 'feria', 'nacional')",
            name="ck_festividad_tipo",
        ),
        # Evita duplicar la misma fiesta al recargar el calendario de un año.
        UniqueConstraint(
            "nombre", "fecha_inicio", "distrito", name="uq_festividad_nombre_fecha_distrito"
        ),
        Index("ix_festividad_rango", "fecha_inicio", "fecha_fin"),
    )

    def __repr__(self) -> str:
        return f"<Festividad {self.nombre!r} {self.fecha_inicio}>"


class AfluenciaHistorica(Base):
    """Visitantes registrados en un recurso durante un mes concreto.

    Es el conjunto de entrenamiento del modelo de afluencia. Los datos vienen
    de las series públicas del Ministerio de Cultura sobre visitantes a sitios
    arqueológicos y museos.

    **Aviso importante y consciente:** el Valle del Mantaro tiene muy pocos
    recursos en esas series. Si al entrenar no hay filas suficientes, el
    sistema lo dice y usa la alternativa por reglas, en vez de entrenar un
    modelo con cuatro datos y presentarlo como si valiera.
    """

    __tablename__ = "afluencia_historica"

    id: Mapped[int] = mapped_column(primary_key=True)

    recurso_id: Mapped[int] = mapped_column(
        ForeignKey("recurso_turistico.id", ondelete="CASCADE"), nullable=False, index=True
    )

    anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    visitantes: Mapped[int] = mapped_column(Integer, nullable=False)

    fuente: Mapped[str] = mapped_column(Text, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recurso: Mapped[RecursoTuristico] = relationship()

    __table_args__ = (
        CheckConstraint("mes BETWEEN 1 AND 12", name="ck_afluencia_mes"),
        CheckConstraint("anio BETWEEN 2000 AND 2100", name="ck_afluencia_anio"),
        CheckConstraint("visitantes >= 0", name="ck_afluencia_visitantes"),
        UniqueConstraint("recurso_id", "anio", "mes", name="uq_afluencia_recurso_periodo"),
    )

    def __repr__(self) -> str:
        return f"<AfluenciaHistorica recurso={self.recurso_id} {self.anio}-{self.mes:02d}>"
