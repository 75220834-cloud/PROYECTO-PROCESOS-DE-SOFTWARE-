"""Pruebas de la lectura de fichas del MINCETUR y de la temporada.

Las de lectura **no piden nada por red**: trabajan sobre HTML escrito a mano
que reproduce la forma real de las fichas. Una prueba que descargue una página
del Estado para comprobarse a sí misma es una prueba que falla el día que se
cae ese servidor, y que además lo castiga cada vez que alguien ejecuta la
suite.

Las de temporada son puro cálculo de meses y tampoco tocan la base.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.servicios.temporada import esta_en_temporada, meses_del_viaje
from app.utilidades.fichas_mincetur import (
    codigo_de_la_url,
    cuando_se_celebra,
    interpretar_horario,
    leer_ficha,
)

#: Una ficha como las de verdad: los datos van en tablas con cabecera, y la
#: descripción en párrafos sueltos.
FICHA = """
<html><body>
  <table><tr><td>Código:</td><td>703</td></tr></table>

  <p>La Plaza Constitución de Huancayo es uno de los espacios más
     emblemáticos de la ciudad, con una historia que se remonta a la época
     colonial y republicana del Perú y que conviene contar con cierto detalle
     para que el párrafo pase de los ciento veinte caracteres.</p>

  <table>
    <tr><td>Tipo de Visitante</td><td>Cantidad</td><td>Fuente de datos</td>
        <td>Año</td><td>Observación</td></tr>
    <tr><td>Turistas Extranjeros</td><td>90</td><td>Conteo Muestral</td>
        <td>2024</td><td>--</td></tr>
    <tr><td>Visitantes Locales</td><td>15840</td><td>Conteo Muestral</td>
        <td>2024</td><td>--</td></tr>
  </table>

  <table>
    <tr><td>Tipo de ingreso</td><td>Observaciones</td></tr>
    <tr><td>Libre</td><td>--</td></tr>
  </table>

  <table>
    <tr><td>Época propicia de visita al recurso</td><td>Especificación</td>
        <td>Hora de visita especificación</td><td>Observaciones</td></tr>
    <tr><td>Todo el Año</td><td>--</td><td>07:00 a.m. - 09:00 p.m.</td><td>--</td></tr>
  </table>
</body></html>
"""

#: Las fichas de fiestas usan otra plantilla: descripción y poco más.
FICHA_DE_FIESTA = """
<html><body>
  <table><tr><td>Código:</td><td>7104</td></tr></table>
  <p>La Fiesta de la Tunantada Jaujina, en honor a San Fabián y San Sebastián,
     es una celebración cultural y religiosa que se realiza cada año en la
     Plaza de Armas de Jauja los días 18, 19 y 20 de enero.</p>
