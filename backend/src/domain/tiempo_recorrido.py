"""Capa 3 — Cuánto se tarda en recorrer un tramo a pie.

**Por qué esto no es «IA» pero sí es la capa 3 de la arquitectura.** La función
de Tobler es física, no aprendizaje: describe una regularidad medida del cuerpo
humano. Se incluye entre las capas del proyecto porque sustituye a una
estimación que de otro modo sería inventada —«un kilómetro son doce minutos»—
por una que responde al terreno real.

Eso es también lo que la hace defendible sin datos propios: **no necesita
histórico**, igual que el resto de capas del Incremento 3. Es el mismo
argumento que sostiene el MLOps diferido del documento académico.

## La función de Tobler

Waldo Tobler la publicó en 1993 a partir de datos de marcha de Eduard Imhof:

    W = 6 · e^(−3,5 · |S + 0,05|)

donde ``W`` es la velocidad en km/h y ``S`` la pendiente como cociente
(desnivel dividido entre distancia horizontal, sin unidades).

Lo que dice, en palabras:

- En llano (S = 0) se caminan **5,04 km/h**.
- La velocidad máxima **no es en llano**, sino en una bajada suave del 5 %
  (S = −0,05), donde se alcanzan 6 km/h. Ahí está el ``+ 0,05`` de la fórmula.
- Subir y bajar cuestan: el valor absoluto hace que una pendiente del 20 %
  hacia arriba y una del 30 % hacia abajo penalicen de forma parecida.

## Por qué importa en el Valle del Mantaro

El valle está entre 3 240 y 3 400 m, pero sus recursos no. Del Parque de la
Identidad Wanka (3 250 m) al Nevado Huaytapallana hay **+2 300 m de desnivel**.
Un cálculo a velocidad constante diría que se llega en tres horas; la realidad
son ocho o más. Prometer lo primero mandaría gente a la montaña con menos luz
de la que necesita.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# La función de Tobler
# ---------------------------------------------------------------------------

#: Velocidad máxima de la función, en km/h. Se alcanza en la pendiente óptima.
VELOCIDAD_MAXIMA_KMH = 6.0

#: Constante de decaimiento. Cuanto mayor, más castiga la pendiente.
DECAIMIENTO = 3.5

#: Pendiente a la que se camina más rápido: una bajada suave del 5 %.
PENDIENTE_OPTIMA = -0.05

#: Tope de pendiente que se considera caminable. Por encima del 100 % (45°) ya
#: no es caminar, es escalar, y la función de Tobler deja de describirlo.
PENDIENTE_MAXIMA_CAMINABLE = 1.0

#: Velocidad mínima que se admite, en km/h. Sin este suelo, una pendiente
#: extrema daría velocidades cercanas a cero y tiempos de traslado absurdos.
VELOCIDAD_MINIMA_KMH = 0.3


def velocidad_de_tobler(pendiente: float) -> float:
    """Velocidad de marcha en km/h para una pendiente dada.

    ``pendiente`` es el cociente desnivel/distancia horizontal: 0,1 significa
    subir 10 m cada 100 m recorridos. Negativa es bajada.

    Ejemplos de referencia:

    ==========  ==================
    Pendiente   Velocidad
    ==========  ==================
    −0,05        6,00 km/h (máxima)
     0,00        5,04 km/h
     0,10        3,55 km/h
     0,20        2,50 km/h
     0,30        1,76 km/h
    ==========  ==================
    """
    velocidad = VELOCIDAD_MAXIMA_KMH * math.exp(-DECAIMIENTO * abs(pendiente - PENDIENTE_OPTIMA))

    return max(velocidad, VELOCIDAD_MINIMA_KMH)


def calcular_pendiente(distancia_horizontal_m: float, desnivel_m: float) -> float:
    """Pendiente de un tramo, como cociente sin unidades.

    Devuelve 0 si la distancia horizontal es nula: un punto no tiene pendiente,
    y dividir entre cero rompería el cálculo.
    """
    if distancia_horizontal_m <= 0:
        return 0.0

    return desnivel_m / distancia_horizontal_m


@dataclass
class TramoCaminando:
    """Un tramo recorrido a pie, con su tiempo y su esfuerzo."""

    distancia_m: float
    desnivel_m: float
    pendiente: float
    velocidad_kmh: float
    minutos: float

    @property
    def es_muy_empinado(self) -> bool:
        """Si el tramo pasa de lo que se puede considerar caminata."""
        return abs(self.pendiente) > PENDIENTE_MAXIMA_CAMINABLE


def calcular_tramo_caminando(
    distancia_m: float,
    altitud_origen_m: float | None = None,
    altitud_destino_m: float | None = None,
) -> TramoCaminando:
    """Calcula cuánto se tarda en recorrer un tramo a pie.

    Si no se conocen las altitudes, se asume terreno llano y se dice así en el
    resultado (pendiente 0). Es preferible a inventar un desnivel: el error de
    suponer llano es acotado y conocido, el de inventar no.
    """
    if altitud_origen_m is None or altitud_destino_m is None:
        desnivel = 0.0
    else:
        desnivel = altitud_destino_m - altitud_origen_m

    pendiente = calcular_pendiente(distancia_m, desnivel)
    velocidad = velocidad_de_tobler(pendiente)

    # distancia (m) → km, dividido entre km/h → horas, por 60 → minutos.
    minutos = (distancia_m / 1000.0) / velocidad * 60.0

    return TramoCaminando(
        distancia_m=round(distancia_m, 1),
        desnivel_m=round(desnivel, 1),
        pendiente=round(pendiente, 4),
        velocidad_kmh=round(velocidad, 2),
        minutos=round(minutos, 1),
    )


# ---------------------------------------------------------------------------
# Esfuerzo físico acumulado del día
# ---------------------------------------------------------------------------

#: Metros de subida acumulada a partir de los cuales un día se considera
#: exigente. 300 m es el orden de una cuesta larga urbana; 800 m ya es una
#: jornada de montaña.
SUBIDA_DIA_MODERADO_M = 300
SUBIDA_DIA_EXIGENTE_M = 800


def clasificar_esfuerzo(subida_acumulada_m: float) -> str:
    """Clasifica el esfuerzo de un día por su desnivel positivo acumulado.

    Solo cuenta la **subida**, no el desnivel neto: bajar lo que se ha subido
    no descansa las piernas, y un día que sube y baja 400 m tres veces es duro
    aunque termine a la misma altura en la que empezó.
    """
    if subida_acumulada_m >= SUBIDA_DIA_EXIGENTE_M:
        return "exigente"
    if subida_acumulada_m >= SUBIDA_DIA_MODERADO_M:
        return "moderado"
    return "suave"


# ---------------------------------------------------------------------------
# Aviso de altitud
# ---------------------------------------------------------------------------

#: Altitud a partir de la cual conviene avisar del mal de altura. El umbral
#: habitual en medicina de montaña son 2 500 m; el valle está muy por encima,
#: así que el aviso aplica prácticamente siempre para quien viene de la costa.
ALTITUD_DE_AVISO_M = 2500


def necesita_aviso_de_altitud(altitud_maxima_m: float | None) -> bool:
    """Si hay que avisar al visitante sobre el mal de altura.

    Huancayo está a 3 250 m. Quien llega de Lima, al nivel del mar, sube más de
    tres kilómetros en unas horas de carretera. Avisarlo es un detalle de
    seguridad real, no un adorno.
    """
    return altitud_maxima_m is not None and altitud_maxima_m >= ALTITUD_DE_AVISO_M
