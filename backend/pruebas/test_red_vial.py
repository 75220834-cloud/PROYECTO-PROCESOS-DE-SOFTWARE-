"""Pruebas del cálculo de traslados sobre la red vial.

## Por qué estas pruebas se hacen con un grafo de cinco nodos

El grafo real del valle tiene unos 40 000 nodos, pesa 28 MB y tarda segundos
en cargarse. Probar contra él tendría dos problemas: las pruebas serían lentas
y, sobre todo, **no se podrían afirmar números concretos** —nadie sabe de
memoria cuánto mide la calle que une dos nodos de Chongos Alto.

Así que aquí se construye a mano una red de cinco nodos en línea, con las
longitudes y las altitudes puestas a propósito. Eso permite comprobar lo que de
verdad importa y que el grafo real no deja ver:

- que el tiempo se calcula **tramo a tramo** y no de una vez sobre el total;
- que solo cuenta la subida, no el desnivel neto;
- que la línea recta se corrige por el factor 1,26 **solo** cuando el cálculo
  es una estimación, y no cuando los dos puntos caen sobre el mismo nodo;
- que se distinguen los tres motivos por los que puede no haber camino.

No se usa ninguna imitación de OpenStreetMap: ``osmnx`` busca el nodo más
cercano sobre este grafo de cinco nodos igual que lo haría sobre el real, sin
tocar la red. Lo único que se sustituye es la descarga del grafo y el muestreo
de altitudes en la prueba de ``construir_y_guardar``, que de otro modo bajaría
cien megas de OpenStreetMap y leería el modelo de elevación de Copernicus.
"""

from __future__ import annotations

# SEGURIDAD: el unico pickle que se lee aqui lo escribe esta misma prueba en
# un directorio temporal, en el mismo proceso. No se carga ningun archivo de
# origen externo; es la misma condicion que documenta app/servicios/red_vial.py.
import pickle

import pytest

from app.ia.tiempo_recorrido import calcular_tramo_caminando
from app.modelos.itinerario import OrigenDelCalculo
from app.servicios.red_vial import (
    DISTANCIA_MAXIMA_AL_NODO_M,
    FACTOR_DE_RODEO,
    RedVial,
    Traslado,
    construir_y_guardar,
    distancia_en_linea_recta_m,
    obtener_red_vial,
)

# ---------------------------------------------------------------------------
# La red de prueba
#
# Cinco nodos sobre el mismo paralelo, separados 0,001° de longitud (unos 109 m
# a esta latitud). Los nodos 1-4 están unidos en cadena; el 9 está suelto, para
# poder provocar el caso de «red partida» sin inventar nada.
#
#   1 ──110 m── 2 ──120 m── 3 ──130 m── 4      9
#  3250 m      3300 m      3250 m     3255 m
#
# Las altitudes suben 50 m y vuelven a bajarlos: es la forma de que una prueba
# pueda distinguir «calculado tramo a tramo» de «calculado de una vez».
# ---------------------------------------------------------------------------

LATITUD = -12.0680

LONGITUD_DEL_NODO = {
    1: -75.2100,
    2: -75.2090,
    3: -75.2080,
    4: -75.2070,
    9: -75.2060,  # suelto, sin aristas
}

ALTITUD_DEL_NODO = {1: 3250.0, 2: 3300.0, 3: 3250.0, 4: 3255.0}

LARGO_DE_LA_ARISTA = {(1, 2): 110.0, (2, 3): 120.0, (3, 4): 130.0}

#: Un punto a más de 500 m de cualquier nodo de la red de prueba: 2 175 m del
#: nodo 1 y 1 743 m del 9. Representa los recursos del 26,1 % sin cobertura.
LONGITUD_SIN_COBERTURA = -75.1900


def _grafo_de_prueba():
    """El grafo de cinco nodos, en el formato que devuelve osmnx."""
    import networkx as nx

    grafo = nx.MultiDiGraph()
    # osmnx necesita saber que las coordenadas son geográficas para medir
    # distancias en metros en vez de en grados.
    grafo.graph["crs"] = "epsg:4326"

    for nodo, longitud in LONGITUD_DEL_NODO.items():
        grafo.add_node(nodo, x=longitud, y=LATITUD)

    for (origen, destino), largo in LARGO_DE_LA_ARISTA.items():
        grafo.add_edge(origen, destino, length=largo)

    return grafo


