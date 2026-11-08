"""Lee las fichas oficiales del inventario del MINCETUR.

## Qué problema resuelve

El CSV del inventario —el que carga `cargar_catalogo`— trae el nombre, la
categoría y las coordenadas, pero **no trae descripción, ni horario, ni
precio**. Durante seis fases eso se declaró como una limitación de la fuente:

> «El inventario del MINCETUR no publica horarios.»

Era verdad **del CSV**. No de la fuente. Cada recurso tiene además una **ficha
web** en el propio sistema del MINCETUR, cuya dirección ya estaba guardada en
la columna ``url_ficha`` desde el primer día, y esa ficha sí trae:

- una descripción larga,
- el **horario de visita**,
- el **tipo de ingreso** (libre o pagado),
- la **época propicia** —que para las 36 fiestas del catálogo son sus fechas—,
- y **cifras reales de visitantes**, con su fuente y su año.

Este módulo las lee. Con eso dejan de ser ciertas dos limitaciones que el
proyecto venía declarando, y la afluencia pasa de calcularse solo con reglas a
apoyarse en conteos reales.

## Cómo se comporta con el servidor del Estado

Son 295 páginas de un servicio público. El módulo:

- **espera entre peticiones** (`SEGUNDOS_ENTRE_PETICIONES`), para no parecer un
  ataque ni degradar el servicio a nadie más;
- **guarda cada página en disco** y no la vuelve a pedir: reejecutar el guion
  no genera ni una petición nueva;
- **se identifica** en la cabecera ``User-Agent`` diciendo qué es y para qué;
- **se puede reanudar**: si se corta a la mitad, sigue donde iba.

## Lo que NO hace

No inventa. Si una ficha no trae horario, el recurso se queda sin horario y el
itinerario sigue avisando de que no lo conoce. Un campo vacío es información;
uno rellenado a ojo es una mentira que nadie va a poder detectar después.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

#: Dónde se guardan las páginas descargadas. Va bajo `datos/`, que está en el
#: .gitignore: son 30 MB de HTML que se pueden volver a bajar.
CARPETA_DE_FICHAS = Path(__file__).resolve().parents[2] / "datos" / "fichas"

#: Cuánto se espera entre una página y la siguiente.
#:
#: No hay un número oficial que respetar; este sale de ser razonable. A este
#: ritmo, las 295 fichas tardan unos cinco minutos, que es tiempo de sobra para
#: un servidor que atiende consultas de una en una.
SEGUNDOS_ENTRE_PETICIONES = 1.0

#: Quiénes somos. Un guion que no se identifica es un guion que alguien tiene
#: que investigar en sus registros; decirlo por adelantado es de buena
#: educación y cuesta una línea.
IDENTIFICACION = (
    "RutaVivaMantaro/0.7 (proyecto academico; Universidad Continental, "
    "Procesos de Software; lee el inventario publico del MINCETUR)"
)

SEGUNDOS_DE_ESPERA = 30.0


@dataclass
class FichaLeida:
    """Lo que se pudo sacar de una ficha. Todo opcional a propósito.

    Ninguna ficha trae los siete campos, y forzar valores por defecto haría
    imposible distinguir «la ficha dice que la entrada es libre» de «la ficha
    no dice nada del precio».
    """

    codigo: str

    #: Los párrafos de la descripción, ya unidos.
    descripcion: str | None = None

    #: Tal cual lo escribe la ficha: «07:00 a.m. - 09:00 p.m.».
    horario_en_texto: str | None = None

    #: «Todo el Año», «Enero», «Julio - Agosto»… Para las 36 fiestas del
    #: catálogo, esto **es su fecha**.
    epoca_propicia: str | None = None

    #: Lo que la ficha llama «especificación» de la época: suele traer los días
    #: concretos de una fiesta.
    especificacion_de_la_epoca: str | None = None

    #: «Libre», «Previa presentación de boleto»…
    tipo_de_ingreso: str | None = None

    #: Conteos de visitantes: ``(anio, tipo, cantidad, fuente)``.
    visitantes: list[tuple[int, str, int, str]] = field(default_factory=list)

    #: Qué no se pudo leer. Se guarda en vez de callarse: al terminar, el guion
    #: dice de cuántas fichas faltó cada cosa, y eso es un dato honesto sobre
    #: la calidad de la fuente.
    ausentes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------


def ruta_en_disco(codigo: str) -> Path:
    """Dónde se guarda la ficha de ese código."""
    return CARPETA_DE_FICHAS / f"{codigo}.html"


def codigo_de_la_url(url: str) -> str | None:
    """Saca el ``cod_Ficha`` de la dirección guardada en el catálogo.

    Las direcciones son de la forma
    ``.../fichaInventario/index.aspx?cod_Ficha=703``.
    """
    coincidencia = re.search(r"cod_Ficha=(\d+)", url, re.IGNORECASE)

    return coincidencia.group(1) if coincidencia else None


def descargar_ficha(url: str, cliente: httpx.Client) -> str | None:
    """Baja una ficha, o la lee de disco si ya estaba.

    Devuelve ``None`` si el código no se puede sacar de la dirección o si el
    servidor no responde. No lanza: una ficha que falla no puede tumbar la
    carga de las otras 294.
    """
    codigo = codigo_de_la_url(url)

    if codigo is None:
        return None

    destino = ruta_en_disco(codigo)

    if destino.exists():
        return destino.read_text(encoding="utf-8", errors="replace")

    try:
        respuesta = cliente.get(url)
        respuesta.raise_for_status()
    except httpx.HTTPError:
        return None

    # El servidor no siempre declara bien la codificación; se fuerza utf-8 con
    # reemplazo porque perder una tilde es mejor que perder la ficha entera.
    texto = respuesta.content.decode("utf-8", errors="replace")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")

    time.sleep(SEGUNDOS_ENTRE_PETICIONES)

    return texto


def abrir_cliente() -> httpx.Client:
    """El cliente HTTP, ya identificado."""
    return httpx.Client(
        headers={"User-Agent": IDENTIFICACION},
        timeout=SEGUNDOS_DE_ESPERA,
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def _limpiar(texto: str | None) -> str | None:
    """Colapsa espacios y convierte en `None` lo que la ficha deja vacío.

    El MINCETUR escribe «--» donde no hay dato. Tratarlo como texto haría que
    295 recursos tuvieran un horario que dice «--», que es peor que no tener
    horario: parece un dato.
    """
    if texto is None:
        return None

    limpio = " ".join(texto.split())

    return None if limpio in ("", "--", "-", "N/A") else limpio


def _tabla_con_cabecera(sopa: BeautifulSoup, *palabras: str) -> list[list[str]] | None:
    """Busca la tabla cuya primera fila contiene todas esas palabras.

    Se busca por cabecera y no por posición porque el orden de las tablas
    cambia entre fichas: las que no tienen visitantes no traen esa tabla, y
    todo lo de abajo se corre una posición.
    """
    for tabla in sopa.find_all("table"):
        filas = [
            [celda.get_text(" ", strip=True) for celda in fila.find_all(["td", "th"])]
            for fila in tabla.find_all("tr")
        ]

        if not filas:
            continue

        cabecera = " ".join(filas[0]).lower()

        if all(palabra.lower() in cabecera for palabra in palabras):
            return filas

    return None


def leer_ficha(html: str, codigo: str) -> FichaLeida:
    """Saca de la página lo que nos sirve.

    Cada campo se busca por su etiqueta, no por su posición, y lo que no
    aparece se anota en ``ausentes`` en vez de rellenarse.
    """
    sopa = BeautifulSoup(html, "html.parser")
    ficha = FichaLeida(codigo=codigo)

    # --- Descripción ------------------------------------------------------
    # Vive en párrafos sueltos, no en tabla. Se cogen los largos: los cortos
    # son pies de foto y avisos de la propia página.
    parrafos = [
        limpio
        for parrafo in sopa.find_all("p")
        if (limpio := _limpiar(parrafo.get_text(" ", strip=True))) and len(limpio) > 120
    ]

    if parrafos:
        ficha.descripcion = "\n\n".join(parrafos)
    else:
        ficha.ausentes.append("descripcion")

    # --- Horario y época --------------------------------------------------
    epoca = _tabla_con_cabecera(sopa, "época propicia", "hora de visita")

    if epoca and len(epoca) > 1:
        # Cabecera: Época propicia | Especificación | Hora de visita | Observaciones
        valores = epoca[1]
        ficha.epoca_propicia = _limpiar(valores[0]) if len(valores) > 0 else None
        ficha.especificacion_de_la_epoca = _limpiar(valores[1]) if len(valores) > 1 else None
        ficha.horario_en_texto = _limpiar(valores[2]) if len(valores) > 2 else None

    if ficha.horario_en_texto is None:
        ficha.ausentes.append("horario")

    if ficha.epoca_propicia is None:
        ficha.ausentes.append("epoca")

    # --- Tipo de ingreso --------------------------------------------------
    ingreso = _tabla_con_cabecera(sopa, "tipo de ingreso")

    if ingreso and len(ingreso) > 1 and ingreso[1]:
        ficha.tipo_de_ingreso = _limpiar(ingreso[1][0])

    if ficha.tipo_de_ingreso is None:
        ficha.ausentes.append("ingreso")

    # --- Visitantes -------------------------------------------------------
    conteos = _tabla_con_cabecera(sopa, "tipo de visitante", "cantidad")

    if conteos:
        # Cabecera: Tipo de Visitante | Cantidad | Fuente | Año | Observación
        for fila in conteos[1:]:
            if len(fila) < 4:
                continue

            tipo = _limpiar(fila[0])
            cantidad = _limpiar(fila[1])
            fuente = _limpiar(fila[2]) or "Ficha del inventario, MINCETUR"
            anio = _limpiar(fila[3])

            if not (tipo and cantidad and anio):
                continue

            try:
                ficha.visitantes.append((int(anio), tipo, int(cantidad.replace(",", "")), fuente))
            except ValueError:
                # Una fila con un número mal escrito se salta; no se adivina.
                continue

    if not ficha.visitantes:
        ficha.ausentes.append("visitantes")

    return ficha


# ---------------------------------------------------------------------------
# Interpretación del horario
# ---------------------------------------------------------------------------

#: Reconoce «07:00 a.m. - 09:00 p.m.» y sus variantes.
#:
#: La ficha las escribe de varias formas —con y sin punto en «a.m.», con guion
#: normal o largo, con «hrs» detrás—, así que la expresión es más suelta de lo
#: que parece necesario. Lo que no encaje se deja sin interpretar en vez de
#: forzarlo: un horario mal leído metería al visitante en un sitio cerrado.
_HORARIO = re.compile(
    r"(\d{1,2})[:.](\d{2})\s*([ap])\.?\s*m\.?"  # hora de apertura
    r"\s*(?:-|–|—|a|hasta)\s*"
    r"(\d{1,2})[:.](\d{2})\s*([ap])\.?\s*m\.?",  # hora de cierre
    re.IGNORECASE,
)


def interpretar_horario(texto: str | None) -> tuple[str, str] | None:
    """Convierte «07:00 a.m. - 09:00 p.m.» en ``("07:00", "21:00")``.

    Devuelve ``None`` si no lo entiende, y eso está bien: el recurso se queda
    sin horario y el itinerario sigue avisando de que no lo conoce.
    """
    if not texto:
        return None

    coincidencia = _HORARIO.search(texto)

    if coincidencia is None:
        return None

    def a_24_horas(hora: str, minuto: str, franja: str) -> str:
        numero = int(hora) % 12

        if franja.lower() == "p":
            numero += 12

        return f"{numero:02d}:{minuto}"

    apertura = a_24_horas(coincidencia[1], coincidencia[2], coincidencia[3])
    cierre = a_24_horas(coincidencia[4], coincidencia[5], coincidencia[6])

    # Un horario que cierra antes de abrir está mal leído. Pasa con sitios que
    # abren de noche, que en este inventario no hay ninguno.
    return None if cierre <= apertura else (apertura, cierre)


# ---------------------------------------------------------------------------
# Cuándo se celebra una fiesta
# ---------------------------------------------------------------------------

#: Los meses, como los escribe la ficha. «Setiembre» con te es la forma
#: peruana y aparece tanto o más que «septiembre», así que van las dos.
MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "setiembre": 9,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

#: Frases de la descripción que mencionan un mes.
#:
#: Se recorta por punto o punto y coma: es la unidad que la ficha usa para una
#: idea completa, y así la frase que se enseña se lee entera.
_FRASE_CON_MES = re.compile(
    r"[^.;]*\b(?:" + "|".join(MESES) + r")\b[^.;]*",
    re.IGNORECASE,
)

#: Señales de que la frase dice CUÁNDO se celebra la fiesta.
#:
#: Cada una suma. Se puntúa en vez de exigirlas todas porque las fichas no
#: siguen ninguna plantilla: unas dicen «se celebra cada 6 de enero» y otras
#: «los días 18, 19 y 20 de enero», y las dos son buenas.
_SENALES_DE_QUE_ES_LA_FECHA = (
    (3, r"\bse\s+(?:celebra|realiza|lleva\s+a\s+cabo|festeja|desarrolla|efect[uú]a)\b"),
    (3, r"\b(?:tiene\s+lugar|se\s+conmemora)\b"),
    (2, r"\bcada\s+(?:a[nñ]o|\d{1,2}\s+de)\b"),
    (2, r"\b(?:los\s+d[ií]as?|todos\s+los)\s+\d{1,2}\b"),
    (2, r"\bdel?\s+\d{1,2}\s+(?:de\s+\w+\s+)?al?\s+\d{1,2}\b"),
    (2, r"\b(?:se\s+inicia|comienza|empieza|se\s+inaugura)\b"),
    (1, r"\b(?:en\s+el\s+mes\s+de|durante\s+(?:el\s+mes|los\s+meses))\b"),
    (1, r"\bfecha\s+m[oó]vil\b"),
)

#: Señales de que la frase cuenta la HISTORIA del pueblo, no la fecha.
#:
#: Las fichas dedican párrafos enteros a cómo empezó la fiesta, y esos
#: párrafos están llenos de meses: «los arrieros acostumbraban salir en
#: diciembre», «el Alcalde la trasladó el 9 de Diciembre». Coger esos meses
#: mandaría al visitante un día en que no hay nada, que es exactamente lo que
#: se venía a arreglar.
#:
#: Restan en vez de descartar: casi toda descripción menciona algún año, y
#: descartar por eso dejaba las 36 fiestas sin fecha.
_SENALES_DE_QUE_ES_HISTORIA = (
    (4, r"\b(?:acostumbraban?|sol[ií]an?|antiguamente)\b"),
    (4, r"\b(?:traslad[óo]|fund[óo]|instituy[óo]|cre[óo]|organiz[óo])\b"),
    (2, r"\ben\s+el\s+a[nñ]o\s+(?:de\s+)?\d{4}\b"),
    (2, r"\b(?:empezaban|terminaban|duraba|era[n]?\s+costumbre)\b"),
)


def _es_el_mes(frase: str, nombre_del_mes: str) -> bool:
    """Si esa palabra es de verdad el mes y no el nombre de alguien.

    «Julio», «Agosto» y «Abril» son también nombres de persona en Perú, y las
    fichas cuentan quién fundó cada fiesta. Sin esta comprobación, el «Concurso
    Regional de Enfrenadura de Caballos Peruanos de Paso» salía celebrándose en
    julio porque uno de sus fundadores se llamaba **Julio Camac**.

    La regla: si el mes va en mayúscula y detrás viene otra palabra en
    mayúscula, es un nombre propio. «11 de Julio en Matahuasi» pasa —«en» va en
    minúscula—; «Julio Camac» no.
    """
    for coincidencia in re.finditer(rf"\b{nombre_del_mes}\b", frase, re.IGNORECASE):
        palabra = coincidencia.group(0)
        resto = frase[coincidencia.end() :].lstrip()
        siguiente = resto.split(" ")[0] if resto else ""

        parece_nombre_propio = palabra[0].isupper() and siguiente[:1].isupper()

        if not parece_nombre_propio:
            return True

    return False


def _puntuar(frase: str) -> int:
    """Cuánto se parece esta frase a «aquí está la fecha de la fiesta»."""
    puntos = sum(
        peso for peso, senal in _SENALES_DE_QUE_ES_LA_FECHA if re.search(senal, frase, re.I)
    )
    penalizacion = sum(
        peso for peso, senal in _SENALES_DE_QUE_ES_HISTORIA if re.search(senal, frase, re.I)
    )

    return puntos - penalizacion


def cuando_se_celebra(descripcion: str | None) -> tuple[str | None, list[int]]:
    """Saca de la descripción cuándo es la fiesta.

    Devuelve ``(frase, meses)``:

    - **la frase**, copiada literal de la ficha —«se realiza cada año en la
      Plaza de Armas de Jauja los días 18, 19 y 20 de enero»—,
    - **los meses** que menciona, del 1 al 12.

    No se intenta convertirlo en un rango de fechas exacto, y es a propósito.
    Muchas fiestas del valle no caen en días fijos: «el último domingo de
    enero», «fecha móvil entre marzo y abril», «el primer domingo de octubre».
    Convertirlas a un rango sería inventarse una precisión que la fuente no
    tiene, y el visitante acabaría plantándose un día en que no hay nada.

    Con la frase literal el visitante sabe de verdad cuándo es; con los meses,
    el sistema sabe si cae o no dentro del viaje. Es todo lo que hace falta.

    Si ninguna frase parece hablar de la fecha, devuelve ``(None, [])``. Decir
    «la ficha no lo precisa» es mejor que dar una fecha sacada de la historia
    del pueblo: un dato que parece bueno y no lo es no se detecta luego.
    """
    if not descripcion:
        return None, []

    texto = " ".join(descripcion.split())
    candidatas = [f.strip() for f in _FRASE_CON_MES.findall(texto)]

    if not candidatas:
        return None, []

    mejor = max(candidatas, key=_puntuar)

    if _puntuar(mejor) <= 0:
        return None, []

    meses = sorted({numero for nombre, numero in MESES.items() if _es_el_mes(mejor, nombre)})

    if not meses:
        return None, []

    # Se recorta lo que se enseña. La ficha a veces mete media historia del
    # distrito en la misma frase, y el visitante quiere saber la fecha.
    return mejor[:400], meses
