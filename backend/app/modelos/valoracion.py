"""Valoraciones de cierre de la experiencia (Incremento 6).

Cierra la **brecha 7**: *la retroalimentación no retorna estructurada al proceso
ni al gestor*.

## Qué significa «estructurada» aquí

Que la opinión del visitante no se quede en una estrella suelta ni en un párrafo
que nadie lee. Cada valoración guarda tres capas:

1. **Lo que la persona puso**: puntuación y comentario. Es el dato crudo y no se
   toca nunca.
2. **Lo que el sistema entendió**: sentimiento y temas mencionados, con la marca
   de si lo dedujo el modelo o las reglas.
3. **A qué se refiere**: el itinerario y, si aplica, el recurso o el servicio
   concretos.

Sin la tercera capa, el gestor sabría que «la gente está contenta» pero no con
qué. Sin la primera, no se podría auditar lo que el modelo entendió.

## Por qué el análisis se guarda y no se recalcula

Podría analizarse el comentario cada vez que se consulta. No se hace, por dos
razones:

- **Reproducibilidad.** Si el modelo cambia de versión, las valoraciones viejas
  cambiarían de sentimiento retroactivamente, y un tablero que cambia solo no
  sirve como evidencia.
- **Coste.** El modelo de sentimiento tarda cientos de milisegundos por texto;
  un tablero con doscientas valoraciones tardaría un minuto en pintarse.

Se guarda además **qué versión lo analizó**, para poder distinguir lo analizado
por el modelo de lo analizado por las reglas cuando se mire dentro de un año.

## Y por qué esto es lo que habilita MLOps, no antes

El documento académico sostiene que MLOps se difiere hasta que el sistema genere
datos propios. **Esta tabla es esos datos propios.** Hasta el Incremento 5 todo
lo que sabía el sistema venía de fuentes externas estables; aquí empieza a
acumular histórico que un día justificaría reentrenar.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
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
from app.modelos.coordinacion import Servicio
from app.modelos.itinerario import Itinerario
from app.modelos.usuario import Usuario


class Sentimiento(StrEnum):
    """Cómo se leyó el comentario.

    Son las tres clases que devuelve el modelo en español de pysentimiento, y
    las mismas que puede producir la alternativa por reglas. Que coincidan no es
    casualidad: si cada vía tuviera sus propias clases, el tablero no podría
    mezclar valoraciones analizadas por una y por otra.
    """

    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"


class TemaValoracion(StrEnum):
    """De qué habla un comentario.

    El conjunto sale del plan de trabajo —*limpieza, atención, precio, acceso,
    señalización…*— más los tres que aparecen una y otra vez en las reseñas de
    turismo: la seguridad, la comida y lo que se ve.

    Es un conjunto cerrado a propósito. Extraer temas libres con un modelo daría
    una nube de palabras bonita e inservible: el gestor necesita poder decir
    «los comentarios sobre señalización empeoraron», y eso exige que
    «señalización» sea siempre la misma categoría.
    """

    LIMPIEZA = "limpieza"
    ATENCION = "atencion"
    PRECIO = "precio"
    ACCESO = "acceso"
    SENALIZACION = "senalizacion"
    SEGURIDAD = "seguridad"
    COMIDA = "comida"
    PAISAJE = "paisaje"
    INFRAESTRUCTURA = "infraestructura"


#: Puntuación mínima y máxima. Cinco estrellas es lo que espera cualquiera que
#: haya usado internet, y cambiarlo solo confundiría.
PUNTUACION_MINIMA = 1
PUNTUACION_MAXIMA = 5


class Valoracion(Base):
    """Lo que el visitante opina de una experiencia ya vivida."""

    __tablename__ = "valoracion"

    id: Mapped[int] = mapped_column(primary_key=True)

    #: A qué itinerario se refiere. Es obligatorio: una valoración suelta, sin
    #: experiencia detrás, no es evidencia de nada.
    itinerario_id: Mapped[int] = mapped_column(
        ForeignKey("itinerario.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: Nulo si se valoró sin cuenta. La aplicación funciona sin registro, y
    #: obligar a registrarse justo al final del viaje perdería la valoración.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    #: Recurso concreto al que se refiere, si se refiere a uno. Nulo cuando la
    #: valoración es del día completo.
    recurso_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurso_turistico.id", ondelete="SET NULL"), nullable=True, index=True
    )

    #: Servicio concreto, si valora un servicio coordinado. Es lo que conecta
    #: este incremento con el anterior: se puede valorar el almuerzo que se
    #: reservó, no solo el sitio que se visitó.
    servicio_id: Mapped[int | None] = mapped_column(
        ForeignKey("servicio.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # --- Capa 1: lo que la persona puso. No se toca nunca. ----------------
    puntuacion: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text)

    # --- Capa 2: lo que el sistema entendió -------------------------------
    #: 'positivo', 'neutro' o 'negativo'. Nulo si no había comentario que leer:
    #: una puntuación sola no tiene sentimiento, tiene número.
    sentimiento: Mapped[str | None] = mapped_column(String(12), index=True)

    #: Confianza del análisis, de 0 a 1. Con las reglas es un valor derivado del
    #: recuento de palabras, no una probabilidad. Se guarda igual para poder
    #: filtrar lo dudoso en el tablero.
    confianza_sentimiento: Mapped[float | None] = mapped_column(Float)

    #: Temas detectados. ARRAY y no una tabla aparte porque siempre se leen
    #: junto a la valoración y nunca se consultan por sí solos.
    temas: Mapped[list[str]] = mapped_column(ARRAY(String(24)), nullable=False, default=list)

    #: 'modelo' o 'reglas'. La trazabilidad que exige la regla de oro de la IA.
    analizado_por: Mapped[str | None] = mapped_column(String(16))

    #: Qué produjo el análisis, con detalle suficiente para reproducirlo. Por
    #: ejemplo «pysentimiento/robertuito-sentiment-analysis». Sin esto, dentro de
    #: un año nadie sabría por qué dos valoraciones parecidas salieron distintas.
    version_del_analisis: Mapped[str | None] = mapped_column(String(120))

    analizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    itinerario: Mapped[Itinerario] = relationship()
    usuario: Mapped[Usuario | None] = relationship()
    recurso: Mapped[RecursoTuristico | None] = relationship()
    servicio: Mapped[Servicio | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            f"puntuacion BETWEEN {PUNTUACION_MINIMA} AND {PUNTUACION_MAXIMA}",
            name="ck_valoracion_puntuacion",
        ),
        CheckConstraint(
            "sentimiento IS NULL OR sentimiento IN ('positivo', 'neutro', 'negativo')",
            name="ck_valoracion_sentimiento",
        ),
        CheckConstraint(
            "analizado_por IS NULL OR analizado_por IN ('modelo', 'reglas')",
            name="ck_valoracion_analizado_por",
        ),
        CheckConstraint(
            "confianza_sentimiento IS NULL OR confianza_sentimiento BETWEEN 0 AND 1",
            name="ck_valoracion_confianza",
        ),
        # Una valoración por itinerario y recurso. Sin esto, alguien podría
        # inflar la media de un sitio valorándolo diez veces desde el mismo
        # itinerario, y la evidencia dejaría de serlo.
        UniqueConstraint(
            "itinerario_id", "recurso_id", "servicio_id", name="uq_valoracion_por_experiencia"
        ),
    )

    @property
    def tiene_comentario(self) -> bool:
        return bool(self.comentario and self.comentario.strip())

    def __repr__(self) -> str:
        return f"<Valoracion {self.id} itinerario {self.itinerario_id} {self.puntuacion}/5>"


class RegistroDeEvidencia(Base):
    """Una foto del estado de la retroalimentación en un momento dado.

    Es al Incremento 6 lo que ``registro_validacion`` es al Incremento 1: una
    instantánea guardada para poder demostrar la evolución del indicador en el
    tiempo, en vez de solo su valor de hoy.

    Sin esto, el tablero del gestor podría decir «el 40 % de las experiencias
    tiene valoración» pero no si eso es mejor o peor que el mes pasado, que es
    justo lo que un gestor necesita saber.
    """

    __tablename__ = "registro_de_evidencia"

    id: Mapped[int] = mapped_column(primary_key=True)

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    total_itinerarios: Mapped[int] = mapped_column(Integer, nullable=False)
    itinerarios_con_valoracion: Mapped[int] = mapped_column(Integer, nullable=False)

    #: **Es el indicador del Incremento 6.**
    porcentaje_con_valoracion: Mapped[float] = mapped_column(Float, nullable=False)

    total_valoraciones: Mapped[int] = mapped_column(Integer, nullable=False)
    con_comentario: Mapped[int] = mapped_column(Integer, nullable=False)

    positivas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neutras: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    puntuacion_media: Mapped[float | None] = mapped_column(Float)

    def __repr__(self) -> str:
        return (
            f"<RegistroDeEvidencia {self.fecha:%Y-%m-%d} " f"{self.porcentaje_con_valoracion:.1f}%>"
        )