def _red(altitudes: dict[int, float] | None = None) -> RedVial:
    return RedVial(_grafo_de_prueba(), dict(ALTITUD_DEL_NODO if altitudes is None else altitudes))


def _punto(nodo: int) -> tuple[float, float]:
    """Las coordenadas exactas de un nodo, como las pediría un recurso."""
    return LATITUD, LONGITUD_DEL_NODO[nodo]


# ---------------------------------------------------------------------------
# Traslado
# ---------------------------------------------------------------------------


class TestTraslado:
    def test_un_traslado_sobre_la_red_no_es_estimado(self):
        traslado = Traslado(
            distancia_m=100.0,
            minutos=1.0,
            desnivel_m=0.0,
            subida_m=0.0,
            origen_del_calculo=OrigenDelCalculo.RED_VIAL,
            trazado=[],
        )

        assert traslado.es_estimado is False

    def test_un_traslado_en_linea_recta_si_es_estimado(self):
        """Es la bandera que hace que la interfaz muestre el aviso."""
        traslado = Traslado(
            distancia_m=100.0,
            minutos=1.0,
            desnivel_m=0.0,
            subida_m=0.0,
            origen_del_calculo=OrigenDelCalculo.LINEA_RECTA,
            trazado=[],
        )

        assert traslado.es_estimado is True


# ---------------------------------------------------------------------------
# El grafo y sus accesos
# ---------------------------------------------------------------------------


class TestAccesoAlGrafo:
    def test_expone_el_grafo_que_recibio(self):
        grafo = _grafo_de_prueba()

        assert RedVial(grafo, {}).grafo is grafo

    def test_el_grafo_sin_direccion_se_calcula_una_vez_y_se_guarda(self):
        """A pie se puede ir en los dos sentidos, pero convertirlo es caro.

        Que las dos llamadas devuelvan **el mismo objeto** es lo que prueba que
        la conversión no se repite en cada cálculo de ruta.
        """
        red = _red()

        primera = red.sin_direccion
        segunda = red.sin_direccion

        assert primera is segunda
        assert primera.has_edge(2, 1), "a pie el tramo 1-2 se recorre en ambos sentidos"

    def test_devuelve_la_altitud_de_un_nodo_conocido(self):
        assert _red().altitud_del_nodo(2) == 3300.0

    def test_devuelve_nulo_y_no_cero_para_un_nodo_sin_altitud(self):
        """Cero metros es una altitud válida; «no lo sé» tiene que ser nulo."""
        assert _red().altitud_del_nodo(9) is None

    def test_encuentra_el_nodo_mas_cercano_y_su_distancia(self):
        red = _red()

        nodo, distancia = red.nodo_mas_cercano(LATITUD, LONGITUD_DEL_NODO[3])

        assert nodo == 3
        assert distancia < 1.0

    def test_la_distancia_al_nodo_mas_cercano_delata_la_falta_de_cobertura(self):
        red = _red()

        _, distancia = red.nodo_mas_cercano(LATITUD, LONGITUD_SIN_COBERTURA)

        assert distancia > DISTANCIA_MAXIMA_AL_NODO_M


# ---------------------------------------------------------------------------
# buscar_camino: los tres motivos de que no haya camino
# ---------------------------------------------------------------------------