</body></html>
"""


class TestLeerUnaFicha:
    """Lo que la ficha web trae y el CSV del inventario no."""

    def test_saca_la_descripcion(self) -> None:
        assert "Plaza Constitución" in (leer_ficha(FICHA, "703").descripcion or "")

    def test_saca_el_horario(self) -> None:
        """Era la limitación número uno del proyecto: «no hay horarios»."""
        assert leer_ficha(FICHA, "703").horario_en_texto == "07:00 a.m. - 09:00 p.m."

    def test_saca_el_tipo_de_ingreso(self) -> None:
        assert leer_ficha(FICHA, "703").tipo_de_ingreso == "Libre"

    def test_saca_los_visitantes_con_su_ano_y_su_tipo(self) -> None:
        """Son conteos reales del MINCETUR, no una estimación nuestra."""
        visitantes = leer_ficha(FICHA, "703").visitantes

        assert (2024, "Turistas Extranjeros", 90, "Conteo Muestral") in visitantes
        assert (2024, "Visitantes Locales", 15840, "Conteo Muestral") in visitantes

    def test_busca_las_tablas_por_su_cabecera_y_no_por_su_posicion(self) -> None:
        """Las fichas sin visitantes no traen esa tabla, y todo se corre.

        Si se buscara «la cuarta tabla», la mitad de las fichas darían el
        horario de otra cosa. Aquí se quita la tabla de visitantes y el resto
        tiene que seguir leyéndose igual.
        """
        sin_visitantes = (
            FICHA[: FICHA.index("<table>\n    <tr><td>Tipo de Visitante")]
            + FICHA[FICHA.index("<table>\n    <tr><td>Tipo de ingreso") :]
        )

        ficha = leer_ficha(sin_visitantes, "703")

        assert ficha.tipo_de_ingreso == "Libre"
        assert ficha.horario_en_texto is not None

    def test_lo_que_no_esta_se_queda_nulo_y_se_anota(self) -> None:
        """Un campo vacío es información; uno rellenado a ojo es una mentira."""
        ficha = leer_ficha("<html><body></body></html>", "0")

        assert ficha.horario_en_texto is None
        assert ficha.tipo_de_ingreso is None
        assert "horario" in ficha.ausentes

    def test_saca_el_codigo_de_la_direccion(self) -> None:
        url = "https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=703"

        assert codigo_de_la_url(url) == "703"


class TestInterpretarElHorario:
    """De «07:00 a.m. - 09:00 p.m.» a algo con lo que se pueda calcular."""

    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("07:00 a.m. - 09:00 p.m.", ("07:00", "21:00")),
            ("10:00 a.m. – 06:00 p.m.", ("10:00", "18:00")),
            ("08:00 a.m. a 05:00 p.m.", ("08:00", "17:00")),
            ("12:00 p.m. - 06:00 p.m.", ("12:00", "18:00")),
        ],
    )
    def test_entiende_las_formas_que_usa_la_ficha(
        self, texto: str, esperado: tuple[str, str]
    ) -> None:
        assert interpretar_horario(texto) == esperado

    @pytest.mark.parametrize("texto", ["--", "", "Todo el día", "de sol a sol", None])
    def test_lo_que_no_entiende_lo_deja_sin_interpretar(self, texto: str | None) -> None:
        """Un horario mal leído metería al visitante en un sitio cerrado."""
        assert interpretar_horario(texto) is None

    def test_rechaza_un_horario_que_cierra_antes_de_abrir(self) -> None:
        assert interpretar_horario("09:00 p.m. - 07:00 a.m.") is None


class TestCuandoSeCelebra:
    """Las fechas de las 36 fiestas, sacadas de la descripción oficial."""

    def test_saca_la_frase_y_el_mes(self) -> None:
        frase, meses = cuando_se_celebra(leer_ficha(FICHA_DE_FIESTA, "7104").descripcion)

        assert meses == [1]
        assert "18, 19 y 20 de enero" in (frase or "")

    def test_no_confunde_un_nombre_de_persona_con_un_mes(self) -> None:
        """«Julio» y «Agosto» son nombres de persona en Perú.

        El «Concurso Regional de Enfrenadura de Caballos» salía celebrándose en
        julio porque uno de sus fundadores se llamaba Julio Camac.
        """
        _, meses = cuando_se_celebra(
            "El concurso fue impulsado por muquinos como Julio Camac y Juan Tiza."
        )

        assert meses == []

    def test_no_coge_la_fecha_de_la_historia_del_pueblo(self) -> None:
        """La Feria de Cuasimodo salía con cinco meses por culpa de esto.

        Las fichas dedican párrafos a cómo empezó la fiesta, y esos párrafos
        están llenos de meses que no son su fecha.
        """
        _, meses = cuando_se_celebra(
            "Los arrieros acostumbraban tener dos salidas, las que empezaban en "
            "diciembre y terminaban en marzo del año siguiente."
        )

        assert meses == []

    def test_prefiere_la_frase_que_habla_de_celebrar(self) -> None:
        """Cuando hay historia Y fecha, gana la fecha."""
        frase, meses = cuando_se_celebra(
            "El Alcalde la trasladó en el año de 1950 a Coto Coto. "
            "La feria se celebra cada 8 de diciembre en la plaza principal."
        )

        assert meses == [12]
        assert "se celebra" in (frase or "")

    def test_admite_una_fiesta_de_dos_meses(self) -> None:
        _, meses = cuando_se_celebra(
            "Se inicia el 30 de agosto y se prolonga hasta el 13 de setiembre."
        )

        assert meses == [8, 9]

    def test_sin_descripcion_no_hay_fecha(self) -> None:
        assert cuando_se_celebra(None) == (None, [])


class TestLaTemporada:
    """Si una fiesta cae o no dentro de un viaje."""

    def test_un_viaje_de_enero_alcanza_una_fiesta_de_enero(self) -> None:
        meses = meses_del_viaje(date(2026, 1, 18), date(2026, 1, 20))

        assert esta_en_temporada([1], meses) is True

    def test_un_viaje_de_mayo_no_alcanza_una_fiesta_de_enero(self) -> None:
        """Es el caso que motivó todo esto: la Tunantada en un viaje de mayo."""
        meses = meses_del_viaje(date(2026, 5, 10), date(2026, 5, 12))

        assert esta_en_temporada([1], meses) is False

    def test_un_viaje_a_caballo_de_dos_meses_cuenta_los_dos(self) -> None:
        """Del 28 de enero al 2 de febrero se llega a las fiestas de febrero."""
        meses = meses_del_viaje(date(2026, 1, 28), date(2026, 2, 2))

        assert meses == {1, 2}
        assert esta_en_temporada([2], meses) is True

    def test_un_viaje_que_cruza_el_ano_no_se_salta_nada(self) -> None:
        """Del 28 de diciembre al 3 de enero son diciembre y enero, no doce."""
        assert meses_del_viaje(date(2026, 12, 28), date(2027, 1, 3)) == {12, 1}

    def test_un_viaje_largo_toca_todos_los_meses_de_por_medio(self) -> None:
        assert meses_del_viaje(date(2026, 3, 1), date(2026, 6, 15)) == {3, 4, 5, 6}

    def test_las_fechas_al_reves_no_rompen_nada(self) -> None:
        assert meses_del_viaje(date(2026, 6, 1), date(2026, 3, 1)) == {3, 4, 5, 6}

    def test_sin_fecha_conocida_no_se_avisa_de_nada(self) -> None:
        """«No sabemos» y «sabemos que no» son cosas distintas.

        Devolver `False` cuando la ficha no precisa la fecha pintaría un aviso
        en rojo sobre algo que no sabemos, que es una forma de mentir.
        """
        meses = meses_del_viaje(date(2026, 5, 1), date(2026, 5, 3))

        assert esta_en_temporada([], meses) is None
        assert esta_en_temporada(None, meses) is None
