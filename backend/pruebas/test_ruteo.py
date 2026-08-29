"""Pruebas del optimizador de itinerarios y de su alternativa por reglas.

Las restricciones que se comprueban aquí son las cuatro que exige el plan de
trabajo del Incremento 4:

1. horario de atención de cada recurso,
2. hora de inicio y fin del día,
3. duración de la visita,
4. presupuesto de traslado.

Se usan candidatos sintéticos y una matriz escrita a mano, sin base de datos ni
grafo. No es por comodidad: es que una prueba que dependa de los 295 recursos
reales no comprueba el algoritmo, comprueba los datos. Aquí se controla cada
número para que, cuando falle, se sepa exactamente qué se rompió.
"""

from datetime import time
from decimal import Decimal

import pytest

from app.modelos.itinerario import OrigenDelCalculo
from app.modelos.transporte import ModoTransporte
from app.servicios.costos import CostoDeTraslado
from app.servicios.ruteo import (
    DURACION_DE_RESERVA_MIN,
    DURACION_PREDETERMINADA_MIN,
    PARADAS_MAXIMAS_POR_RITMO,
    CandidatoARutear,
    _a_hora,
    _a_minutos,
    _es_visitable_ese_dia,
    _ventana_de_atencion,
    armar_horario,
    resolver_con_ortools,
    resolver_con_reglas,
)

FECHA = __import__("datetime").date(2026, 9, 12)

INICIO_DIA = 8 * 60  # 08:00
FIN_DIA = 18 * 60  # 18:00

SIN_LIMITE = Decimal("10000")

#: Segundos de busqueda en las pruebas. Los problemas sinteticos tienen seis
#: nodos: OR-Tools converge al instante y agotar los 5 segundos de produccion
#: solo alargaria la suite. La estrategia de busqueda es la misma.
SEGUNDOS_EN_PRUEBAS = 1


def candidato(
    identificador: int,
    afinidad: int,
    *,
    duracion: int = 60,
    distrito: str = "HUANCAYO",
    apertura: time | None = None,
    cierre: time | None = None,
) -> CandidatoARutear:
    """Un candidato sintético. Las coordenadas no se usan: la matriz es fija."""
    return CandidatoARutear(
        recurso_id=identificador,
        nombre=f"Recurso {identificador}",
        distrito=distrito,
        categoria="2. MANIFESTACIONES CULTURALES",
        latitud=-12.0 - identificador / 100,
        longitud=-75.2 - identificador / 100,
        altitud_m=3250.0,
        puntaje_relativo=afinidad,
        duracion_visita_min=duracion,
        apertura=apertura,
        cierre=cierre,
    )


def traslado(minutos: int, soles: str = "2.00") -> CostoDeTraslado:
    """Un traslado sintético con el tiempo y el precio que se le indiquen."""
    return CostoDeTraslado(
        modo=ModoTransporte.COMBI,
        distancia_km=minutos / 3,
        minutos=minutos,
        desnivel_m=0.0,
        subida_m=0.0,
        precio_min_soles=Decimal(soles),
        precio_max_soles=Decimal(soles),
        origen_del_calculo=OrigenDelCalculo.RED_VIAL,
        es_estimado=True,
        fuente="prueba",
        fecha_referencia=FECHA,
        trazado=[],
    )


def matriz_uniforme(tamano: int, minutos: int, soles: str = "2.00"):
    """Matriz donde ir de cualquier sitio a cualquier otro cuesta lo mismo."""
    return [
        [None if i == j else traslado(minutos, soles) for j in range(tamano)] for i in range(tamano)
    ]


# ---------------------------------------------------------------------------
# Conversión de horas
# ---------------------------------------------------------------------------


def test_las_horas_van_y_vuelven_a_minutos_sin_perderse():
    assert _a_minutos(time(8, 0)) == 480
    assert _a_minutos(time(18, 30)) == 1110
    assert _a_hora(480) == time(8, 0)
    assert _a_hora(1110) == time(18, 30)


def test_pasarse_de_medianoche_se_topa_en_lugar_de_desbordar():
    """Un itinerario que llegue aquí tiene un error de cálculo detrás.

    Se prefiere que se vea un 23:59 imposible antes que un 00:30 que parezca
    razonable siendo del día siguiente.
    """
    assert _a_hora(25 * 60) == time(23, 59)
    assert _a_hora(-30) == time(0, 0)


