"""Análisis de sentimiento y temas de las valoraciones (Incremento 6).

Es la última capa de IA del proyecto, y la primera que trabaja sobre **datos
que el propio sistema genera**. Hasta aquí todo venía de fuentes externas
estables: el inventario del MINCETUR, las series de visitantes, la red vial.

## Las dos vías, y por qué las dos existen

La regla de oro del proyecto exige que toda funcionalidad con modelo tenga una
alternativa por reglas explícitas, elegible por configuración:

| ``USAR_MODELO_SENTIMIENTO`` | Qué se usa |
|---|---|
| ``true`` | **pysentimiento**, modelo RoBERTuito en español, local |
| ``false`` | **Reglas**: puntuación + diccionario de palabras |

Aquí la alternativa por reglas no es un adorno defensivo. El modelo pesa
cientos de megas y tarda en cargar; en un portátil de exposición sin GPU, o en
una máquina donde la descarga falle, el sistema **tiene que seguir dando
valoraciones analizadas**. Con las reglas lo hace, peor pero al instante.

## Por qué las reglas empiezan por la puntuación y no por el texto

Porque la puntuación es el dato más fiable que hay. Quien pone una estrella
está descontento aunque escriba «bueno, no estuvo tan mal». Un diccionario de
palabras que ignore el número acertaría menos que el número solo.

El texto se usa para **corregir** la lectura de la puntuación, no para
sustituirla: sirve sobre todo con los tres de cinco, que es donde el número no
dice nada.

## Por qué los temas son un conjunto cerrado

Extraer temas libres con un modelo daría una nube de palabras bonita e
inservible. El gestor necesita poder decir «los comentarios sobre señalización
empeoraron respecto del mes pasado», y para eso «señalización» tiene que ser
siempre la misma categoría, escrita igual.

Los temas salen del plan de trabajo —*limpieza, atención, precio, acceso,
señalización…*— más los que aparecen constantemente en reseñas de turismo.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modelos.valoracion import PUNTUACION_MAXIMA, PUNTUACION_MINIMA, Sentimiento, TemaValoracion

# ---------------------------------------------------------------------------
# Diccionarios de la alternativa por reglas
# ---------------------------------------------------------------------------

#: Palabras que empujan hacia lo positivo. Están en la forma en que la gente
#: escribe reseñas en Perú, no en la forma canónica del diccionario.
PALABRAS_POSITIVAS: frozenset[str] = frozenset(
    {
        "excelente",
        "excelentes",
        "bueno",
        "buena",
        "buenos",
        "buenas",
        "bonito",
        "bonita",
        "bonitos",
        "bonitas",
        "hermoso",
        "hermosa",
        "lindo",
        "linda",
        "lindos",
        "lindas",
        "increible",
        "espectacular",
        "maravilloso",
        "maravillosa",
        "recomendado",
        "recomendable",
        "recomiendo",
        "encanto",
        "encanta",
        "gusto",
        "gusta",
        "agradable",
        "amable",
        "amables",
        "limpio",
        "limpia",
        "ordenado",
        "tranquilo",
        "tranquila",
        "acogedor",
        "rico",
        "rica",
        "delicioso",
        "deliciosa",
        "impresionante",
        "perfecto",
        "perfecta",
        "genial",
        "chevere",
        "bacan",
        "vale",
        "volveria",
        "volver",
        "atento",
        "atenta",
        "atentos",
        "puntual",
        "barato",
        "barata",
        "accesible",
        "facil",
        "comodo",
        "comoda",
        "seguro",
        "segura",
    }
)

#: Palabras que empujan hacia lo negativo.
#:
#: **Solo palabras sueltas y sin tildes.** El texto se trocea en palabras y se
#: normaliza antes de comparar, asi que una entrada como «no recomiendo» o
#: «pesimo» con tilde nunca coincidiria: seria codigo muerto que aparenta
#: funcionar. Las expresiones con negacion las cubre el mecanismo de negadores,
#: que invierte «recomiendo» cuando lleva un «no» delante.
PALABRAS_NEGATIVAS: frozenset[str] = frozenset(
    {
        "malo",
        "mala",
        "malos",
        "malas",
        "pesimo",
        "pesima",
        "terrible",
        "horrible",
        "feo",
        "fea",
        "sucio",
        "sucia",
        "sucios",
        "sucias",
        "desordenado",
        "caro",
        "cara",
        "caros",
        "caras",
        "carisimo",
        "lento",
        "lenta",
        "demora",
        "demoro",
        "demoraron",
        "tardaron",
        "grosero",
        "grosera",
        "maleducado",
        "descortes",
        "peligroso",
        "peligrosa",
        "inseguro",
        "insegura",
        "roto",
        "rota",
        "abandonado",
        "abandonada",
        "descuidado",
        "descuidada",
        "estafa",
        "engano",
        "decepcion",
        "decepcionante",
        "decepcionado",
        "aburrido",
        "aburrida",
        "dificil",
        "complicado",
        "imposible",
        "nunca",
        "jamas",
        "peor",
        "lamentable",
        "incomodo",
        "incomoda",
        "frio",
        "fria",
        "ruidoso",
    }
)

#: Palabras que invierten lo que viene después. «No estuvo limpio» no es una
#: valoración positiva por contener «limpio».
NEGADORES: frozenset[str] = frozenset({"no", "ni", "nunca", "jamas", "tampoco", "sin"})

#: Cuántas palabras hacia adelante alcanza una negación. Tres cubre «no muy
#: bueno» y «no estuvo nada limpio» sin llegar a invertir la frase siguiente.
ALCANCE_DE_LA_NEGACION = 3

#: Términos que delatan cada tema. Se buscan con límites de palabra, igual que
#: en el módulo de afinidad: sin eso, «caro» aparecería dentro de «carretera».
TERMINOS_POR_TEMA: dict[str, tuple[str, ...]] = {
    TemaValoracion.LIMPIEZA: (
        "limpio",
        "limpia",
        "limpieza",
        "sucio",
        "sucia",
        "suciedad",
        "basura",
        "aseo",
        "bano",
        "banos",
        "higiene",
        "olor",
    ),
    TemaValoracion.ATENCION: (
        "atencion",
        "atendieron",
        "atendio",
        "trato",
        "amable",
        "amables",
        "personal",
        "guia",
        "guias",
        "servicio",
        "grosero",
        "cortes",
        "atento",
        "atenta",
        "recibieron",
    ),
    TemaValoracion.PRECIO: (
        "precio",
        "precios",
        "caro",
        "cara",
        "barato",
        "barata",
        "costo",
        "cuesta",
        "cobran",
        "cobraron",
        "tarifa",
        "entrada",
        "vale la pena",
        "economico",
        "economica",
    ),
    TemaValoracion.ACCESO: (
        "acceso",
        "llegar",
        "llegamos",
        "camino",
        "carretera",
        "trocha",
        "transporte",
        "movilidad",
        "combi",
        "colectivo",
        "taxi",
        "lejos",
        "cerca",
        "estacionamiento",
        "subida",
        "escaleras",
    ),
    TemaValoracion.SENALIZACION: (
        "senalizacion",
        "senales",
        "senal",
        "letrero",
        "letreros",
        "cartel",
        "carteles",
        "indicaciones",
        "informacion",
        "mapa",
        "perdimos",
        "perdidos",
        "ubicar",
    ),
    TemaValoracion.SEGURIDAD: (
        "seguridad",
        "seguro",
        "segura",
        "inseguro",
        "insegura",
        "peligro",
        "peligroso",
        "peligrosa",
        "robo",
        "robaron",
        "cuidado",
        "vigilancia",
        "policia",
    ),
    TemaValoracion.COMIDA: (
        "comida",
        "comer",
        "almuerzo",
        "desayuno",
        "cena",
        "trucha",
        "plato",
        "platos",
        "restaurante",
        "rico",
        "rica",
        "delicioso",
        "deliciosa",
        "sabor",
        "porcion",
        "porciones",
        "bebida",
    ),
    TemaValoracion.PAISAJE: (
        "paisaje",
        "paisajes",
        "vista",
        "vistas",
        "naturaleza",
        "cerro",
        "cerros",
        "laguna",
        "rio",
        "nevado",
        "campo",
        "verde",
        "hermoso",
        "bonito",
        "fotos",
        "atardecer",
        "mirador",
    ),
    TemaValoracion.INFRAESTRUCTURA: (
        "infraestructura",
        "instalaciones",
        "construccion",
        "edificio",
        "museo",
        "iglesia",
        "mantenimiento",
        "conservado",
        "conservacion",
        "restaurado",
        "abandonado",
        "roto",
        "deteriorado",
        "banca",
        "sombra",
    ),
}


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes, para comparar con los diccionarios.

    Se quitan las tildes porque la gente escribe reseñas desde el móvil y la
    mitad no las pone. Un diccionario que exija «pésimo» con tilde se perdería
    todos los «pesimo».

    A diferencia del normalizador del catálogo, aquí **sí** se pierde la Ñ: los
    diccionarios de este módulo están escritos sin ella («bano», «senalizacion»)
    justo por el mismo motivo, y conservarla obligaría a duplicar cada entrada.
    """
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> list[str]:
    """Trocea el texto en palabras, descartando la puntuación."""
    return re.findall(r"\b\w+\b", normalizar(texto))


