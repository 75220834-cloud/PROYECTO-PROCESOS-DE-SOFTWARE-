"""Pruebas de las tablas del calendario festivo y de la afluencia histórica.

## Qué se comprueba aquí, y por qué importa

No se comprueba que SQLAlchemy sepa guardar una fila: eso lo garantiza la
biblioteca. Lo que se comprueba son las **restricciones declaradas en la
migración**, que son reglas de negocio escritas en la base de datos:

- una fiesta no puede terminar antes de empezar;
- su tipo tiene que ser uno de los cinco admitidos;
- la misma fiesta no se puede duplicar al recargar el calendario de un año;
- un mes solo puede ser nulo o estar entre 1 y 12;
- los visitantes no pueden ser negativos.

Estas reglas son invisibles desde Python: viven en el esquema. Si alguien
reescribe una migración y se deja una fuera, **ninguna prueba de servicio lo
notaría** —el código seguiría funcionando— y la base empezaría a aceptar datos
imposibles en silencio. Estas pruebas son la red que lo caza.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modelos.afluencia import AfluenciaHistorica, Festividad
from app.modelos.catalogo import RecursoTuristico
from pruebas.conftest import necesita_base_de_datos

pytestmark = necesita_base_de_datos


def _fiesta(**cambios) -> Festividad:
    """Una fiesta válida, con los campos que la prueba quiera cambiar."""
    datos = {
        "nombre": "Fiesta de Santiago",
        "provincia": "HUANCAYO",
        "distrito": "HUANCAYO",
        "fecha_inicio": date(2026, 7, 25),
        "fecha_fin": date(2026, 7, 27),
        "es_movil": False,
        "tipo": "costumbrista",
        "fuente": "Calendario del proyecto",
    }
    datos.update(cambios)
    return Festividad(**datos)


def _recurso(sesion, codigo: str = "900001") -> RecursoTuristico:
    """Un recurso mínimo, para colgar de él la afluencia."""
    recurso = RecursoTuristico(
        codigo_mincetur=codigo,
        nombre="Recurso de prueba",
        provincia="HUANCAYO",
        distrito="HUANCAYO",
    )
    sesion.add(recurso)
    sesion.flush()
    return recurso


class TestFestividad:
    def test_se_guarda_y_se_recupera(self, sesion):
        sesion.add(_fiesta())
        sesion.flush()

        guardada = sesion.scalars(select(Festividad)).one()

        assert guardada.nombre == "Fiesta de Santiago"
        assert guardada.fecha_inicio == date(2026, 7, 25)
        assert guardada.es_movil is False

    def test_el_texto_de_depuracion_lleva_nombre_y_fecha(self, sesion):
        fiesta = _fiesta()
        sesion.add(fiesta)
        sesion.flush()

        texto = repr(fiesta)

        assert "Fiesta de Santiago" in texto
        assert "2026-07-25" in texto

    def test_una_fiesta_no_puede_terminar_antes_de_empezar(self, sesion):
        """La restricción ck_festividad_fechas, comprobada contra la base."""
        sesion.add(_fiesta(fecha_inicio=date(2026, 7, 27), fecha_fin=date(2026, 7, 25)))

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    def test_rechaza_un_tipo_que_no_esta_en_la_lista(self, sesion):
        """ck_festividad_tipo: solo cinco valores son admisibles."""
        sesion.add(_fiesta(tipo="inventado"))

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    @pytest.mark.parametrize("tipo", ["religiosa", "costumbrista", "civica", "feria", "nacional"])
    def test_acepta_los_cinco_tipos_documentados(self, sesion, tipo):
        sesion.add(_fiesta(tipo=tipo, nombre=f"Fiesta {tipo}"))
        sesion.flush()

        assert sesion.scalars(select(Festividad).where(Festividad.tipo == tipo)).one()

    def test_no_se_puede_duplicar_la_misma_fiesta_el_mismo_dia_y_distrito(self, sesion):
        """uq_festividad_nombre_fecha_distrito.

        Es lo que hace idempotente a `cargar_calendario`: volver a ejecutarlo
        no duplica las fiestas del año que ya estaban.
        """
        sesion.add(_fiesta())
        sesion.flush()

        sesion.add(_fiesta())

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    def test_la_misma_fiesta_en_otro_distrito_si_se_admite(self, sesion):
        """La Fiesta de Santiago se celebra en unos 28 distritos a la vez."""
        sesion.add(_fiesta(distrito="SICAYA"))
        sesion.add(_fiesta(distrito="CHUPACA"))
        sesion.flush()

        assert len(sesion.scalars(select(Festividad)).all()) == 2

    def test_sin_distrito_significa_todo_el_valle(self, sesion):
        """Los feriados nacionales no tienen distrito, y eso es válido."""
        sesion.add(
            _fiesta(
                nombre="Fiestas Patrias",
                provincia=None,
                distrito=None,
                tipo="nacional",
                fecha_inicio=date(2026, 7, 28),
                fecha_fin=date(2026, 7, 29),
            )
        )
        sesion.flush()

        guardada = sesion.scalars(
            select(Festividad).where(Festividad.nombre == "Fiestas Patrias")
        ).one()

        assert guardada.distrito is None
        assert guardada.provincia is None

    def test_una_fiesta_de_un_solo_dia_es_valida(self, sesion):
        """fecha_fin == fecha_inicio cumple la restricción, que es `>=`."""
        sesion.add(
            _fiesta(
                nombre="Corpus Christi",
                fecha_inicio=date(2026, 6, 4),
                fecha_fin=date(2026, 6, 4),
                tipo="religiosa",
                es_movil=True,
            )
        )
        sesion.flush()

        guardada = sesion.scalars(
            select(Festividad).where(Festividad.nombre == "Corpus Christi")
        ).one()

        assert guardada.fecha_inicio == guardada.fecha_fin
        assert guardada.es_movil is True


class TestAfluenciaHistorica:
    def test_se_guarda_colgando_de_un_recurso(self, sesion):
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(
                recurso_id=recurso.id,
                anio=2025,
                mes=7,
                visitantes=1200,
                fuente="Ministerio de Cultura",
            )
        )
        sesion.flush()

        fila = sesion.scalars(select(AfluenciaHistorica)).one()

        assert fila.visitantes == 1200
        assert fila.recurso.nombre == "Recurso de prueba"

    def test_el_texto_de_depuracion_muestra_el_mes_con_dos_digitos(self, sesion):
        recurso = _recurso(sesion)
        fila = AfluenciaHistorica(
            recurso_id=recurso.id, anio=2025, mes=7, visitantes=10, fuente="x"
        )
        sesion.add(fila)
        sesion.flush()

        assert "2025-07" in repr(fila)

    def test_el_texto_de_depuracion_sin_mes_muestra_solo_el_anio(self, sesion):
        """La otra rama del __repr__: la cifra es del año entero."""
        recurso = _recurso(sesion)
        fila = AfluenciaHistorica(
            recurso_id=recurso.id, anio=2025, mes=None, visitantes=10, fuente="x"
        )
        sesion.add(fila)
        sesion.flush()

        texto = repr(fila)

        assert "2025" in texto
        assert "2025-" not in texto

    def test_el_mes_nulo_es_valido_porque_la_ficha_da_el_total_del_anio(self, sesion):
        """ck_afluencia_mes admite nulo a propósito.

        Las fichas del MINCETUR dan el total anual. Repartirlo entre doce meses
        sería inventar una estacionalidad que la fuente no mide.
        """
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(
                recurso_id=recurso.id,
                anio=2024,
                mes=None,
                visitantes=45000,
                fuente="Ficha MINCETUR",
            )
        )
        sesion.flush()

        assert sesion.scalars(select(AfluenciaHistorica)).one().mes is None

    @pytest.mark.parametrize("mes", [0, 13, -1])
    def test_rechaza_un_mes_fuera_de_rango(self, sesion, mes):
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(recurso_id=recurso.id, anio=2025, mes=mes, visitantes=1, fuente="x")
        )

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    @pytest.mark.parametrize("anio", [1999, 2101])
    def test_rechaza_un_anio_fuera_de_rango(self, sesion, anio):
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(recurso_id=recurso.id, anio=anio, mes=1, visitantes=1, fuente="x")
        )

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    def test_rechaza_visitantes_negativos(self, sesion):
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(recurso_id=recurso.id, anio=2025, mes=1, visitantes=-5, fuente="x")
        )

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    def test_cero_visitantes_es_un_dato_valido(self, sesion):
        """Un mes sin visitantes es informacion, no un error."""
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(recurso_id=recurso.id, anio=2025, mes=2, visitantes=0, fuente="x")
        )
        sesion.flush()

        assert sesion.scalars(select(AfluenciaHistorica)).one().visitantes == 0

    def test_no_se_puede_repetir_el_mismo_periodo_y_tipo_de_visitante(self, sesion):
        """uq_afluencia_recurso_periodo, lo que hace idempotente a la carga."""
        recurso = _recurso(sesion)
        comunes = {
            "recurso_id": recurso.id,
            "anio": 2025,
            "mes": 3,
            "tipo_de_visitante": "Turistas Extranjeros",
            "fuente": "x",
        }
        sesion.add(AfluenciaHistorica(visitantes=100, **comunes))
        sesion.flush()

        sesion.add(AfluenciaHistorica(visitantes=200, **comunes))

        with pytest.raises(IntegrityError):
            sesion.flush()

        sesion.rollback()

    def test_el_mismo_periodo_con_otro_tipo_de_visitante_si_se_admite(self, sesion):
        """La ficha del MINCETUR desglosa por tipo, y ese desglose se conserva."""
        recurso = _recurso(sesion)
        comunes = {"recurso_id": recurso.id, "anio": 2025, "mes": 3, "fuente": "x"}
        sesion.add(AfluenciaHistorica(tipo_de_visitante="Extranjeros", visitantes=100, **comunes))
        sesion.add(AfluenciaHistorica(tipo_de_visitante="Nacionales", visitantes=900, **comunes))
        sesion.flush()

        assert len(sesion.scalars(select(AfluenciaHistorica)).all()) == 2

    def test_borrar_el_recurso_se_lleva_su_afluencia(self, sesion):
        """ondelete=CASCADE: no deben quedar filas huérfanas."""
        recurso = _recurso(sesion)
        sesion.add(
            AfluenciaHistorica(recurso_id=recurso.id, anio=2025, mes=4, visitantes=50, fuente="x")
        )
        sesion.flush()

        sesion.delete(recurso)
        sesion.flush()

        assert sesion.scalars(select(AfluenciaHistorica)).all() == []
