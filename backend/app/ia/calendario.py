"""Calendario festivo del Valle del Mantaro.

Este módulo alimenta la predicción de afluencia del Incremento 3: saber si un
día cae en fiesta cambia por completo cuánta gente hay en un sitio.

**Las fiestas móviles se CALCULAN, no se escriben a mano.** Semana Santa,
Carnavales y Corpus Christi dependen de la fecha de Pascua, que cambia cada
año. Escribirlas fijas obligaría a editar el código cada enero y garantizaría
que el sistema se equivoque el año que nadie se acuerde de hacerlo.

Fuentes de las fiestas fijas: sección 9 de ``CONTEXTO_PROYECTO.md``, que a su
vez las toma del inventario del MINCETUR, del expediente UNESCO de la
Huaconada de Mito y del calendario de feriados nacionales del Perú.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class TipoFestividad(StrEnum):
    """Para qué sirve distinguirlas: no todas atraen al mismo tipo de gente."""

    RELIGIOSA = "religiosa"
    COSTUMBRISTA = "costumbrista"
    CIVICA = "civica"
    FERIA = "feria"
    NACIONAL = "nacional"


@dataclass(frozen=True)
class Festividad:
    """Una celebración con fecha, lugar y origen documentado."""

    nombre: str
    fecha_inicio: date
    fecha_fin: date
    tipo: TipoFestividad
    #: Distritos donde se celebra. Vacío significa que abarca todo el valle.
    distritos: tuple[str, ...] = ()
    es_movil: bool = False
    fuente: str = ""

    def ocurre_el(self, dia: date) -> bool:
        return self.fecha_inicio <= dia <= self.fecha_fin

    def afecta_al_distrito(self, distrito: str) -> bool:
        """Una fiesta sin distritos declarados afecta a todo el valle."""
        return not self.distritos or distrito.upper() in self.distritos


# ---------------------------------------------------------------------------
# Cálculo de la Pascua (computus)
# ---------------------------------------------------------------------------


def calcular_domingo_de_pascua(anio: int) -> date:
    """Devuelve el Domingo de Pascua del año indicado.

    Implementa el **algoritmo de Butcher** (1876) para el calendario
    gregoriano, que es el que sigue la Iglesia católica y, por tanto, el que
    rige Semana Santa, Carnavales y Corpus Christi en el Perú.

    Cómo funciona, en corto: la Pascua es el primer domingo después de la
    primera luna llena que cae en el equinoccio de primavera boreal (21 de
    marzo) o después. Como el ciclo lunar y el solar no encajan, hay que
    reconciliarlos con dos correcciones —el *ciclo metónico* de 19 años y las
    reglas gregorianas de los años seculares—, y eso es lo que hacen las
    divisiones de abajo.

    No se buscan nombres «bonitos» para las variables a propósito: son las
    letras del algoritmo original, y renombrarlas haría imposible cotejarlo
    con la fuente. Cada una lleva su comentario.
    """
    a = anio % 19  # posición del año en el ciclo lunar de 19 años
    b, c = divmod(anio, 100)  # siglo y año dentro del siglo
    d, e = divmod(b, 4)  # correcciones del calendario gregoriano
    f = (b + 8) // 25  # corrección secular
    g = (b - f + 1) // 3  # corrección lunar secular
    h = (19 * a + b - d - g + 15) % 30  # epacta: edad de la luna el 22 de marzo
    i, k = divmod(c, 4)
    ele = (32 + 2 * e + 2 * i - h - k) % 7  # días hasta el domingo siguiente
    m = (a + 11 * h + 22 * ele) // 451  # corrección de los casos límite
    mes, dia = divmod(h + ele - 7 * m + 114, 31)

    return date(anio, mes, dia + 1)


def calcular_fiestas_moviles(anio: int) -> list[Festividad]:
    """Devuelve las fiestas cuya fecha depende de la Pascua.

    Los desplazamientos respecto al Domingo de Pascua son los del calendario
    litúrgico y no cambian nunca:

    ==========================  ==================
    Celebración                 Días desde Pascua
    ==========================  ==================
    Carnavales (dom. a martes)  −49 a −47
    Domingo de Ramos            −7
    Jueves y Viernes Santo      −3 y −2
    Domingo de Pascua            0
    Corpus Christi             +60
    ==========================  ==================
    """
    pascua = calcular_domingo_de_pascua(anio)

    return [
        Festividad(
            nombre="Carnavales",
            fecha_inicio=pascua - timedelta(days=49),
            fecha_fin=pascua - timedelta(days=47),
            tipo=TipoFestividad.COSTUMBRISTA,
            es_movil=True,
            fuente="Calendario litúrgico (49 días antes de Pascua)",
        ),
        Festividad(
            # Se toma desde el Domingo de Ramos, que es cuando empieza el
            # movimiento real de visitantes, no desde el Jueves Santo.
            nombre="Semana Santa",
            fecha_inicio=pascua - timedelta(days=7),
            fecha_fin=pascua,
            tipo=TipoFestividad.RELIGIOSA,
            es_movil=True,
            fuente="Calendario litúrgico (Domingo de Ramos a Domingo de Pascua)",
        ),
        Festividad(
            nombre="Corpus Christi",
            fecha_inicio=pascua + timedelta(days=60),
            fecha_fin=pascua + timedelta(days=60),
            tipo=TipoFestividad.RELIGIOSA,
            es_movil=True,
            fuente="Calendario litúrgico (60 días después de Pascua)",
        ),
    ]


# ---------------------------------------------------------------------------
# Fiestas de fecha fija
# ---------------------------------------------------------------------------

#: Fiestas del Valle del Mantaro con fecha fija, en formato (mes, día inicio,
#: mes, día fin). Solo se incluyen las de confianza alta documentada en
#: CONTEXTO_PROYECTO.md; las de confianza baja (aniversarios distritales sin
#: fuente) quedan fuera a propósito.
_FIESTAS_FIJAS: list[
    tuple[str, tuple[int, int], tuple[int, int], TipoFestividad, tuple[str, ...], str]
] = [
    (
        "Huaconada de Mito",
        (1, 1),
        (1, 3),
        TipoFestividad.COSTUMBRISTA,
        ("MITO",),
        "Patrimonio Cultural Inmaterial de la Humanidad, UNESCO 2010",
    ),
    (
        "La Tunantada",
        (1, 20),
        (1, 30),
        TipoFestividad.COSTUMBRISTA,
        ("JAUJA", "YAUYOS"),
        "CONTEXTO_PROYECTO.md, sección 9",
    ),
    (
        "Batalla de Carato",
        (4, 19),
        (4, 19),
        TipoFestividad.CIVICA,
        ("CHUPACA",),
        "CONTEXTO_PROYECTO.md, sección 9",
    ),
    (
        "Fundación española de Jauja",
        (4, 25),
        (4, 25),
        TipoFestividad.CIVICA,
        ("JAUJA",),
        "CONTEXTO_PROYECTO.md, sección 9",
    ),
    (
        "Fiesta de Santiago",
        (7, 24),
        (7, 30),
        TipoFestividad.COSTUMBRISTA,
        (),  # se celebra en cerca de 28 distritos del valle
        "CONTEXTO_PROYECTO.md, sección 9",
    ),
    (
        "Virgen de Cocharcas",
        (9, 8),
        (9, 14),
        TipoFestividad.RELIGIOSA,
        ("SAPALLANGA", "ORCOTUNA", "APATA"),
        "CONTEXTO_PROYECTO.md, sección 9",
    ),
]

#: Feriados nacionales del Perú con fecha fija. Mueven gente por todo el país,
#: no solo por el valle.
_FERIADOS_NACIONALES: list[tuple[str, tuple[int, int]]] = [
    ("Año Nuevo", (1, 1)),
    ("Día del Trabajo", (5, 1)),
    ("San Pedro y San Pablo", (6, 29)),
    ("Fiestas Patrias", (7, 28)),
    ("Fiestas Patrias", (7, 29)),
    ("Santa Rosa de Lima", (8, 30)),
    ("Combate de Angamos", (10, 8)),
    ("Todos los Santos", (11, 1)),
    ("Inmaculada Concepción", (12, 8)),
    ("Batalla de Ayacucho", (12, 9)),
    ("Navidad", (12, 25)),
]


def calcular_fiestas_fijas(anio: int) -> list[Festividad]:
    """Devuelve las fiestas del valle que caen siempre en la misma fecha."""
    festividades = [
        Festividad(
            nombre=nombre,
            fecha_inicio=date(anio, mes_inicio, dia_inicio),
            fecha_fin=date(anio, mes_fin, dia_fin),
            tipo=tipo,
            distritos=distritos,
            es_movil=False,
            fuente=fuente,
        )
        for nombre, (mes_inicio, dia_inicio), (
            mes_fin,
            dia_fin,
        ), tipo, distritos, fuente in _FIESTAS_FIJAS
    ]

    festividades += [
        Festividad(
            nombre=nombre,
            fecha_inicio=date(anio, mes, dia),
            fecha_fin=date(anio, mes, dia),
            tipo=TipoFestividad.NACIONAL,
            es_movil=False,
            fuente="Feriados nacionales del Perú",
        )
        for nombre, (mes, dia) in _FERIADOS_NACIONALES
    ]

    return festividades


def calendario_del_anio(anio: int) -> list[Festividad]:
    """Todas las fiestas del año, móviles y fijas, ordenadas por fecha."""
    todas = calcular_fiestas_moviles(anio) + calcular_fiestas_fijas(anio)
    return sorted(todas, key=lambda festividad: festividad.fecha_inicio)


# ---------------------------------------------------------------------------
# Consultas sobre una fecha concreta
# ---------------------------------------------------------------------------

#: Día de la semana en que se celebra la Feria Dominical de Huancayo, en la
#: avenida Huancavelica. Es el evento recurrente más importante del valle:
#: no es una fiesta de calendario, pero llena Huancayo todos los domingos.
DIA_DE_LA_FERIA_DOMINICAL = 6  # 6 = domingo, según date.weekday()

DISTRITO_DE_LA_FERIA_DOMINICAL = "HUANCAYO"


def festividades_en(dia: date, distrito: str | None = None) -> list[Festividad]:
    """Devuelve las fiestas activas ese día, opcionalmente filtradas por distrito."""
    activas = [f for f in calendario_del_anio(dia.year) if f.ocurre_el(dia)]

    if distrito is None:
        return activas

    return [f for f in activas if f.afecta_al_distrito(distrito)]


def hay_feria_dominical(dia: date, distrito: str) -> bool:
    """Comprueba si ese día hay Feria Dominical en ese distrito."""
    return (
        dia.weekday() == DIA_DE_LA_FERIA_DOMINICAL
        and distrito.upper() == DISTRITO_DE_LA_FERIA_DOMINICAL
    )


def es_feriado_nacional(dia: date) -> bool:
    """Comprueba si es feriado nacional, contando los móviles."""
    return any(
        festividad.tipo == TipoFestividad.NACIONAL
        or (festividad.nombre == "Semana Santa" and festividad.ocurre_el(dia))
        for festividad in festividades_en(dia)
    )


def dias_hasta_la_festividad_mas_cercana(dia: date, distrito: str | None = None) -> int:
    """Días que faltan (o sobran) hasta la fiesta más próxima.

    Devuelve 0 si ese mismo día hay fiesta. Se miran también el año anterior y
    el siguiente para que un 30 de diciembre encuentre el Año Nuevo, y un 2 de
    enero encuentre la Huaconada que acaba de terminar.

    Es una de las características que consume el modelo de afluencia: la gente
    empieza a moverse antes de que la fiesta empiece.
    """
    candidatas = [
        festividad
        for anio in (dia.year - 1, dia.year, dia.year + 1)
        for festividad in calendario_del_anio(anio)
        if distrito is None or festividad.afecta_al_distrito(distrito)
    ]

    if not candidatas:
        return 999

    def distancia(festividad: Festividad) -> int:
        if festividad.ocurre_el(dia):
            return 0
        if dia < festividad.fecha_inicio:
            return (festividad.fecha_inicio - dia).days
        return (dia - festividad.fecha_fin).days

    return min(distancia(festividad) for festividad in candidatas)


def temporada_de(dia: date) -> str:
    """Clasifica el mes en temporada turística del Valle del Mantaro.

    No son las estaciones del hemisferio sur: son los periodos que de verdad
    mueven visitantes en el valle.

    - **alta**: julio y agosto. Fiesta de Santiago, Fiestas Patriasy vacaciones
      escolares se juntan en el mismo mes.
    - **media**: enero y febrero (Huaconada, Tunantada, Carnavales y verano
      costeño) y diciembre (fiestas de fin de año).
    - **baja**: el resto, con la salvedad de que Semana Santa la levanta
      puntualmente y eso lo recoge la característica de festividad.
    """
    if dia.month in (7, 8):
        return "alta"
    if dia.month in (1, 2, 12):
        return "media"
    return "baja"