def contiene_termino(texto_normalizado: str, termino: str) -> bool:
    """Si el término aparece como palabra completa.

    Con límites de palabra, no como subcadena. Es la misma lección que dejó el
    Incremento 3, donde «rio» aparecía dentro de «santuaRIO» y clasificaba mal
    los recursos.
    """
    return re.search(rf"\b{re.escape(termino)}\b", texto_normalizado) is not None


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass
class AnalisisDeComentario:
    """Lo que el sistema entendió de un comentario."""

    sentimiento: str
    confianza: float
    temas: list[str] = field(default_factory=list)
    #: 'modelo' o 'reglas'.
    analizado_por: str = "reglas"
    #: Qué produjo el análisis, con detalle para poder reproducirlo.
    version: str = ""
    #: Las palabras que decidieron el resultado. Solo las llenan las reglas: es
    #: lo que hace auditable esta vía y lo que el modelo no puede dar.
    terminos_decisivos: list[str] = field(default_factory=list)

    analizado_en: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Detección de temas — común a las dos vías
# ---------------------------------------------------------------------------


def detectar_temas(comentario: str) -> list[str]:
    """Devuelve los temas que menciona un comentario.

    Es común a las dos vías a propósito. El modelo de pysentimiento clasifica
    sentimiento, no temas: pedirle temas exigiría otro modelo, y un conjunto
    cerrado de nueve categorías se detecta bien con términos.

    El orden del resultado es el de ``TemaValoracion``, no el de aparición, para
    que dos comentarios con los mismos temas den siempre la misma lista.
    """
    if not comentario or not comentario.strip():
        return []

    normalizado = normalizar(comentario)

    return [
        tema
        for tema, terminos in TERMINOS_POR_TEMA.items()
        if any(contiene_termino(normalizado, termino) for termino in terminos)
    ]


