"""Pruebas de las dos capas de IA del Incremento 3.

Lo que más importa comprobar aquí, y por qué:

1. Que **las dos vías funcionen**: con modelo y con reglas. La regla de oro
   del proyecto dice que apagar el modelo no puede romper nada.
2. Que **la explicación sea de verdad**: los términos que se devuelven tienen
   que ser los que provocaron el puntaje, no adorno.
3. Que **preferencias distintas den resultados distintos**. Si no, no hay
   personalización, solo una lista fija con otro nombre.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.ia.afinidad import (
    RecursoParaPuntuar,
    calcular_afinidad,
    calcular_afinidad_con_modelo,
    calcular_afinidad_con_reglas,
    construir_consulta_del_visitante,
    contiene_termino,
    normalizar,
)
from app.ia.afluencia import (
    FILAS_MINIMAS_PARA_ENTRENAR,
    CaracteristicasDelDia,
    NivelAfluencia,
    entrenar_modelo_de_afluencia,
    extraer_caracteristicas,
    predecir_afluencia,
    predecir_afluencia_con_reglas,
)
from app.servicios.avisos import CODIGOS_CONOCIDOS

# Recursos reales del catálogo, con sus categorías tal como vienen del MINCETUR.
CATALOGO_DE_PRUEBA = [
    RecursoParaPuntuar(
        id=1,
        nombre="Pueblo Artesanal de Cochas Grande",
        categoria="2. MANIFESTACIONES CULTURALES",
        tipo="Arquitectura y Espacios Urbanos",
        subtipo="Pueblo artesanal",
        distrito="EL TAMBO",
    ),
    RecursoParaPuntuar(
        id=2,
        nombre="Laguna de Paca",
        categoria="1. SITIOS NATURALES",
        tipo="Cuerpos de Agua",
        subtipo="Laguna",
        distrito="PACA",
    ),
    RecursoParaPuntuar(
        id=3,
        nombre="Convento de Santa Rosa de Ocopa",
        categoria="2. MANIFESTACIONES CULTURALES",
        tipo="Arquitectura y Espacios Urbanos",
        subtipo="Convento",
        distrito="SANTA ROSA DE OCOPA",
    ),
    RecursoParaPuntuar(
        id=4,
        nombre="Sitio Arqueológico de Arwaturo",
        categoria="2. MANIFESTACIONES CULTURALES",
        tipo="Sitios Arqueológicos",
        subtipo="Zonas arqueológicas",
        distrito="CHUPACA",
    ),
]


def puntajes_por_id(resultados) -> dict[int, float]:
    return {r.recurso_id: r.puntaje for r in resultados}


class TestNormalizacion:
    def test_quita_tildes_y_pasa_a_minusculas(self):
        assert normalizar("Arqueológico") == "arqueologico"
        assert normalizar("CONVENTO") == "convento"

    def test_tolera_valores_vacios(self):
        assert normalizar(None) == ""
        assert normalizar("") == ""


class TestCoincidenciaDeTerminos:
    """Los términos deben coincidir como palabra completa, no como subcadena."""

    def test_coincide_una_palabra_completa(self):
        assert contiene_termino("laguna de paca", "laguna") is True
        assert contiene_termino("sitios arqueologicos", "sitios arqueologicos") is True

    def test_no_coincide_dentro_de_otra_palabra(self):
        """El fallo que motivó esta función.

        «rio» coincidía dentro de «santuario», así que el Santuario
        Arqueológico de Wariwillka se clasificaba como naturaleza. Con
        límites de palabra ya no ocurre.
        """
        assert contiene_termino("santuario arqueologico", "rio") is False
        assert contiene_termino("martes de carnaval", "arte") is False
        assert contiene_termino("incapaz", "inca") is False

    def test_un_santuario_arqueologico_no_es_naturaleza(self):
        """La comprobación de extremo a extremo del mismo fallo."""
        santuario = RecursoParaPuntuar(
            id=99,
            nombre="Santuario Arqueológico de Wariwillka",
            categoria="2. MANIFESTACIONES CULTURALES",
            tipo="Sitios Arqueológicos",
            subtipo="Santuarios",
            distrito="HUANCAN",
        )

        resultados = calcular_afinidad_con_reglas([santuario], ["naturaleza", "arqueologia"])

        assert resultados[0].intereses_cubiertos == ["arqueologia"]

    def test_un_museo_de_sitio_es_arqueologia_no_una_iglesia(self):
        """Otro error de clasificación que salió al probar en el navegador."""
        museo = RecursoParaPuntuar(
            id=98,
            nombre="Museo de Sitio Wariwillka",
            categoria="2. MANIFESTACIONES CULTURALES",
            tipo="Museos y otros",
            subtipo="Museos de sitio",
            distrito="HUANCAN",
        )

        resultados = calcular_afinidad_con_reglas([museo], ["iglesias_conventos", "arqueologia"])

        assert resultados[0].intereses_cubiertos == ["arqueologia"]


class TestConsultaDelVisitante:
    def test_expande_el_interes_al_vocabulario_del_mincetur(self):
        """El puente sin el cual la similitud sería siempre cero.

        El visitante marca «artesanía»; el MINCETUR lo describe como «Pueblo
        artesanal». Si no se expande, los dos textos no comparten ni una
        palabra.
        """
        consulta = construir_consulta_del_visitante(["artesania"])

        assert "artesanal" in consulta
        assert "ceramica" in consulta

    def test_junta_varios_intereses(self):
        consulta = construir_consulta_del_visitante(["naturaleza", "arqueologia"])

        assert "laguna" in consulta
        assert "arqueologico" in consulta


class TestAfinidadConModelo:
    def test_premia_el_recurso_que_corresponde_al_interes(self):
        puntajes = puntajes_por_id(calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["artesania"]))

        # El pueblo artesanal debe puntuar más que la laguna.
        assert puntajes[1] > puntajes[2]

    def test_intereses_distintos_ordenan_distinto(self):
        """Sin esto no hay personalización, solo una lista fija."""
        orden_artesania = [
            r.recurso_id
            for r in sorted(
                calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["artesania"]),
                key=lambda r: -r.puntaje,
            )
        ]
        orden_naturaleza = [
            r.recurso_id
            for r in sorted(
                calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["naturaleza"]),
                key=lambda r: -r.puntaje,
            )
        ]

        assert orden_artesania[0] == 1, "con artesanía debe ganar el pueblo artesanal"
        assert orden_naturaleza[0] == 2, "con naturaleza debe ganar la laguna"
        assert orden_artesania != orden_naturaleza

    def test_toda_recomendacion_explica_por_que(self):
        """La brecha 2 habla de que faltan criterios explícitos."""
        resultados = calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["artesania"])
        pueblo = next(r for r in resultados if r.recurso_id == 1)

        assert pueblo.terminos_decisivos, "un recurso puntuado debe decir qué lo puntuó"
        assert any("artesanal" in termino for termino in pueblo.terminos_decisivos)

    def test_los_terminos_explican_el_puntaje_de_verdad(self):
        """Un recurso con puntaje cero no puede tener términos decisivos.

        Si los tuviera, la explicación estaría inventada.
        """
        for resultado in calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["gastronomia"]):
            if resultado.puntaje == 0:
                assert resultado.terminos_decisivos == []

    def test_marca_que_lo_calculo_el_modelo(self):
        resultados = calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, ["artesania"])
        assert all(r.calculado_por == "modelo" for r in resultados)

    def test_no_falla_con_una_lista_vacia(self):
        assert calcular_afinidad_con_modelo([], ["artesania"]) == []

    def test_no_falla_sin_intereses(self):
        resultados = calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, [])
        assert all(r.puntaje == 0.0 for r in resultados)


class TestAfinidadConReglas:
    def test_el_puntaje_es_la_proporcion_de_intereses_cubiertos(self):
        """La ventaja de las reglas es que el número se lee solo.

        El Convento cubre «iglesias_conventos» pero no «naturaleza»: 1 de 2.
        """
        resultados = calcular_afinidad_con_reglas(
            CATALOGO_DE_PRUEBA, ["iglesias_conventos", "naturaleza"]
        )
        convento = next(r for r in resultados if r.recurso_id == 3)

        assert convento.puntaje == pytest.approx(0.5)
        assert convento.intereses_cubiertos == ["iglesias_conventos"]

    def test_bonifica_estar_en_el_distrito_de_salida(self):
        # Se usan DOS intereses a propósito. Con uno solo, la Laguna cubriría
        # el 100 % y el tope de 1,0 se tragaría la bonificación: la prueba
        # pasaría sin comprobar nada.
        intereses = ["naturaleza", "gastronomia"]

        sin_bonificacion = puntajes_por_id(
            calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, intereses, "HUANCAYO")
        )
        con_bonificacion = puntajes_por_id(
            calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, intereses, "PACA")
        )

        # La Laguna de Paca está en el distrito de PACA.
        assert sin_bonificacion[2] == pytest.approx(0.5)
        assert con_bonificacion[2] > sin_bonificacion[2]

    def test_el_tope_impide_pasar_de_uno_con_la_bonificacion(self):
        """Caso borde: cubrir todo Y estar en el distrito de salida."""
        resultados = calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, ["naturaleza"], "PACA")
        laguna = next(r for r in resultados if r.recurso_id == 2)

        assert laguna.puntaje == 1.0

    def test_el_puntaje_nunca_pasa_de_uno(self):
        """Caso borde: cubrir todo y además estar en el distrito de salida."""
        resultados = calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, ["naturaleza"], "PACA")

        assert all(r.puntaje <= 1.0 for r in resultados)

    def test_marca_que_lo_calcularon_las_reglas(self):
        resultados = calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, ["artesania"])
        assert all(r.calculado_por == "reglas" for r in resultados)


class TestConmutadorDelModelo:
    """La regla de oro del proyecto: apagar el modelo no puede romper nada."""

    def test_con_el_modelo_encendido_usa_el_modelo(self):
        resultados = calcular_afinidad(CATALOGO_DE_PRUEBA, ["artesania"], usar_modelo=True)
        assert all(r.calculado_por == "modelo" for r in resultados)

    def test_con_el_modelo_apagado_usa_las_reglas(self):
        resultados = calcular_afinidad(CATALOGO_DE_PRUEBA, ["artesania"], usar_modelo=False)
        assert all(r.calculado_por == "reglas" for r in resultados)

    def test_ambas_vias_aciertan_cuando_no_hay_ambiguedad(self):
        """Con un interés que solo un recurso satisface, las dos coinciden.

        OJO con lo que esta prueba NO demuestra: que ambas vías coincidan
        siempre. Sobre el catálogo real de 234 recursos **no coinciden**, y el
        motivo está medido en el cuaderno de experimentación: las reglas
        producen tan pocos puntajes distintos que decenas de recursos empatan
        arriba. Ver el caso siguiente.
        """
        for usar_modelo in (True, False):
            mejor = max(
                calcular_afinidad(CATALOGO_DE_PRUEBA, ["artesania"], usar_modelo=usar_modelo),
                key=lambda r: r.puntaje,
            )
            assert mejor.recurso_id == 1, f"falla con usar_modelo={usar_modelo}"

    def test_las_reglas_producen_empates_y_el_modelo_no(self):
        """El hallazgo que decidió aceptar el modelo, fijado como prueba.

        Las reglas puntúan como proporción de intereses cubiertos, así que con
        dos intereses solo pueden dar 0, 0,5 o 1. Sobre el catálogo real eso
        deja 38 recursos empatados en el primer puesto, y el orden que ve el
        visitante entre ellos es arbitrario. El modelo distingue.

        Si algún día las reglas dejaran de empatar, habría que rehacer la
        comparación del cuaderno: la decisión de aceptar el modelo se apoya
        justo en esto.
        """
        intereses = ["iglesias_conventos", "arqueologia"]

        puntajes_reglas = {
            r.puntaje for r in calcular_afinidad_con_reglas(CATALOGO_DE_PRUEBA, intereses)
        }
        puntajes_modelo = {
            r.puntaje for r in calcular_afinidad_con_modelo(CATALOGO_DE_PRUEBA, intereses)
        }

        # Con dos intereses, las reglas solo pueden dar 0, 0.5 o 1.
        assert puntajes_reglas <= {0.0, 0.5, 1.0}
        # El modelo produce más variedad incluso en este catálogo diminuto.
        assert len(puntajes_modelo) >= len(puntajes_reglas)


class TestCaracteristicasDelDia:
    def test_extrae_las_ocho_caracteristicas(self):
        caracteristicas = extraer_caracteristicas(date(2026, 4, 1), "HUANCAYO")

        assert len(caracteristicas.como_vector()) == 8
        assert len(CaracteristicasDelDia.nombres_de_las_caracteristicas()) == 8

    def test_detecta_la_semana_santa(self):
        # 1 de abril de 2026: Miércoles Santo.
        caracteristicas = extraer_caracteristicas(date(2026, 4, 1), "HUANCAYO")

        assert caracteristicas.hay_festividad_en_el_distrito is True
        assert caracteristicas.dias_hasta_la_festividad_mas_cercana == 0

    def test_ninguna_caracteristica_necesita_historico_propio(self):
        """Argumento central del documento sobre MLOps diferido.

        Todas salen del calendario, que es público y estable. Por eso este
        modelo se entrena una vez y no necesita reentrenamiento continuo.
        """
        caracteristicas = extraer_caracteristicas(date(2026, 4, 1), "HUANCAYO")

        # Se puede calcular para una fecha del futuro sin ningún dato de uso.
        futuro = extraer_caracteristicas(date(2030, 4, 1), "HUANCAYO")
        assert futuro.mes == 4
        assert caracteristicas.mes == 4


class TestAfluenciaConReglas:
    def test_la_feria_dominical_da_afluencia_alta(self):
        # 10 de mayo de 2026 es domingo.
        prediccion = predecir_afluencia_con_reglas(date(2026, 5, 10), "HUANCAYO")

        assert prediccion.nivel == NivelAfluencia.ALTO
        assert prediccion.motivo.codigo == "afluencia_feria_dominical"

    def test_una_festividad_da_afluencia_alta(self):
        # Semana Santa 2026.
        prediccion = predecir_afluencia_con_reglas(date(2026, 4, 1), "HUANCAYO")

        assert prediccion.nivel == NivelAfluencia.ALTO
        assert prediccion.motivo.codigo == "afluencia_festividad"
        # El nombre de la fiesta viaja como parámetro: es un nombre propio y no
        # se traduce, pero la frase que lo envuelve sí.
        assert "Semana Santa" in prediccion.motivo.parametros["fiestas"]

    def test_un_sabado_corriente_da_afluencia_media(self):
        # 16 de mayo de 2026 es sábado, sin fiestas cerca.
        prediccion = predecir_afluencia_con_reglas(date(2026, 5, 16), "JAUJA")

        assert prediccion.nivel == NivelAfluencia.MEDIO
        assert prediccion.motivo.codigo == "afluencia_fin_de_semana"

    def test_un_martes_de_temporada_baja_da_afluencia_baja(self):
        prediccion = predecir_afluencia_con_reglas(date(2026, 5, 12), "JAUJA")

        assert prediccion.nivel == NivelAfluencia.BAJO

    def test_toda_prediccion_explica_su_motivo(self):
        """«Mucha gente» sin decir por qué obliga al visitante a creérselo."""
        for dia in (date(2026, 4, 1), date(2026, 5, 10), date(2026, 5, 12)):
            prediccion = predecir_afluencia_con_reglas(dia, "HUANCAYO")
            # Un código sin declarar saldría en pantalla como texto crudo.
            assert prediccion.motivo.codigo in CODIGOS_CONOCIDOS

    def test_la_feria_dominical_solo_afecta_a_huancayo(self):
        domingo = date(2026, 5, 10)

        en_huancayo = predecir_afluencia_con_reglas(domingo, "HUANCAYO")
        en_jauja = predecir_afluencia_con_reglas(domingo, "JAUJA")

        assert en_huancayo.nivel == NivelAfluencia.ALTO
        assert en_jauja.nivel == NivelAfluencia.MEDIO


class TestEntrenamientoDelModeloDeAfluencia:
    def test_se_niega_a_entrenar_con_pocos_datos(self):
        """Es lo correcto, no una limitación.

        Un modelo de árboles con veinte filas memoriza los ejemplos: su error
        de entrenamiento sale precioso y su predicción real no vale nada.
        Decir «no entrené y este es el motivo» es información útil.
        """
        pocos = [
            (extraer_caracteristicas(date(2026, 1, dia), "HUANCAYO"), 100 * dia)
            for dia in range(1, 21)
        ]

        resultado = entrenar_modelo_de_afluencia(pocos)

        assert resultado.se_entreno is False
        assert resultado.filas_disponibles == 20
        assert str(FILAS_MINIMAS_PARA_ENTRENAR) in resultado.motivo

    def test_sin_datos_no_entrena_y_lo_dice(self):
        resultado = entrenar_modelo_de_afluencia([])

        assert resultado.se_entreno is False
        assert "alternativa por reglas" in resultado.motivo


class TestConmutadorDeAfluencia:
    def test_cae_en_las_reglas_cuando_no_hay_modelo_entrenado(self):
        """La configuración expresa una intención; los datos mandan.

        Aunque se pida el modelo, si no hay modelo entrenado se usan las
        reglas. El campo calculado_por deja constancia de cuál se usó.
        """
        prediccion = predecir_afluencia(date(2026, 5, 12), "HUANCAYO", usar_modelo=True)

        assert prediccion.calculado_por == "reglas"

    def test_con_el_modelo_apagado_usa_las_reglas(self):
        prediccion = predecir_afluencia(date(2026, 5, 12), "HUANCAYO", usar_modelo=False)

        assert prediccion.calculado_por == "reglas"