class TestBuscarCamino:
    def test_encuentra_la_cadena_completa_entre_los_extremos(self):
        red = _red()

        busqueda = red.buscar_camino(*_punto(1), *_punto(4))

        assert busqueda.camino == [1, 2, 3, 4]
        assert busqueda.hay_cobertura is True
        assert busqueda.recta_m == pytest.approx(326.2, abs=0.5)

    def test_sin_cobertura_no_hay_camino_y_se_dice_que_no_la_hay(self):
        """Primer motivo: el destino está a más de 500 m de cualquier vía."""
        red = _red()

        busqueda = red.buscar_camino(*_punto(1), LATITUD, LONGITUD_SIN_COBERTURA)

        assert busqueda.camino is None
        assert busqueda.hay_cobertura is False
        assert busqueda.recta_m == pytest.approx(2174.8, abs=0.5)

    def test_dos_puntos_sobre_el_mismo_nodo_no_tienen_camino_pero_si_cobertura(self):
        """Segundo motivo, y el que obligó a separar las dos cosas.

        Están a once metros: prácticamente en el mismo sitio. Avisar aquí de
        que el tiempo es «una estimación» alarmaría sin ningún motivo.
        """
        red = _red()
        longitud_vecina = LONGITUD_DEL_NODO[1] + 0.0001  # unos 11 m al este

        busqueda = red.buscar_camino(*_punto(1), LATITUD, longitud_vecina)

        assert busqueda.camino is None
        assert busqueda.hay_cobertura is True

    def test_la_red_partida_entre_los_extremos_se_trata_como_falta_de_cobertura(self):
        """Tercer motivo: hay vías en los dos extremos, pero no se tocan.

        El nodo 9 está sobre la red y a menos de 500 m, así que la cobertura
        existe; lo que no existe es camino. El tiempo no se conoce, y eso sí
        hay que avisarlo.
        """
        red = _red()

        busqueda = red.buscar_camino(*_punto(1), *_punto(9))

        assert busqueda.camino is None
        assert busqueda.hay_cobertura is False


# ---------------------------------------------------------------------------
# Longitud de un camino: lo que necesitan los traslados motorizados
# ---------------------------------------------------------------------------


class TestLongitudDelCamino:
    def test_suma_las_longitudes_de_las_aristas(self):
        total, trazado = _red().longitud_del_camino_m([1, 2, 3, 4])

        assert total == 360.0  # 110 + 120 + 130
        assert len(trazado) == 4
        assert trazado[0] == (LATITUD, LONGITUD_DEL_NODO[1])
        assert trazado[-1] == (LATITUD, LONGITUD_DEL_NODO[4])

    def test_un_camino_de_un_solo_nodo_mide_cero_pero_tiene_un_punto(self):
        total, trazado = _red().longitud_del_camino_m([1])

        assert total == 0.0
        assert trazado == [(LATITUD, LONGITUD_DEL_NODO[1])]

    def test_un_camino_vacio_no_rompe_el_calculo(self):
        total, trazado = _red().longitud_del_camino_m([])

        assert total == 0.0
        assert trazado == []

    def test_mide_igual_el_tramo_recorrido_al_reves(self):
        """Las aristas del grafo son dirigidas; a pie da igual el sentido.

        Sin esto, bajar por la misma calle por la que se subió mediría cero.
        """
        total, _ = _red().longitud_del_camino_m([4, 3, 2, 1])

        assert total == 360.0

    def test_entre_dos_nodos_sin_arista_la_longitud_es_cero(self):
        """No se inventa una distancia donde el grafo no dice nada."""
        total, _ = _red().longitud_del_camino_m([1, 9])

        assert total == 0.0

    def test_entre_aristas_paralelas_toma_la_mas_corta(self):
        """OpenStreetMap registra calzadas paralelas entre los mismos nodos."""
        grafo = _grafo_de_prueba()
        grafo.add_edge(1, 2, length=95.0)  # un atajo junto a la vía de 110 m

        total, _ = RedVial(grafo, {}).longitud_del_camino_m([1, 2])

        assert total == 95.0

    def test_una_arista_sin_longitud_declarada_no_aporta_metros(self):
        grafo = _grafo_de_prueba()
        grafo.add_edge(4, 9)  # sin atributo length

        total, _ = RedVial(grafo, {}).longitud_del_camino_m([4, 9])

        assert total == 0.0


# ---------------------------------------------------------------------------
# El cálculo tramo a tramo: el corazón del módulo
# ---------------------------------------------------------------------------