# ---------------------------------------------------------------------------
# Vía A — las reglas
# ---------------------------------------------------------------------------

#: Puntuaciones que se leen como positivas y negativas por sí solas. El 3 queda
#: fuera a propósito: es el que no dice nada, y donde el texto decide.
PUNTUACION_CLARAMENTE_POSITIVA = 4
PUNTUACION_CLARAMENTE_NEGATIVA = 2

#: Cuántas palabras de ventaja necesita un bando para imponerse a la puntuación.
#: Con una sola palabra, un «pero estaba sucio» al final de una reseña de cinco
#: estrellas volcaría toda la valoración.
VENTAJA_PARA_CONTRADECIR_LA_PUNTUACION = 2


def analizar_con_reglas(comentario: str | None, puntuacion: int) -> AnalisisDeComentario:
    """Clasifica una valoración con la puntuación y un diccionario de palabras.

    **Es la alternativa explícita que exige la regla de oro del proyecto.**
    Funciona sin descargar nada, sin GPU y en microsegundos.

    El algoritmo, en orden:

    1. Se parte de lo que dice la **puntuación**, que es el dato más fiable.
    2. Se cuentan las palabras positivas y negativas del comentario, invirtiendo
       las que van detrás de una negación.
    3. El texto solo cambia el veredicto de la puntuación si gana por margen
       suficiente, o si la puntuación era un 3, que no dice nada.
    """
    por_la_puntuacion = _sentimiento_de_la_puntuacion(puntuacion)

    if not comentario or not comentario.strip():
        # Sin texto no hay nada que leer: manda el número, y la confianza es
        # menor porque una estrella sola dice poco.
        return AnalisisDeComentario(
            sentimiento=por_la_puntuacion,
            confianza=0.6,
            temas=[],
            analizado_por="reglas",
            version="reglas: solo puntuacion",
        )

    positivas, negativas, decisivas = _contar_palabras(comentario)

    sentimiento, confianza = _resolver(por_la_puntuacion, puntuacion, positivas, negativas)

    return AnalisisDeComentario(
        sentimiento=sentimiento,
        confianza=confianza,
        temas=detectar_temas(comentario),
        analizado_por="reglas",
        version=f"reglas: puntuacion + diccionario ({len(PALABRAS_POSITIVAS)}+"
        f"{len(PALABRAS_NEGATIVAS)} palabras)",
        terminos_decisivos=decisivas,
    )


