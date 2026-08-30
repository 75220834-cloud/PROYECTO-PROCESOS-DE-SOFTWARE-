"""Asistente conversacional con Ollama (Fase 7).

## Esto NO cierra ninguna brecha nueva

Es importante decirlo antes que nada, porque es lo que mantiene la coherencia
con los dos documentos académicos entregados: **el asistente es capa de
interacción, no funcionalidad nueva.** Es una forma alternativa de llegar a lo
que ya construyeron los Incrementos 2, 3 y 4.

Todo lo que el asistente puede hacer se puede hacer también por formulario. Si
mañana se apaga, no se pierde ninguna capacidad del sistema: se pierde una
manera cómoda de pedirla.

## El modelo nunca inventa datos

Es la regla más importante de este módulo, y la que hay que poder defender.

El modelo de lenguaje **no sabe nada** del Valle del Mantaro. No conoce sus
atractivos, no conoce sus precios y no conoce sus horarios. Lo único que hace
es:

1. Leer lo que pide el visitante.
2. **Elegir qué función del backend responde a eso.**
3. Redactar una respuesta **con lo que devolvió la función**.

Si alguien pregunta por un lugar que no está en el catálogo del MINCETUR, la
función de búsqueda devuelve cero resultados y el modelo tiene que decir que no
lo encuentra. No puede inventarlo, porque no está en el texto que se le pasa.

Esto no es una promesa: es una consecuencia de la arquitectura. El modelo solo
ve el resultado de la función, y ese resultado sale de la base de datos.

## Y si Ollama no está

La interfaz lo dice y ofrece el camino por formulario. **No falla en
silencio**, que es lo que exige el plan de trabajo. Un asistente que se queda
pensando para siempre es peor que uno que dice «no estoy disponible».
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modelos.catalogo import RecursoTuristico

registro = logging.getLogger(__name__)

#: Cuánto se espera a Ollama antes de rendirse. Un modelo de 7 000 millones de
#: parámetros en CPU tarda; pero más de esto y el visitante ya se fue.
SEGUNDOS_DE_ESPERA = 120.0

#: Cuánto se espera solo para saber si Ollama está vivo. Es una comprobación de
#: salud: si no contesta en dos segundos, no está.
SEGUNDOS_PARA_COMPROBAR = 2.0

#: Cuántas vueltas de «el modelo pide una función, se ejecuta, el modelo lee el
#: resultado» se permiten. Con tres cabe buscar, crear preferencia y recomendar;
#: sin tope, un modelo confundido podría llamarse a sí mismo indefinidamente.
VUELTAS_MAXIMAS = 4

#: Lo que el asistente es y lo que no puede hacer. Va en cada conversación.
INSTRUCCIONES = """\
Eres el asistente de RutaVivaMantaro, una plataforma de turismo para la Ruta \
del Valle del Mantaro, en Junín (Perú).

REGLAS QUE NO PUEDES ROMPER:

1. NUNCA inventes atractivos turísticos, precios, horarios ni distancias. Solo \
puedes hablar de lo que devuelvan las funciones. Si una función no devuelve \
nada, di que no lo encontraste en el catálogo. No adivines. Tampoco propongas \
un lugar «parecido» que recuerdes: si quieres ofrecer una alternativa, búscala \
antes con buscar_recursos y nombra solo lo que esa búsqueda devuelva.
2. Si te preguntan por un lugar concreto, LLAMA SIEMPRE a buscar_recursos antes \
de contestar, aunque creas saber la respuesta. No puedes afirmar que algo no \
está en el catálogo sin haberlo consultado.
3. El catálogo procede del Inventario Nacional de Recursos Turísticos del \
MINCETUR. Si algo no está ahí, para esta plataforma no existe, aunque tú creas \
conocerlo.
4. Los precios que devuelven las funciones son ESTIMACIONES. Menciónalos \
siempre con la palabra «aproximadamente» y di que no son tarifas oficiales.
5. Si te preguntan algo que no puedes responder con las funciones disponibles, \
dilo con claridad y sugiere qué sí puedes hacer.
6. Responde en el idioma en que te escriban. Sé breve: dos o tres frases y, si \
hace falta, una lista corta.

