"""Pruebas de los endpoints del catálogo.

Se levanta la API completa con TestClient y se sustituye su sesión de base de
datos por la de la prueba, que se deshace al terminar. Así se ejercita el
camino real —consulta SQL incluida— sin dejar rastro.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.base_datos import obtener_sesion
from app.main import aplicacion
from app.servicios.catalogo import importar_inventario
from app.servicios.validacion_catalogo import validar_catalogo


@pytest.fixture
def cliente(sesion):
    """Cliente HTTP que usa la sesión de prueba en lugar de la real."""
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


@pytest.fixture
def catalogo_cargado(sesion, csv_de_ejemplo):
    """Importa y valida el CSV de ejemplo antes de la prueba."""
    importar_inventario(sesion, csv_de_ejemplo)
    validar_catalogo(sesion)
    return sesion


class TestListarRecursos:
    def test_devuelve_todos_los_recursos_de_la_ruta(self, cliente, catalogo_cargado):
        respuesta = cliente.get("/api/recursos")

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["total"] == 3
        assert len(cuerpo["elementos"]) == 3

    def test_filtra_por_provincia(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/recursos", params={"provincia": "CONCEPCION"}).json()

        assert cuerpo["total"] == 1
        assert cuerpo["elementos"][0]["distrito"] == "SANTA ROSA DE OCOPA"

    def test_el_filtro_de_provincia_no_distingue_mayusculas(self, cliente, catalogo_cargado):
        # El visitante no tiene por qué escribir en mayúsculas.
        cuerpo = cliente.get("/api/recursos", params={"provincia": "concepcion"}).json()
        assert cuerpo["total"] == 1

    def test_busca_por_texto_en_el_nombre(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/recursos", params={"texto": "convento"}).json()

        assert cuerpo["total"] == 1
        assert "Convento" in cuerpo["elementos"][0]["nombre"]

    def test_la_busqueda_no_distingue_tildes(self, cliente, catalogo_cargado):
        """Caso borde importante: nadie escribe "Constitución" con tilde al buscar."""
        con_tilde = cliente.get("/api/recursos", params={"texto": "Constitución"}).json()
        sin_tilde = cliente.get("/api/recursos", params={"texto": "constitucion"}).json()

        assert con_tilde["total"] == 1
        assert sin_tilde["total"] == 1

    def test_filtra_solo_los_validados(self, cliente, catalogo_cargado):
        # De los 3 recursos, el que no tiene coordenadas no pasa la validación.
        cuerpo = cliente.get("/api/recursos", params={"solo_validados": True}).json()

        assert cuerpo["total"] == 2
        assert all(elemento["esta_validado"] for elemento in cuerpo["elementos"])

    def test_pagina_los_resultados(self, cliente, catalogo_cargado):
        primera = cliente.get("/api/recursos", params={"tamano_pagina": 2, "pagina": 1}).json()
        segunda = cliente.get("/api/recursos", params={"tamano_pagina": 2, "pagina": 2}).json()

        # El total es el de TODOS los que cumplen el filtro, no el de la página.
        assert primera["total"] == 3
        assert len(primera["elementos"]) == 2
        assert len(segunda["elementos"]) == 1

        # Las páginas no deben repetir elementos.
        ids_primera = {e["id"] for e in primera["elementos"]}
        ids_segunda = {e["id"] for e in segunda["elementos"]}
        assert ids_primera.isdisjoint(ids_segunda)

    def test_rechaza_un_tamano_de_pagina_excesivo(self, cliente, catalogo_cargado):
        """Caso borde: hay que impedir que una petición pida todo de golpe."""
        respuesta = cliente.get("/api/recursos", params={"tamano_pagina": 5000})
        assert respuesta.status_code == 422

    def test_devuelve_una_pagina_vacia_si_nada_coincide(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/recursos", params={"texto": "zzzznoexiste"}).json()

        assert cuerpo["total"] == 0
        assert cuerpo["elementos"] == []


class TestRecursosParaElMapa:
    def test_devuelve_geojson_valido(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/recursos/mapa").json()

        assert cuerpo["type"] == "FeatureCollection"
        assert all(rasgo["type"] == "Feature" for rasgo in cuerpo["features"])

    def test_excluye_los_recursos_sin_coordenadas(self, cliente, catalogo_cargado):
        """Un marcador sin coordenada no se puede dibujar, y no se inventa."""
        cuerpo = cliente.get("/api/recursos/mapa").json()

        # De los 3 recursos importados, solo 2 tienen ubicación.
        assert len(cuerpo["features"]) == 2

    def test_las_coordenadas_van_en_el_orden_de_geojson(self, cliente, catalogo_cargado):
        """GeoJSON exige [longitud, latitud], al revés de como se dice al hablar.

        Si se invirtieran, todos los marcadores del mapa aparecerían en China.
        """
        cuerpo = cliente.get("/api/recursos/mapa").json()

        for rasgo in cuerpo["features"]:
            longitud, latitud = rasgo["geometry"]["coordinates"]
            assert -76 < longitud < -74, "la primera coordenada debe ser la longitud"
            assert -13 < latitud < -11, "la segunda coordenada debe ser la latitud"


class TestDetalleDeRecurso:
    def test_devuelve_el_detalle(self, cliente, catalogo_cargado):
        listado = cliente.get("/api/recursos").json()
        id_recurso = listado["elementos"][0]["id"]

        cuerpo = cliente.get(f"/api/recursos/{id_recurso}").json()

        assert cuerpo["id"] == id_recurso
        assert "codigo_mincetur" in cuerpo

    def test_devuelve_404_si_no_existe(self, cliente, catalogo_cargado):
        respuesta = cliente.get("/api/recursos/99999999")

        assert respuesta.status_code == 404
        assert respuesta.json()["detail"]["codigo"] == "sin_recurso"


class TestFiltrosDisponibles:
    def test_devuelve_los_valores_que_existen_en_el_catalogo(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/recursos/filtros").json()

        assert set(cuerpo["provincias"]) == {"HUANCAYO", "CONCEPCION", "JAUJA"}
        assert "SANTA ROSA DE OCOPA" in cuerpo["distritos"]
        assert len(cuerpo["categorias"]) >= 1


class TestIndicadorDelCatalogo:
    def test_devuelve_el_indicador_del_incremento_1(self, cliente, catalogo_cargado):
        cuerpo = cliente.get("/api/indicadores/catalogo").json()

        assert cuerpo["total_recursos"] == 3
        assert cuerpo["validados"] == 2
        assert cuerpo["porcentaje_validado"] == pytest.approx(66.67, abs=0.01)
        assert cuerpo["porcentaje_con_coordenadas"] == pytest.approx(66.67, abs=0.01)

    def test_avisa_con_claridad_si_nunca_se_valido(self, cliente, sesion, csv_de_ejemplo):
        """Caso borde: el catálogo existe pero nadie ejecutó la validación."""
        importar_inventario(sesion, csv_de_ejemplo)  # sin validar

        respuesta = cliente.get("/api/indicadores/catalogo")

        assert respuesta.status_code == 404
        # El mensaje con el comando que hay que ejecutar vive en los archivos
        # de idioma; aquí se fija el código, que es lo que decide el backend.
        assert respuesta.json()["detail"]["codigo"] == "catalogo_sin_validar"
