"""Capa 1 — Afinidad entre lo que el visitante quiere y cada recurso.

Ordena los recursos según lo bien que encajan con los intereses declarados.

**Las dos vías, y por qué existen ambas.** La regla de oro del proyecto exige
que toda funcionalidad con modelo tenga una alternativa por reglas explícitas,
conmutable con una variable de configuración:

- ``USAR_MODELO_RECOMENDACION = True``  → TF-IDF + similitud coseno
- ``USAR_MODELO_RECOMENDACION = False`` → coincidencia directa por reglas

No es un capricho: es el mecanismo de control de riesgo declarado en el
documento académico. Si el modelo no supera a las reglas, se entrega la
alternativa y el modelo vuelve al backlog.

**Toda recomendación explica por qué.** Cada resultado devuelve los términos
que más pesaron en su puntaje. Sin eso, la recomendación sería una caja negra
que el visitante no puede cuestionar ni el gestor auditar, y la brecha 2 habla
justamente de que *el análisis recae en el visitante sin criterios explícitos*.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.modelos.preferencias import Interes

# ---------------------------------------------------------------------------
# Puente entre los intereses del visitante y el vocabulario del MINCETUR
# ---------------------------------------------------------------------------

#: Palabras con las que se describe cada interés en el inventario oficial.
#:
#: Este diccionario es el corazón del asunto: el visitante marca «artesanía» y
#: el MINCETUR clasifica ese mismo recurso como «Arquitectura y Espacios
#: Urbanos / Pueblo artesanal». Sin este puente, el vector del visitante y el
#: del recurso no comparten ni una palabra y la similitud sería siempre cero.
#:
#: Los términos salen de leer las categorías, tipos y subtipos que de verdad
#: aparecen en las 295 filas del catálogo, no de imaginarlos.
TERMINOS_POR_INTERES: dict[str, tuple[str, ...]] = {
    Interes.NATURALEZA: (
        "sitios naturales",
        "laguna",
        "lagunas",
        "bosque",
        "bosques",
        "catarata",
        "cataratas",
        "cascada",
        "rio",
        "rios",
        "valle",
        "quebrada",
        "nevado",
        "montana",
        "montanas",
        "cerro",
        "manantial",
        "aguas termales",
        "puya",
        "flora",
        "fauna",
        "paisaje",
    ),
    Interes.ARQUEOLOGIA: (
        "sitios arqueologicos",
        "arqueologico",
        "arqueologica",
        "zona arqueologica",
        "restos",
        "ruinas",
        "petroglifos",
        "pinturas rupestres",
        "abrigo rocoso",
        "monumento",
        "prehispanico",
        "wanka",
        "inca",
        # Un «museo de sitio» es el museo de una zona arqueológica, no un
        # edificio religioso. Estuvo mal clasificado bajo iglesias y hacía que
        # el Museo de Sitio Wariwillka encabezara las búsquedas de quien pedía
        # «iglesias y conventos».
        "museo de sitio",
        "museos de sitio",
        # En este inventario, «santuario» aparece casi siempre en «Santuario
        # Arqueológico». Va aquí y no en iglesias por eso.
        "santuario",
        "santuarios",
    ),
    Interes.IGLESIAS_CONVENTOS: (
        "iglesia",
        "iglesias",
        "convento",
        "capilla",
        "templo",
        "catedral",
        "arquitectura religiosa",
        "religiosa",
        "monasterio",
        "parroquia",
        "virgen",
        "cruz",
    ),
    Interes.ARTESANIA: (
        "artesania",
        "artesanal",
        "pueblo artesanal",
        "ceramica",
        "textil",
        "textileria",
        "mate burilado",
        "tallado",
        "platería",
        "plateria",
        "bordado",
        "tejido",
        "taller",
        "arte popular",
    ),
    Interes.GASTRONOMIA: (
        "gastronomia",
        "gastronomica",
        "comida",
        "plato",
        "platos tipicos",
        "bebida",
        "bebidas",
        "dulce",
        "papa",
        "trucha",
        "pachamanca",
        "explotaciones agropecuarias",
        "lacteos",
    ),
    Interes.FERIAS_FIESTAS: (
        "acontecimientos programados",
        "fiesta",
        "fiestas",
        "feria",
        "ferias",
        "festividad",
        "danza",
        "danzas",
        "carnaval",
        "folclore",
        "musica",
        "costumbres",
        "patronal",
        "celebracion",
    ),
    Interes.AVENTURA: (
        "aventura",
        "caminata",
        "trekking",
        "escalada",
        "ciclismo",
        "canotaje",
        "parapente",
        "camping",
        "deporte",
        "mirador",
        "nevado",
        "altura",
    ),
    Interes.FOTOGRAFIA: (
        "mirador",
        "paisaje",
        "panoramica",
        "vista",
        "formaciones geologicas",
        "bosque de piedras",
        "laguna",
        "nevado",
        "arquitectura",
    ),
}


def normalizar(texto: str | None) -> str:
    """Pasa a minúsculas y quita tildes, para comparar sin sorpresas.

    Aquí sí se quita la Ñ, al contrario que en el catálogo: esto no se muestra
    a nadie, solo se usa para comparar textos internamente.
    """
    if not texto:
        return ""

    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def contiene_termino(texto: str, termino: str) -> bool:
    """Comprueba si un texto contiene un término **como palabra completa**.

    POR QUÉ NO BASTA CON ``termino in texto``. La comparación por subcadena
    produce falsos positivos silenciosos y difíciles de detectar:

    - «rio» coincide dentro de «santua**rio**», y un santuario se clasificaba
      como naturaleza.
    - «inca» coincide dentro de «**inca**paz» o «vert**inca**».
    - «arte» coincidiría dentro de «m**arte**s».

    Con ``\\b`` (límite de palabra) solo coinciden palabras enteras. Se usa
    ``re.escape`` porque algunos términos llevan espacios y puntos.
    """
    return re.search(rf"\b{re.escape(termino)}\b", texto) is not None


@dataclass
class RecursoParaPuntuar:
    """Los datos de un recurso que entran en el cálculo de afinidad.

    Se usa una estructura propia y no el modelo de SQLAlchemy para que las
    funciones se puedan probar sin base de datos.
    """

    id: int
    nombre: str
    categoria: str | None = None
    tipo: str | None = None
    subtipo: str | None = None
    descripcion: str | None = None
    distrito: str = ""

    def texto_descriptivo(self) -> str:
        """Junta todo lo que describe al recurso en un solo texto.

        Es lo que el vectorizador convierte en números. Se incluye el nombre
        porque a menudo lleva la palabra clave: «Pueblo Artesanal de Cochas
        Grande» dice «artesanal» aunque su categoría no lo diga.
        """
        partes = [self.nombre, self.categoria, self.tipo, self.subtipo, self.descripcion]
        return normalizar(" ".join(parte for parte in partes if parte))


@dataclass
class ResultadoAfinidad:
    """Puntaje de un recurso y la explicación de por qué lo obtuvo."""

    recurso_id: int
    puntaje: float
    #: Términos que más pesaron, de mayor a menor.
    terminos_decisivos: list[str] = field(default_factory=list)
    #: Intereses del visitante que este recurso satisface.
    intereses_cubiertos: list[str] = field(default_factory=list)
    #: Cómo se calculó: 'modelo' o 'reglas'. Trazabilidad de la regla de oro.
    calculado_por: str = "modelo"


# ---------------------------------------------------------------------------
# Vía A — el modelo: TF-IDF + similitud coseno
# ---------------------------------------------------------------------------


def construir_consulta_del_visitante(intereses: list[str]) -> str:
    """Convierte los intereses marcados en un texto comparable con los recursos.

    El visitante marca «artesanía»; esto lo expande a todas las palabras con
    las que el MINCETUR describe la artesanía. Es lo que permite que los dos
    textos compartan vocabulario.
    """
    palabras: list[str] = []

    for interes in intereses:
        palabras.extend(TERMINOS_POR_INTERES.get(interes, (interes,)))

    return normalizar(" ".join(palabras))


def calcular_afinidad_con_modelo(
    recursos: list[RecursoParaPuntuar],
    intereses: list[str],
    terminos_a_explicar: int = 3,
) -> list[ResultadoAfinidad]:
    """Ordena los recursos por similitud coseno entre TF-IDF.

    **Qué es TF-IDF, en una frase:** convierte cada texto en un vector donde
    cada palabra pesa según lo frecuente que es en ese texto (TF) y lo rara
    que es en el conjunto (IDF). Así, «laguna» distingue mucho y «de» no
    distingue nada, sin tener que mantener una lista de palabras vacías.

    **Qué es la similitud coseno:** el coseno del ángulo entre dos vectores.
    Vale 1 si apuntan en la misma dirección y 0 si son perpendiculares.
    Se usa en vez de la distancia porque no le afecta la longitud del texto:
    una descripción larga no gana por ser larga.

    La explicación sale de multiplicar el peso de cada término en el recurso
    por su peso en la consulta: los términos con producto más alto son,
    literalmente, los que hicieron subir el puntaje.
    """
    if not recursos:
        return []

    consulta = construir_consulta_del_visitante(intereses)
    documentos = [recurso.texto_descriptivo() for recurso in recursos]

    if not consulta.strip() or not any(documento.strip() for documento in documentos):
        return [ResultadoAfinidad(recurso.id, 0.0) for recurso in recursos]

    vectorizador = TfidfVectorizer(
        # Palabras sueltas y pares de palabras: «sitios naturales» y «pueblo
        # artesanal» significan más juntas que por separado.
        ngram_range=(1, 2),
        # Un término que aparece en todos los recursos no distingue nada.
        max_df=0.9,
        sublinear_tf=True,
    )

    matriz = vectorizador.fit_transform([*documentos, consulta])
    matriz_recursos = matriz[:-1]
    vector_consulta = matriz[-1]

    similitudes = cosine_similarity(matriz_recursos, vector_consulta).ravel()

    vocabulario = np.array(vectorizador.get_feature_names_out())
    pesos_consulta = vector_consulta.toarray().ravel()

    resultados: list[ResultadoAfinidad] = []

    for indice, recurso in enumerate(recursos):
        pesos_recurso = matriz_recursos[indice].toarray().ravel()

        # La contribución de cada término al puntaje es el producto de su peso
        # en el recurso por su peso en la consulta. Es exactamente lo que suma
        # el numerador del coseno, así que la explicación no es una
        # aproximación: es la descomposición real del cálculo.
        contribuciones = pesos_recurso * pesos_consulta
        mejores = np.argsort(contribuciones)[::-1][:terminos_a_explicar]

        terminos = [
            str(vocabulario[posicion]) for posicion in mejores if contribuciones[posicion] > 0
        ]

        resultados.append(
            ResultadoAfinidad(
                recurso_id=recurso.id,
                puntaje=round(float(similitudes[indice]), 4),
                terminos_decisivos=terminos,
                intereses_cubiertos=_intereses_que_cubre(recurso, intereses),
                calculado_por="modelo",
            )
        )

    return resultados


# ---------------------------------------------------------------------------
# Vía B — la alternativa por reglas
# ---------------------------------------------------------------------------

#: Cuánto suma que el recurso esté en el mismo distrito del que sale el
#: visitante. Es una bonificación modesta a propósito: la cercanía ayuda, pero
#: no debe hacer que un recurso irrelevante gane a uno que sí interesa.
BONIFICACION_MISMO_DISTRITO = 0.15


def calcular_afinidad_con_reglas(
    recursos: list[RecursoParaPuntuar],
    intereses: list[str],
    distrito_origen: str = "",
) -> list[ResultadoAfinidad]:
    """Puntúa por coincidencia directa entre interés declarado y descripción.

    Es la alternativa explícita al modelo, y es **auditable a simple vista**:
    el puntaje es la proporción de intereses del visitante que el recurso
    satisface, más una bonificación por estar en el distrito de origen.

    Un puntaje de 0,5 significa literalmente «cubre la mitad de lo que pediste».
    Esa claridad es su ventaja frente al modelo, no un consuelo.
    """
    if not recursos or not intereses:
        return [ResultadoAfinidad(recurso.id, 0.0, calculado_por="reglas") for recurso in recursos]

    origen = normalizar(distrito_origen)
    resultados: list[ResultadoAfinidad] = []

    for recurso in recursos:
        texto = recurso.texto_descriptivo()

        cubiertos: list[str] = []
        terminos_encontrados: list[str] = []

        for interes in intereses:
            coincidencias = [
                termino
                for termino in TERMINOS_POR_INTERES.get(interes, (interes,))
                if contiene_termino(texto, normalizar(termino))
            ]

            if coincidencias:
                cubiertos.append(interes)
                # Se guarda el término más largo: es el más específico y el
                # que mejor explica la coincidencia. «pueblo artesanal» dice
                # más que «artesanal».
                terminos_encontrados.append(max(coincidencias, key=len))

        puntaje = len(cubiertos) / len(intereses)

        if origen and normalizar(recurso.distrito) == origen:
            puntaje = min(1.0, puntaje + BONIFICACION_MISMO_DISTRITO)
            terminos_encontrados.append("mismo distrito de salida")

        resultados.append(
            ResultadoAfinidad(
                recurso_id=recurso.id,
                puntaje=round(puntaje, 4),
                terminos_decisivos=terminos_encontrados[:3],
                intereses_cubiertos=cubiertos,
                calculado_por="reglas",
            )
        )

    return resultados


def _intereses_que_cubre(recurso: RecursoParaPuntuar, intereses: list[str]) -> list[str]:
    """Qué intereses del visitante toca este recurso, por coincidencia directa.

    Se calcula igual con modelo o con reglas: sirve para mostrar al visitante
    «esto responde a tu interés por la artesanía», que es más comprensible que
    un número.
    """
    texto = recurso.texto_descriptivo()

    return [
        interes
        for interes in intereses
        if any(
            contiene_termino(texto, normalizar(termino))
            for termino in TERMINOS_POR_INTERES.get(interes, (interes,))
        )
    ]


# ---------------------------------------------------------------------------
# Punto de entrada: elige la vía según la configuración
# ---------------------------------------------------------------------------


def calcular_afinidad(
    recursos: list[RecursoParaPuntuar],
    intereses: list[str],
    distrito_origen: str = "",
    usar_modelo: bool = True,
) -> list[ResultadoAfinidad]:
    """Calcula la afinidad por la vía que indique la configuración.

    Es el único punto por el que el resto del sistema pide afinidad, de modo
    que cambiar de vía no obliga a tocar nada más.
    """
    if usar_modelo:
        return calcular_afinidad_con_modelo(recursos, intereses)

    return calcular_afinidad_con_reglas(recursos, intereses, distrito_origen)
