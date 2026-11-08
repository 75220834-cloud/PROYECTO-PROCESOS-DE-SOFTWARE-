"""Pruebas del bucle de conversación del asistente y de sus cinco funciones.

``test_asistente.py`` cubre la mitad del asistente que son datos: la búsqueda
en el catálogo y los tres fallos reales que la rompieron. Aquí se cubre la otra
mitad: **lo que rodea al modelo**.

## Qué se puede probar de un modelo de lenguaje, y qué no

Lo que el modelo decide no es determinista y no se fija con un ``assert``. Pero
el modelo no es la mitad interesante: solo elige una función y redacta. Lo que
sí se puede —y hay que— comprobar es todo lo demás, que sí es código normal:

- que **el modelo solo ve lo que devolvió la función**. Esta es la prueba que
  sostiene la promesa del módulo: el texto que se le manda de vuelta a Ollama
  se arma con el resultado de la consulta a la base, y nada más. Si un día
  alguien metiera ahí un «por si acaso, añade lugares parecidos», esta prueba
  se caería.
- que si Ollama no está, o se cae a mitad, **se dice** y se ofrece el
  formulario, en vez de quedarse pensando para siempre.
- que un modelo confundido que se llama a sí mismo sin parar se detiene en la
  cuarta vuelta.
- que los valores que el asistente rellena por su cuenta se declaran como
  supuestos, para que el modelo pueda confirmarlos en vez de darlos por hechos.

## El Ollama de mentira

Las pruebas no necesitan Ollama levantado: se sustituyen ``httpx.get`` y
``httpx.post``, que son los dos únicos sitios por donde el módulo sale a la
red. Lo que se sustituye es **el servidor**, no el código del asistente: el
bucle de conversación, el parseo de los argumentos y la ejecución de las
funciones son los de verdad, y las funciones consultan la base de datos real.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.ia.asistente import (
    HERRAMIENTAS,
    INSTRUCCIONES,
    VUELTAS_MAXIMAS,
    comprobar_disponibilidad,
    conversar,
    ejecutar_funcion,
)
from src.modelos.catalogo import RecursoTuristico
from src.modelos.preferencias import PreferenciaViaje
from src.servicios import ruteo
from pruebas.conftest import necesita_base_de_datos

pytestmark = necesita_base_de_datos

#: Un sábado, para que el itinerario caiga en día con horarios abiertos.
SABADO = date(2026, 9, 12)

URL = "http://localhost:11434"
MODELO = "qwen2.5:7b-instruct"

#: Cuatro recursos con coordenadas reales del valle, los suficientes para que
#: el optimizador tenga algo que ordenar sin que la prueba tarde.
RECURSOS = [
    ("980001", "Parque De La Identidad Wanka", "Huancayo", "EL TAMBO", -12.0520, -75.1980, 3250),
    ("980002", "Cerrito De La Libertad", "Huancayo", "HUANCAYO", -12.0750, -75.2200, 3290),
    (
        "980003",
        "Convento De Santa Rosa De Ocopa",
        "Concepcion",
        "SANTA ROSA DE OCOPA",
        -11.8740,
        -75.2944,
        3384,
    ),
    ("980004", "Laguna De Nahuinpuquio", "Chupaca", "AHUAC", -12.0592, -75.2867, 3263),
]


# ---------------------------------------------------------------------------
# El Ollama de mentira
# ---------------------------------------------------------------------------


class _RespuestaFalsa:
    """Lo mínimo que el módulo usa de una respuesta de httpx."""

    def __init__(self, cuerpo: dict) -> None:
        self._cuerpo = cuerpo

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._cuerpo


class _OllamaFalso:
    """Un servidor de mentira que dice lo que la prueba le indique.

    ``mensajes`` es la lista de respuestas que irá dando, en orden. Cuando se
    agota repite la última: así se puede simular un modelo que pide funciones
    sin parar sin escribir cuatro veces lo mismo.
    """

    def __init__(
        self,
        mensajes: list[dict],
        *,
        modelos_instalados: tuple[str, ...] = (MODELO,),
        esta_caido: bool = False,
        se_cae_en_la_llamada: int | None = None,
    ) -> None:
        self.mensajes = list(mensajes)
        self.modelos_instalados = modelos_instalados
        self.esta_caido = esta_caido
        self.se_cae_en_la_llamada = se_cae_en_la_llamada
        #: Los cuerpos que el asistente mandó a /api/chat, para inspeccionarlos.
        self.peticiones: list[dict] = []

    def instalar(self, monkeypatch: pytest.MonkeyPatch) -> _OllamaFalso:
        monkeypatch.setattr(httpx, "get", self._tags)
        monkeypatch.setattr(httpx, "post", self._chat)
        return self

    def _tags(self, url: str, **_) -> _RespuestaFalsa:
        if self.esta_caido:
            raise httpx.ConnectError("connection refused")

        return _RespuestaFalsa({"models": [{"name": nombre} for nombre in self.modelos_instalados]})

    def _chat(self, url: str, *, json: dict, **_) -> _RespuestaFalsa:
        self.peticiones.append(json)

        if self.se_cae_en_la_llamada == len(self.peticiones):
            raise httpx.ReadTimeout("el modelo dejo de responder")

        mensaje = self.mensajes[0] if len(self.mensajes) == 1 else self.mensajes.pop(0)
        return _RespuestaFalsa({"message": mensaje})


def _dice(texto: str) -> dict:
    """Un mensaje del modelo que es texto, no una petición de función."""
    return {"role": "assistant", "content": texto}


def _pide(nombre: str, argumentos) -> dict:
    """Un mensaje del modelo que pide ejecutar una función."""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": nombre, "arguments": argumentos}}],
    }


def _mensajes_de_herramienta(peticion: dict) -> list[str]:
    """El texto que el asistente le devolvió al modelo tras cada función."""
    return [m["content"] for m in peticion["messages"] if m.get("role") == "tool"]


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def busqueda_corta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un segundo de optimización en vez de los cinco de producción.

    Con cuatro recursos OR-Tools converge al instante; agotar el límite solo
    alargaría la suite. La estrategia de búsqueda es exactamente la misma.
    """
    monkeypatch.setattr(ruteo, "SEGUNDOS_DE_BUSQUEDA", 1)