# ---------------------------------------------------------------------------
# Ventanas de atención
# ---------------------------------------------------------------------------


def test_sin_horario_conocido_la_ventana_es_el_dia_entero():
    """No saber cuándo abre no es lo mismo que saber que abre siempre.

    Pero es lo único honesto que se puede hacer: inventar un horario sería
    peor, y descartarlo dejaría el catálogo entero fuera.
    """
    apertura, ultimo = _ventana_de_atencion(candidato(1, 50), INICIO_DIA, FIN_DIA)

    assert (apertura, ultimo) == (INICIO_DIA, FIN_DIA)


def test_la_ventana_resta_la_duracion_de_la_visita_al_cierre():
    """Llegar a un museo diez minutos antes de que cierre no es visitarlo."""
    con_horario = candidato(1, 50, duracion=90, apertura=time(9, 0), cierre=time(17, 0))

    apertura, ultimo = _ventana_de_atencion(con_horario, INICIO_DIA, FIN_DIA)

    assert apertura == 9 * 60
    assert ultimo == 17 * 60 - 90  # hay que empezar a las 15:30 como muy tarde


def test_un_recurso_que_abre_menos_de_lo_que_dura_la_visita_no_es_visitable():
    imposible = candidato(1, 50, duracion=120, apertura=time(10, 0), cierre=time(11, 0))

    assert not _es_visitable_ese_dia(imposible, INICIO_DIA, FIN_DIA)


def test_un_recurso_con_horario_holgado_si_es_visitable():
    holgado = candidato(1, 50, duracion=60, apertura=time(9, 0), cierre=time(17, 0))

    assert _es_visitable_ese_dia(holgado, INICIO_DIA, FIN_DIA)


def test_un_recurso_que_solo_abre_de_noche_no_es_visitable_de_dia():
    """Su ventana no se solapa con la jornada de 8 a 18."""
    nocturno = candidato(1, 50, duracion=60, apertura=time(20, 0), cierre=time(23, 0))

    assert not _es_visitable_ese_dia(nocturno, INICIO_DIA, FIN_DIA)


# ---------------------------------------------------------------------------
# Restricción 4 — el presupuesto de traslado
# ---------------------------------------------------------------------------


def test_las_reglas_no_se_pasan_del_presupuesto():
    candidatos = [candidato(i, 100 - i * 10) for i in range(6)]
    # Cada traslado cuesta 5 soles y solo hay 12: caben dos traslados.
    matriz = matriz_uniforme(6, minutos=20, soles="5.00")

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 6, Decimal("12.00"))

    gastado = sum(matriz[orden[i]][orden[i + 1]].precio_max_soles for i in range(len(orden) - 1))

    assert gastado <= Decimal("12.00")
    assert len(orden) == 3  # el primero es gratis, más dos traslados


def test_el_optimizador_no_se_pasa_del_presupuesto():
    candidatos = [candidato(i, 100 - i * 10) for i in range(6)]
    matriz = matriz_uniforme(6, minutos=20, soles="5.00")

    orden = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 6, Decimal("12.00"), SEGUNDOS_EN_PRUEBAS
    )

    assert orden is not None
    gastado = sum(matriz[orden[i]][orden[i + 1]].precio_max_soles for i in range(len(orden) - 1))

    assert gastado <= Decimal("12.00")


def test_un_presupuesto_de_cero_deja_solo_la_primera_parada():
    candidatos = [candidato(i, 50) for i in range(4)]
    matriz = matriz_uniforme(4, minutos=20, soles="3.00")

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 4, Decimal("0.00"))

    assert orden == [0]


# ---------------------------------------------------------------------------
# Restricciones 1 a 3 — horarios, jornada y duración
# ---------------------------------------------------------------------------


def test_las_reglas_no_programan_nada_fuera_del_horario_de_atencion():
    """La verificación de horarios que pide el plan, comprobada de verdad.

    El recurso 1 cierra a las 10:00 y la visita dura una hora, así que llegando
    a las 9:20 (8:00 + visita de 60 + traslado de 20) no cabe y hay que
    descartarlo.
    """
    candidatos = [
        candidato(0, 100),
        candidato(1, 90, apertura=time(9, 0), cierre=time(10, 0)),
        candidato(2, 80, apertura=time(9, 0), cierre=time(18, 0)),
    ]
    matriz = matriz_uniforme(3, minutos=20)

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 3, SIN_LIMITE)

    assert 1 not in orden, "se programó una visita que no cabía antes del cierre"
    assert orden == [0, 2]


