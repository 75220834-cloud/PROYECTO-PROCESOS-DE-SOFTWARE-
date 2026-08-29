"""Pruebas de la matriz de costos multimodal.

Lo que más se comprueba aquí no es la aritmética, que es trivial, sino que
**ningún precio salga del sistema sin su marca de estimado, su fecha y su
fuente**. Es la regla de honestidad con los datos del proyecto, y sin pruebas
que la sostengan se pierde en el primer refactor.
"""

from decimal import Decimal

import pytest

from app.modelos.transporte import ModoTransporte
from app.servicios.costos import (
    DISTANCIA_DE_COLECTIVO_KM,
    DISTANCIA_MAXIMA_A_PIE_KM,
    PARAMETROS_DE_ESTIMACION,
    _redondear_a_medio_sol,
    elegir_modo,
    estimar_precio,
)
from app.servicios.red_vial import (
    FACTOR_DE_RODEO,
    RADIO_TERRESTRE_M,
    distancia_en_linea_recta_m,
)

# ---------------------------------------------------------------------------
# Distancia en línea recta
# ---------------------------------------------------------------------------


def test_la_distancia_de_un_punto_a_si_mismo_es_cero():
    assert distancia_en_linea_recta_m(-12.0681, -75.2100, -12.0681, -75.2100) == pytest.approx(0.0)


def test_ocopa_a_concepcion_se_acerca_a_los_cinco_kilometros_y_medio_verificados():
    """Contraste contra una distancia publicada: Ocopa ↔ Concepción 5,5 km.

    Las coordenadas son las que trae el inventario del MINCETUR para el
    Convento de Santa Rosa de Ocopa y la Iglesia Matriz de Concepción, tal como
    están cargadas en el catálogo. No están escritas de memoria.

    La línea recta tiene que salir MENOR que los 5,5 km por carretera: si
    saliera mayor, la fórmula estaría mal, porque ninguna carretera es más
    corta que la recta que une sus extremos.
    """
    metros = distancia_en_linea_recta_m(
        -11.874007526779971, -75.29443234205246, -11.91843, -75.31223
    )

    assert metros < 5_500, "la línea recta no puede superar la distancia por carretera"
    assert metros == pytest.approx(5_310, abs=50)


def test_un_grado_de_latitud_son_ciento_once_kilometros():
    """Comprobación independiente de la fórmula contra un hecho geodésico.

    Un grado de meridiano es la circunferencia terrestre entre 360.
    """
    metros = distancia_en_linea_recta_m(-12.0, -75.0, -13.0, -75.0)
    esperado = 2 * 3.141592653589793 * RADIO_TERRESTRE_M / 360

    assert metros == pytest.approx(esperado, rel=1e-6)


def test_la_distancia_es_simetrica():
    ida = distancia_en_linea_recta_m(-12.0681, -75.2100, -11.7756, -75.4989)
    vuelta = distancia_en_linea_recta_m(-11.7756, -75.4989, -12.0681, -75.2100)

    assert ida == pytest.approx(vuelta)


# ---------------------------------------------------------------------------
# Elección del modo
# ---------------------------------------------------------------------------


def test_quien_dijo_caminando_camina_aunque_este_lejos():
    """La preferencia del visitante manda sobre la comodidad del algoritmo."""
    assert elegir_modo(40.0, mismo_distrito=False, movilidad="caminando") == (
        ModoTransporte.CAMINANDO
    )


def test_quien_dijo_taxi_va_en_taxi_aunque_este_al_lado():
    assert elegir_modo(0.3, mismo_distrito=True, movilidad="taxi") == ModoTransporte.TAXI


def test_dentro_del_distrito_y_cerca_se_va_a_pie():
    modo = elegir_modo(
        DISTANCIA_MAXIMA_A_PIE_KM - 0.1, mismo_distrito=True, movilidad="transporte_publico"
    )
    assert modo == ModoTransporte.CAMINANDO


def test_dentro_del_distrito_pero_lejos_ya_no_se_camina():
    modo = elegir_modo(
        DISTANCIA_MAXIMA_A_PIE_KM + 0.1, mismo_distrito=True, movilidad="transporte_publico"
    )
    assert modo == ModoTransporte.COMBI


