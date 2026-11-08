"""Pruebas del cálculo completo de un traslado: modo, distancia y precio.

``test_costos.py`` prueba las piezas sueltas —elegir el modo, aplicar la
fórmula, redondear al medio sol— sin tocar la base de datos. Aquí se prueba
``calcular_traslado``, que es la entrada que usa el optimizador de rutas y la
que junta las tres cosas.

## Las tres distinciones que se fijan aquí

**«Precio estimado» y «distancia estimada» no son lo mismo.** Un traslado a pie
llega con ``es_estimado=False`` aunque su distancia se haya calculado en línea
recta. No es una contradicción: ``es_estimado`` habla del **precio**, y que
caminar sea gratis no es una estimación, es un hecho. Lo que habla de la
distancia es ``origen_del_calculo``. Si alguien unificara los dos campos,
caminar empezaría a mostrarse con «aprox. S/ 0,00», que es absurdo.

**Una tarifa consultada manda sobre la fórmula.** Toda la estimación de precios
de este módulo son supuestos declarados del equipo. En cuanto alguien consulta
una tarifa real y la inserta en ``tarifa_transporte``, ese trayecto deja de
estimarse. Se comprueba que efectivamente deja de estimarse, y que lo que llega
al visitante es la fuente y la fecha de la tarifa y no el texto de la fórmula.

**Una tarifa vale en los dos sentidos.** Ir de Huancayo a El Tambo cuesta lo
mismo que volver, así que la clave de búsqueda es un conjunto y no un par
ordenado. Sin eso habría que cargar cada trayecto dos veces, y la mitad de las
vueltas se estimarían con la fórmula mientras la ida usa la tarifa real.

## Por qué la red vial va a mano

``obtener_red_vial()`` carga un grafo de 28 MB que no está en el repositorio:
en una máquina recién clonada devuelve ``None``. Una prueba que dependiera de
él pasaría aquí y se saltaría sola en la integración continua. Así que se
sustituye por el mismo grafo de cinco nodos de ``test_red_vial.py``, con las
longitudes puestas a mano.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modelos.itinerario import OrigenDelCalculo
from src.modelos.transporte import ModoTransporte, TarifaTransporte
from src.servicios import costos
from src.servicios.costos import (
    FUENTE_ESTIMADA,
    CostoDeTraslado,
    _tarifas_de_la_sesion,
    calcular_traslado,
    estimar_precio,
)
from src.servicios.red_vial import FACTOR_DE_RODEO, RedVial, distancia_en_linea_recta_m
from pruebas.conftest import necesita_base_de_datos

pytestmark = necesita_base_de_datos

HOY = date(2026, 9, 12)

# Tres nodos sobre el mismo paralelo, unidos en cadena:
#   1 ──110 m── 2 ──120 m── 3
LATITUD = -12.0680
LONGITUD = {1: -75.2100, 2: -75.2090, 3: -75.2080}
ALTITUD = {1: 3250.0, 2: 3260.0, 3: 3255.0}

#: Un punto a once metros del nodo 1: cae sobre el mismo nodo de la red.
LONGITUD_PEGADA_AL_UNO = LONGITUD[1] + 0.0001


def _red_de_tres_nodos() -> RedVial:
    import networkx as nx

    grafo = nx.MultiDiGraph()
    grafo.graph["crs"] = "epsg:4326"

    for nodo, longitud in LONGITUD.items():
        grafo.add_node(nodo, x=longitud, y=LATITUD)

    grafo.add_edge(1, 2, length=110.0)
    grafo.add_edge(2, 3, length=120.0)

    return RedVial(grafo, dict(ALTITUD))


@pytest.fixture
def con_red_vial(monkeypatch: pytest.MonkeyPatch) -> RedVial:
    """Sustituye el grafo real del valle por el de tres nodos."""
    red = _red_de_tres_nodos()
    monkeypatch.setattr(costos, "obtener_red_vial", lambda: red)
    return red


def _traslado(sesion: Session, **cambios) -> CostoDeTraslado:
    """Llama a calcular_traslado del nodo 1 al 3, con lo que se quiera cambiar."""
    argumentos = {
        "latitud_origen": LATITUD,
        "longitud_origen": LONGITUD[1],
        "altitud_origen": ALTITUD[1],
        "distrito_origen": "HUANCAYO",
        "latitud_destino": LATITUD,
        "longitud_destino": LONGITUD[3],
        "altitud_destino": ALTITUD[3],
        "distrito_destino": "HUANCAYO",
        "movilidad": "caminando",
        "fecha": HOY,
    }
    argumentos.update(cambios)

    return calcular_traslado(sesion, **argumentos)


def _tarifa(**cambios) -> TarifaTransporte:
    datos = {
        "distrito_origen": "HUANCAYO",
        "distrito_destino": "EL TAMBO",
        "modo": ModoTransporte.COMBI.value,
        # Deliberadamente no son multiplos de medio sol: la formula redondea
        # al medio sol, asi que asi una tarifa consultada no puede coincidir
        # con la estimacion por casualidad y falsear la comparacion.
        "precio_min_soles": Decimal("1.80"),
        "precio_max_soles": Decimal("2.30"),
        "duracion_estimada_min": 18,
        "fecha_referencia": date(2026, 8, 30),
        "fuente": "Tarifa consultada en paradero de la Av. Huancavelica",
        "es_estimado": False,
    }
    datos.update(cambios)
    return TarifaTransporte(**datos)


# ---------------------------------------------------------------------------
# El punto medio del rango
# ---------------------------------------------------------------------------


class TestPrecioMedio:
    def test_es_el_punto_medio_exacto_del_rango(self) -> None:
        """Se usa para sumar totales del día, nunca para mostrar al visitante.

        Enseñar «S/ 3,00» donde el dato es «entre 2 y 4» convertiría un rango
        honesto en una cifra que parece una tarifa.
        """
        costo = CostoDeTraslado(
            modo=ModoTransporte.COMBI,
            distancia_km=5.0,
            minutos=20,
            desnivel_m=0.0,
            subida_m=0.0,
            precio_min_soles=Decimal("2.00"),
            precio_max_soles=Decimal("4.00"),
            origen_del_calculo=OrigenDelCalculo.LINEA_RECTA,
            es_estimado=True,
            fuente="x",
            fecha_referencia=HOY,
            trazado=[],
        )

        assert costo.precio_medio_soles == Decimal("3.00")


# ---------------------------------------------------------------------------
# Caminar: gratis de verdad, distancia estimada o no
# ---------------------------------------------------------------------------


class TestTrasladoAPie:
    def test_caminar_cuesta_cero_y_eso_no_es_una_estimacion(self, sesion: Session) -> None:
        """La distinción entre precio estimado y distancia estimada.

        La distancia salió de una línea recta corregida, así que
        ``origen_del_calculo`` dice ``linea_recta``. El precio, en cambio, es
        exacto: caminar es gratis. Por eso ``es_estimado`` es False y la
        interfaz no escribe «aprox.» delante de un cero.
        """
        costo = _traslado(sesion, usar_red=False)

        assert costo.modo == ModoTransporte.CAMINANDO
        assert costo.precio_min_soles == Decimal("0.00")
        assert costo.precio_max_soles == Decimal("0.00")
        assert costo.es_estimado is False
        assert costo.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA

    def test_sin_grafo_la_caminata_se_corrige_por_el_factor_de_rodeo(self, sesion: Session) -> None:
        """Sin red no se finge que la distancia sea la recta: se corrige y se dice."""
        recta_km = distancia_en_linea_recta_m(LATITUD, LONGITUD[1], LATITUD, LONGITUD[3]) / 1000.0

        costo = _traslado(sesion, usar_red=False)

        assert costo.distancia_km == pytest.approx(round(recta_km * FACTOR_DE_RODEO, 2), abs=0.01)
        assert costo.trazado == [], "sin camino no hay nada que dibujar"

    def test_la_fuente_nombra_a_tobler_y_al_modelo_de_elevacion(self, sesion: Session) -> None:
        """Un tiempo de caminata sin decir de dónde sale es un número suelto."""
        costo = _traslado(sesion, usar_red=False)

        assert "Tobler" in costo.fuente
        assert "Copernicus" in costo.fuente

    def test_con_grafo_la_distancia_sale_de_la_red_y_se_marca_como_tal(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        """Los 230 m de las dos aristas, no los 217 de la línea recta."""
        costo = _traslado(sesion)

        assert costo.origen_del_calculo == OrigenDelCalculo.RED_VIAL
        assert costo.distancia_km == pytest.approx(0.23, abs=0.001)
        assert costo.trazado, "la ruta real sí se puede dibujar"
        assert costo.precio_min_soles == Decimal("0.00")

    def test_con_grafo_se_conserva_la_subida_acumulada(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        """Del nodo 1 al 3 se sube 10 m y se baja 5: la subida son 10, no 5."""
        costo = _traslado(sesion)

        assert costo.subida_m == 10.0
        assert costo.desnivel_m == 5.0

    def test_el_tiempo_de_caminata_se_devuelve_en_minutos_enteros(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        costo = _traslado(sesion)

        assert isinstance(costo.minutos, int)
        assert costo.minutos > 0


# ---------------------------------------------------------------------------
# La tabla de tarifas y su caché por sesión
# ---------------------------------------------------------------------------


class TestTablaDeTarifas:
    def test_se_lee_una_sola_vez_por_sesion(self, sesion: Session) -> None:
        """El arreglo de las 380 consultas por itinerario.

        ``construir_matriz`` llama a ``calcular_traslado`` N² veces. Antes cada
        llamada hacía su propia consulta; con la base en São Paulo eso costaba
        76 de los 85 segundos que tardaba un itinerario. Que las dos llamadas
        devuelvan **el mismo diccionario** es lo que prueba que ya no.
        """
        sesion.add(_tarifa())
        sesion.flush()

        primera = _tarifas_de_la_sesion(sesion)
        segunda = _tarifas_de_la_sesion(sesion)

        assert primera is segunda
        assert len(primera) == 1

    def test_los_dos_sentidos_del_trayecto_comparten_una_sola_entrada(
        self, sesion: Session
    ) -> None:
        """Ir cuesta lo mismo que volver, así que la clave es un conjunto.

        Las dos filas existen en la base —la restricción de unicidad las
        permite, porque para ella el par está ordenado—, pero la tabla en
        memoria las colapsa en una. Es lo que evita que la ida use la tarifa
        real y la vuelta la fórmula.
        """
        sesion.add(_tarifa(distrito_origen="HUANCAYO", distrito_destino="EL TAMBO"))
        sesion.add(_tarifa(distrito_origen="EL TAMBO", distrito_destino="HUANCAYO"))
        sesion.flush()

        assert len(sesion.scalars(select(TarifaTransporte)).all()) == 2
        assert len(_tarifas_de_la_sesion(sesion)) == 1

    def test_el_modo_si_distingue_tarifas_del_mismo_trayecto(self, sesion: Session) -> None:
        """La combi y el taxi al mismo sitio no cuestan lo mismo."""
        sesion.add(_tarifa(modo=ModoTransporte.COMBI.value))
        sesion.add(
            _tarifa(
                modo=ModoTransporte.TAXI.value,
                precio_min_soles=Decimal("12.00"),
                precio_max_soles=Decimal("15.00"),
            )
        )
        sesion.flush()

        assert len(_tarifas_de_la_sesion(sesion)) == 2


# ---------------------------------------------------------------------------
# Una tarifa consultada manda sobre la fórmula
# ---------------------------------------------------------------------------


class TestTarifaConsultada:
    def test_el_precio_sale_de_la_tarifa_y_no_de_la_formula(self, sesion: Session) -> None:
        sesion.add(_tarifa())
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.modo == ModoTransporte.COMBI
        assert costo.precio_min_soles == Decimal("1.80")
        assert costo.precio_max_soles == Decimal("2.30")

        de_la_formula = estimar_precio(ModoTransporte.COMBI, costo.distancia_km)
        assert (costo.precio_min_soles, costo.precio_max_soles) != de_la_formula

    def test_una_tarifa_consultada_deja_de_marcarse_como_estimada(self, sesion: Session) -> None:
        """Es la promesa del módulo: en cuanto hay dato real, se deja de estimar."""
        sesion.add(_tarifa(es_estimado=False))
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.es_estimado is False
        assert costo.fuente != FUENTE_ESTIMADA
        assert "paradero" in costo.fuente
        assert costo.fecha_referencia == date(2026, 8, 30)

    def test_una_tarifa_que_el_equipo_dedujo_sigue_marcada_como_estimada(
        self, sesion: Session
    ) -> None:
        """No es lo mismo un precio consultado que uno inferido, aunque los dos
        estén en la tabla. La bandera de la fila manda."""
        sesion.add(_tarifa(es_estimado=True, fuente="Deducido por el equipo"))
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.es_estimado is True

    def test_la_duracion_tambien_sale_de_la_tarifa(self, sesion: Session) -> None:
        """Quien publicó el precio sabe cuánto tarda mejor que una media."""
        sesion.add(_tarifa(duracion_estimada_min=18))
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.minutos == 18

    def test_la_tarifa_vale_tambien_en_sentido_contrario(self, sesion: Session) -> None:
        """Se carga Huancayo -> El Tambo y se consulta El Tambo -> Huancayo."""
        sesion.add(_tarifa(distrito_origen="HUANCAYO", distrito_destino="EL TAMBO"))
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_origen="EL TAMBO",
            distrito_destino="HUANCAYO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.precio_min_soles == Decimal("1.80")
        assert costo.es_estimado is False

    def test_la_distancia_sigue_saliendo_de_la_geometria_y_no_de_la_tarifa(
        self, sesion: Session
    ) -> None:
        """La tarifa dice el precio y el tiempo; la distancia no la sabe."""
        sesion.add(_tarifa())
        sesion.flush()

        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        recta_km = distancia_en_linea_recta_m(LATITUD, LONGITUD[1], LATITUD, LONGITUD[3]) / 1000.0
        assert costo.distancia_km == pytest.approx(round(recta_km * FACTOR_DE_RODEO, 2), abs=0.01)
        assert costo.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA

    def test_sin_tarifa_en_la_tabla_se_estima_y_se_dice(self, sesion: Session) -> None:
        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
            usar_red=False,
        )

        assert costo.es_estimado is True
        assert costo.fuente == FUENTE_ESTIMADA


# ---------------------------------------------------------------------------
# Dos puntos sobre el mismo nodo de la red
# ---------------------------------------------------------------------------


class TestMismoNodoDeLaRed:
    def test_la_distancia_rodada_no_se_corrige_cuando_cae_en_el_mismo_nodo(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        """Once metros sobre la red: la línea recta es la distancia correcta.

        Son dos distritos distintos a once metros —ocurre en los límites
        distritales del valle, que parten calles por la mitad—. No hay camino
        que buscar porque los dos puntos caen en el mismo nodo, pero sí hay
        cobertura: aplicarle el factor de rodeo inflaría la distancia un 26 %
        y marcaría el tramo como estimado sin que lo sea.
        """
        recta_km = (
            distancia_en_linea_recta_m(LATITUD, LONGITUD[1], LATITUD, LONGITUD_PEGADA_AL_UNO)
            / 1000.0
        )

        costo = _traslado(
            sesion,
            longitud_destino=LONGITUD_PEGADA_AL_UNO,
            altitud_destino=ALTITUD[1],
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
        )

        assert costo.modo == ModoTransporte.COMBI
        assert costo.origen_del_calculo == OrigenDelCalculo.RED_VIAL
        assert costo.distancia_km == pytest.approx(round(recta_km, 2), abs=0.001)
        assert costo.trazado == [], "no hay tramo que dibujar entre un punto y sí mismo"


# ---------------------------------------------------------------------------
# La distancia rodada sobre la red
# ---------------------------------------------------------------------------


class TestDistanciaPorCarretera:
    def test_un_traslado_motorizado_usa_la_longitud_real_de_las_vias(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        """Los 230 m de las dos aristas, no los 217 de la recta corregida.

        El grafo se descargó con ``network_type="all"``, así que contiene las
        carreteras además de los caminos peatonales y sirve igual para la combi
        que para la caminata.
        """
        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
        )

        assert costo.modo == ModoTransporte.COMBI
        assert costo.origen_del_calculo == OrigenDelCalculo.RED_VIAL
        assert costo.distancia_km == pytest.approx(0.23, abs=0.001)
        assert costo.trazado, "la ruta rodada también se dibuja en el mapa"

    def test_en_vehiculo_el_desnivel_no_cuenta_como_esfuerzo(
        self, sesion: Session, con_red_vial: RedVial
    ) -> None:
        """La cuesta la sube el motor, no las piernas del visitante.

        El desnivel se informa igual —es información del terreno— pero la
        subida acumulada, que es la que clasifica el esfuerzo del día, es cero.
        """
        costo = _traslado(
            sesion,
            distrito_destino="EL TAMBO",
            movilidad="transporte_publico",
        )

        assert costo.desnivel_m == 5.0
        assert costo.subida_m == 0.0