@pytest.fixture
def catalogo(sesion: Session) -> Session:
    for codigo, nombre, provincia, distrito, latitud, longitud, altitud in RECURSOS:
        sesion.add(
            RecursoTuristico(
                codigo_mincetur=codigo,
                nombre=nombre,
                provincia=provincia,
                distrito=distrito,
                categoria="1. SITIOS NATURALES",
                descripcion_es=f"{nombre}: recurso de prueba en {distrito}.",
                ubicacion=func.ST_GeogFromText(f"SRID=4326;POINT({longitud} {latitud})"),
                altitud_msnm=altitud,
                esta_validado=True,
                esta_vigente=True,
            )
        )

    sesion.commit()
    return sesion


@pytest.fixture
def preferencia(catalogo: Session) -> PreferenciaViaje:
    """Una preferencia sin cuenta, como la que crea el propio asistente."""
    fila = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=SABADO,
        fecha_fin=SABADO + timedelta(days=1),
        distrito_origen="HUANCAYO",
        presupuesto_soles=Decimal("300.00"),
        intereses=["naturaleza"],
        movilidad="transporte_publico",
        requiere_accesibilidad=False,
        idioma="es",
        ritmo="moderado",
    )
    catalogo.add(fila)
    catalogo.commit()
    catalogo.refresh(fila)

    return fila


# ---------------------------------------------------------------------------
# Disponibilidad: dos fallos que se arreglan distinto
# ---------------------------------------------------------------------------