class TestTrasladoPorLaRed:
    def test_el_tiempo_se_calcula_tramo_a_tramo_y_no_de_una_vez(self):
        """La razón de ser de ``_traslado_por_la_red``, en números.

        El camino sube 50 m, los baja y vuelve a subir 5. El desnivel neto es
        de solo +5 m sobre 360 m, casi llano. Si el tiempo se calculara de una
        vez sobre el total, saldrían 4,5 minutos; calculado tramo a tramo son
        12,5, porque la pendiente no es lineal y la cuesta del 45 % del primer
        tramo cuesta lo que cuesta.

        Casi tres veces más. Prometer 4,5 minutos sería mandar a alguien a una
        cuesta diciéndole que es un paseo.
        """
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), ALTITUD_DEL_NODO[1], *_punto(4), ALTITUD_DEL_NODO[4]
        )

        de_una_vez = calcular_tramo_caminando(360.0, ALTITUD_DEL_NODO[1], ALTITUD_DEL_NODO[4])

        assert traslado.minutos == pytest.approx(12.5, abs=0.1)
        assert de_una_vez.minutos == pytest.approx(4.5, abs=0.1)
        assert traslado.minutos > de_una_vez.minutos * 2

    def test_solo_cuenta_la_subida_y_no_el_desnivel_neto(self):
        """Bajar lo que se ha subido no descansa las piernas.

        El camino sube 50 m del nodo 1 al 2 y 5 m del 3 al 4: 55 m de subida
        acumulada, aunque entre el principio y el final solo haya +5 m.
        """
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), ALTITUD_DEL_NODO[1], *_punto(4), ALTITUD_DEL_NODO[4]
        )

        assert traslado.subida_m == 55.0
        assert traslado.desnivel_m == 5.0

    def test_la_distancia_es_la_suma_de_las_aristas_recorridas(self):
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), ALTITUD_DEL_NODO[1], *_punto(4), ALTITUD_DEL_NODO[4]
        )

        assert traslado.distancia_m == 360.0
        assert traslado.origen_del_calculo == OrigenDelCalculo.RED_VIAL
        assert traslado.es_estimado is False

    def test_devuelve_el_trazado_para_dibujarlo_en_el_mapa(self):
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), ALTITUD_DEL_NODO[1], *_punto(4), ALTITUD_DEL_NODO[4]
        )

        assert traslado.trazado == [(LATITUD, LONGITUD_DEL_NODO[nodo]) for nodo in (1, 2, 3, 4)]

    def test_sin_altitudes_en_los_extremos_el_desnivel_neto_es_cero(self):
        """No se inventa un desnivel que no se conoce."""
        red = _red()

        traslado = red.calcular_traslado_caminando(*_punto(1), None, *_punto(4), None)

        assert traslado.desnivel_m == 0.0
        # La subida de los tramos sí se conoce: sale de las altitudes de los
        # nodos del grafo, que no dependen de lo que reciba la función.
        assert traslado.subida_m == 55.0

    def test_un_nodo_intermedio_sin_altitud_se_trata_como_llano(self):
        """Lo mismo tramo a tramo: sin dato, llano; nunca un desnivel inventado.

        Al quitar la altitud del nodo 2, los tramos 1-2 y 2-3 pasan a contarse
        como llanos y la subida acumulada se reduce a los 5 m del último tramo.
        """
        sin_el_dos = {nodo: alt for nodo, alt in ALTITUD_DEL_NODO.items() if nodo != 2}
        red = _red(sin_el_dos)

        traslado = red.calcular_traslado_caminando(
            *_punto(1), ALTITUD_DEL_NODO[1], *_punto(4), ALTITUD_DEL_NODO[4]
        )

        assert traslado.subida_m == 5.0
        assert traslado.minutos < 12.5, "sin la cuesta del 45 % se tarda menos"


# ---------------------------------------------------------------------------
# La estimación sobre línea recta, y cuándo NO se estima
# ---------------------------------------------------------------------------


