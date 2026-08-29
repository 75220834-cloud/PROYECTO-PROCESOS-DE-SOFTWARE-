"""Pruebas del calendario festivo y del cálculo de la Pascua.

Estas pruebas son la red de seguridad de un cálculo que nadie va a revisar a
mano cada año. Si el algoritmo se rompe, la predicción de afluencia empieza a
mentir en silencio: dirá que un día cualquiera es Semana Santa, o al revés.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.ia.calendario import (
    DIA_DE_LA_FERIA_DOMINICAL,
    TipoFestividad,
    calcular_domingo_de_pascua,
    calcular_fiestas_moviles,
    calendario_del_anio,
    dias_hasta_la_festividad_mas_cercana,
    es_feriado_nacional,
    festividades_en,
    hay_feria_dominical,
    temporada_de,
)

#: Domingos de Pascua publicados por la Iglesia católica. Son la verdad contra
#: la que se compara: no se calculan aquí, se copian.
PASCUAS_CONOCIDAS = {
    2020: date(2020, 4, 12),
    2021: date(2021, 4, 4),
    2022: date(2022, 4, 17),
    2023: date(2023, 4, 9),
    2024: date(2024, 3, 31),
    2025: date(2025, 4, 20),
    2026: date(2026, 4, 5),
    2027: date(2027, 3, 28),
    2028: date(2028, 4, 16),
    2029: date(2029, 4, 1),
    2030: date(2030, 4, 21),
    2035: date(2035, 3, 25),
}


class TestCalculoDePascua:
    @pytest.mark.parametrize(("anio", "esperada"), sorted(PASCUAS_CONOCIDAS.items()))
    def test_coincide_con_las_fechas_oficiales(self, anio: int, esperada: date):
        assert calcular_domingo_de_pascua(anio) == esperada

    def test_la_pascua_de_2026_es_el_5_de_abril(self):
        """La comprobación que pide explícitamente el plan de trabajo."""
        assert calcular_domingo_de_pascua(2026) == date(2026, 4, 5)

    def test_siempre_cae_en_domingo(self):
        """Comprobación estructural sobre un siglo entero.

        No hace falta conocer la fecha exacta de cada año para saber que el
        Domingo de Pascua tiene que caer en domingo. Si el algoritmo se
        desviara, esto lo detectaría sin tener que copiar cien fechas.
        """
        for anio in range(2000, 2101):
            assert calcular_domingo_de_pascua(anio).weekday() == 6, f"falla en {anio}"

    def test_siempre_cae_entre_el_22_de_marzo_y_el_25_de_abril(self):
        """Son los límites matemáticos del computus gregoriano."""
        for anio in range(2000, 2101):
            pascua = calcular_domingo_de_pascua(anio)
            assert date(anio, 3, 22) <= pascua <= date(anio, 4, 25), f"falla en {anio}"


class TestFiestasMoviles:
    def test_semana_santa_de_2026_va_del_29_de_marzo_al_5_de_abril(self):
        """Del Domingo de Ramos al Domingo de Pascua."""
        semana_santa = next(f for f in calcular_fiestas_moviles(2026) if f.nombre == "Semana Santa")

        assert semana_santa.fecha_inicio == date(2026, 3, 29)
        assert semana_santa.fecha_fin == date(2026, 4, 5)

    def test_los_carnavales_caen_49_dias_antes_de_pascua(self):
        carnavales = next(f for f in calcular_fiestas_moviles(2026) if f.nombre == "Carnavales")

        assert (calcular_domingo_de_pascua(2026) - carnavales.fecha_inicio).days == 49
        assert carnavales.fecha_inicio == date(2026, 2, 15)

    def test_corpus_christi_cae_60_dias_despues_de_pascua(self):
        corpus = next(f for f in calcular_fiestas_moviles(2026) if f.nombre == "Corpus Christi")

        assert (corpus.fecha_inicio - calcular_domingo_de_pascua(2026)).days == 60
        assert corpus.fecha_inicio == date(2026, 6, 4)

    def test_todas_vienen_marcadas_como_moviles(self):
        """Es lo que distingue las que hay que recalcular cada año."""
        assert all(f.es_movil for f in calcular_fiestas_moviles(2026))

    def test_cambian_de_fecha_de_un_ano_a_otro(self):
        """Si salieran iguales, es que alguien las escribió fijas."""
        de_2026 = {f.nombre: f.fecha_inicio for f in calcular_fiestas_moviles(2026)}
        de_2027 = {f.nombre: f.fecha_inicio for f in calcular_fiestas_moviles(2027)}

        for nombre, fecha in de_2026.items():
            assert de_2027[nombre] != fecha, f"{nombre} no se movió entre 2026 y 2027"

    def test_funciona_en_un_ano_bisiesto(self):
        """Caso borde: 2028 es bisiesto y los Carnavales tocan el 29 de febrero."""
        carnavales = next(f for f in calcular_fiestas_moviles(2028) if f.nombre == "Carnavales")

        assert carnavales.fecha_fin == date(2028, 2, 29)


class TestFiestasFijas:
    def test_la_huaconada_de_mito_es_del_1_al_3_de_enero(self):
        huaconada = next(f for f in calendario_del_anio(2026) if f.nombre == "Huaconada de Mito")

        assert huaconada.fecha_inicio == date(2026, 1, 1)
        assert huaconada.fecha_fin == date(2026, 1, 3)
        assert huaconada.distritos == ("MITO",)
        assert not huaconada.es_movil

    def test_la_fiesta_de_santiago_afecta_a_todo_el_valle(self):
        """Se celebra en cerca de 28 distritos: no se limita a ninguno."""
        santiago = next(f for f in calendario_del_anio(2026) if f.nombre == "Fiesta de Santiago")

        assert santiago.distritos == ()
        assert santiago.afecta_al_distrito("HUANCAYO")
        assert santiago.afecta_al_distrito("JAUJA")

    def test_toda_fiesta_declara_su_fuente(self):
        """Sin fuente documentada, una fiesta es un rumor."""
        for festividad in calendario_del_anio(2026):
            assert festividad.fuente, f"{festividad.nombre} no declara su fuente"


class TestConsultasSobreUnDia:
    def test_detecta_que_un_dia_cae_en_semana_santa(self):
        # 1 de abril de 2026: Miércoles Santo.
        activas = [f.nombre for f in festividades_en(date(2026, 4, 1))]
        assert "Semana Santa" in activas

    def test_un_dia_cualquiera_no_tiene_fiestas(self):
        # 12 de mayo de 2026: martes sin nada.
        assert festividades_en(date(2026, 5, 12)) == []

    def test_filtra_las_fiestas_por_distrito(self):
        # La Huaconada es solo de Mito.
        en_mito = [f.nombre for f in festividades_en(date(2026, 1, 2), "MITO")]
        en_jauja = [f.nombre for f in festividades_en(date(2026, 1, 2), "JAUJA")]

        assert "Huaconada de Mito" in en_mito
        assert "Huaconada de Mito" not in en_jauja

    def test_la_feria_dominical_es_los_domingos_en_huancayo(self):
        # 10 de mayo de 2026 es domingo.
        domingo = date(2026, 5, 10)
        assert domingo.weekday() == DIA_DE_LA_FERIA_DOMINICAL

        assert hay_feria_dominical(domingo, "HUANCAYO") is True
        assert hay_feria_dominical(domingo, "JAUJA") is False
        assert hay_feria_dominical(date(2026, 5, 11), "HUANCAYO") is False

    def test_reconoce_los_feriados_nacionales(self):
        assert es_feriado_nacional(date(2026, 7, 28)) is True  # Fiestas Patrias
        assert es_feriado_nacional(date(2026, 12, 25)) is True  # Navidad
        assert es_feriado_nacional(date(2026, 5, 12)) is False

    def test_cuenta_los_dias_hasta_la_fiesta_mas_cercana(self):
        # Corpus Christi 2026 es el 4 de junio.
        assert dias_hasta_la_festividad_mas_cercana(date(2026, 6, 4)) == 0
        assert dias_hasta_la_festividad_mas_cercana(date(2026, 6, 2)) == 2

    def test_mira_tambien_el_ano_siguiente(self):
        """Caso borde: un 31 de diciembre debe encontrar el Año Nuevo."""
        assert dias_hasta_la_festividad_mas_cercana(date(2026, 12, 31)) == 1

    def test_mira_tambien_el_ano_anterior(self):
        """Caso borde: un 4 de enero debe encontrar la Huaconada recién pasada."""
        assert dias_hasta_la_festividad_mas_cercana(date(2026, 1, 4)) == 1


class TestTemporadas:
    @pytest.mark.parametrize(
        ("mes", "esperada"),
        [
            (7, "alta"),
            (8, "alta"),
            (1, "media"),
            (2, "media"),
            (12, "media"),
            (3, "baja"),
            (5, "baja"),
            (9, "baja"),
            (10, "baja"),
        ],
    )
    def test_clasifica_el_mes(self, mes: int, esperada: str):
        assert temporada_de(date(2026, mes, 15)) == esperada


class TestTiposDeFestividad:
    def test_los_feriados_nacionales_se_marcan_como_tales(self):
        navidad = next(f for f in festividades_en(date(2026, 12, 25)) if f.nombre == "Navidad")
        assert navidad.tipo == TipoFestividad.NACIONAL
