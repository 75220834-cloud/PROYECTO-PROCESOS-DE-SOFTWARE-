"""Pruebas de la función de Tobler y del esfuerzo acumulado.

La función de Tobler es de 1993 y está publicada con valores concretos, así que
estas pruebas no comprueban «lo que devuelve mi código»: comprueban que mi
código reproduce **la curva publicada**. Si algún día alguien toca las
constantes, estas pruebas lo cazan.
"""

import math

import pytest

from app.ia.tiempo_recorrido import (
    ALTITUD_DE_AVISO_M,
    PENDIENTE_OPTIMA,
    VELOCIDAD_MAXIMA_KMH,
    VELOCIDAD_MINIMA_KMH,
    calcular_pendiente,
    calcular_tramo_caminando,
    clasificar_esfuerzo,
    necesita_aviso_de_altitud,
    velocidad_de_tobler,
)

#: Valores de la curva publicada de Tobler (1993), redondeados a dos decimales.
#: Cada par es (pendiente, velocidad esperada en km/h).
CURVA_PUBLICADA = [
    (-0.05, 6.00),  # el máximo: una bajada suave, no el llano
    (0.00, 5.04),
    (0.05, 4.23),
    (0.10, 3.55),
    (0.20, 2.50),
    (0.30, 1.76),
    (-0.20, 3.55),  # bajar el 20 % es más rápido que subirlo
]


@pytest.mark.parametrize(("pendiente", "esperada"), CURVA_PUBLICADA)
def test_la_velocidad_reproduce_la_curva_publicada(pendiente: float, esperada: float):
    assert velocidad_de_tobler(pendiente) == pytest.approx(esperada, abs=0.01)


def test_la_velocidad_maxima_esta_en_la_bajada_suave_y_no_en_el_llano():
    """Es la parte contraintuitiva de la función y conviene tenerla fijada.

    Se camina más rápido bajando un 5 % que en terreno llano: el propio peso
    ayuda sin llegar a obligar a frenar.
    """
    en_la_optima = velocidad_de_tobler(PENDIENTE_OPTIMA)
    en_llano = velocidad_de_tobler(0.0)

    assert en_la_optima == pytest.approx(VELOCIDAD_MAXIMA_KMH, abs=0.001)
    assert en_la_optima > en_llano


def test_subir_y_bajar_la_misma_pendiente_no_cuesta_lo_mismo():
    """El ``+0,05`` de la fórmula rompe la simetría, y así debe ser."""
    assert velocidad_de_tobler(-0.15) > velocidad_de_tobler(0.15)


def test_bajar_el_veinte_por_ciento_va_igual_que_subir_el_diez():
    """La simetría real de la fórmula, que no es la que uno esperaría.

    El eje de simetría no está en el llano sino en −0,05, así que la pendiente
    de −0,20 y la de +0,10 quedan a la misma distancia del óptimo (0,15) y dan
    exactamente la misma velocidad. Esta prueba fija ese hecho porque es fácil
    romperlo al «corregir» la fórmula creyendo que el eje era el cero.
    """
    assert velocidad_de_tobler(-0.20) == pytest.approx(velocidad_de_tobler(0.10))


def test_una_pendiente_absurda_no_da_una_velocidad_de_cero():
    """Sin el suelo de velocidad, un tramo vertical daría un tiempo infinito."""
    assert velocidad_de_tobler(5.0) == pytest.approx(VELOCIDAD_MINIMA_KMH)
    assert velocidad_de_tobler(-5.0) == pytest.approx(VELOCIDAD_MINIMA_KMH)


def test_la_pendiente_de_una_distancia_nula_es_cero_y_no_revienta():
    """Un punto no tiene pendiente. Sin esta guarda habría división por cero."""
    assert calcular_pendiente(0.0, 100.0) == 0.0


def test_la_pendiente_es_el_cociente_desnivel_entre_distancia():
    assert calcular_pendiente(1000.0, 100.0) == pytest.approx(0.1)
    assert calcular_pendiente(1000.0, -100.0) == pytest.approx(-0.1)


# ---------------------------------------------------------------------------
# El tramo completo
# ---------------------------------------------------------------------------