class TestTrasladoEnLineaRecta:
    def test_sin_cobertura_se_corrige_la_recta_por_el_factor_medido(self):
        """El 1,26 no es una suposición: es la mediana de 400 pares medidos."""
        red = _red()
        recta = distancia_en_linea_recta_m(
            LATITUD, LONGITUD_DEL_NODO[1], LATITUD, LONGITUD_SIN_COBERTURA
        )

        traslado = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, LONGITUD_SIN_COBERTURA, 3400.0
        )

        assert traslado.distancia_m == pytest.approx(recta * FACTOR_DE_RODEO, abs=0.1)
        assert traslado.distancia_m > recta

    def test_sin_cobertura_el_traslado_queda_marcado_como_estimado(self):
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, LONGITUD_SIN_COBERTURA, 3400.0
        )

        assert traslado.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA
        assert traslado.es_estimado is True
        assert traslado.trazado == [], "no hay camino que dibujar en el mapa"

    def test_sin_cobertura_el_desnivel_si_se_conoce_y_se_aplica(self):
        """El modelo de elevación cubre todo el valle, aunque OSM no.

        Así que el tiempo estimado no es una regla de tres: la subida de 150 m
        entra en la función de Tobler igual que en un tramo calculado.
        """
        red = _red()

        cuesta_arriba = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, LONGITUD_SIN_COBERTURA, 3400.0
        )
        en_llano = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, LONGITUD_SIN_COBERTURA, 3250.0
        )

        assert cuesta_arriba.desnivel_m == 150.0
        assert cuesta_arriba.subida_m == 150.0
        assert en_llano.desnivel_m == 0.0
        assert cuesta_arriba.minutos > en_llano.minutos

    def test_bajando_la_subida_acumulada_es_cero_y_no_negativa(self):
        red = _red()

        traslado = red.calcular_traslado_caminando(
            *_punto(1), 3400.0, LATITUD, LONGITUD_SIN_COBERTURA, 3250.0
        )

        assert traslado.desnivel_m == -150.0
        assert traslado.subida_m == 0.0

    def test_en_el_mismo_nodo_la_recta_es_exacta_y_no_se_corrige(self):
        """El caso que obligó a separar «no hay camino» de «no hay cobertura».

        Once metros sobre la red: la línea recta **es** la distancia correcta.
        Aplicarle el factor de rodeo inflaría la distancia un 26 % y marcaría
        el tramo como estimado sin que lo sea.
        """
        red = _red()
        longitud_vecina = LONGITUD_DEL_NODO[1] + 0.0001
        recta = distancia_en_linea_recta_m(LATITUD, LONGITUD_DEL_NODO[1], LATITUD, longitud_vecina)

        traslado = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, longitud_vecina, 3251.0
        )

        assert traslado.distancia_m == pytest.approx(recta, abs=0.1)
        assert traslado.distancia_m != pytest.approx(recta * FACTOR_DE_RODEO, abs=0.1)
        assert traslado.origen_del_calculo == OrigenDelCalculo.RED_VIAL
        assert traslado.es_estimado is False
        assert traslado.trazado == []

    def test_en_el_mismo_nodo_el_desnivel_tambien_cuenta(self):
        red = _red()
        longitud_vecina = LONGITUD_DEL_NODO[1] + 0.0001

        traslado = red.calcular_traslado_caminando(
            *_punto(1), 3250.0, LATITUD, longitud_vecina, 3253.0
        )

        assert traslado.desnivel_m == 3.0
        assert traslado.subida_m == 3.0


# ---------------------------------------------------------------------------
# Construcción y carga del grafo desde disco
# ---------------------------------------------------------------------------


class _MuestreadorFalso:
    """Sustituye al muestreador real, que lee las teselas de Copernicus.

    Devuelve nulo para el nodo 9 a propósito: el modelo de elevación tiene
    huecos, y lo que hay que comprobar es que esos nodos quedan **fuera** del
    diccionario de altitudes en vez de entrar con un cero.
    """

    def __enter__(self) -> _MuestreadorFalso:
        return self

    def __exit__(self, *_) -> None:
        return None

    def altitud(self, latitud: float, longitud: float) -> float | None:
        for nodo, longitud_del_nodo in LONGITUD_DEL_NODO.items():
            if abs(longitud - longitud_del_nodo) < 1e-9:
                return ALTITUD_DEL_NODO.get(nodo)
        return None