def test_el_optimizador_no_programa_nada_fuera_del_horario_de_atencion():
    candidatos = [
        candidato(0, 100),
        candidato(1, 90, apertura=time(9, 0), cierre=time(10, 0)),
        candidato(2, 80, apertura=time(9, 0), cierre=time(18, 0)),
    ]
    matriz = matriz_uniforme(3, minutos=20)

    orden = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 3, SIN_LIMITE, SEGUNDOS_EN_PRUEBAS
    )

    assert orden is not None
    assert 1 not in orden


def test_ninguna_parada_termina_despues_de_la_hora_de_fin_del_dia():
    """Restricción 2: la jornada tiene un final y no se estira."""
    candidatos = [candidato(i, 100 - i) for i in range(8)]
    matriz = matriz_uniforme(8, minutos=60)  # una hora entre cada parada

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 8, SIN_LIMITE)
    traslados = [matriz[orden[i]][orden[i + 1]] for i in range(len(orden) - 1)]

    paradas, _ = armar_horario(candidatos, orden, traslados, INICIO_DIA, FIN_DIA)

    for parada in paradas:
        assert _a_minutos(parada.hora_salida) <= FIN_DIA


def test_la_duracion_de_la_visita_se_respeta_en_cada_parada():
    """Restricción 3: si la visita dura 90 minutos, la parada dura 90 minutos."""
    candidatos = [candidato(0, 100, duracion=90), candidato(1, 90, duracion=45)]
    matriz = matriz_uniforme(2, minutos=30)

    orden = [0, 1]
    traslados = [matriz[0][1]]

    paradas, _ = armar_horario(candidatos, orden, traslados, INICIO_DIA, FIN_DIA)

    duraciones = [_a_minutos(p.hora_salida) - _a_minutos(p.hora_llegada) for p in paradas]

    assert duraciones == [90, 45]


def test_el_horario_encadena_visita_mas_traslado_sin_solaparse():
    candidatos = [candidato(i, 100 - i, duracion=60) for i in range(3)]
    matriz = matriz_uniforme(3, minutos=30)

    orden = [0, 1, 2]
    traslados = [matriz[0][1], matriz[1][2]]

    paradas, _ = armar_horario(candidatos, orden, traslados, INICIO_DIA, FIN_DIA)

    assert [p.hora_llegada for p in paradas] == [time(8, 0), time(9, 30), time(11, 0)]
    assert [p.hora_salida for p in paradas] == [time(9, 0), time(10, 30), time(12, 0)]


def test_si_se_llega_antes_de_que_abra_se_espera_y_no_se_entra():
    """El recurso abre a las 11:00 y se llegaría a las 9:30."""
    candidatos = [
        candidato(0, 100, duracion=60),
        candidato(1, 90, duracion=60, apertura=time(11, 0), cierre=time(17, 0)),
    ]
    matriz = matriz_uniforme(2, minutos=30)

    paradas, _ = armar_horario(candidatos, [0, 1], [matriz[0][1]], INICIO_DIA, FIN_DIA)

    assert paradas[1].hora_llegada == time(11, 0)


def test_al_recortar_por_falta_de_tiempo_se_avisa():
    """La honestidad de la segunda pasada: si no cabe, se dice."""
    candidatos = [candidato(i, 100 - i, duracion=60) for i in range(6)]
    matriz = matriz_uniforme(6, minutos=200)  # traslados larguísimos

    orden = [0, 1, 2, 3, 4, 5]
    traslados = [matriz[orden[i]][orden[i + 1]] for i in range(5)]

    paradas, avisos = armar_horario(candidatos, orden, traslados, INICIO_DIA, FIN_DIA)

    assert len(paradas) < len(orden)
    assert avisos, "se recortaron paradas sin decírselo a nadie"
    assert "quitaron" in avisos[0]


# ---------------------------------------------------------------------------
# El objetivo: maximizar la afinidad
# ---------------------------------------------------------------------------