def test_un_kilometro_en_llano_son_unos_doce_minutos():
    tramo = calcular_tramo_caminando(1000.0, 3250.0, 3250.0)

    assert tramo.pendiente == 0.0
    assert tramo.minutos == pytest.approx(11.9, abs=0.1)


def test_la_misma_distancia_cuesta_arriba_tarda_el_doble():
    """Es el argumento entero de usar Tobler en vez de velocidad constante."""
    llano = calcular_tramo_caminando(1000.0, 3250.0, 3250.0)
    cuesta = calcular_tramo_caminando(1000.0, 3250.0, 3450.0)  # +200 m, 20 %

    assert cuesta.minutos / llano.minutos == pytest.approx(2.0, abs=0.05)


def test_sin_altitudes_se_asume_llano_y_se_dice_asi():
    """Suponer llano tiene un error acotado; inventar un desnivel no."""
    tramo = calcular_tramo_caminando(1000.0)

    assert tramo.desnivel_m == 0.0
    assert tramo.pendiente == 0.0


def test_falta_una_sola_altitud_y_tambien_se_asume_llano():
    tramo = calcular_tramo_caminando(1000.0, 3250.0, None)

    assert tramo.desnivel_m == 0.0


def test_el_desnivel_es_destino_menos_origen():
    subida = calcular_tramo_caminando(1000.0, 3250.0, 3400.0)
    bajada = calcular_tramo_caminando(1000.0, 3400.0, 3250.0)

    assert subida.desnivel_m == pytest.approx(150.0)
    assert bajada.desnivel_m == pytest.approx(-150.0)


def test_un_tramo_vertical_se_marca_como_demasiado_empinado():
    tramo = calcular_tramo_caminando(100.0, 3250.0, 3400.0)  # 150 % de pendiente

    assert tramo.es_muy_empinado


def test_el_ascenso_al_huaytapallana_no_se_promete_en_tres_horas():
    """El caso que motiva todo el módulo, con los datos verificados del valle.

    Huancayo está a 3 250 m y el Huaytapallana a 5 557 m: son +2 307 m. A
    velocidad constante de 5 km/h, los 25 km darían cinco horas. Con Tobler no.
    """
    tramo = calcular_tramo_caminando(25_000.0, 3250.0, 5557.0)

    horas = tramo.minutos / 60

    assert horas > 6, "Tobler tiene que castigar el ascenso, no repartirlo"


# ---------------------------------------------------------------------------
# Esfuerzo del día y aviso de altitud
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("subida", "esperado"),
    [
        (0, "suave"),
        (299, "suave"),
        (300, "moderado"),
        (799, "moderado"),
        (800, "exigente"),
        (2307, "exigente"),
    ],
)
def test_el_esfuerzo_se_clasifica_por_la_subida_acumulada(subida: float, esperado: str):
    assert clasificar_esfuerzo(subida) == esperado


def test_bajar_no_descansa_las_piernas():
    """Sube y baja 400 m tres veces: acaba igual de alto y agotado.

    Se comprueba que la clasificación mira la subida acumulada y no el desnivel
    neto, que en este caso sería cero.
    """
    subida_acumulada = 400 * 3

    assert clasificar_esfuerzo(subida_acumulada) == "exigente"


def test_el_aviso_de_altitud_se_dispara_en_todo_el_valle():
    """Huancayo está a 3 250 m: por encima del umbral de 2 500 m."""
    assert necesita_aviso_de_altitud(3250)
    assert necesita_aviso_de_altitud(ALTITUD_DE_AVISO_M)
    assert not necesita_aviso_de_altitud(ALTITUD_DE_AVISO_M - 1)


def test_sin_altitud_conocida_no_se_avisa_de_nada():
    """Avisar sin saber sería tan malo como callar sabiendo."""
    assert not necesita_aviso_de_altitud(None)


def test_la_formula_es_la_publicada_y_no_una_tabla_de_valores():
    """Comprueba la fórmula contra su expresión matemática, punto por punto.

    Si alguien sustituyera la exponencial por una interpolación de la tabla de
    arriba, las pruebas anteriores seguirían pasando y esta no.
    """
    for pendiente in (-0.4, -0.13, 0.02, 0.17, 0.44):
        esperada = 6.0 * math.exp(-3.5 * abs(pendiente + 0.05))
        assert velocidad_de_tobler(pendiente) == pytest.approx(esperada, abs=1e-9)