class TestDisponibilidad:
    def test_si_ollama_no_contesta_se_explica_que_hacer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """«connection refused» no le sirve a nadie; «usa el formulario» sí."""
        _OllamaFalso([], esta_caido=True).instalar(monkeypatch)

        disponible, motivo = comprobar_disponibilidad(URL, MODELO)

        assert disponible is False
        assert motivo is not None
        assert "formulario" in motivo

    def test_si_ollama_esta_pero_le_falta_el_modelo_se_dice_como_bajarlo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Los dos fallos se arreglan distinto, así que se informan distinto.

        Si Ollama no está, hay que arrancarlo. Si falta el modelo, hay que
        descargarlo. Un único mensaje para los dos dejaría al usuario probando.
        """
        _OllamaFalso([], modelos_instalados=("llama3.2:3b",)).instalar(monkeypatch)

        disponible, motivo = comprobar_disponibilidad(URL, MODELO)

        assert disponible is False
        assert motivo is not None
        assert f"ollama pull {MODELO}" in motivo

    def test_esta_disponible_cuando_el_modelo_coincide_exactamente(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _OllamaFalso([], modelos_instalados=(MODELO,)).instalar(monkeypatch)

        assert comprobar_disponibilidad(URL, MODELO) == (True, None)

    def test_acepta_el_modelo_instalado_con_otra_etiqueta(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ollama etiqueta los modelos y no siempre con la etiqueta esperada.

        Pedir «qwen2.5:7b-instruct» y encontrar «qwen2.5:latest» instalado no
        es un fallo: es el mismo modelo con otra etiqueta.
        """
        _OllamaFalso([], modelos_instalados=("qwen2.5:latest",)).instalar(monkeypatch)

        assert comprobar_disponibilidad(URL, MODELO) == (True, None)

    def test_un_modelo_de_otra_familia_no_cuela_por_el_prefijo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _OllamaFalso([], modelos_instalados=("qwen2.5-coder:7b",)).instalar(monkeypatch)

        disponible, _ = comprobar_disponibilidad(URL, MODELO)

        assert disponible is False


# ---------------------------------------------------------------------------
# El bucle de conversación
# ---------------------------------------------------------------------------


