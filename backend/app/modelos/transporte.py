"""Tarifas de transporte entre distritos del Valle del Mantaro.

**Aquí es donde el proyecto se juega su honestidad con los datos.** El
`CONTEXTO_PROYECTO.md` lo dice sin rodeos: *«las tarifas de Huancayo cambian y
no hay tarifa oficial única»*, y lista varias como **dato no verificado**.

Por eso la tabla no guarda «un precio». Guarda:

- un **rango** (mínimo y máximo), porque no existe una tarifa única;
- una **fecha de referencia**, porque un precio sin fecha caduca en silencio;
- una **fuente**, porque un precio sin fuente es un rumor;
- una marca de **estimado**, para poder distinguir lo que alguien comprobó de
  lo que el equipo dedujo.

La interfaz muestra siempre la palabra «aprox.» y la fecha. Es una exigencia
del plan de trabajo, no una decisión de estilo.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.base_datos import Base


class ModoTransporte(StrEnum):
    """Cómo se cubre un traslado entre dos puntos."""

    CAMINANDO = "caminando"
    COMBI = "combi"
    COLECTIVO = "colectivo"
    TAXI = "taxi"


class TarifaTransporte(Base):
    """Cuánto cuesta y cuánto tarda ir de un distrito a otro."""

    __tablename__ = "tarifa_transporte"

    id: Mapped[int] = mapped_column(primary_key=True)

    distrito_origen: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    distrito_destino: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    modo: Mapped[str] = mapped_column(String(16), nullable=False)

    # Rango, nunca un precio único. Numeric y no Float: con dinero, los
    # decimales binarios acumulan errores de redondeo.
    precio_min_soles: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    precio_max_soles: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)

    duracion_estimada_min: Mapped[int] = mapped_column(Integer, nullable=False)

    # Sin fecha, un precio caduca sin que nadie se entere.
    fecha_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    # Sin fuente, un precio es un rumor.
    fuente: Mapped[str] = mapped_column(Text, nullable=False)

    # True cuando el equipo lo dedujo en vez de comprobarlo. La interfaz lo
    # distingue: no es lo mismo un precio consultado que uno inferido.
    es_estimado: Mapped[bool] = mapped_column(nullable=False, default=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("precio_max_soles >= precio_min_soles", name="ck_tarifa_rango"),
        CheckConstraint("precio_min_soles >= 0", name="ck_tarifa_precio_positivo"),
        CheckConstraint("duracion_estimada_min > 0", name="ck_tarifa_duracion"),
        CheckConstraint(
            "modo IN ('caminando', 'combi', 'colectivo', 'taxi')", name="ck_tarifa_modo"
        ),
        UniqueConstraint("distrito_origen", "distrito_destino", "modo", name="uq_tarifa_ruta_modo"),
    )

    @property
    def precio_medio_soles(self) -> float:
        """Punto medio del rango. Se usa para sumar totales, no para mostrar."""
        return float(self.precio_min_soles + self.precio_max_soles) / 2

    def __repr__(self) -> str:
        return (
            f"<TarifaTransporte {self.distrito_origen}->{self.distrito_destino} "
            f"{self.modo} S/{self.precio_min_soles}-{self.precio_max_soles}>"
        )