Puedes buscar recursos del catálogo, registrar las preferencias de un viaje, \
generar recomendaciones, armar un itinerario de un día y consultar la afluencia \
esperada de una fecha.
"""


# ---------------------------------------------------------------------------
# Las funciones que el modelo puede pedir
# ---------------------------------------------------------------------------

#: Cómo se llaman de verdad las categorías en el inventario del MINCETUR.
#:
#: Son cinco y vienen con su número delante. El modelo nunca las escribe así:
#: escribe «iglesias», «cultural» o directamente el código de interés
#: «iglesias_conventos». Esta tabla traduce lo que el modelo dice a lo que la
#: base de datos guarda. Lo que no esté aquí no filtra —ver `_buscar_recursos`.
_CATEGORIA_DEL_INVENTARIO: dict[str, str] = {
    "1": "1. SITIOS NATURALES",
    "sitios naturales": "1. SITIOS NATURALES",
    "naturaleza": "1. SITIOS NATURALES",
    "natural": "1. SITIOS NATURALES",
    "2": "2. MANIFESTACIONES CULTURALES",
    "manifestaciones culturales": "2. MANIFESTACIONES CULTURALES",
    "cultural": "2. MANIFESTACIONES CULTURALES",
    "culturales": "2. MANIFESTACIONES CULTURALES",
    "arqueologia": "2. MANIFESTACIONES CULTURALES",
    "iglesias": "2. MANIFESTACIONES CULTURALES",
    "iglesias_conventos": "2. MANIFESTACIONES CULTURALES",
    "3": "3. FOLCLORE",
    "folclore": "3. FOLCLORE",
    "artesania": "3. FOLCLORE",
    "gastronomia": "3. FOLCLORE",
    "4": "4. REALIZACIONES TÉCNICAS, CIENTÍFICAS Y ARTÍSTICAS CONTEMPORÁNEAS",
    "realizaciones tecnicas": "4. REALIZACIONES TÉCNICAS, CIENTÍFICAS Y ARTÍSTICAS CONTEMPORÁNEAS",
    "5": "5. ACONTECIMIENTOS PROGRAMADOS",
    "acontecimientos programados": "5. ACONTECIMIENTOS PROGRAMADOS",
    "ferias_fiestas": "5. ACONTECIMIENTOS PROGRAMADOS",
    "fiestas": "5. ACONTECIMIENTOS PROGRAMADOS",
}

#: Palabras que no aportan nada a la búsqueda y que, exigidas, la estropean.
#: «Convento de Ocopa» tiene que encontrar «Convento De Santa Rosa De Ocopa»;
#: si se exigiera «de» como palabra más, seguiría funcionando, pero «el», «la»
#: o «en» sí descartan filas por puro ruido.
_PALABRAS_VACIAS = frozenset(
    {"el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una", "al", "para"}
)

#: Trocea el texto en palabras. Se define una vez porque se usa por cada
#: búsqueda y compilar la expresión en cada llamada es gasto tonto.
_PALABRAS = re.compile(r"[a-z0-9]+")


#: Descripción de las funciones, en el formato de herramientas de Ollama.
#:
#: Se declaran aquí y no se generan por reflexión a propósito: lo que el modelo
#: lee tiene que poder revisarse de un vistazo, porque una descripción confusa
#: hace que el modelo llame a la función equivocada y eso es difícil de depurar.
HERRAMIENTAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_recursos",
            "description": (
                "Busca atractivos turísticos en el catálogo oficial del MINCETUR "
                "para el Valle del Mantaro. Úsala siempre que pregunten por un "
                "lugar, o por qué visitar en un distrito o de una categoría."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {
                        "type": "string",
                        "description": "Palabras a buscar en el nombre o la descripción",
                    },
                    "distrito": {
                        "type": "string",
                        "description": "Distrito del valle, por ejemplo HUANCAYO o JAUJA",
                    },
                    "categoria": {
                        "type": "string",
                        "description": (
                            "Una de las cinco del inventario: sitios naturales, "
                            "manifestaciones culturales, folclore, realizaciones "
                            "tecnicas o acontecimientos programados"
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_preferencia",
            "description": (
                "Registra las preferencias de viaje del visitante. Necesita saber "
                "de dónde parte, cuánto tiempo tiene, cuánto puede gastar y qué le "
                "interesa. Úsala antes de recomendar o armar un itinerario."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "distrito_origen": {
                        "type": "string",
                        "description": "Distrito desde el que parte, por ejemplo HUANCAYO",
                    },
                    "dias": {
                        "type": "integer",
                        "description": "Cuántos días dura el viaje",
                    },
                    "presupuesto_soles": {
                        "type": "number",
                        "description": "Presupuesto total en soles",
                    },
                    "intereses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "De: arqueologia, artesania, aventura, ferias_fiestas, "
                            "fotografia, gastronomia, iglesias_conventos, naturaleza"
                        ),
                    },
                    "movilidad": {
                        "type": "string",
                        "description": "caminando, transporte_publico, taxi o combinado",
                    },
                    "ritmo": {
                        "type": "string",
                        "description": "relajado, moderado o intenso",
                    },
                },
                "required": ["distrito_origen", "intereses"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generar_recomendaciones",
            "description": (
                "Devuelve los recursos que mejor encajan con una preferencia ya "
                "creada, ordenados por afinidad y con la razón de cada uno."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "preferencia_id": {"type": "integer"},
                    "limite": {"type": "integer", "description": "Cuántos devolver"},
                },
                "required": ["preferencia_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "construir_itinerario",
            "description": (
                "Arma el plan de un día para una preferencia: qué visitar, en qué "
                "orden, a qué hora, cómo desplazarse y cuánto cuesta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "preferencia_id": {"type": "integer"},
                    "fecha": {
                        "type": "string",
                        "description": "Día a planificar, en formato AAAA-MM-DD",
                    },
                },
                "required": ["preferencia_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_afluencia",
            "description": (
                "Dice cuánta gente se espera un día concreto en un distrito, y por "
                "qué: festividades, feria dominical, temporada."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                    "distrito": {"type": "string"},
                },
                "required": ["fecha"],
            },
        },
    },
]


@dataclass
class RespuestaDelAsistente:
    """Lo que el asistente devuelve, con todo lo que hizo para llegar ahí."""

    mensaje: str
    #: Qué funciones se ejecutaron y con qué argumentos. Es lo que hace
    #: auditable la conversación: se puede comprobar que el texto sale de datos.
    funciones_usadas: list[dict[str, Any]] = field(default_factory=list)
    #: Preferencia creada durante la conversación, si se creó alguna. La
    #: interfaz la usa para ofrecer el enlace al itinerario completo.
    preferencia_id: int | None = None
    #: True si Ollama no estaba y hubo que decirlo.
    esta_disponible: bool = True
    aviso: str | None = None


class AsistenteNoDisponible(Exception):
    """Ollama no responde. Quien llama debe ofrecer el camino por formulario."""


# ---------------------------------------------------------------------------
# Disponibilidad
# ---------------------------------------------------------------------------


def comprobar_disponibilidad(url_ollama: str, modelo: str) -> tuple[bool, str | None]:
    """Comprueba si Ollama responde y si tiene el modelo cargado.

    Devuelve ``(disponible, motivo)``. El motivo es un texto legible para
    enseñárselo al visitante: «Ollama no está corriendo» es útil, «connection
    refused» no.

    Se comprueban las dos cosas por separado porque fallan distinto y se
    arreglan distinto: si Ollama no está, hay que arrancarlo; si falta el
    modelo, hay que descargarlo.
    """
    try:
        respuesta = httpx.get(f"{url_ollama}/api/tags", timeout=SEGUNDOS_PARA_COMPROBAR)
        respuesta.raise_for_status()
    except Exception:  # noqa: BLE001 - cualquier fallo significa «no está»
        return False, (
            "El asistente conversacional necesita Ollama corriendo en local, y "
            "ahora mismo no responde. Puedes usar el planificador por formulario, "
            "que hace exactamente lo mismo."
        )

    modelos = {m.get("name", "") for m in respuesta.json().get("models", [])}

    # Ollama nombra los modelos con etiqueta («qwen2.5:7b-instruct»), y a veces
    # se configura sin ella. Se acepta cualquiera que empiece igual.
    base = modelo.split(":")[0]

    if not any(m == modelo or m.startswith(f"{base}:") for m in modelos):
        return False, (
            f"Ollama está corriendo pero no tiene el modelo «{modelo}». "
            f"Descárgalo con: ollama pull {modelo}"
        )

    return True, None


# ---------------------------------------------------------------------------
# El bucle de conversación
# ---------------------------------------------------------------------------


def conversar(
    sesion: Session,
    mensajes: list[dict[str, str]],
    url_ollama: str,
    modelo: str,
    idioma: str = "es",
) -> RespuestaDelAsistente:
    """Mantiene una vuelta de conversación con llamada a funciones.

    El bucle es siempre el mismo:

    1. Se le manda al modelo la conversación y la lista de funciones.
    2. Si pide una función, **el backend la ejecuta** y le devuelve el
       resultado.
    3. Se repite hasta que el modelo redacta una respuesta en vez de pedir otra
       función, o hasta agotar el tope de vueltas.

    El modelo nunca toca la base de datos: solo dice qué quiere, y este módulo
    decide si eso se puede hacer y con qué argumentos.
    """
    disponible, motivo = comprobar_disponibilidad(url_ollama, modelo)

    if not disponible:
        return RespuestaDelAsistente(mensaje="", esta_disponible=False, aviso=motivo)

    conversacion: list[dict[str, Any]] = [
        {"role": "system", "content": INSTRUCCIONES},
        *mensajes,
    ]

    usadas: list[dict[str, Any]] = []
    preferencia_creada: int | None = None

    for _ in range(VUELTAS_MAXIMAS):
        try:
            respuesta = _pedir_al_modelo(conversacion, url_ollama, modelo)
        except Exception as error:  # noqa: BLE001
            registro.warning("Ollama falló durante la conversación: %s", error)
            return RespuestaDelAsistente(
                mensaje="",
                esta_disponible=False,
                aviso=(
                    "El asistente se desconectó a mitad de la respuesta. Puedes "
                    "usar el planificador por formulario."
                ),
                funciones_usadas=usadas,
            )

        llamadas = respuesta.get("tool_calls") or []

        if not llamadas:
            return RespuestaDelAsistente(
                mensaje=respuesta.get("content", "").strip(),
                funciones_usadas=usadas,
                preferencia_id=preferencia_creada,
            )

        conversacion.append(respuesta)

        for llamada in llamadas:
            nombre = llamada.get("function", {}).get("name", "")
            argumentos = llamada.get("function", {}).get("arguments") or {}

            if isinstance(argumentos, str):
                # Algunos modelos devuelven los argumentos como texto JSON.
                try:
                    argumentos = json.loads(argumentos)
                except json.JSONDecodeError:
                    argumentos = {}

            resultado = ejecutar_funcion(sesion, nombre, argumentos, idioma)

            usadas.append({"nombre": nombre, "argumentos": argumentos})

            if nombre == "crear_preferencia" and "preferencia_id" in resultado:
                preferencia_creada = resultado["preferencia_id"]

            conversacion.append(
                {
                    "role": "tool",
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                }
            )

    # Se agotaron las vueltas sin que el modelo redactara nada.
    return RespuestaDelAsistente(
        mensaje=(
            "No conseguí armar una respuesta con la información disponible. "
            "Prueba a preguntarlo de otra forma, o usa el planificador por "
            "formulario."
        ),
        funciones_usadas=usadas,
        preferencia_id=preferencia_creada,
    )


def _pedir_al_modelo(
    conversacion: list[dict[str, Any]], url_ollama: str, modelo: str
) -> dict[str, Any]:
    """Una llamada a Ollama. Devuelve el mensaje que produjo el modelo."""
    respuesta = httpx.post(
        f"{url_ollama}/api/chat",
        json={
            "model": modelo,
            "messages": conversacion,
            "tools": HERRAMIENTAS,
            "stream": False,
            # Temperatura baja: no se le pide creatividad, se le pide que elija
            # bien la función y redacte lo que le den.
            "options": {"temperature": 0.2},
        },
        timeout=SEGUNDOS_DE_ESPERA,
    )
    respuesta.raise_for_status()

    return respuesta.json().get("message", {})


# ---------------------------------------------------------------------------
# La ejecución de las funciones — aquí es donde salen los datos reales
# ---------------------------------------------------------------------------


def ejecutar_funcion(
    sesion: Session, nombre: str, argumentos: dict[str, Any], idioma: str = "es"
) -> dict[str, Any]:
    """Ejecuta la función que pidió el modelo y devuelve su resultado.

    **Es la frontera entre el modelo y los datos.** Todo lo que el modelo pueda
    decir sobre el valle tiene que haber pasado por aquí.

    Un nombre desconocido devuelve un error explicado en vez de reventar: los
    modelos a veces se inventan nombres de función, y eso no debe tumbar la
    conversación.
    """
    funciones = {
        "buscar_recursos": _buscar_recursos,
        "crear_preferencia": _crear_preferencia,
        "generar_recomendaciones": _generar_recomendaciones,
        "construir_itinerario": _construir_itinerario,
        "consultar_afluencia": _consultar_afluencia,
    }

    funcion = funciones.get(nombre)

    if funcion is None:
        return {
            "error": (
                f"No existe una función llamada «{nombre}». Las disponibles son: "
                f"{', '.join(funciones)}."
            )
        }

    try:
        return funcion(sesion, argumentos, idioma)
    except Exception as error:  # noqa: BLE001
        registro.exception("Falló la función %s del asistente", nombre)
        return {"error": f"La función {nombre} falló: {type(error).__name__}"}


def _normalizar(texto: str) -> str:
    """Deja el texto en minúsculas y sin tildes, igual que hace la consulta SQL.

    Se necesita porque el modelo escribe «CONCEPCIÓN» con tilde y el inventario
    del MINCETUR la guarda como «CONCEPCION» sin ella. Comparar directamente
    devolvía cero resultados y el asistente respondía —con toda la seguridad del
    mundo— que Concepción no tiene atractivos, cuando tiene trece.
    """
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()


def _columna_sin_tildes(columna: Any) -> Any:
    """La misma normalización, pero del lado de PostgreSQL.

    ``unaccent`` es una extensión estándar de PostgreSQL y ya está instalada por
    una migración anterior; ``lower`` es SQL puro. Se aplican a la columna en
    cada consulta en vez de guardar una columna normalizada aparte porque el
    catálogo tiene 295 filas: el coste de recorrerlas es irrelevante y así no
    hay dos copias del nombre que puedan desincronizarse.
    """
    return func.unaccent(func.lower(columna))


def _buscar_recursos(sesion: Session, argumentos: dict[str, Any], idioma: str) -> dict[str, Any]:
    """Busca en el catálogo del MINCETUR.

    Si no encuentra nada devuelve una lista vacía **y lo dice explícitamente**,
    para que el modelo no tenga margen de interpretar el silencio como permiso
    para inventar.

    La búsqueda por texto va **palabra a palabra**, no por la frase entera. Un
    visitante escribe «Convento de Ocopa» y el inventario lo llama «Convento De
    Santa Rosa De Ocopa»: buscar la frase literal no encuentra nada, buscar
    «convento» Y «ocopa» sí. Las palabras se exigen todas (Y, no O) para que
    añadir detalle acote la búsqueda en lugar de ensancharla.
    """
    del idioma

    consulta = select(RecursoTuristico).where(RecursoTuristico.esta_validado.is_(True))

    texto = (argumentos.get("texto") or "").strip()
    if texto:
        for palabra in _PALABRAS.findall(_normalizar(texto)):
            if palabra in _PALABRAS_VACIAS:
                continue
            patron = f"%{palabra}%"
            consulta = consulta.where(
                or_(
                    _columna_sin_tildes(RecursoTuristico.nombre).like(patron),
                    _columna_sin_tildes(RecursoTuristico.descripcion_es).like(patron),
                )
            )

    distrito = (argumentos.get("distrito") or "").strip()
    if distrito:
        consulta = consulta.where(
            _columna_sin_tildes(RecursoTuristico.distrito).like(f"%{_normalizar(distrito)}%")
        )

    categoria = (argumentos.get("categoria") or "").strip()
    if categoria:
        # El modelo escribe la categoría como le parece («iglesias», «cultural»,
        # «2. MANIFESTACIONES CULTURALES»). Se traduce a la etiqueta exacta del
        # inventario cuando se reconoce; si no se reconoce, se ignora el filtro
        # en vez de vaciar la búsqueda. Descartar una consulta entera por un
        # filtro mal escrito es peor que devolver de más: la respuesta vacía
        # empuja al modelo a inventar.
        etiqueta = _CATEGORIA_DEL_INVENTARIO.get(_normalizar(categoria))
        if etiqueta is not None:
            consulta = consulta.where(RecursoTuristico.categoria == etiqueta)

    recursos = sesion.scalars(consulta.limit(8)).all()

    if not recursos:
        return {
            "encontrados": 0,
            "recursos": [],
            "aviso": (
                "No hay ningún recurso con esos criterios en el Inventario Nacional "
                "de Recursos Turísticos del MINCETUR. NO inventes uno y NO propongas "
                "ningún otro lugar de memoria: cualquier alternativa que sugieras "
                "tiene que salir de una nueva llamada a buscar_recursos. Dile al "
                "visitante que eso no está en el catálogo y ofrécele buscar por "
                "distrito o por categoría."
            ),
        }

    return {
        "encontrados": len(recursos),
        "recursos": [
            {
                "id": recurso.id,
                "nombre": recurso.nombre,
                "distrito": recurso.distrito,
                "provincia": recurso.provincia,
                "categoria": recurso.categoria,
                "altitud_msnm": recurso.altitud_msnm,
                "descripcion": (recurso.descripcion_es or "")[:280] or None,
            }
            for recurso in recursos
        ],
        "fuente": "Inventario Nacional de Recursos Turísticos, MINCETUR",
    }


def _crear_preferencia(sesion: Session, argumentos: dict[str, Any], idioma: str) -> dict[str, Any]:
    """Registra una preferencia de viaje a partir de lo que dijo el visitante.

    Los valores que faltan se rellenan con predeterminados razonables **y se
    dice cuáles**, para que el modelo pueda confirmarlos en vez de dar por hecho
    que el visitante los eligió.
    """
    from decimal import Decimal

    from app.modelos.preferencias import INTERESES_VALIDOS, PreferenciaViaje

    intereses = [
        interes for interes in (argumentos.get("intereses") or []) if interes in INTERESES_VALIDOS
    ]

    if not intereses:
        return {
            "error": (
                "No se indicó ningún interés válido. Los válidos son: "
                f"{', '.join(sorted(INTERESES_VALIDOS))}. Pregúntale al visitante "
                "cuáles le interesan."
            )
        }

    supuestos: list[str] = []

    dias = int(argumentos.get("dias") or 0)
    if dias < 1:
        dias = 2
        supuestos.append("duración de 2 días")

    presupuesto = argumentos.get("presupuesto_soles")
    if presupuesto is None:
        presupuesto = 300
        supuestos.append("presupuesto de S/ 300")

    movilidad = argumentos.get("movilidad") or "transporte_publico"
    ritmo = argumentos.get("ritmo") or "moderado"

    inicio = date.today() + timedelta(days=7)

    preferencia = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=dias - 1),
        distrito_origen=(argumentos.get("distrito_origen") or "HUANCAYO").upper(),
        presupuesto_soles=Decimal(str(presupuesto)),
        intereses=intereses,
        movilidad=movilidad,
        requiere_accesibilidad=False,
        idioma=idioma,
        ritmo=ritmo,
    )

    sesion.add(preferencia)
    sesion.commit()
    sesion.refresh(preferencia)

    return {
        "preferencia_id": preferencia.id,
        "distrito_origen": preferencia.distrito_origen,
        "fecha_inicio": preferencia.fecha_inicio,
        "fecha_fin": preferencia.fecha_fin,
        "intereses": intereses,
        "supuestos": supuestos,
        "aviso": (
            "Confirma con el visitante los valores que se supusieron antes de " "seguir."
            if supuestos
            else None
        ),
    }


def _buscar_preferencia(sesion: Session, identificador: Any) -> Any:
    """Busca una preferencia sin fiarse de lo que mandó el modelo.

    El modelo puede omitir el identificador o mandarlo como texto —«la que
    acabamos de crear», por ejemplo—. Pasarle eso directamente a ``sesion.get()``
    provoca un aviso de SQLAlchemy hoy y un error en versiones futuras, así que
    se filtra antes: lo que no sea un entero se trata como «no encontrada», que
    es la respuesta correcta y ya está contemplada por quien llama.
    """
    from app.modelos.preferencias import PreferenciaViaje

    try:
        numero = int(identificador)
    except (TypeError, ValueError):
        return None

    return sesion.get(PreferenciaViaje, numero)


def _generar_recomendaciones(
    sesion: Session, argumentos: dict[str, Any], idioma: str
) -> dict[str, Any]:
    """Devuelve las recomendaciones de una preferencia ya creada."""
    del idioma

    from app.servicios.recomendador import recomendar

    preferencia = _buscar_preferencia(sesion, argumentos.get("preferencia_id"))

    if preferencia is None:
        return {
            "error": (
                "No hay ninguna preferencia con ese identificador. Crea una "
                "primero con crear_preferencia."
            )
        }

    limite = min(int(argumentos.get("limite") or 5), 10)
    resultado = recomendar(sesion, preferencia, limite=limite)

    return {
        "generado_por": resultado.generado_por,
        "total_evaluados": resultado.total_evaluados,
        "recomendaciones": [
            {
                "recurso_id": r.recurso_id,
                "nombre": r.nombre,
                "distrito": r.distrito,
                "afinidad": r.puntaje_relativo,
                "por_que": r.terminos_decisivos[:4],
                "afluencia": r.afluencia.nivel.value,
            }
            for r in resultado.recomendaciones[:limite]
        ],
        "avisos": resultado.avisos,
    }


def _construir_itinerario(
    sesion: Session, argumentos: dict[str, Any], idioma: str
) -> dict[str, Any]:
    """Arma el plan de un día.

    Devuelve **también los avisos** del itinerario —tramos estimados, altitud,
    presupuesto— porque son justo lo que un asistente conversacional tiende a
    omitir por brevedad, y son lo que el visitante necesita saber.
    """
    del idioma

    from app.servicios.recomendador import recomendar
    from app.servicios.ruteo import construir_itinerario as armar

    preferencia = _buscar_preferencia(sesion, argumentos.get("preferencia_id"))

    if preferencia is None:
        return {
            "error": (
                "No hay ninguna preferencia con ese identificador. Crea una "
                "primero con crear_preferencia."
            )
        }

    texto_fecha = argumentos.get("fecha")
    try:
        fecha = date.fromisoformat(texto_fecha) if texto_fecha else preferencia.fecha_inicio
    except ValueError:
        fecha = preferencia.fecha_inicio

    if not preferencia.fecha_inicio <= fecha <= preferencia.fecha_fin:
        fecha = preferencia.fecha_inicio

    recomendacion = recomendar(sesion, preferencia, limite=40)
    itinerario = armar(sesion, preferencia, recomendacion.recomendaciones, fecha)

    return {
        "fecha": fecha,
        "generado_por": itinerario.generado_por,
        "paradas": [
            {
                "orden": p.orden + 1,
                "nombre": p.candidato.nombre,
                "distrito": p.candidato.distrito,
                "llegada": p.hora_llegada.strftime("%H:%M"),
                "salida": p.hora_salida.strftime("%H:%M"),
                "como_llegar": p.traslado.modo if p.traslado else None,
                "minutos_de_traslado": p.traslado.minutos if p.traslado else 0,
            }
            for p in itinerario.paradas
        ],
        "tiempo_total_min": itinerario.tiempo_total_min,
        "costo_aproximado_soles": (f"{itinerario.costo_min_soles} a {itinerario.costo_max_soles}"),
        "distancia_km": itinerario.distancia_total_km,
        "esfuerzo": itinerario.esfuerzo,
        "avisos": itinerario.avisos,
        "recordatorio": (
            "Los costos son estimaciones, no tarifas oficiales. Menciónalo. Y "
            "transmite los avisos al visitante: son de seguridad."
        ),
    }


def _consultar_afluencia(
    sesion: Session, argumentos: dict[str, Any], idioma: str
) -> dict[str, Any]:
    """Cuánta gente se espera un día, y por qué."""
    del sesion, idioma

    from app.ia.afluencia import predecir_afluencia

    texto_fecha = argumentos.get("fecha")

    try:
        fecha = date.fromisoformat(texto_fecha) if texto_fecha else date.today()
    except ValueError:
        return {"error": f"«{texto_fecha}» no es una fecha válida. Usa AAAA-MM-DD."}

    distrito = (argumentos.get("distrito") or "HUANCAYO").upper()
    prediccion = predecir_afluencia(fecha, distrito)

    return {
        "fecha": fecha,
        "distrito": distrito,
        "nivel": prediccion.nivel.value,
        "motivo": prediccion.motivo,
        "festividades": prediccion.festividades,
        "calculado_por": prediccion.calculado_por,
    }
