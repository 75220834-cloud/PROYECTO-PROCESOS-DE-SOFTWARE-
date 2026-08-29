"""Pruebas de los endpoints de preferencias de viaje (Incremento 2).

La prueba más importante del archivo es
``test_se_puede_guardar_sin_haber_iniciado_sesion``: sostiene la promesa
central del proyecto, que es armar el viaje sin registrarse.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.base_datos import obtener_sesion
from app.main import aplicacion
from app.servicios.usuarios import registrar_usuario

HOY = date.today()

PREFERENCIA_VALIDA = {
    "fecha_inicio": str(HOY + timedelta(days=7)),
    "fecha_fin": str(HOY + timedelta(days=9)),
    "distrito_origen": "Huancayo",
    "presupuesto_soles": "250.00",
    "intereses": ["artesania", "gastronomia"],
    "movilidad": "combinado",
    "requiere_accesibilidad": False,
    "ritmo": "moderado",
    "idioma": "es",
}


@pytest.fixture
def cliente(sesion):
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


@pytest.fixture
def cabeceras(cliente, sesion):
    """Registra un usuario y devuelve la cabecera con su token."""
    registrar_usuario(
        sesion, correo="visitante@ejemplo.pe", contrasena="unaClaveSegura1", nombre="Visitante"
    )
    respuesta = cliente.post(
        "/api/autenticacion/sesion",
        json={"correo": "visitante@ejemplo.pe", "contrasena": "unaClaveSegura1"},
    )
    return {"Authorization": f"Bearer {respuesta.json()['token_de_acceso']}"}


class TestGuardarPreferencia:
    def test_se_puede_guardar_sin_haber_iniciado_sesion(self, cliente):
        """LA regla del proyecto: no hay que registrarse para empezar.

        Si esta prueba falla, la aplicación está pidiendo cuenta antes de dar
        nada a cambio, que es justo lo que el análisis quería evitar.
        """
        respuesta = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA)

        assert respuesta.status_code == 201
        assert respuesta.json()["usuario_id"] is None

    def test_con_sesion_queda_asociada_a_la_cuenta(self, cliente, cabeceras):
        cuerpo = cliente.post(
            "/api/preferencias", json=PREFERENCIA_VALIDA, headers=cabeceras
        ).json()

        assert cuerpo["usuario_id"] is not None

    def test_calcula_la_duracion_del_viaje(self, cliente):
        cuerpo = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()

        # Del día 7 al 9 son tres días, contando el primero y el último.
        assert cuerpo["duracion_dias"] == 3

    def test_normaliza_el_distrito_como_en_el_catalogo(self, cliente):
        cuerpo = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "distrito_origen": "Concepción"}
        ).json()

        # Se guarda igual que en el catálogo: mayúsculas y sin tildes, para
        # que el ruteo de la Fase 4 pueda cruzarlo sin conversiones.
        assert cuerpo["distrito_origen"] == "CONCEPCION"

    def test_conserva_la_ene_del_distrito(self, cliente):
        cuerpo = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "distrito_origen": "Saño"}
        ).json()

        assert cuerpo["distrito_origen"] == "SAÑO"

    def test_quita_los_intereses_repetidos(self, cliente):
        cuerpo = cliente.post(
            "/api/preferencias",
            json={**PREFERENCIA_VALIDA, "intereses": ["artesania", "artesania", "gastronomia"]},
        ).json()

        assert cuerpo["intereses"] == ["artesania", "gastronomia"]


class TestValidacionDeCadaPaso:
    """Un caso por cada paso del asistente que puede rellenarse mal."""

    def test_paso_1_rechaza_fechas_al_reves(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias",
            json={**PREFERENCIA_VALIDA, "fecha_fin": str(HOY)},
        )

        assert respuesta.status_code == 422

    def test_paso_1_acepta_un_viaje_de_un_solo_dia(self, cliente):
        """Caso borde: salir y volver el mismo día es un viaje válido."""
        mismo_dia = str(HOY + timedelta(days=7))
        respuesta = cliente.post(
            "/api/preferencias",
            json={**PREFERENCIA_VALIDA, "fecha_inicio": mismo_dia, "fecha_fin": mismo_dia},
        )

        assert respuesta.status_code == 201
        assert respuesta.json()["duracion_dias"] == 1

    def test_paso_1_rechaza_un_viaje_demasiado_largo(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias",
            json={**PREFERENCIA_VALIDA, "fecha_fin": str(HOY + timedelta(days=100))},
        )

        assert respuesta.status_code == 422

    def test_paso_2_rechaza_un_distrito_vacio(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "distrito_origen": ""}
        )

        assert respuesta.status_code == 422

    def test_paso_3_rechaza_un_presupuesto_negativo(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "presupuesto_soles": "-50"}
        )

        assert respuesta.status_code == 422

    def test_paso_3_acepta_presupuesto_cero(self, cliente):
        """Caso borde: viajar sin gastar nada es una respuesta legítima."""
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "presupuesto_soles": "0"}
        )

        assert respuesta.status_code == 201

    def test_paso_4_rechaza_no_elegir_ningun_interes(self, cliente):
        respuesta = cliente.post("/api/preferencias", json={**PREFERENCIA_VALIDA, "intereses": []})

        assert respuesta.status_code == 422

    def test_paso_4_rechaza_un_interes_inventado(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "intereses": ["submarinismo"]}
        )

        assert respuesta.status_code == 422
        assert "submarinismo" in str(respuesta.json()["detail"])

    def test_paso_5_rechaza_una_movilidad_desconocida(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "movilidad": "helicoptero"}
        )

        assert respuesta.status_code == 422

    def test_paso_5_guarda_la_marca_de_accesibilidad(self, cliente):
        cuerpo = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "requiere_accesibilidad": True}
        ).json()

        assert cuerpo["requiere_accesibilidad"] is True

    def test_paso_6_rechaza_un_ritmo_desconocido(self, cliente):
        respuesta = cliente.post(
            "/api/preferencias", json={**PREFERENCIA_VALIDA, "ritmo": "frenetico"}
        )

        assert respuesta.status_code == 422


class TestConsultarYActualizar:
    def test_se_puede_consultar_una_preferencia_sin_dueno(self, cliente):
        """Quien la creó sin cuenta guarda el identificador en su navegador."""
        creada = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()

        respuesta = cliente.get(f"/api/preferencias/{creada['id']}")

        assert respuesta.status_code == 200

    def test_una_preferencia_ajena_responde_404(self, cliente, cabeceras, sesion):
        """Se responde 404 y no 403: un 403 confirmaría que existe."""
        del_otro = cliente.post(
            "/api/preferencias", json=PREFERENCIA_VALIDA, headers=cabeceras
        ).json()

        # Ahora se consulta sin sesión, como si fuera otra persona.
        respuesta = cliente.get(f"/api/preferencias/{del_otro['id']}")

        assert respuesta.status_code == 404

    def test_actualiza_una_preferencia(self, cliente):
        creada = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()

        respuesta = cliente.put(
            f"/api/preferencias/{creada['id']}",
            json={**PREFERENCIA_VALIDA, "ritmo": "intenso", "presupuesto_soles": "500.00"},
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["ritmo"] == "intenso"
        assert float(respuesta.json()["presupuesto_soles"]) == 500.0

    def test_una_preferencia_que_no_existe_responde_404(self, cliente):
        assert cliente.get("/api/preferencias/999999").status_code == 404


class TestReclamarPreferencia:
    """El cierre del recorrido: armar sin cuenta, guardar creándola."""

    def test_asocia_a_la_cuenta_una_preferencia_creada_sin_ella(self, cliente, cabeceras):
        sin_cuenta = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()
        assert sin_cuenta["usuario_id"] is None

        respuesta = cliente.post(
            f"/api/preferencias/{sin_cuenta['id']}/reclamar", headers=cabeceras
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["usuario_id"] is not None

    def test_reclamar_dos_veces_no_falla(self, cliente, cabeceras):
        """Caso borde: pulsar dos veces el botón no debe dar error."""
        sin_cuenta = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()

        primera = cliente.post(f"/api/preferencias/{sin_cuenta['id']}/reclamar", headers=cabeceras)
        segunda = cliente.post(f"/api/preferencias/{sin_cuenta['id']}/reclamar", headers=cabeceras)

        assert primera.status_code == segunda.status_code == 200

    def test_no_se_puede_reclamar_sin_sesion(self, cliente):
        sin_cuenta = cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA).json()

        assert cliente.post(f"/api/preferencias/{sin_cuenta['id']}/reclamar").status_code == 401


class TestMisViajes:
    def test_lista_solo_las_preferencias_propias(self, cliente, cabeceras):
        cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA, headers=cabeceras)
        cliente.post("/api/preferencias", json=PREFERENCIA_VALIDA)  # de un anónimo

        cuerpo = cliente.get("/api/preferencias", headers=cabeceras).json()

        assert cuerpo["total"] == 1

    def test_sin_sesion_responde_401(self, cliente):
        assert cliente.get("/api/preferencias").status_code == 401


class TestOpcionesDelAsistente:
    def test_devuelve_los_valores_de_cada_paso(self, cliente):
        cuerpo = cliente.get("/api/preferencias/opciones").json()

        assert len(cuerpo["intereses"]) == 8
        assert set(cuerpo["movilidades"]) == {
            "caminando",
            "transporte_publico",
            "taxi",
            "combinado",
        }
        assert cuerpo["ritmos"] == ["relajado", "moderado", "intenso"]

    def test_no_necesita_sesion(self, cliente):
        """El asistente tiene que poder dibujarse antes de tener cuenta."""
        assert cliente.get("/api/preferencias/opciones").status_code == 200