def _sentimiento_de_la_puntuacion(puntuacion: int) -> str:
    """Lo que dice la puntuación por sí sola."""
    if puntuacion >= PUNTUACION_CLARAMENTE_POSITIVA:
        return Sentimiento.POSITIVO
    if puntuacion <= PUNTUACION_CLARAMENTE_NEGATIVA:
        return Sentimiento.NEGATIVO
    return Sentimiento.NEUTRO


def _contar_palabras(comentario: str) -> tuple[int, int, list[str]]:
    """Cuenta palabras positivas y negativas, respetando las negaciones.

    Devuelve ``(positivas, negativas, terminos_decisivos)``. Los términos
    decisivos son las palabras que contaron, con un prefijo ``no `` cuando
    venían negadas: es lo que permite auditar por qué salió lo que salió.
    """
    palabras = _palabras(comentario)

    positivas = 0
    negativas = 0
    decisivos: list[str] = []

    for indice, palabra in enumerate(palabras):
        es_positiva = palabra in PALABRAS_POSITIVAS
        es_negativa = palabra in PALABRAS_NEGATIVAS

        if not es_positiva and not es_negativa:
            continue

        # ¿Hay una negación en las tres palabras anteriores?
        desde = max(0, indice - ALCANCE_DE_LA_NEGACION)
        negada = any(anterior in NEGADORES for anterior in palabras[desde:indice])

        if negada:
            # «No limpio» cuenta como negativo, «no sucio» como positivo.
            es_positiva, es_negativa = es_negativa, es_positiva
            decisivos.append(f"no {palabra}")
        else:
            decisivos.append(palabra)

        positivas += int(es_positiva)
        negativas += int(es_negativa)

    return positivas, negativas, decisivos


def _resolver(
    por_la_puntuacion: str, puntuacion: int, positivas: int, negativas: int
) -> tuple[str, float]:
    """Combina lo que dice la puntuación con lo que dice el texto."""
    diferencia = positivas - negativas

    # Con un 3, la puntuación no aporta nada: decide el texto, aunque sea por
    # una palabra.
    if puntuacion == 3:
        if diferencia > 0:
            return Sentimiento.POSITIVO, min(0.5 + 0.1 * diferencia, 0.85)
        if diferencia < 0:
            return Sentimiento.NEGATIVO, min(0.5 + 0.1 * abs(diferencia), 0.85)
        return Sentimiento.NEUTRO, 0.5

    # Con el resto, el texto tiene que ganar por margen para contradecir.
    if diferencia >= VENTAJA_PARA_CONTRADECIR_LA_PUNTUACION:
        del_texto = Sentimiento.POSITIVO
    elif diferencia <= -VENTAJA_PARA_CONTRADECIR_LA_PUNTUACION:
        del_texto = Sentimiento.NEGATIVO
    else:
        del_texto = por_la_puntuacion

    if del_texto == por_la_puntuacion:
        # Los dos dicen lo mismo: mucha confianza.
        return por_la_puntuacion, min(0.75 + 0.05 * abs(diferencia), 0.95)

    # Se contradicen. Manda el texto, pero con poca confianza: es justo el caso
    # que un humano debería revisar, y el tablero puede filtrarlo.
    return del_texto, 0.55