@pytest.fixture
def ruta_temporal_del_grafo(tmp_path, monkeypatch):
    """Manda el grafo a un archivo temporal y limpia la caché del cargador.

    Sin lo primero, la prueba sobrescribiría el grafo real de 28 MB. Sin lo
    segundo, el ``lru_cache`` de ``obtener_red_vial`` arrastraría el resultado
    de una prueba a la siguiente.
    """
    ruta = tmp_path / "red" / "grafo_de_prueba.pickle"
    monkeypatch.setattr("app.servicios.red_vial.RUTA_DEL_GRAFO", ruta)
    obtener_red_vial.cache_clear()

    yield ruta

    obtener_red_vial.cache_clear()


class TestConstruccionYCarga:
    def test_construye_el_grafo_lo_guarda_y_devuelve_la_red(
        self, ruta_temporal_del_grafo, monkeypatch
    ):
        """Se sustituyen las dos fuentes externas, no la lógica.

        La descarga de OpenStreetMap y el muestreo de Copernicus son los dos
        pasos que tardan minutos y necesitan red. Lo que se comprueba es lo que
        hace el código con lo que le devuelven.
        """
        import osmnx as ox

        grafo = _grafo_de_prueba()
        limites_recibidos = []

        def descarga_falsa(*, bbox, network_type, simplify):
            limites_recibidos.append((bbox, network_type, simplify))
            return grafo

        monkeypatch.setattr(ox, "graph_from_bbox", descarga_falsa)
        monkeypatch.setattr(
            "app.servicios.elevacion.MuestreadorDeAltitud", lambda: _MuestreadorFalso()
        )

        limites = (-75.4, -12.3, -75.0, -11.7)
        red = construir_y_guardar(limites)

        assert limites_recibidos == [(limites, "all", True)]
        assert red.grafo is grafo
        assert red.altitud_del_nodo(2) == 3300.0
        assert red.altitud_del_nodo(9) is None, "un hueco del modelo no entra como cero"
        assert ruta_temporal_del_grafo.exists()

    def test_lo_guardado_en_disco_contiene_el_grafo_y_las_altitudes(
        self, ruta_temporal_del_grafo, monkeypatch
    ):
        import osmnx as ox

        monkeypatch.setattr(ox, "graph_from_bbox", lambda **_: _grafo_de_prueba())
        monkeypatch.setattr(
            "app.servicios.elevacion.MuestreadorDeAltitud", lambda: _MuestreadorFalso()
        )

        construir_y_guardar((-75.4, -12.3, -75.0, -11.7))

        with ruta_temporal_del_grafo.open("rb") as archivo:
            guardado = pickle.load(archivo)

        assert set(guardado) == {"grafo", "altitudes"}
        assert guardado["altitudes"] == ALTITUD_DEL_NODO
        assert sorted(guardado["grafo"].nodes) == sorted(LONGITUD_DEL_NODO)

    def test_carga_del_disco_la_red_ya_preparada(self, ruta_temporal_del_grafo):
        ruta_temporal_del_grafo.parent.mkdir(parents=True, exist_ok=True)
        with ruta_temporal_del_grafo.open("wb") as archivo:
            pickle.dump({"grafo": _grafo_de_prueba(), "altitudes": dict(ALTITUD_DEL_NODO)}, archivo)

        red = obtener_red_vial()

        assert red is not None
        assert red.altitud_del_nodo(2) == 3300.0
        assert red.buscar_camino(*_punto(1), *_punto(4)).camino == [1, 2, 3, 4]

    def test_el_grafo_se_lee_del_disco_una_sola_vez_por_proceso(self, ruta_temporal_del_grafo):
        """Cien megas de grafo en cada petición dejarían la API inservible."""
        ruta_temporal_del_grafo.parent.mkdir(parents=True, exist_ok=True)
        with ruta_temporal_del_grafo.open("wb") as archivo:
            pickle.dump({"grafo": _grafo_de_prueba(), "altitudes": {}}, archivo)

        assert obtener_red_vial() is obtener_red_vial()

    def test_sin_grafo_preparado_devuelve_nulo_en_vez_de_fallar(self, ruta_temporal_del_grafo):
        """El sistema tiene que arrancar sin la red y decir que no hay ruteo.

        Si esto lanzara una excepción, un despliegue sin el grafo —que pesa
        28 MB y no está en el repositorio— no arrancaría en absoluto.
        """
        assert not ruta_temporal_del_grafo.exists()

        assert obtener_red_vial() is None