def test_el_optimizador_prefiere_los_recursos_de_mayor_afinidad():
    """Con todo lo demás igual, se queda con los que más encajan."""
    candidatos = [
        candidato(0, 100),
        candidato(1, 10),
        candidato(2, 95),
        candidato(3, 5),
        candidato(4, 90),
    ]
    matriz = matriz_uniforme(5, minutos=30)

    # Solo caben tres paradas: tiene que elegir las de 100, 95 y 90.
    orden = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 3, SIN_LIMITE, SEGUNDOS_EN_PRUEBAS
    )

    assert orden is not None
    elegidos = {candidatos[i].puntaje_relativo for i in orden}

    assert elegidos == {100, 95, 90}


def test_el_optimizador_recoge_al_menos_tanta_afinidad_como_las_reglas():
    """Es la razón de ser del optimizador. Si no, sobra.

    Se construye un caso donde el vecino más cercano se equivoca: el recurso
    más cercano al inicio es el de menor afinidad.
    """
    candidatos = [candidato(i, [100, 5, 95, 90][i]) for i in range(4)]

    # El 1 (afinidad 5) está pegado al 0; los demás, lejos.
    matriz = matriz_uniforme(4, minutos=40)
    for i in range(4):
        if i != 1:
            matriz[i][1] = traslado(5)
            matriz[1][i] = traslado(5)

    con_modelo = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 2, SIN_LIMITE, SEGUNDOS_EN_PRUEBAS
    )
    con_reglas = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 2, SIN_LIMITE)

    assert con_modelo is not None

    afinidad_modelo = sum(candidatos[i].puntaje_relativo for i in con_modelo)
    afinidad_reglas = sum(candidatos[i].puntaje_relativo for i in con_reglas)

    assert afinidad_modelo >= afinidad_reglas
    # El vecino más cercano cae en la trampa y se lleva el de afinidad 5.
    assert 1 in con_reglas
    assert 1 not in con_modelo


def test_el_dia_no_obliga_a_volver_a_la_primera_parada():
    """Regresion: el recorrido es abierto, no un circuito cerrado.

    OR-Tools esta pensado para vehiculos de reparto, que vuelven al almacen. Si
    se modela el dia como circuito cerrado, el regreso a la primera parada
    consume presupuesto y tiempo, y el optimizador entrega menos paradas de las
    que caben. Paso de verdad: con la preferencia de prueba en taxi, devolvia
    UNA parada mientras el vecino mas cercano encontraba TRES con el mismo
    dinero.

    Aqui el presupuesto da exactamente para dos traslados de ida. Si el modelo
    cobrara la vuelta, solo cabria uno.
    """
    candidatos = [candidato(i, 100 - i * 10) for i in range(4)]
    matriz = matriz_uniforme(4, minutos=20, soles="10.00")

    orden = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 4, Decimal("20.00"), SEGUNDOS_EN_PRUEBAS
    )

    assert orden is not None
    assert len(orden) == 3, (
        f"se esperaban 3 paradas (2 traslados de S/10 con S/20), y salieron {len(orden)}: "
        "el modelo esta cobrando el regreso a la primera parada"
    )


def test_el_optimizador_nunca_entrega_menos_paradas_que_las_reglas_con_el_mismo_dinero():
    """El optimizador no puede quedar por debajo de su propia linea base.

    Si lo hace, no es un optimizador: es un rodeo caro para llegar a un
    resultado peor. Esta prueba compara los dos caminos sobre el mismo problema
    y el mismo presupuesto.
    """
    candidatos = [candidato(i, 100 - i * 5) for i in range(6)]
    matriz = matriz_uniforme(6, minutos=25, soles="8.00")

    presupuesto = Decimal("24.00")  # da para tres traslados

    con_modelo = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 6, presupuesto, SEGUNDOS_EN_PRUEBAS
    )
    con_reglas = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 6, presupuesto)

    assert con_modelo is not None
    assert len(con_modelo) >= len(con_reglas)

    afinidad_modelo = sum(candidatos[i].puntaje_relativo for i in con_modelo)
    afinidad_reglas = sum(candidatos[i].puntaje_relativo for i in con_reglas)

    assert afinidad_modelo >= afinidad_reglas


