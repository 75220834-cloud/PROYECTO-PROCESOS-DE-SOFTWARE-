"""Pruebas del análisis de sentimiento y de la detección de temas.

**Todas las pruebas de este archivo usan la vía por reglas.** No es pereza: la
alternativa por reglas es la que tiene que funcionar siempre, en cualquier
máquina, sin descargar cientos de megas ni tener red. Si estas pruebas
dependieran del modelo, la suite fallaría en el portátil de la exposición
justo cuando más importa que pase.

El modelo se prueba aparte, y esas pruebas se saltan si no está instalado.
"""

from __future__ import annotations

import importlib.util

import pytest

from app.ia.sentimiento import (
    ALCANCE_DE_LA_NEGACION,
    PALABRAS_NEGATIVAS,
    PALABRAS_POSITIVAS,
    TERMINOS_POR_TEMA,
    analizar,
    analizar_con_reglas,
    contiene_termino,
    detectar_temas,
    normalizar,
    validar_puntuacion,
)
from app.modelos.valoracion import Sentimiento, TemaValoracion

#: Se salta lo que necesita el modelo si pysentimiento no está instalado. El
#: proyecto tiene que poder probarse sin él.
necesita_el_modelo = pytest.mark.skipif(
    importlib.util.find_spec("pysentimiento") is None,
    reason="pysentimiento no está instalado. Instálalo con: pip install pysentimiento",
)


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------


class TestNormalizacion:
    def test_pasa_a_minusculas(self):
        assert normalizar("EXCELENTE") == "excelente"

    def test_quita_las_tildes(self):
        """La gente escribe reseñas desde el móvil y la mitad no pone tildes."""
        assert normalizar("pésimo") == "pesimo"
        assert normalizar("atención") == "atencion"
        assert normalizar("señalización") == "senalizacion"

    def test_una_palabra_sin_tildes_no_cambia(self):
        assert normalizar("limpio") == "limpio"


class TestContieneTermino:
    def test_encuentra_la_palabra_completa(self):
        assert contiene_termino("el precio es caro", "caro")

    def test_no_la_encuentra_dentro_de_otra(self):
        """La lección del Incremento 3: «rio» aparecía dentro de «santuaRIO»."""
        assert not contiene_termino("la carretera estaba mal", "caro")

    def test_distingue_singular_de_plural(self):
        assert contiene_termino("los banos", "banos")
        assert not contiene_termino("el bano", "banos")


# ---------------------------------------------------------------------------
# Los diccionarios, que no pueden tener entradas muertas
# ---------------------------------------------------------------------------


class TestIntegridadDeLosDiccionarios:
    """Una entrada que nunca coincide es código muerto que aparenta funcionar."""

    @pytest.mark.parametrize(
        ("nombre", "conjunto"),
        [("positivas", PALABRAS_POSITIVAS), ("negativas", PALABRAS_NEGATIVAS)],
    )
    def test_ninguna_palabra_tiene_tildes(self, nombre: str, conjunto: frozenset[str]):
        """El texto se normaliza antes de comparar: una tilde nunca coincidiría."""
        con_tildes = [p for p in conjunto if p != normalizar(p)]

        assert not con_tildes, f"{nombre}: {con_tildes} nunca coincidirían"

    @pytest.mark.parametrize(
        ("nombre", "conjunto"),
        [("positivas", PALABRAS_POSITIVAS), ("negativas", PALABRAS_NEGATIVAS)],
    )
    def test_ninguna_palabra_tiene_espacios(self, nombre: str, conjunto: frozenset[str]):
        """El texto se trocea en palabras: «no recomiendo» nunca coincidiría."""
        compuestas = [p for p in conjunto if " " in p]

        assert not compuestas, f"{nombre}: {compuestas} nunca coincidirían"

    def test_ninguna_palabra_esta_en_los_dos_conjuntos(self):
        assert not (PALABRAS_POSITIVAS & PALABRAS_NEGATIVAS)

    def test_cada_tema_del_enum_tiene_sus_terminos(self):
        """Si alguien añade un tema y olvida sus términos, no se detectaría nunca."""
        for tema in TemaValoracion:
            assert tema in TERMINOS_POR_TEMA, f"al tema {tema} le faltan términos"
            assert TERMINOS_POR_TEMA[tema], f"el tema {tema} tiene la lista vacía"

    def test_los_terminos_de_los_temas_no_tienen_tildes(self):
        malos = [
            (tema, termino)
            for tema, terminos in TERMINOS_POR_TEMA.items()
            for termino in terminos
            if termino != normalizar(termino)
        ]

        assert not malos, f"con tildes: {malos}"