# ---------------------------------------------------------------------------
# Vía B — el modelo
# ---------------------------------------------------------------------------

#: Identificador del modelo, para poder reproducir un análisis viejo.
MODELO_DE_SENTIMIENTO = "pysentimiento/robertuito-sentiment-analysis"

#: Cómo traducir las etiquetas del modelo a las del proyecto. pysentimiento
#: devuelve POS, NEU y NEG.
ETIQUETAS_DEL_MODELO: dict[str, str] = {
    "POS": Sentimiento.POSITIVO,
    "NEU": Sentimiento.NEUTRO,
    "NEG": Sentimiento.NEGATIVO,
}

#: El analizador cargado, para no reconstruirlo en cada comentario. Cargarlo
#: tarda segundos; hacerlo por valoración dejaría el tablero inservible.
_analizador = None


def hay_modelo_disponible() -> bool:
    """Si pysentimiento está instalado y su modelo se puede cargar.

    Se comprueba de verdad, cargándolo. Preguntar solo si el paquete está
    instalado no basta: el modelo se descarga la primera vez, y sin internet la
    carga falla aunque la biblioteca esté.
    """
    try:
        return _obtener_analizador() is not None
    except Exception:  # noqa: BLE001 - falta el paquete, o el modelo, o la red
        return False


def _obtener_analizador():
    """Carga el analizador una sola vez por proceso."""
    global _analizador  # noqa: PLW0603 - es una caché deliberada de proceso

    if _analizador is None:
        from pysentimiento import create_analyzer

        _analizador = create_analyzer(task="sentiment", lang="es")

    return _analizador


#: Por debajo de esta confianza, el modelo no se impone a la puntuación.
#:
#: Sale de la medición: los dos fallos del modelo sobre el conjunto de prueba
#: («Estuvo normal, nada del otro mundo» → positivo con 0,63; «No es caro y no
#: tuvimos ningún problema» → neutro con 0,67) venían los dos con confianza
#: baja, mientras que sus aciertos rondaban 0,80–0,98. El umbral separa esos
#: dos grupos.
CONFIANZA_PARA_IMPONERSE = 0.70


def analizar_con_modelo(comentario: str | None, puntuacion: int) -> AnalisisDeComentario:
    """Clasifica el comentario con el modelo en español, y lo cruza con la puntuación.

    Si no hay comentario, cae a las reglas: un modelo de texto no tiene nada que
    leer en una cadena vacía, y devolver «neutro» sería tirar la información que
    sí da la puntuación.

    ## Por qué el modelo también mira las estrellas

    La primera versión de este módulo dejaba que el modelo decidiera solo con el
    texto, y al medir salió esto:

    ============================  ==========  ==========
    Conjunto de prueba            Reglas      Modelo
    ============================  ==========  ==========
    Con la puntuación disponible  13/13       11/13
    **Solo el texto**             **8/14**    **11/14**
    ============================  ==========  ==========

    Las reglas solo ganaban porque veían un dato que al modelo se le estaba
    ocultando. En comprensión del texto el modelo gana claramente: acierta con
    vocabulario que no está en ningún diccionario («superó las expectativas»,
    «nos arrepentimos», «nadie se disculpó») y con la ironía («muy bonito todo,
    lástima que cerraran»).

    Así que se le da el mismo dato. El modelo lee el texto, la puntuación aporta
    su señal, y solo cuando el modelo está **seguro** se impone al número.
    """
    if not comentario or not comentario.strip():
        return analizar_con_reglas(comentario, puntuacion)

    prediccion = _obtener_analizador().predict(comentario)

    del_texto = ETIQUETAS_DEL_MODELO.get(prediccion.output, Sentimiento.NEUTRO)
    confianza_del_texto = float(prediccion.probas.get(prediccion.output, 0.0))

    sentimiento, confianza = _cruzar_con_la_puntuacion(del_texto, confianza_del_texto, puntuacion)

    return AnalisisDeComentario(
        sentimiento=sentimiento,
        confianza=round(confianza, 4),
        # Los temas los detectan las reglas también aquí: el modelo clasifica
        # sentimiento, no temas.
        temas=detectar_temas(comentario),
        analizado_por="modelo",
        version=MODELO_DE_SENTIMIENTO,
    )


