"""Tablas del catálogo de recursos turísticos.

Son las tres tablas del Incremento 1:

- ``recurso_turistico``: cada atractivo del inventario oficial del MINCETUR.
- ``horario_atencion``: a qué hora abre y cierra cada recurso, por día.
- ``registro_validacion``: una fila por cada ejecución de la validación. Es la
  que sostiene el indicador «porcentaje de oferta con información validada y
  vigente», así que no es una tabla auxiliar: es la evidencia del incremento.
"""

from datetime import date, datetime, time

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base


class RecursoTuristico(Base):
    """Un atractivo turístico del Valle del Mantaro.

    Los datos provienen del Inventario Nacional de Recursos Turísticos del
    MINCETUR. No se inventa ningún recurso ni ningún dato: lo que no viene en
    la fuente queda nulo y se marca como no validado.
    """

    __tablename__ = "recurso_turistico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Código oficial del MINCETUR. Es único y permite volver a importar el
    # archivo sin duplicar recursos.
    codigo_mincetur: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)

    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    provincia: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    distrito: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    categoria: Mapped[str | None] = mapped_column(String(120), index=True)
    tipo: Mapped[str | None] = mapped_column(String(160))
    subtipo: Mapped[str | None] = mapped_column(String(160))

    url_ficha: Mapped[str | None] = mapped_column(Text)

    # GEOGRAPHY(POINT, 4326): un punto en coordenadas geográficas WGS84, el
    # mismo sistema del GPS. Se usa GEOGRAPHY y no GEOMETRY porque calcula
    # distancias reales sobre el elipsoide, en metros, sin tener que
    # reproyectar a un sistema plano.
    #
    # Es NULA a propósito: 61 de los 295 recursos de la ruta no traen
    # coordenadas en la fuente oficial. Inventarlas sería mentir.
    ubicacion: Mapped[object | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    altitud_msnm: Mapped[int | None] = mapped_column(Integer)

    # Fecha de corte declarada por el MINCETUR. Es lo que sostiene el
    # indicador de vigencia del Incremento 1.
    fecha_corte: Mapped[date | None] = mapped_column(Date, index=True)

    esta_validado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    esta_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Motivos por los que la validación rechazó el recurso. Se guardan para
    # que el gestor pueda ver qué corregir, no solo que "falló".
    motivos_invalidez: Mapped[str | None] = mapped_column(Text)

    foto_url: Mapped[str | None] = mapped_column(Text)
    descripcion_es: Mapped[str | None] = mapped_column(Text)
    descripcion_en: Mapped[str | None] = mapped_column(Text)

    # Duración sugerida de la visita, en minutos. La necesita el ruteo de la
    # Fase 4 para las ventanas de tiempo.
    duracion_visita_min: Mapped[int | None] = mapped_column(Integer)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    horarios: Mapped[list["HorarioAtencion"]] = relationship(
        back_populates="recurso", cascade="all, delete-orphan"
    )

    # NOTA sobre el índice espacial GIST, que el proyecto exige:
    # NO se declara aquí. GeoAlchemy2 lo crea automáticamente al crear una
    # columna Geography (con el nombre idx_recurso_turistico_ubicacion).
    # Declararlo además a mano generaba DOS índices GIST idénticos sobre la
    # misma columna: ocupan el doble y ralentizan cada escritura sin aportar
    # nada. Se comprueba que existe en tests/test_catalogo.py.
    __table_args__ = (
        # Índice de texto para el buscador tolerante a errores de tipeo.
        Index(
            "ix_recurso_turistico_nombre_trigrama",
            "nombre",
            postgresql_using="gin",
            postgresql_ops={"nombre": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<RecursoTuristico {self.codigo_mincetur} {self.nombre!r}>"


class HorarioAtencion(Base):
    """Horario de atención de un recurso para un día de la semana.

    Un recurso puede tener varias filas por día (por ejemplo, si cierra al
    mediodía). El ruteo de la Fase 4 las usa como ventanas de tiempo.
    """

    __tablename__ = "horario_atencion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    recurso_id: Mapped[int] = mapped_column(
        ForeignKey("recurso_turistico.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 0 = lunes ... 6 = domingo. Se usa el mismo criterio que Python
    # (date.weekday()) para no tener que convertir en cada cálculo.
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    hora_apertura: Mapped[time] = mapped_column(Time, nullable=False)
    hora_cierre: Mapped[time] = mapped_column(Time, nullable=False)

    recurso: Mapped[RecursoTuristico] = relationship(back_populates="horarios")

    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_horario_dia_semana"),
        CheckConstraint("hora_cierre > hora_apertura", name="ck_horario_cierre_posterior"),
        UniqueConstraint(
            "recurso_id", "dia_semana", "hora_apertura", name="uq_horario_recurso_dia_apertura"
        ),
    )


class RegistroValidacion(Base):
    """Resultado de una ejecución de la validación del catálogo.

    Cada vez que se corre la validación se guarda una fila. La última fila es
    el indicador del Incremento 1, y el histórico permite demostrar que la
    calidad del catálogo mejora con el tiempo, que es justamente lo que el
    documento académico afirma del enfoque DataOps.
    """

    __tablename__ = "registro_validacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    total_recursos: Mapped[int] = mapped_column(Integer, nullable=False)
    validados: Mapped[int] = mapped_column(Integer, nullable=False)
    vigentes: Mapped[int] = mapped_column(Integer, nullable=False)
    con_coordenadas: Mapped[int] = mapped_column(Integer, nullable=False)

    # Se guarda calculado, no se recalcula al leerlo: el indicador debe
    # reflejar el estado del catálogo en el momento de la validación, aunque
    # el catálogo cambie después.
    porcentaje_validado: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<RegistroValidacion {self.fecha:%Y-%m-%d} "
            f"{self.validados}/{self.total_recursos} ({self.porcentaje_validado:.1f} %)>"
        )