# ---------------------------------------------------------------------------
# La alternativa por reglas — lo que el plan pide demostrar
# ---------------------------------------------------------------------------


class TestSentimientoConReglas:
    """Frases conocidas, con su clasificación esperada.

    La verificación del plan de trabajo pide exactamente esto: «una valoración
    positiva y una negativa se clasifican correctamente».
    """

    def test_una_valoracion_claramente_positiva(self):
        analisis = analizar_con_reglas(
            "Excelente lugar, el guía muy amable y todo muy limpio. Recomiendo.", 5
        )

        assert analisis.sentimiento == Sentimiento.POSITIVO
        assert analisis.confianza > 0.7
        assert analisis.analizado_por == "reglas"

    def test_una_valoracion_claramente_negativa(self):
        analisis = analizar_con_reglas("Pésimo. Los baños estaban sucios y nos cobraron de más.", 1)

        assert analisis.sentimiento == Sentimiento.NEGATIVO
        assert analisis.confianza > 0.7

    def test_una_valoracion_neutra(self):
        analisis = analizar_con_reglas("Estuvo normal, nada del otro mundo.", 3)

        assert analisis.sentimiento == Sentimiento.NEUTRO

    def test_deja_los_terminos_que_decidieron(self):
        """Es lo que hace auditable esta vía, y lo que el modelo no puede dar."""
        analisis = analizar_con_reglas("El sitio estaba sucio y muy caro.", 2)

        assert "sucio" in analisis.terminos_decisivos
        assert "caro" in analisis.terminos_decisivos


class TestLasNegaciones:
    """La trampa clásica de un diccionario de palabras."""

    def test_no_limpio_es_negativo_y_no_positivo(self):
        analisis = analizar_con_reglas("No estuvo limpio y la atención no fue buena.", 2)

        assert analisis.sentimiento == Sentimiento.NEGATIVO
        assert "no limpio" in analisis.terminos_decisivos

    def test_no_caro_es_positivo(self):
        analisis = analizar_con_reglas("No es caro y no tuvimos problemas.", 4)

        assert analisis.sentimiento == Sentimiento.POSITIVO
        assert "no caro" in analisis.terminos_decisivos

    def test_la_negacion_no_alcanza_a_una_frase_lejana(self):
        """«No» al principio no debe invertir una palabra diez palabras después."""
        palabras_intermedias = " ".join(["palabra"] * (ALCANCE_DE_LA_NEGACION + 3))
        analisis = analizar_con_reglas(f"No {palabras_intermedias} excelente", 5)

        assert "excelente" in analisis.terminos_decisivos
        assert "no excelente" not in analisis.terminos_decisivos


class TestLaPuntuacionYElTexto:
    def test_sin_comentario_manda_la_puntuacion(self):
        assert analizar_con_reglas(None, 5).sentimiento == Sentimiento.POSITIVO
        assert analizar_con_reglas(None, 1).sentimiento == Sentimiento.NEGATIVO
        assert analizar_con_reglas("", 3).sentimiento == Sentimiento.NEUTRO

    def test_sin_comentario_la_confianza_es_menor(self):
        """Una estrella sola dice poco: no debe salir con la misma confianza."""
        solo_numero = analizar_con_reglas(None, 5)
        con_texto = analizar_con_reglas("Excelente, todo perfecto y muy limpio.", 5)

        assert solo_numero.confianza < con_texto.confianza

    def test_el_texto_no_tumba_la_puntuacion_por_una_sola_palabra(self):
        """Un «pero estaba sucio» al final no debe volcar cinco estrellas."""
        analisis = analizar_con_reglas(
            "Todo increíble, el paisaje espectacular, aunque el baño estaba sucio.", 5
        )

        assert analisis.sentimiento == Sentimiento.POSITIVO

    def test_el_texto_si_tumba_la_puntuacion_por_margen(self):
        analisis = analizar_con_reglas("Sucio, caro, y el trato fue grosero. Una decepción.", 5)

        assert analisis.sentimiento == Sentimiento.NEGATIVO

    def test_cuando_se_contradicen_la_confianza_baja(self):
        """Es el caso que un humano debería revisar, y el tablero puede filtrar."""
        analisis = analizar_con_reglas("Sucio, caro, y el trato fue grosero. Una decepción.", 5)

        assert analisis.confianza < 0.7

    def test_con_tres_estrellas_decide_el_texto(self):
        """El 3 es el que no dice nada: ahí manda lo que se escribió."""
        assert analizar_con_reglas("El paisaje es hermoso.", 3).sentimiento == Sentimiento.POSITIVO
        assert analizar_con_reglas("Estaba todo sucio.", 3).sentimiento == Sentimiento.NEGATIVO


