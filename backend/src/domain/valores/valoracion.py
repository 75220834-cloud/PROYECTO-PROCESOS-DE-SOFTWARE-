"""Objetos de valor de valoracion.

Viven en el dominio y no en los modelos de SQLAlchemy porque no son una forma
de guardar datos: son parte de las reglas. El ORM los importa desde aqui, de
modo que la dependencia apunta hacia adentro.
"""

from __future__ import annotations

from enum import StrEnum


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
