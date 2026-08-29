"""Pruebas de la validación DataOps del catálogo.

Estas reglas producen el indicador del Incremento 1, así que un error aquí no
rompe una pantalla: hace que el proyecto declare un número falso. Por eso se
prueban una por una y con sus casos borde.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.modelos.catalogo import RecursoTuristico, RegistroValidacion
from app.servicios.catalogo import importar_inventario
from app.servicios.validacion_catalogo import (
    DIAS_DE_VIGENCIA,
    coordenada_esta_en_el_valle,
    evaluar_recurso,
    obtener_ultimo_registro,
    validar_catalogo,
)

#: Fecha fija de referencia. Las pruebas no deben depender de qué día se
#: ejecuten: si usaran date.today(), dentro de dos años empezarían a fallar
#: solas sin que nadie haya tocado el código.
HOY = date(2026, 8, 29)

#: Coordenadas reales de la Plaza de la Constitución de Huancayo.
LATITUD_HUANCAYO, LONGITUD_HUANCAYO = -12.0687, -75.2099


class TestCoordenadaEstaEnElValle:
    def test_acepta_un_punto_de_huancayo(self):
        assert coordenada_esta_en_el_valle(LATITUD_HUANCAYO, LONGITUD_HUANCAYO) is True

    def test_acepta_los_distritos_altos_del_occidente(self):
        # Caso borde real: San José de Quero (Concepción) y Yanacancha
        # (Chupaca) están en la zona alta, al oeste. El rectángulo inicial del
        # plan de trabajo los dejaba fuera y los marcaba como inválidos.
        assert coordenada_esta_en_el_valle(-12.0891, -75.5350) is True  # San José de Quero
        assert coordenada_esta_en_el_valle(-12.2514, -75.5831) is True  # Yanacancha
        assert coordenada_esta_en_el_valle(-11.2960, -75.7730) is True  # norte de Jauja

    def test_rechaza_un_punto_de_lima(self):
        assert coordenada_esta_en_el_valle(-12.0464, -77.0428) is False

    def test_rechaza_coordenadas_intercambiadas(self):
        # Si alguien vuelve a meter latitud y longitud al revés, la regla lo
        # detecta: -75 no es una latitud posible en el valle.
        assert coordenada_esta_en_el_valle(-75.2099, -12.0687) is False

    def test_rechaza_valores_ausentes(self):
        assert coordenada_esta_en_el_valle(None, LONGITUD_HUANCAYO) is False
        assert coordenada_esta_en_el_valle(LATITUD_HUANCAYO, None) is False
        assert coordenada_esta_en_el_valle(None, None) is False


class TestEvaluarRecurso:
    """Las cuatro reglas de validación, una por una."""

    @staticmethod
    def _evaluar(**cambios):
        """Evalúa un recurso válido, cambiando solo lo que indique la prueba."""
        argumentos = {
            "nombre": "Plaza de la Constitución",
            "provincia": "HUANCAYO",
            "latitud": LATITUD_HUANCAYO,
            "longitud": LONGITUD_HUANCAYO,
            "fecha_corte": date(2026, 8, 27),
            "fecha_de_referencia": HOY,
        }
        argumentos.update(cambios)
        return evaluar_recurso(**argumentos)

    def test_caso_normal_un_recurso_completo_es_valido_y_vigente(self):
        validado, vigente, motivos = self._evaluar()

        assert validado is True
        assert vigente is True
        assert motivos == []

    def test_rechaza_un_recurso_sin_nombre(self):
        validado, _, motivos = self._evaluar(nombre="")
        assert validado is False
        assert "sin nombre" in motivos

    def test_rechaza_un_nombre_de_solo_espacios(self):
        # Caso borde: "   " no es cadena vacía, pero tampoco es un nombre.
        validado, _, motivos = self._evaluar(nombre="   ")
        assert validado is False
        assert "sin nombre" in motivos

    def test_rechaza_una_provincia_fuera_de_la_ruta(self):
        validado, _, motivos = self._evaluar(provincia="TARMA")
        assert validado is False
        assert "provincia fuera de la ruta" in motivos

    def test_rechaza_un_recurso_sin_coordenadas(self):
        validado, _, motivos = self._evaluar(latitud=None, longitud=None)
        assert validado is False
        assert "sin coordenadas" in motivos

    def test_rechaza_una_coordenada_fuera_del_area(self):
        validado, _, motivos = self._evaluar(latitud=-12.0464, longitud=-77.0428)
        assert validado is False
        assert "coordenada fuera del area del valle" in motivos

    def test_validado_y_vigente_son_cosas_distintas(self):
        """Un recurso puede estar bien descrito y ubicado, y aun así caducado.

        El indicador los cuenta por separado a propósito: mezclarlos ocultaría
        que la fuente oficial lleva años sin actualizarse.
        """
        fecha_muy_antigua = HOY - timedelta(days=DIAS_DE_VIGENCIA + 1)

        validado, vigente, motivos = self._evaluar(fecha_corte=fecha_muy_antigua)

        assert validado is True, "los datos siguen siendo correctos"
        assert vigente is False, "pero el dato está caducado"
        assert "fecha de corte demasiado antigua" in motivos

    def test_el_limite_exacto_de_vigencia_todavia_cuenta_como_vigente(self):
        # Caso borde: justo el último día del plazo debe seguir siendo vigente.
        limite = HOY - timedelta(days=DIAS_DE_VIGENCIA)

        _, vigente, _ = self._evaluar(fecha_corte=limite)
        assert vigente is True

    def test_rechaza_un_recurso_sin_fecha_de_corte(self):
        _, vigente, motivos = self._evaluar(fecha_corte=None)
        assert vigente is False
        assert "sin fecha de corte" in motivos

    def test_acumula_varios_motivos_a_la_vez(self):
        """Se guardan TODOS los motivos, no solo el primero.

        El gestor necesita saber todo lo que hay que corregir de un recurso,
        no enterarse de un problema por cada validación que ejecute.
        """
        _, _, motivos = self._evaluar(nombre="", provincia="TARMA", latitud=None, longitud=None)

        assert "sin nombre" in motivos
        assert "provincia fuera de la ruta" in motivos
        assert "sin coordenadas" in motivos
        assert len(motivos) >= 3


class TestValidarCatalogo:
    """La validación completa, contra la base de datos."""

    def test_calcula_el_indicador_y_lo_guarda(self, sesion, csv_de_ejemplo):
        """De los 3 recursos importados, 2 tienen coordenadas válidas."""
        importar_inventario(sesion, csv_de_ejemplo)

        resultado = validar_catalogo(sesion, fecha_de_referencia=HOY)

        assert resultado.total_recursos == 3
        assert resultado.con_coordenadas == 2
        assert resultado.validados == 2
        assert resultado.porcentaje_validado == pytest.approx(66.67, abs=0.01)

    def test_deja_una_fila_en_el_registro_de_validacion(self, sesion, csv_de_ejemplo):
        """Sin esta fila, el Incremento 1 no tendría evidencia medible."""
        importar_inventario(sesion, csv_de_ejemplo)
        validar_catalogo(sesion, fecha_de_referencia=HOY)

        registro = obtener_ultimo_registro(sesion)

        assert registro is not None
        assert registro.total_recursos == 3
        assert registro.validados == 2

    def test_marca_cada_recurso_con_sus_motivos(self, sesion, csv_de_ejemplo):
        importar_inventario(sesion, csv_de_ejemplo)
        validar_catalogo(sesion, fecha_de_referencia=HOY)

        sin_coordenadas = sesion.scalars(
            select(RecursoTuristico).where(RecursoTuristico.codigo_mincetur == "900003")
        ).one()

        assert sin_coordenadas.esta_validado is False
        assert "sin coordenadas" in (sin_coordenadas.motivos_invalidez or "")

        valido = sesion.scalars(
            select(RecursoTuristico).where(RecursoTuristico.codigo_mincetur == "900001")
        ).one()

        assert valido.esta_validado is True
        assert valido.motivos_invalidez is None

    def test_no_borra_los_recursos_que_no_pasan(self, sesion, csv_de_ejemplo):
        """Un recurso inválido se marca, nunca se elimina.

        Borrarlo haría subir el porcentaje artificialmente y ocultaría la
        calidad real de la fuente oficial.
        """
        importar_inventario(sesion, csv_de_ejemplo)
        validar_catalogo(sesion, fecha_de_referencia=HOY)

        total = len(sesion.scalars(select(RecursoTuristico)).all())
        assert total == 3

    def test_cada_ejecucion_anade_un_registro_nuevo(self, sesion, csv_de_ejemplo):
        """El histórico permite demostrar que la calidad mejora con el tiempo."""
        importar_inventario(sesion, csv_de_ejemplo)

        validar_catalogo(sesion, fecha_de_referencia=HOY)
        validar_catalogo(sesion, fecha_de_referencia=HOY)

        registros = sesion.scalars(select(RegistroValidacion)).all()
        assert len(registros) >= 2