class TestConversar:
    def test_sin_ollama_no_falla_sino_que_lo_dice(
        self, sesion: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Un asistente que se queda pensando es peor que uno que dice «no»."""
        _OllamaFalso([], esta_caido=True).instalar(monkeypatch)

        respuesta = conversar(sesion, [{"role": "user", "content": "hola"}], URL, MODELO)

        assert respuesta.esta_disponible is False
        assert respuesta.mensaje == ""
        assert respuesta.aviso is not None
        assert "formulario" in respuesta.aviso

    def test_devuelve_el_texto_del_modelo_cuando_no_pide_ninguna_funcion(
        self, sesion: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _OllamaFalso([_dice("  Puedo ayudarte a armar un plan.  ")]).instalar(monkeypatch)

        respuesta = conversar(sesion, [{"role": "user", "content": "¿qué haces?"}], URL, MODELO)

        assert respuesta.mensaje == "Puedo ayudarte a armar un plan."
        assert respuesta.esta_disponible is True
        assert respuesta.funciones_usadas == []
        assert respuesta.preferencia_id is None

    def test_las_reglas_y_las_funciones_van_en_cada_conversacion(
        self, sesion: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Las reglas no se mandan «la primera vez»: van siempre.

        También se comprueba la temperatura baja: al modelo no se le pide
        creatividad, se le pide que elija bien la función y redacte lo que le
        den. Una temperatura alta es la vía más corta a un lugar inventado.
        """
        ollama = _OllamaFalso([_dice("hola")]).instalar(monkeypatch)

        conversar(sesion, [{"role": "user", "content": "hola"}], URL, MODELO)

        peticion = ollama.peticiones[0]
        assert peticion["messages"][0] == {"role": "system", "content": INSTRUCCIONES}
        assert peticion["messages"][1] == {"role": "user", "content": "hola"}
        assert peticion["tools"] == HERRAMIENTAS
        assert peticion["stream"] is False
        assert peticion["options"]["temperature"] == 0.2
        assert peticion["model"] == MODELO

    def test_el_modelo_solo_ve_lo_que_devolvio_la_consulta_a_la_base(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """La prueba que sostiene «el asistente no inventa lugares».

        El modelo pide buscar «Ocopa», el backend consulta la base y le manda
        de vuelta **solo** lo que la consulta devolvió. El texto que llega a
        Ollama en la segunda vuelta contiene el recurso del catálogo y no
        contiene nada más: no hay ningún sitio donde se le añadan sugerencias.
        """
        ollama = _OllamaFalso(
            [_pide("buscar_recursos", {"texto": "Ocopa"}), _dice("Encontré el convento.")]
        ).instalar(monkeypatch)

        respuesta = conversar(
            catalogo, [{"role": "user", "content": "háblame de Ocopa"}], URL, MODELO
        )

        devueltos = _mensajes_de_herramienta(ollama.peticiones[1])
        assert len(devueltos) == 1

        resultado = json.loads(devueltos[0])
        nombres = [r["nombre"] for r in resultado["recursos"]]
        assert nombres == ["Convento De Santa Rosa De Ocopa"]
        assert respuesta.mensaje == "Encontré el convento."

    def test_queda_registrado_que_funcion_se_uso_y_con_que_argumentos(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Es lo que hace auditable la conversación.

        Sin este registro no habría forma de comprobar que una respuesta salió
        de la base y no de la memoria del modelo.
        """
        _OllamaFalso(
            [_pide("buscar_recursos", {"texto": "laguna"}), _dice("Hay una laguna.")]
        ).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "lagunas"}], URL, MODELO)

        assert respuesta.funciones_usadas == [
            {"nombre": "buscar_recursos", "argumentos": {"texto": "laguna"}}
        ]

    def test_entiende_los_argumentos_cuando_llegan_como_texto_json(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Algunos modelos mandan los argumentos como cadena en vez de objeto."""
        ollama = _OllamaFalso(
            [_pide("buscar_recursos", '{"texto": "Ocopa"}'), _dice("listo")]
        ).instalar(monkeypatch)

        conversar(catalogo, [{"role": "user", "content": "Ocopa"}], URL, MODELO)

        resultado = json.loads(_mensajes_de_herramienta(ollama.peticiones[1])[0])
        assert resultado["encontrados"] == 1

    def test_unos_argumentos_que_no_son_json_no_tumban_la_conversacion(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Se ejecuta sin argumentos, que devuelve un resultado vacío y honesto.

        Lo importante es que el modelo recibe algo con lo que seguir en vez de
        que la petición reviente.
        """
        _OllamaFalso(
            [_pide("buscar_recursos", "{esto no es json"), _dice("No te entendí.")]
        ).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "???"}], URL, MODELO)

        assert respuesta.funciones_usadas == [{"nombre": "buscar_recursos", "argumentos": {}}]
        assert respuesta.mensaje == "No te entendí."

    def test_la_preferencia_creada_durante_la_charla_sale_en_la_respuesta(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """La interfaz la usa para ofrecer el enlace al itinerario completo."""
        _OllamaFalso(
            [
                _pide("crear_preferencia", {"intereses": ["naturaleza"], "dias": 2}),
                _dice("Ya registré tu viaje."),
            ]
        ).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "dos días"}], URL, MODELO)

        assert isinstance(respuesta.preferencia_id, int)
        assert catalogo.get(PreferenciaViaje, respuesta.preferencia_id) is not None

    def test_si_ollama_se_cae_a_mitad_se_avisa_y_se_conserva_lo_hecho(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """La búsqueda ya se hizo; perderla sería perder trabajo real."""
        _OllamaFalso(
            [_pide("buscar_recursos", {"texto": "Ocopa"}), _dice("no llega a decirlo")],
            se_cae_en_la_llamada=2,
        ).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "Ocopa"}], URL, MODELO)

        assert respuesta.esta_disponible is False
        assert respuesta.aviso is not None
        assert "formulario" in respuesta.aviso
        assert respuesta.funciones_usadas == [
            {"nombre": "buscar_recursos", "argumentos": {"texto": "Ocopa"}}
        ]

    def test_un_modelo_que_pide_funciones_sin_parar_se_detiene(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sin tope, un modelo confundido se llamaría a sí mismo sin fin.

        El Ollama de mentira repite la misma petición indefinidamente. Tras
        cuatro vueltas el bucle corta y devuelve un mensaje que sirve, en vez
        de dejar la petición colgada.
        """
        ollama = _OllamaFalso([_pide("buscar_recursos", {"texto": "Ocopa"})]).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "Ocopa"}], URL, MODELO)

        assert len(ollama.peticiones) == VUELTAS_MAXIMAS
        assert len(respuesta.funciones_usadas) == VUELTAS_MAXIMAS
        assert "No conseguí armar una respuesta" in respuesta.mensaje
        assert respuesta.esta_disponible is True, "Ollama sí estaba; el modelo se perdió"

    def test_una_funcion_inventada_por_el_modelo_se_le_devuelve_como_error(
        self, catalogo: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Los modelos se inventan nombres de función. Eso no tumba la charla."""
        ollama = _OllamaFalso(
            [_pide("reservar_hotel", {}), _dice("Eso no lo puedo hacer.")]
        ).instalar(monkeypatch)

        respuesta = conversar(catalogo, [{"role": "user", "content": "resérvame"}], URL, MODELO)

        devuelto = json.loads(_mensajes_de_herramienta(ollama.peticiones[1])[0])
        assert "No existe una función" in devuelto["error"]
        assert respuesta.mensaje == "Eso no lo puedo hacer."


# ---------------------------------------------------------------------------
# La frontera entre el modelo y los datos
# ---------------------------------------------------------------------------


class TestFronteraConLosDatos:
    def test_si_una_funcion_revienta_se_devuelve_el_error_y_no_la_excepcion(
        self, sesion: Session
    ) -> None:
        """Un presupuesto escrito en palabras rompe la conversión a Decimal.

        El modelo puede mandar «mucho» donde se espera un número. Lo correcto
        es contestarle con un error que pueda leer, no propagar la excepción
        hasta tumbar la petición HTTP.
        """
        resultado = ejecutar_funcion(
            sesion,
            "crear_preferencia",
            {"intereses": ["naturaleza"], "presupuesto_soles": "mucho dinero"},
            idioma="es",
        )

        assert "error" in resultado
        assert "crear_preferencia" in resultado["error"]
        assert "InvalidOperation" in resultado["error"]


# ---------------------------------------------------------------------------
# crear_preferencia
# ---------------------------------------------------------------------------


def _crear(sesion: Session, **argumentos) -> dict:
    return ejecutar_funcion(sesion, "crear_preferencia", argumentos, idioma="es")


class TestCrearPreferencia:
    def test_registra_la_preferencia_en_la_base(self, sesion: Session) -> None:
        resultado = _crear(sesion, intereses=["naturaleza", "artesania"], dias=3)

        fila = sesion.get(PreferenciaViaje, resultado["preferencia_id"])

        assert fila is not None
        assert sorted(fila.intereses) == ["artesania", "naturaleza"]
        assert fila.usuario_id is None, "el asistente no exige cuenta"

    def test_sin_ningun_interes_valido_no_crea_nada_y_dice_cuales_valen(
        self, sesion: Session
    ) -> None:
        """Inventarle un interés al visitante sería decidir por él."""
        resultado = _crear(sesion, intereses=["parapente", "buceo"])

        assert "error" in resultado
        assert "naturaleza" in resultado["error"]
        assert sesion.scalars(select(PreferenciaViaje)).all() == []

    def test_descarta_los_intereses_inventados_y_conserva_los_validos(
        self, sesion: Session
    ) -> None:
        resultado = _crear(sesion, intereses=["parapente", "gastronomia"])

        fila = sesion.get(PreferenciaViaje, resultado["preferencia_id"])

        assert fila is not None
        assert fila.intereses == ["gastronomia"]

    def test_lo_que_se_supone_se_declara_para_que_el_modelo_lo_confirme(
        self, sesion: Session
    ) -> None:
        """La diferencia entre un predeterminado y un dato del visitante.

        Si el asistente rellena la duración y el presupuesto por su cuenta y no
        lo dice, el modelo los repetirá como si el visitante los hubiera
        elegido. Declararlos obliga a confirmarlos.
        """
        resultado = _crear(sesion, intereses=["naturaleza"])

        assert "duración de 2 días" in resultado["supuestos"]
        assert "presupuesto de S/ 300" in resultado["supuestos"]
        assert resultado["aviso"] is not None
        assert "Confirma" in resultado["aviso"]

    def test_sin_nada_que_suponer_no_hay_aviso_que_dar(self, sesion: Session) -> None:
        resultado = _crear(
            sesion, intereses=["naturaleza"], dias=4, presupuesto_soles=800, ritmo="intenso"
        )

        assert resultado["supuestos"] == []
        assert resultado["aviso"] is None

    def test_la_duracion_se_traduce_a_fecha_de_fin(self, sesion: Session) -> None:
        """Tres días son dos noches: del día 1 al 3, no al 4."""
        resultado = _crear(sesion, intereses=["naturaleza"], dias=3)

        assert resultado["fecha_fin"] - resultado["fecha_inicio"] == timedelta(days=2)

    def test_una_duracion_absurda_cae_al_predeterminado(self, sesion: Session) -> None:
        resultado = _crear(sesion, intereses=["naturaleza"], dias=0)

        assert resultado["fecha_fin"] - resultado["fecha_inicio"] == timedelta(days=1)
        assert "duración de 2 días" in resultado["supuestos"]

    def test_el_viaje_se_propone_con_una_semana_de_margen(self, sesion: Session) -> None:
        """Proponer «mañana» obligaría a correr; proponer «en un mes», a esperar."""
        resultado = _crear(sesion, intereses=["naturaleza"])

        assert resultado["fecha_inicio"] == date.today() + timedelta(days=7)

    def test_el_distrito_se_guarda_en_mayusculas_como_el_inventario(self, sesion: Session) -> None:
        resultado = _crear(sesion, intereses=["naturaleza"], distrito_origen="el tambo")

        assert resultado["distrito_origen"] == "EL TAMBO"

    def test_sin_distrito_se_parte_de_huancayo(self, sesion: Session) -> None:
        resultado = _crear(sesion, intereses=["naturaleza"])

        assert resultado["distrito_origen"] == "HUANCAYO"

    def test_el_idioma_de_la_conversacion_queda_en_la_preferencia(self, sesion: Session) -> None:
        """Quien pregunta en inglés recibirá el itinerario en inglés."""
        resultado = ejecutar_funcion(
            sesion, "crear_preferencia", {"intereses": ["naturaleza"]}, idioma="en"
        )

        fila = sesion.get(PreferenciaViaje, resultado["preferencia_id"])

        assert fila is not None
        assert fila.idioma == "en"


# ---------------------------------------------------------------------------
# generar_recomendaciones
# ---------------------------------------------------------------------------


class TestGenerarRecomendaciones:
    def test_devuelve_las_recomendaciones_con_el_por_que_de_cada_una(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        """El «por qué» no es adorno: es lo que el modelo puede contar.

        Sin los términos decisivos, el asistente diría «te recomiendo esto» y
        tendría que inventarse el motivo.
        """
        resultado = ejecutar_funcion(
            catalogo,
            "generar_recomendaciones",
            {"preferencia_id": preferencia.id},
            idioma="es",
        )

        assert "error" not in resultado
        assert resultado["total_evaluados"] == len(RECURSOS)
        assert resultado["generado_por"]
        assert resultado["recomendaciones"], "hay cuatro recursos validados"

        primera = resultado["recomendaciones"][0]
        assert set(primera) == {
            "recurso_id",
            "nombre",
            "distrito",
            "afinidad",
            "por_que",
            "afluencia",
        }
        assert isinstance(primera["por_que"], list)

    def test_el_limite_que_pida_el_modelo_se_recorta_a_diez(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        """Una lista de cincuenta en un chat no la lee nadie."""
        resultado = ejecutar_funcion(
            catalogo,
            "generar_recomendaciones",
            {"preferencia_id": preferencia.id, "limite": 50},
            idioma="es",
        )

        assert len(resultado["recomendaciones"]) <= 10

    def test_sin_preferencia_se_dice_que_hay_que_crearla_primero(self, catalogo: Session) -> None:
        resultado = ejecutar_funcion(
            catalogo, "generar_recomendaciones", {"preferencia_id": 999_999}, idioma="es"
        )

        assert "crear_preferencia" in resultado["error"]


# ---------------------------------------------------------------------------
# construir_itinerario
# ---------------------------------------------------------------------------


def _itinerario(sesion: Session, **argumentos) -> dict:
    return ejecutar_funcion(sesion, "construir_itinerario", argumentos, idioma="es")


class TestConstruirItinerario:
    def test_arma_el_plan_del_dia_con_sus_paradas(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        resultado = _itinerario(catalogo, preferencia_id=preferencia.id)

        assert "error" not in resultado
        assert resultado["fecha"] == preferencia.fecha_inicio
        assert resultado["paradas"], "con cuatro recursos tiene que salir algo"
        assert resultado["tiempo_total_min"] > 0

        primera = resultado["paradas"][0]
        assert primera["orden"] == 1, "para el visitante la primera parada es la 1"
        assert ":" in primera["llegada"], "la hora va legible, no como objeto"

    def test_devuelve_los_avisos_y_recuerda_al_modelo_que_los_transmita(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        """Lo que un asistente conversacional tiende a omitir por brevedad.

        Los avisos de tramo estimado, altitud y presupuesto son de seguridad.
        Por eso el resultado lleva un recordatorio explícito: el modelo redacta
        con lo que recibe, y si no recibe la instrucción, la resume fuera.
        """
        resultado = _itinerario(catalogo, preferencia_id=preferencia.id)

        assert "avisos" in resultado
        assert "estimaciones" in resultado["recordatorio"]
        assert "avisos" in resultado["recordatorio"]

    def test_el_costo_se_da_como_rango_y_nunca_como_cifra_unica(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        """Un número solo se leería como una tarifa oficial, y no lo es."""
        resultado = _itinerario(catalogo, preferencia_id=preferencia.id)

        assert " a " in resultado["costo_aproximado_soles"]

    def test_una_fecha_fuera_del_viaje_se_corrige_al_primer_dia(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        """El modelo pide a veces un día que no está en el viaje.

        Devolver un error por eso sería cortar la conversación por algo que
        tiene una respuesta razonable.
        """
        fuera = preferencia.fecha_fin + timedelta(days=30)

        resultado = _itinerario(catalogo, preferencia_id=preferencia.id, fecha=fuera.isoformat())

        assert resultado["fecha"] == preferencia.fecha_inicio

    def test_una_fecha_ilegible_tambien_cae_al_primer_dia(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        resultado = _itinerario(catalogo, preferencia_id=preferencia.id, fecha="el proximo sabado")

        assert resultado["fecha"] == preferencia.fecha_inicio

    def test_una_fecha_del_viaje_se_respeta(
        self, catalogo: Session, preferencia: PreferenciaViaje
    ) -> None:
        resultado = _itinerario(
            catalogo, preferencia_id=preferencia.id, fecha=preferencia.fecha_fin.isoformat()
        )

        assert resultado["fecha"] == preferencia.fecha_fin

    def test_sin_preferencia_se_dice_que_hay_que_crearla_primero(self, catalogo: Session) -> None:
        resultado = _itinerario(catalogo, preferencia_id=999_999)

        assert "crear_preferencia" in resultado["error"]


# ---------------------------------------------------------------------------
# consultar_afluencia
# ---------------------------------------------------------------------------


def _afluencia(sesion: Session, **argumentos) -> dict:
    return ejecutar_funcion(sesion, "consultar_afluencia", argumentos, idioma="es")


class TestConsultarAfluencia:
    def test_una_fecha_ilegible_se_rechaza_diciendo_el_formato(self, sesion: Session) -> None:
        """Aquí sí es un error: sin fecha no hay nada que predecir.

        A diferencia del itinerario, no hay una fecha razonable a la que caer:
        el visitante preguntó por un día concreto y no se sabe cuál.
        """
        resultado = _afluencia(sesion, fecha="el 30 de febrero")

        assert "no es una fecha válida" in resultado["error"]
        assert "AAAA-MM-DD" in resultado["error"]

    def test_devuelve_el_nivel_con_su_motivo_y_quien_lo_calculo(self, sesion: Session) -> None:
        """Decir «mucha gente» sin explicar por qué obliga a creérselo."""
        resultado = _afluencia(sesion, fecha=SABADO.isoformat(), distrito="HUANCAYO")

        assert "error" not in resultado
        assert resultado["fecha"] == SABADO
        assert resultado["nivel"] in {"bajo", "medio", "alto"}
        assert resultado["motivo"]
        assert resultado["calculado_por"]

    def test_sin_fecha_responde_por_hoy(self, sesion: Session) -> None:
        resultado = _afluencia(sesion)

        assert resultado["fecha"] == date.today()

    def test_el_distrito_se_normaliza_a_mayusculas(self, sesion: Session) -> None:
        resultado = _afluencia(sesion, fecha=SABADO.isoformat(), distrito="el tambo")

        assert resultado["distrito"] == "EL TAMBO"

    def test_sin_distrito_responde_por_huancayo(self, sesion: Session) -> None:
        resultado = _afluencia(sesion, fecha=SABADO.isoformat())

        assert resultado["distrito"] == "HUANCAYO"
