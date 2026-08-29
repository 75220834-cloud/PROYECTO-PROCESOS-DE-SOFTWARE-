"""Pruebas del servicio de recomendación y de su endpoint (Incremento 3)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.base_datos import obtener_sesion
from app.configuracion import Configuracion, obtener_configuracion
from app.main import aplicacion
from app.modelos.preferencias import PreferenciaViaje
from app.servicios.catalogo import importar_inventario
from app.servicios.recomendador import ALCANCE_POR_MOVILIDAD_KM, recomendar
from app.servicios.validacion_catalogo import validar_catalogo

HOY = date.today()


@pytest.fixture
def catalogo(sesion, csv_de_ejemplo):
    """Importa y valida el CSV de ejemplo: 3 recursos, 2 con coordenadas."""
    importar_inventario(sesion, csv_de_ejemplo)
    validar_catalogo(sesion)
    return sesion


def crear_preferencia(sesion, **cambios) -> PreferenciaViaje:
    """Crea una preferencia con valores razonables, cambiando lo que se pida."""
    datos = {
        "usuario_id": None,
        "fecha_inicio": HOY + timedelta(days=30),
        "fecha_fin": HOY + timedelta(days=32),
        "distrito_origen": "HUANCAYO",
        "presupuesto_soles": Decimal("300.00"),
        "intereses": ["iglesias_conventos"],
        "movilidad": "taxi",
        "requiere_accesibilidad": False,
        "idioma": "es",
        "ritmo": "moderado",
    }
    datos.update(cambios)

    preferencia = PreferenciaViaje(**datos)
    sesion.add(preferencia)
    sesion.commit()
    sesion.refresh(preferencia)

    return preferencia


@pytest.fixture
def cliente(sesion):
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


class TestFiltrosDuros:
    """Capa 0. Descarta lo imposible antes de puntuar nada."""

    def test_descarta_los_recursos_sin_coordenadas(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)

        motivos = [d.motivo for d in resultado.descartados]
        assert any("sin coordenadas" in motivo for motivo in motivos)

    def test_cada_descarte_dice_su_motivo(self, catalogo):
        """Es lo que permite explicar por qué no aparece un sitio esperado."""
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)

        assert all(d.motivo.strip() for d in resultado.descartados)

    def test_caminando_alcanza_menos_que_en_taxi(self, catalogo):
        """La movilidad declarada limita de verdad lo que se recomienda."""
        a_pie = recomendar(catalogo, crear_preferencia(catalogo, movilidad="caminando"))
        en_taxi = recomendar(catalogo, crear_preferencia(catalogo, movilidad="taxi"))

        assert ALCANCE_POR_MOVILIDAD_KM["caminando"] < ALCANCE_POR_MOVILIDAD_KM["taxi"]
        assert len(a_pie.recomendaciones) <= len(en_taxi.recomendaciones)

    def test_avisa_si_el_presupuesto_no_alcanza_para_una_visita(self, catalogo):
        preferencia = crear_preferencia(catalogo, presupuesto_soles=Decimal("2.00"))

        resultado = recomendar(catalogo, preferencia)

        assert any("no alcanza" in aviso for aviso in resultado.avisos)

    def test_informa_de_cuantas_visitas_cubre_el_presupuesto(self, catalogo):
        preferencia = crear_preferencia(catalogo, presupuesto_soles=Decimal("80.00"))

        resultado = recomendar(catalogo, preferencia)

        assert any("visitas" in aviso for aviso in resultado.avisos)


class TestRecomendacion:
    def test_recomienda_lo_que_corresponde_al_interes(self, catalogo):
        """Con «iglesias y conventos» debe ganar el Convento de Ocopa."""
        preferencia = crear_preferencia(catalogo, intereses=["iglesias_conventos"])

        resultado = recomendar(catalogo, preferencia)

        assert resultado.recomendaciones
        assert "Convento" in resultado.recomendaciones[0].nombre

    def test_toda_recomendacion_explica_por_que(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)

        for recomendacion in resultado.recomendaciones:
            assert recomendacion.terminos_decisivos or recomendacion.intereses_cubiertos

    def test_toda_recomendacion_trae_su_afluencia_con_motivo(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)

        for recomendacion in resultado.recomendaciones:
            assert recomendacion.afluencia.nivel in ("bajo", "medio", "alto")
            assert recomendacion.afluencia.motivo.strip()

    def test_el_mejor_resultado_tiene_puntaje_relativo_cien(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)

        assert resultado.recomendaciones[0].puntaje_relativo == 100

    def test_estan_ordenadas_de_mayor_a_menor_afinidad(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia)
        puntajes = [r.puntaje_afinidad for r in resultado.recomendaciones]

        assert puntajes == sorted(puntajes, reverse=True)

    def test_respeta_el_limite_pedido(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        resultado = recomendar(catalogo, preferencia, limite=1)

        assert len(resultado.recomendaciones) <= 1


class TestConmutadorDeModelo:
    """La regla de oro: apagar el modelo no puede romper la recomendación."""

    def test_con_el_modelo_apagado_sigue_recomendando(self, catalogo):
        preferencia = crear_preferencia(catalogo)

        con_reglas = recomendar(catalogo, preferencia, usar_modelo_recomendacion=False)

        assert con_reglas.recomendaciones, "sin modelo tiene que seguir recomendando"
        assert con_reglas.generado_por == "reglas"

    def test_deja_constancia_de_la_via_usada(self, catalogo):
        """Trazabilidad: hay que poder saber qué produjo cada resultado."""
        preferencia = crear_preferencia(catalogo)

        con_modelo = recomendar(catalogo, preferencia, usar_modelo_recomendacion=True)
        con_reglas = recomendar(catalogo, preferencia, usar_modelo_recomendacion=False)

        assert all(r.generado_por == "modelo" for r in con_modelo.recomendaciones)
        assert all(r.generado_por == "reglas" for r in con_reglas.recomendaciones)

    def test_ambas_vias_encuentran_el_mismo_mejor_recurso(self, catalogo):
        """Si el modelo no aporta sobre las reglas, se entregan las reglas."""
        preferencia = crear_preferencia(catalogo, intereses=["iglesias_conventos"])

        con_modelo = recomendar(catalogo, preferencia, usar_modelo_recomendacion=True)
        con_reglas = recomendar(catalogo, preferencia, usar_modelo_recomendacion=False)

        assert con_modelo.recomendaciones[0].recurso_id == con_reglas.recomendaciones[0].recurso_id


class TestEndpointDeRecomendaciones:
    def test_recomienda_sin_haber_iniciado_sesion(self, cliente, catalogo):
        """Igual que el asistente: no hace falta cuenta."""
        preferencia = crear_preferencia(catalogo)

        respuesta = cliente.post("/api/recomendaciones", json={"preferencia_id": preferencia.id})

        assert respuesta.status_code == 200
        assert respuesta.json()["total_recomendados"] >= 1

    def test_devuelve_404_si_la_preferencia_no_existe(self, cliente, catalogo):
        respuesta = cliente.post("/api/recomendaciones", json={"preferencia_id": 999999})

        assert respuesta.status_code == 404

    def test_la_respuesta_incluye_los_descartes_y_su_total(self, cliente, catalogo):
        preferencia = crear_preferencia(catalogo)

        cuerpo = cliente.post(
            "/api/recomendaciones", json={"preferencia_id": preferencia.id}
        ).json()

        assert cuerpo["total_descartados"] >= 1
        assert cuerpo["descartados"]

    def test_respeta_los_interruptores_de_la_configuracion(self, cliente, catalogo):
        """Comprobación directa de la regla de oro, a través de la API."""
        preferencia = crear_preferencia(catalogo)

        aplicacion.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
            usar_modelo_recomendacion=False, usar_modelo_afluencia=False
        )

        cuerpo = cliente.post(
            "/api/recomendaciones", json={"preferencia_id": preferencia.id}
        ).json()

        assert cuerpo["generado_por"] == "reglas"
        assert cuerpo["total_recomendados"] >= 1

    def test_rechaza_un_limite_excesivo(self, cliente, catalogo):
        preferencia = crear_preferencia(catalogo)

        respuesta = cliente.post(
            "/api/recomendaciones", json={"preferencia_id": preferencia.id, "limite": 500}
        )

        assert respuesta.status_code == 422


class TestEndpointDeCalendario:
    def test_devuelve_las_fiestas_del_ano(self, cliente):
        cuerpo = cliente.get("/api/calendario/2026").json()

        assert cuerpo["anio"] == 2026
        assert cuerpo["total"] > 0

        nombres = [f["nombre"] for f in cuerpo["festividades"]]
        assert "Semana Santa" in nombres
        assert "Huaconada de Mito" in nombres

    def test_las_fechas_moviles_cambian_de_un_ano_a_otro(self, cliente):
        de_2026 = cliente.get("/api/calendario/2026").json()
        de_2027 = cliente.get("/api/calendario/2027").json()

        def semana_santa(cuerpo):
            return next(f for f in cuerpo["festividades"] if f["nombre"] == "Semana Santa")

        assert semana_santa(de_2026)["fecha_inicio"] != semana_santa(de_2027)["fecha_inicio"]

    def test_responde_para_cualquier_ano_sin_cargar_nada(self, cliente):
        """Las móviles se calculan, así que no hace falta precargar el año."""
        cuerpo = cliente.get("/api/calendario/2045").json()

        assert cuerpo["total"] > 0

    def test_rechaza_un_ano_fuera_de_rango(self, cliente):
        assert cliente.get("/api/calendario/1500").status_code == 422

    def test_consulta_un_dia_concreto(self, cliente):
        # 1 de abril de 2026: Miércoles Santo.
        cuerpo = cliente.get("/api/calendario/dia/2026-04-01").json()

        assert cuerpo["afluencia"]["nivel"] == "alto"
        assert "Semana Santa" in cuerpo["afluencia"]["motivo"]

    def test_la_feria_dominical_aparece_en_huancayo(self, cliente):
        # 10 de mayo de 2026 es domingo.
        cuerpo = cliente.get(
            "/api/calendario/dia/2026-05-10", params={"distrito": "HUANCAYO"}
        ).json()

        assert cuerpo["afluencia"]["nivel"] == "alto"
        assert "Feria Dominical" in cuerpo["afluencia"]["motivo"]