# ---------------------------------------------------------------------------
# Los temas
# ---------------------------------------------------------------------------


class TestDeteccionDeTemas:
    def test_detecta_los_temas_del_plan_de_trabajo(self):
        """limpieza, atención, precio, acceso, señalización."""
        temas = detectar_temas(
            "Los baños sucios, la atención pésima, muy caro, difícil llegar " "y sin letreros."
        )

        assert TemaValoracion.LIMPIEZA in temas
        assert TemaValoracion.ATENCION in temas
        assert TemaValoracion.PRECIO in temas
        assert TemaValoracion.ACCESO in temas
        assert TemaValoracion.SENALIZACION in temas

    def test_un_comentario_sin_temas_devuelve_lista_vacia(self):
        assert detectar_temas("Fuimos el martes.") == []

    def test_sin_comentario_devuelve_lista_vacia(self):
        assert detectar_temas(None) == []
        assert detectar_temas("") == []
        assert detectar_temas("   ") == []

    def test_funciona_sin_tildes(self):
        """Como escribe la mitad de la gente desde el móvil."""
        assert TemaValoracion.SENALIZACION in detectar_temas("faltaba senalizacion")
        assert TemaValoracion.SENALIZACION in detectar_temas("faltaba señalización")

    def test_el_orden_es_estable(self):
        """Dos comentarios con los mismos temas deben dar la misma lista.

        Sin esto, el tablero agruparía mal y dos valoraciones idénticas
        parecerían distintas.
        """
        uno = detectar_temas("sucio y caro")
        otro = detectar_temas("caro y sucio")

        assert uno == otro

    def test_no_detecta_un_tema_por_una_subcadena(self):
        """«caro» dentro de «carretera» no debe activar el tema de precio."""
        temas = detectar_temas("la carretera estaba en obras")

        assert TemaValoracion.PRECIO not in temas
        assert TemaValoracion.ACCESO in temas


# ---------------------------------------------------------------------------
# El interruptor de la regla de oro
# ---------------------------------------------------------------------------


class TestElInterruptor:
    def test_con_el_modelo_apagado_se_usan_las_reglas(self):
        analisis = analizar("Excelente todo", 5, usar_modelo=False)

        assert analisis.analizado_por == "reglas"

    def test_con_el_modelo_apagado_sigue_clasificando_bien(self):
        """La comprobación del plan: «con USAR_MODELO_SENTIMIENTO=False sigue funcionando»."""
        positiva = analizar("Excelente lugar, muy limpio y amable.", 5, usar_modelo=False)
        negativa = analizar("Pésimo, sucio y carísimo.", 1, usar_modelo=False)

        assert positiva.sentimiento == Sentimiento.POSITIVO
        assert negativa.sentimiento == Sentimiento.NEGATIVO

    def test_con_el_modelo_apagado_los_temas_se_siguen_detectando(self):
        analisis = analizar("Los baños estaban sucios", 2, usar_modelo=False)

        assert TemaValoracion.LIMPIEZA in analisis.temas

    def test_si_el_modelo_falla_se_degrada_a_reglas_y_se_dice(self, monkeypatch):
        """Fallar dejaría valoraciones sin analizar justo en la exposición."""
        import app.ia.sentimiento as modulo

        def revienta(*_args, **_kwargs):
            raise RuntimeError("el modelo no está")

        monkeypatch.setattr(modulo, "analizar_con_modelo", revienta)

        analisis = analizar("Excelente todo", 5, usar_modelo=True)

        assert analisis.analizado_por == "reglas"
        assert "no estaba disponible" in analisis.version

    def test_siempre_declara_su_version(self):
        """Sin la versión, dentro de un año nadie sabría qué produjo el análisis."""
        assert analizar("Excelente", 5, usar_modelo=False).version