def _cruzar_con_la_puntuacion(
    del_texto: str, confianza_del_texto: float, puntuacion: int
) -> tuple[str, float]:
    """Combina lo que dijo el modelo del texto con lo que dicen las estrellas.

    Tres casos:

    1. **Coinciden** → se mantiene, con más confianza: dos fuentes que dicen lo
       mismo valen más que una.
    2. **Discrepan y el modelo está seguro** → manda el modelo. Es el caso de
       «5 estrellas, pero el guía llegó tarde y nadie se disculpó»: la persona
       redondeó la nota hacia arriba y el texto dice lo que pasó.
    3. **Discrepan y el modelo duda** → mandan las estrellas, que es el dato
       más fiable que hay, y la confianza baja para que el tablero pueda
       filtrar estos casos.
    """
    por_la_puntuacion = _sentimiento_de_la_puntuacion(puntuacion)

    if del_texto == por_la_puntuacion:
        return del_texto, min(confianza_del_texto + 0.1, 0.99)

    # Discrepan. El modelo solo se impone si está seguro; si duda, mandan las
    # estrellas.
    #
    # Esto vale también para el 3, que en la primera versión se trataba como
    # «sin señal» y por eso dejaba pasar cualquier veredicto del modelo. Un 3 no
    # es la ausencia de opinión: es una opinión tibia, y contradecirla exige el
    # mismo nivel de seguridad que contradecir un 1 o un 5. El caso que lo
    # destapó: «Estuvo normal, nada del otro mundo» con 3 estrellas, que el
    # modelo leía como positivo con solo 0,63 de confianza.
    if confianza_del_texto >= CONFIANZA_PARA_IMPONERSE:
        return del_texto, confianza_del_texto

    return por_la_puntuacion, 0.55


# ---------------------------------------------------------------------------
# El interruptor
# ---------------------------------------------------------------------------


def analizar(
    comentario: str | None, puntuacion: int, usar_modelo: bool = True
) -> AnalisisDeComentario:
    """Analiza una valoración por la vía que corresponda.

    Si se pide el modelo y no está disponible, **se usa las reglas y se dice**:
    el resultado lleva ``analizado_por = "reglas"``, así que el tablero nunca
    atribuye al modelo algo que no hizo.

    Fallar en vez de degradar dejaría valoraciones sin analizar en la máquina de
    la exposición, que es donde más importa que funcione.
    """
    if not usar_modelo:
        return analizar_con_reglas(comentario, puntuacion)

    try:
        return analizar_con_modelo(comentario, puntuacion)
    except Exception:  # noqa: BLE001 - sin paquete, sin modelo o sin memoria
        analisis = analizar_con_reglas(comentario, puntuacion)
        analisis.version = f"{analisis.version} (se pidió el modelo y no estaba disponible)"
        return analisis


def validar_puntuacion(puntuacion: int) -> None:
    """Comprueba que la puntuación esté en el rango, o lanza ``ValueError``."""
    if not PUNTUACION_MINIMA <= puntuacion <= PUNTUACION_MAXIMA:
        raise ValueError(
            f"La puntuación debe estar entre {PUNTUACION_MINIMA} y {PUNTUACION_MAXIMA}"
        )
