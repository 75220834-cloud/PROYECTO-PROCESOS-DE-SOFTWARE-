"""Pruebas del endpoint de salud.

Estas pruebas no necesitan que Docker ni Ollama esten encendidos: sustituyen
esas dependencias por dobles de prueba con el mecanismo dependency_overrides
de FastAPI. Una prueba que solo pasa si el entorno completo esta levantado no
sirve como red de seguridad.
"""

import pytest
from fastapi.testclient import TestClient

from app.base_datos import obtener_sesion
from app.configuracion import Configuracion, obtener_configuracion
from app.main import aplicacion


class SesionSimulada:
    """Doble de prueba de una sesion de SQLAlchemy.

    Devuelve la version de PostGIS que se le indique, o lanza un error si se
    quiere simular la base de datos caida.
    """

    def __init__(self, version_postgis: str | None):
        self.version_postgis = version_postgis

    def execute(self, *_args, **_kwargs):
        if self.version_postgis is None:
            raise RuntimeError("no hay conexion con la base de datos")

        version = self.version_postgis

        class Resultado:
            def scalar_one(self):
                return version

        return Resultado()


@pytest.fixture
def cliente():
    """Cliente HTTP de pruebas que limpia las sustituciones al terminar."""
    with TestClient(aplicacion) as cliente_prueba:
        yield cliente_prueba
    aplicacion.dependency_overrides.clear()


def test_la_raiz_orienta_hacia_la_documentacion(cliente):
    """La ruta / debe responder 200 e indicar donde esta la documentacion."""
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json()["documentacion"] == "/docs"


def test_salud_reporta_degradado_cuando_la_base_de_datos_esta_caida(cliente):
    """Caso borde: si PostgreSQL no responde, el estado general es 'degradado'.

    Lo importante es que el endpoint siga devolviendo 200. Si devolviera 500
    no se podria distinguir "el servicio de salud esta roto" de "un componente
    esta caido", que es justo el dato que se quiere obtener.
    """
    # Puerto 1: nadie escucha ahi, asi que la llamada a Ollama falla de inmediato.
    configuracion_sin_ollama = Configuracion(ollama_url="http://127.0.0.1:1")

    aplicacion.dependency_overrides[obtener_sesion] = lambda: SesionSimulada(None)
    aplicacion.dependency_overrides[obtener_configuracion] = lambda: configuracion_sin_ollama

    respuesta = cliente.get("/api/salud")
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["estado_general"] == "degradado"
    assert cuerpo["base_datos"]["estado"] == "no_disponible"
    assert cuerpo["ollama"]["estado"] == "no_disponible"
    # La API siempre esta operativa: si no lo estuviera, no habria respuesta.
    assert cuerpo["api"]["estado"] == "operativo"


def test_salud_reporta_operativo_cuando_todo_responde(cliente, monkeypatch):
    """Caso normal: con base de datos y Ollama respondiendo, el estado es 'operativo'."""
    configuracion = Configuracion(ollama_modelo="modelo-de-prueba")

    class RespuestaSimulada:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "modelo-de-prueba"}]}

    # Sustituimos la llamada HTTP real a Ollama por una respuesta fija.
    monkeypatch.setattr("app.rutas.salud.httpx.get", lambda *a, **k: RespuestaSimulada())

    aplicacion.dependency_overrides[obtener_sesion] = lambda: SesionSimulada("3.4 USE_GEOS=1")
    aplicacion.dependency_overrides[obtener_configuracion] = lambda: configuracion

    cuerpo = cliente.get("/api/salud").json()

    assert cuerpo["estado_general"] == "operativo"
    assert cuerpo["base_datos"]["detalle"] == "PostGIS 3.4 USE_GEOS=1"
    assert cuerpo["ollama"]["estado"] == "operativo"


def test_los_interruptores_de_modelo_existen_y_se_pueden_apagar():
    """Regla de oro de la IA: cada modelo debe poder desactivarse por configuracion.

    Esta prueba fija esa regla en el codigo. Si alguien elimina un interruptor
    en una fase futura, esta prueba falla y obliga a discutirlo.
    """
    configuracion = Configuracion(
        usar_modelo_recomendacion=False,
        usar_modelo_afluencia=False,
        usar_modelo_sentimiento=False,
    )

    assert configuracion.usar_modelo_recomendacion is False
    assert configuracion.usar_modelo_afluencia is False
    assert configuracion.usar_modelo_sentimiento is False