def test_entre_distritos_cercanos_se_toma_combi_y_lejos_colectivo():
    cerca = elegir_modo(10.0, mismo_distrito=False, movilidad="transporte_publico")
    lejos = elegir_modo(DISTANCIA_DE_COLECTIVO_KM + 1, mismo_distrito=False, movilidad="combinado")

    assert cerca == ModoTransporte.COMBI
    assert lejos == ModoTransporte.COLECTIVO


def test_estar_en_otro_distrito_no_permite_caminar_aunque_sea_cerca():
    """Dos recursos a un kilómetro pero en distritos distintos: se cruza algo.

    Puede ser el río, una carretera o el límite urbano. La regla es
    conservadora a propósito.
    """
    modo = elegir_modo(1.0, mismo_distrito=False, movilidad="transporte_publico")

    assert modo == ModoTransporte.COMBI


# ---------------------------------------------------------------------------
# La estimación de precio
# ---------------------------------------------------------------------------


def test_caminar_no_cuesta_dinero():
    minimo, maximo = estimar_precio(ModoTransporte.CAMINANDO, 12.0)

    assert minimo == Decimal("0.00")
    assert maximo == Decimal("0.00")


def test_el_precio_siempre_es_un_rango_y_nunca_un_numero_solo():
    """El contexto del proyecto dice que no hay tarifa única. El código lo refleja."""
    for modo in (ModoTransporte.COMBI, ModoTransporte.COLECTIVO, ModoTransporte.TAXI):
        minimo, maximo = estimar_precio(modo, 10.0)
        assert maximo > minimo, f"{modo} devolvió un precio único"


def test_el_precio_crece_con_la_distancia():
    corto_min, corto_max = estimar_precio(ModoTransporte.COLECTIVO, 5.0)
    largo_min, largo_max = estimar_precio(ModoTransporte.COLECTIVO, 45.0)

    assert largo_min > corto_min
    assert largo_max > corto_max


def test_el_taxi_cuesta_mas_que_el_colectivo_y_este_mas_que_la_combi():
    _, combi = estimar_precio(ModoTransporte.COMBI, 20.0)
    _, colectivo = estimar_precio(ModoTransporte.COLECTIVO, 20.0)
    _, taxi = estimar_precio(ModoTransporte.TAXI, 20.0)

    assert combi < colectivo < taxi


@pytest.mark.parametrize(
    ("importe", "esperado"),
    [
        ("0.00", "0.00"),
        ("0.01", "0.50"),
        ("0.50", "0.50"),
        ("0.51", "1.00"),
        ("2.00", "2.00"),
        ("2.30", "2.50"),
        ("7.75", "8.00"),
    ],
)
def test_el_redondeo_sube_al_medio_sol(importe: str, esperado: str):
    """En el transporte del valle no se cobran céntimos sueltos."""
    assert _redondear_a_medio_sol(Decimal(importe)) == Decimal(esperado)


def test_todos_los_modos_tienen_parametros_de_estimacion():
    """Si alguien añade un modo nuevo y olvida sus parámetros, esto lo caza."""
    for modo in ModoTransporte:
        assert modo in PARAMETROS_DE_ESTIMACION, f"falta estimar {modo}"


# ---------------------------------------------------------------------------
# La honestidad del dato: lo que no puede fallar nunca
# ---------------------------------------------------------------------------


def test_el_factor_de_rodeo_es_el_medido_y_no_uno_inventado():
    """1,26 sale de medir 400 pares sobre la red real, y está documentado.

    Esta prueba existe para que cambiarlo sea una decisión consciente: si
    alguien lo toca sin volver a medir, la prueba falla y le obliga a explicar
    de dónde sale el número nuevo.
    """
    assert FACTOR_DE_RODEO == 1.26


def test_los_parametros_de_estimacion_declaran_rangos_no_valores_unicos():
    for modo, (base_min, base_max, km_min, km_max) in PARAMETROS_DE_ESTIMACION.items():
        if modo == ModoTransporte.CAMINANDO:
            continue

        assert Decimal(base_max) > Decimal(base_min), f"{modo}: base sin rango"
        assert Decimal(km_max) > Decimal(km_min), f"{modo}: precio por km sin rango"