class TestValidacionDePuntuacion:
    @pytest.mark.parametrize("puntuacion", [1, 2, 3, 4, 5])
    def test_acepta_el_rango_valido(self, puntuacion: int):
        validar_puntuacion(puntuacion)

    @pytest.mark.parametrize("puntuacion", [0, 6, -1, 100])
    def test_rechaza_lo_que_esta_fuera(self, puntuacion: int):
        with pytest.raises(ValueError, match="entre 1 y 5"):
            validar_puntuacion(puntuacion)


# ---------------------------------------------------------------------------
# El modelo — se salta si no está instalado
# ---------------------------------------------------------------------------


@necesita_el_modelo
class TestElModelo:
    def test_clasifica_una_positiva_y_una_negativa(self):
        """La comprobación explícita del plan de trabajo, con el modelo."""
        from app.ia.sentimiento import analizar_con_modelo

        positiva = analizar_con_modelo("Excelente lugar, el guía muy amable y todo muy limpio.", 5)
        negativa = analizar_con_modelo("Pésimo. Los baños estaban sucios y nos cobraron de más.", 1)

        assert positiva.sentimiento == Sentimiento.POSITIVO
        assert negativa.sentimiento == Sentimiento.NEGATIVO
        assert positiva.analizado_por == "modelo"

    def test_entiende_vocabulario_que_no_esta_en_el_diccionario(self):
        """Es la razón por la que el modelo se aceptó.

        Las reglas fallan estas dos: ninguna de sus palabras está en el
        diccionario de sentimiento, así que devolverían «neutro». El modelo las
        lee. Las frases son literalmente las de la medición documentada en el
        ADR del incremento.
        """
        from app.ia.sentimiento import analizar_con_modelo

        assert (
            analizar_con_modelo(
                "La verdad es que superó todas nuestras expectativas.", 3
            ).sentimiento
            == Sentimiento.POSITIVO
        )
        assert (
            analizar_con_modelo("Nos arrepentimos de haber ido hasta allá.", 3).sentimiento
            == Sentimiento.NEGATIVO
        )

        # Y lo mismo con las reglas, para que se vea la diferencia.
        assert (
            analizar_con_reglas(
                "La verdad es que superó todas nuestras expectativas.", 3
            ).sentimiento
            == Sentimiento.NEUTRO
        )

    def test_el_modelo_tambien_falla_con_frases_muy_cortas(self):
        """Limitación conocida y medida, no escondida.

        «Superó todas nuestras expectativas.» sale NEUTRO con 0,52 de confianza;
        la misma idea con cuatro palabras más delante («La verdad es que…») sale
        POSITIVO con 0,85. El modelo necesita contexto.

        Esta prueba existe para que la limitación esté escrita y para que se
        entere alguien si un día deja de ser cierta. Y para justificar el umbral
        de confianza: con 0,52 el modelo NO se impone a la puntuación, que es
        exactamente lo que debe pasar cuando duda.
        """
        from app.ia.sentimiento import CONFIANZA_PARA_IMPONERSE, _obtener_analizador

        prediccion = _obtener_analizador().predict("Superó todas nuestras expectativas.")
        confianza = prediccion.probas[prediccion.output]

        assert confianza < CONFIANZA_PARA_IMPONERSE, (
            "si el modelo ya acierta esta frase con confianza, actualiza la "
            "limitación documentada en el ADR"
        )

    def test_tambien_detecta_temas(self):
        """El modelo clasifica sentimiento; los temas los ponen las reglas."""
        from app.ia.sentimiento import analizar_con_modelo

        analisis = analizar_con_modelo("Los baños estaban sucios y caro.", 2)

        assert TemaValoracion.LIMPIEZA in analisis.temas
        assert TemaValoracion.PRECIO in analisis.temas

    def test_sin_comentario_cae_a_las_reglas(self):
        """Un modelo de texto no tiene nada que leer en una cadena vacía."""
        from app.ia.sentimiento import analizar_con_modelo

        analisis = analizar_con_modelo(None, 5)

        assert analisis.sentimiento == Sentimiento.POSITIVO
        assert analisis.analizado_por == "reglas"
