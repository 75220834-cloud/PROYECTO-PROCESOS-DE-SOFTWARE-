"""Agregación de las valoraciones en evidencia para el gestor (Incremento 6).

Es la segunda mitad de la brecha 7: *la retroalimentación no retorna
estructurada **al proceso ni al gestor***. Guardar las valoraciones cierra la
primera mitad; convertirlas en algo sobre lo que se pueda decidir cierra la
segunda.

## Qué distingue esto de «mostrar las reseñas»

Un listado de comentarios no es evidencia: es trabajo pendiente para quien lo
lea. Lo que un gestor necesita poder decir es:

- «los comentarios sobre señalización empeoraron respecto del mes pasado»,
- «este recurso tiene la peor valoración media y es por el acceso»,
- «la limpieza se menciona en el 40 % de los comentarios negativos».

Las tres exigen agregación por tema, por recurso y por tiempo. Eso es lo que
hay aquí.

## Por qué se avisa cuando hay pocos datos

Una media de dos valoraciones no es una media. Todos los agregados de este
módulo llevan su ``total``, y los que no llegan al mínimo se marcan como poco
fiables en vez de esconderse: esconderlos daría un tablero que parece completo
y no lo está.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos.catalogo import RecursoTuristico
from app.modelos.itinerario import Itinerario
from app.modelos.valoracion import RegistroDeEvidencia, Sentimiento, Valoracion

#: Cuántas valoraciones hacen falta para que una media signifique algo.
#:
#: No sale de una prueba estadística: sale de que con menos de cinco, una sola
#: opinión mueve la media más de medio punto. Se declara aquí para poder
#: discutirlo, y el tablero marca lo que no llega.
MINIMO_PARA_FIARSE = 5

#: Cuántos recursos se devuelven en las listas de mejor y peor valorados.
CUANTOS_EN_EL_RANQUIN = 5


@dataclass
class DistribucionDeSentimiento:
    """Cuántas valoraciones hay de cada signo."""

    positivas: int = 0
    neutras: int = 0
    negativas: int = 0

    @property
    def total(self) -> int:
        return self.positivas + self.neutras + self.negativas

    @property
    def porcentaje_positivo(self) -> float | None:
        """Nulo si no hay valoraciones: un porcentaje de cero casos no es cero."""
        return round(100 * self.positivas / self.total, 1) if self.total else None


@dataclass
class TemaAgregado:
    """Cuánto se menciona un tema, y con qué signo."""

    tema: str
    menciones: int
    positivas: int = 0
    neutras: int = 0
    negativas: int = 0

    @property
    def porcentaje_negativo(self) -> float | None:
        """De las menciones de este tema, cuántas vienen en comentarios negativos.

        Es el número que le dice al gestor **dónde actuar**: un tema muy
        mencionado y mayoritariamente negativo es un problema; uno muy
        mencionado y positivo es una fortaleza que conviene no romper.
        """
        return round(100 * self.negativas / self.menciones, 1) if self.menciones else None


@dataclass
class RecursoValorado:
    """Un recurso con su valoración media."""

    recurso_id: int
    nombre: str
    distrito: str
    total_valoraciones: int
    puntuacion_media: float
    #: Los temas que más se le mencionan, para saber POR QUÉ está donde está.
    temas_frecuentes: list[str] = field(default_factory=list)

    @property
    def es_fiable(self) -> bool:
        """Si tiene valoraciones suficientes para que la media signifique algo."""
        return self.total_valoraciones >= MINIMO_PARA_FIARSE


@dataclass
class PuntoEnElTiempo:
    """La media de un mes, para poder ver la evolución."""

    periodo: str
    total: int
    puntuacion_media: float
    positivas: int = 0
    negativas: int = 0


@dataclass
class ResumenDeEvidencia:
    """Todo lo que el tablero del gestor necesita para decidir."""

    # --- El indicador del incremento --------------------------------------
    total_itinerarios: int = 0
    itinerarios_con_valoracion: int = 0
    porcentaje_con_valoracion: float = 0.0

    # --- Volumen ----------------------------------------------------------
    total_valoraciones: int = 0
    con_comentario: int = 0
    puntuacion_media: float | None = None

    # --- Análisis ---------------------------------------------------------
    sentimiento: DistribucionDeSentimiento = field(default_factory=DistribucionDeSentimiento)
    temas: list[TemaAgregado] = field(default_factory=list)

    mejor_valorados: list[RecursoValorado] = field(default_factory=list)
    peor_valorados: list[RecursoValorado] = field(default_factory=list)

    evolucion: list[PuntoEnElTiempo] = field(default_factory=list)

    #: Cuántas se analizaron con el modelo y cuántas con las reglas. Es la
    #: trazabilidad de la regla de oro, agregada: el gestor puede saber si el
    #: tablero que está mirando lo produjo el modelo o el respaldo.
    analizadas_por_modelo: int = 0
    analizadas_por_reglas: int = 0

    #: Avisos sobre la fiabilidad de lo que se está mostrando.
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# El indicador
# ---------------------------------------------------------------------------


def calcular_cobertura(sesion: Session) -> tuple[int, int, float]:
    """Qué porcentaje de itinerarios tiene al menos una valoración.

    **Es el indicador del Incremento 6.** Devuelve
    ``(total, con_valoracion, porcentaje)``.

    Se cuenta sobre itinerarios y no sobre valoraciones porque la pregunta es
    «¿cuántas experiencias volvieron al proceso?», no «¿cuántas opiniones hay?».
    Diez valoraciones de un mismo viaje siguen siendo una experiencia.
    """
    total = sesion.scalar(select(func.count()).select_from(Itinerario)) or 0

    con_valoracion = sesion.scalar(select(func.count(func.distinct(Valoracion.itinerario_id)))) or 0

    porcentaje = round(100 * con_valoracion / total, 2) if total else 0.0

    return total, con_valoracion, porcentaje


# ---------------------------------------------------------------------------
# Agregaciones
# ---------------------------------------------------------------------------


def _distribucion(sesion: Session) -> DistribucionDeSentimiento:
    """Cuántas valoraciones hay de cada sentimiento."""
    filas = sesion.execute(
        select(Valoracion.sentimiento, func.count())
        .where(Valoracion.sentimiento.is_not(None))
        .group_by(Valoracion.sentimiento)
    ).all()

    por_signo = dict(filas)

    return DistribucionDeSentimiento(
        positivas=por_signo.get(Sentimiento.POSITIVO.value, 0),
        neutras=por_signo.get(Sentimiento.NEUTRO.value, 0),
        negativas=por_signo.get(Sentimiento.NEGATIVO.value, 0),
    )


def _temas_mas_mencionados(sesion: Session) -> list[TemaAgregado]:
    """Los temas ordenados por cuánto se mencionan.

    Se agregan en Python y no en SQL porque los temas viven en un ``ARRAY`` y
    desplegarlo con ``unnest`` obligaría a escribir SQL crudo. Con el volumen
    de este proyecto —cientos de valoraciones, no millones— la diferencia no se
    nota, y el código se lee.
    """
    filas = sesion.execute(
        select(Valoracion.temas, Valoracion.sentimiento).where(
            func.cardinality(Valoracion.temas) > 0
        )
    ).all()

    menciones: Counter[str] = Counter()
    por_signo: dict[str, Counter[str]] = {}

    for temas, sentimiento in filas:
        for tema in temas or []:
            menciones[tema] += 1
            por_signo.setdefault(tema, Counter())[sentimiento or "sin_analizar"] += 1

    agregados = [
        TemaAgregado(
            tema=tema,
            menciones=total,
            positivas=por_signo[tema].get(Sentimiento.POSITIVO.value, 0),
            neutras=por_signo[tema].get(Sentimiento.NEUTRO.value, 0),
            negativas=por_signo[tema].get(Sentimiento.NEGATIVO.value, 0),
        )
        for tema, total in menciones.items()
    ]

    return sorted(agregados, key=lambda t: -t.menciones)


def _recursos_valorados(sesion: Session) -> list[RecursoValorado]:
    """Todos los recursos con al menos una valoración, con su media."""
    filas = sesion.execute(
        select(
            RecursoTuristico.id,
            RecursoTuristico.nombre,
            RecursoTuristico.distrito,
            func.count(Valoracion.id),
            func.avg(Valoracion.puntuacion),
        )
        .join(Valoracion, Valoracion.recurso_id == RecursoTuristico.id)
        .group_by(RecursoTuristico.id, RecursoTuristico.nombre, RecursoTuristico.distrito)
    ).all()

    if not filas:
        return []

    # Los temas de cada recurso, para poder decir POR QUÉ está donde está.
    temas_por_recurso: dict[int, Counter[str]] = {}

    for recurso_id, temas in sesion.execute(
        select(Valoracion.recurso_id, Valoracion.temas).where(Valoracion.recurso_id.is_not(None))
    ).all():
        contador = temas_por_recurso.setdefault(recurso_id, Counter())
        for tema in temas or []:
            contador[tema] += 1

    return [
        RecursoValorado(
            recurso_id=recurso_id,
            nombre=nombre,
            distrito=distrito,
            total_valoraciones=total,
            puntuacion_media=round(float(media), 2),
            temas_frecuentes=[
                tema for tema, _ in temas_por_recurso.get(recurso_id, Counter()).most_common(3)
            ],
        )
        for recurso_id, nombre, distrito, total, media in filas
    ]


def _evolucion(sesion: Session) -> list[PuntoEnElTiempo]:
    """La media por mes, para ver si la cosa mejora o empeora.

    Se agrupa por mes y no por semana porque con el volumen que puede tener
    este proyecto, una semana tendría dos o tres valoraciones y la línea sería
    ruido con forma de gráfico.
    """
    mes = func.to_char(Valoracion.creado_en, "YYYY-MM").label("mes")

    filas = sesion.execute(
        select(
            mes,
            func.count(Valoracion.id),
            func.avg(Valoracion.puntuacion),
            func.count(Valoracion.id).filter(Valoracion.sentimiento == Sentimiento.POSITIVO.value),
            func.count(Valoracion.id).filter(Valoracion.sentimiento == Sentimiento.NEGATIVO.value),
        )
        .group_by(mes)
        .order_by(mes)
    ).all()

    return [
        PuntoEnElTiempo(
            periodo=periodo,
            total=total,
            puntuacion_media=round(float(media), 2),
            positivas=positivas,
            negativas=negativas,
        )
        for periodo, total, media, positivas, negativas in filas
    ]


def resumir_evidencia(sesion: Session) -> ResumenDeEvidencia:
    """Construye todo lo que el tablero del gestor necesita.

    Una sola función porque el tablero se pinta de una vez: partirlo en seis
    endpoints haría seis viajes de ida y vuelta para pintar una pantalla.
    """
    resumen = ResumenDeEvidencia()

    (
        resumen.total_itinerarios,
        resumen.itinerarios_con_valoracion,
        resumen.porcentaje_con_valoracion,
    ) = calcular_cobertura(sesion)

    resumen.total_valoraciones = sesion.scalar(select(func.count()).select_from(Valoracion)) or 0

    if resumen.total_valoraciones == 0:
        resumen.avisos.append(
            "Todavía no hay ninguna valoración registrada. El tablero se llena "
            "cuando los visitantes empiezan a valorar sus itinerarios."
        )
        return resumen

    resumen.con_comentario = (
        sesion.scalar(
            select(func.count()).where(
                Valoracion.comentario.is_not(None), Valoracion.comentario != ""
            )
        )
        or 0
    )

    media = sesion.scalar(select(func.avg(Valoracion.puntuacion)))
    resumen.puntuacion_media = round(float(media), 2) if media is not None else None

    resumen.sentimiento = _distribucion(sesion)
    resumen.temas = _temas_mas_mencionados(sesion)

    valorados = _recursos_valorados(sesion)
    por_media = sorted(valorados, key=lambda r: (-r.puntuacion_media, -r.total_valoraciones))

    resumen.mejor_valorados = por_media[:CUANTOS_EN_EL_RANQUIN]
    resumen.peor_valorados = list(reversed(por_media[-CUANTOS_EN_EL_RANQUIN:]))

    resumen.evolucion = _evolucion(sesion)

    por_via = dict(
        sesion.execute(
            select(Valoracion.analizado_por, func.count())
            .where(Valoracion.analizado_por.is_not(None))
            .group_by(Valoracion.analizado_por)
        ).all()
    )
    resumen.analizadas_por_modelo = por_via.get("modelo", 0)
    resumen.analizadas_por_reglas = por_via.get("reglas", 0)

    _agregar_avisos(resumen, valorados)

    return resumen


def _agregar_avisos(resumen: ResumenDeEvidencia, valorados: list[RecursoValorado]) -> None:
    """Añade los avisos sobre la fiabilidad de lo que se está mostrando.

    Un tablero que no dice cuándo sus números son frágiles invita a decidir
    sobre nada.
    """
    if resumen.total_valoraciones < MINIMO_PARA_FIARSE:
        resumen.avisos.append(
            f"Solo hay {resumen.total_valoraciones} valoración(es). Las medias de "
            "este tablero son orientativas hasta que haya al menos "
            f"{MINIMO_PARA_FIARSE}."
        )

    poco_fiables = sum(1 for recurso in valorados if not recurso.es_fiable)

    if poco_fiables:
        resumen.avisos.append(
            f"{poco_fiables} de los {len(valorados)} recursos valorados tienen "
            f"menos de {MINIMO_PARA_FIARSE} valoraciones. Su media se mueve mucho "
            "con cada opinión nueva."
        )

    sin_comentario = resumen.total_valoraciones - resumen.con_comentario

    if sin_comentario:
        resumen.avisos.append(
            f"{sin_comentario} valoración(es) no traen comentario. De esas solo se "
            "conoce la puntuación, no de qué hablan."
        )

    if resumen.analizadas_por_reglas and not resumen.analizadas_por_modelo:
        resumen.avisos.append(
            "Todas las valoraciones se analizaron con la alternativa por reglas, "
            "no con el modelo de lenguaje. Es peor leyendo matices y expresiones "
            "que no están en su diccionario."
        )


# ---------------------------------------------------------------------------
# La instantánea
# ---------------------------------------------------------------------------


def guardar_instantanea(sesion: Session) -> RegistroDeEvidencia:
    """Guarda una foto del estado actual, para poder comparar en el tiempo.

    Es lo que hace ``registro_validacion`` en el Incremento 1: sin
    instantáneas, el tablero puede decir dónde está el indicador hoy pero no si
    eso es mejor o peor que el mes pasado.

    No hace ``commit``: quien llama decide la transacción.
    """
    total, con_valoracion, porcentaje = calcular_cobertura(sesion)
    distribucion = _distribucion(sesion)

    media = sesion.scalar(select(func.avg(Valoracion.puntuacion)))

    registro = RegistroDeEvidencia(
        fecha=datetime.now(UTC),
        total_itinerarios=total,
        itinerarios_con_valoracion=con_valoracion,
        porcentaje_con_valoracion=porcentaje,
        total_valoraciones=sesion.scalar(select(func.count()).select_from(Valoracion)) or 0,
        con_comentario=sesion.scalar(
            select(func.count()).where(
                Valoracion.comentario.is_not(None), Valoracion.comentario != ""
            )
        )
        or 0,
        positivas=distribucion.positivas,
        neutras=distribucion.neutras,
        negativas=distribucion.negativas,
        puntuacion_media=round(float(media), 2) if media is not None else None,
    )

    sesion.add(registro)
    sesion.flush()

    return registro


def obtener_instantaneas(sesion: Session, limite: int = 24) -> list[RegistroDeEvidencia]:
    """Las últimas instantáneas, de la más antigua a la más reciente.

    Se devuelven en orden cronológico porque es como se dibuja una línea de
    evolución; invertirlas en la interfaz sería trabajo que ya se puede hacer
    aquí.
    """
    recientes = list(
        sesion.scalars(
            select(RegistroDeEvidencia).order_by(RegistroDeEvidencia.fecha.desc()).limit(limite)
        ).all()
    )

    return list(reversed(recientes))


def valoraciones_del_dia(sesion: Session, dia: date) -> int:
    """Cuántas valoraciones se registraron un día concreto."""
    return sesion.scalar(select(func.count()).where(func.date(Valoracion.creado_en) == dia)) or 0