# ---------------------------------------------------------------------------
# La alternativa por reglas, por sí misma
# ---------------------------------------------------------------------------


def test_las_reglas_van_siempre_al_mas_cercano():
    candidatos = [candidato(i, 50) for i in range(4)]
    matriz = matriz_uniforme(4, minutos=60)

    # Cadena: 0 -> 2 -> 1 -> 3, cada uno el más cercano del anterior.
    matriz[0][2] = traslado(5)
    matriz[2][1] = traslado(5)
    matriz[1][3] = traslado(5)

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 4, SIN_LIMITE)

    assert orden == [0, 2, 1, 3]


def test_las_reglas_no_repiten_ninguna_parada():
    candidatos = [candidato(i, 50) for i in range(5)]
    matriz = matriz_uniforme(5, minutos=10)

    orden = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, 5, SIN_LIMITE)

    assert len(orden) == len(set(orden))


def test_el_optimizador_no_repite_ninguna_parada():
    candidatos = [candidato(i, 50 + i) for i in range(6)]
    matriz = matriz_uniforme(6, minutos=10)

    orden = resolver_con_ortools(
        candidatos, matriz, INICIO_DIA, FIN_DIA, 6, SIN_LIMITE, SEGUNDOS_EN_PRUEBAS
    )

    assert orden is not None
    assert len(orden) == len(set(orden))


def test_ninguno_de_los_dos_caminos_pasa_del_tope_de_paradas():
    """El tope viene del ritmo que eligió el visitante."""
    candidatos = [candidato(i, 50 + i) for i in range(10)]
    matriz = matriz_uniforme(10, minutos=5)

    for tope in (1, 3, 5):
        con_reglas = resolver_con_reglas(candidatos, matriz, INICIO_DIA, FIN_DIA, tope, SIN_LIMITE)
        con_modelo = resolver_con_ortools(
            candidatos, matriz, INICIO_DIA, FIN_DIA, tope, SIN_LIMITE, SEGUNDOS_EN_PRUEBAS
        )

        assert len(con_reglas) <= tope
        assert con_modelo is not None
        assert len(con_modelo) <= tope


def test_las_reglas_con_un_solo_candidato_devuelven_ese_candidato():
    orden = resolver_con_reglas([candidato(0, 100)], [[None]], INICIO_DIA, FIN_DIA, 5, SIN_LIMITE)

    assert orden == [0]


def test_las_reglas_sin_candidatos_no_revientan():
    assert resolver_con_reglas([], [], INICIO_DIA, FIN_DIA, 5, SIN_LIMITE) == []


# ---------------------------------------------------------------------------
# Duración de visita y ritmo
# ---------------------------------------------------------------------------


def test_cada_categoria_del_mincetur_tiene_su_duracion_por_defecto():
    """Si el MINCETUR añade una categoría, esto obliga a decidir su duración."""
    categorias_del_catalogo = {
        "1. SITIOS NATURALES",
        "2. MANIFESTACIONES CULTURALES",
        "3. FOLCLORE",
        "4. REALIZACIONES TÉCNICAS, CIENTÍFICAS Y ARTÍSTICAS CONTEMPORÁNEAS",
        "5. ACONTECIMIENTOS PROGRAMADOS",
    }

    assert categorias_del_catalogo == set(DURACION_PREDETERMINADA_MIN)


def test_las_duraciones_por_defecto_son_todas_positivas_y_razonables():
    for categoria, minutos in DURACION_PREDETERMINADA_MIN.items():
        assert 15 <= minutos <= 240, f"{categoria}: {minutos} min no es una visita"

    assert 15 <= DURACION_DE_RESERVA_MIN <= 240


@pytest.mark.parametrize("ritmo", ["relajado", "moderado", "intenso"])
def test_cada_ritmo_tiene_su_tope_de_paradas(ritmo: str):
    assert ritmo in PARADAS_MAXIMAS_POR_RITMO
    assert PARADAS_MAXIMAS_POR_RITMO[ritmo] >= 1


def test_un_ritmo_mas_intenso_permite_mas_paradas():
    assert (
        PARADAS_MAXIMAS_POR_RITMO["relajado"]
        < PARADAS_MAXIMAS_POR_RITMO["moderado"]
        < PARADAS_MAXIMAS_POR_RITMO["intenso"]
    )
