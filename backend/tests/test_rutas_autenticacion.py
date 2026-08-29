"""Pruebas de los endpoints de registro e inicio de sesión."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.base_datos import obtener_sesion
from app.main import aplicacion
from app.modelos.usuario import RolUsuario, Usuario
from app.servicios.usuarios import registrar_usuario

CREDENCIALES = {
    "correo": "italo@ejemplo.pe",
    "contrasena": "unaClaveSegura1",
    "nombre": "Ítalo Reyes",
}


@pytest.fixture
def cliente(sesion):
    """Cliente HTTP que usa la sesión de prueba, que se deshace al terminar."""
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


def cabeceras_con(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRegistro:
    def test_crea_la_cuenta_y_abre_la_sesion(self, cliente):
        """Tras registrarse no hay que iniciar sesión otra vez."""
        respuesta = cliente.post("/api/autenticacion/registro", json=CREDENCIALES)

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["usuario"]["correo"] == "italo@ejemplo.pe"
        assert cuerpo["token_de_acceso"]
        assert cuerpo["tipo_de_token"] == "bearer"

    def test_la_respuesta_nunca_incluye_el_hash(self, cliente):
        """El esquema de salida hace imposible filtrarlo, y se comprueba."""
        cuerpo = cliente.post("/api/autenticacion/registro", json=CREDENCIALES).json()

        assert "hash_contrasena" not in cuerpo["usuario"]
        assert "contrasena" not in cuerpo["usuario"]
        assert CREDENCIALES["contrasena"] not in respuesta_como_texto(cuerpo)

    def test_guarda_la_contrasena_hasheada(self, cliente, sesion):
        """La comprobación que exige la lista de verificación de la fase."""
        cliente.post("/api/autenticacion/registro", json=CREDENCIALES)

        usuario = sesion.scalars(select(Usuario).where(Usuario.correo == "italo@ejemplo.pe")).one()

        assert usuario.hash_contrasena.startswith("$argon2id$")
        assert CREDENCIALES["contrasena"] not in usuario.hash_contrasena

    def test_toda_cuenta_nueva_es_de_rol_visitante(self, cliente):
        """Nadie puede registrarse directamente como gestor o administrador."""
        cuerpo = cliente.post(
            "/api/autenticacion/registro",
            json={**CREDENCIALES, "rol": "administrador"},  # se intenta colar
        ).json()

        assert cuerpo["usuario"]["rol"] == RolUsuario.VISITANTE.value

    def test_normaliza_el_correo_a_minusculas(self, cliente):
        cuerpo = cliente.post(
            "/api/autenticacion/registro",
            json={**CREDENCIALES, "correo": "  ITALO@Ejemplo.PE  "},
        ).json()

        assert cuerpo["usuario"]["correo"] == "italo@ejemplo.pe"

    def test_rechaza_un_correo_ya_registrado(self, cliente):
        cliente.post("/api/autenticacion/registro", json=CREDENCIALES)
        repetido = cliente.post("/api/autenticacion/registro", json=CREDENCIALES)

        assert repetido.status_code == 409

    def test_detecta_el_correo_repetido_aunque_cambien_las_mayusculas(self, cliente):
        """Caso borde: "Italo@X" e "italo@x" son la misma persona."""
        cliente.post("/api/autenticacion/registro", json=CREDENCIALES)
        repetido = cliente.post(
            "/api/autenticacion/registro", json={**CREDENCIALES, "correo": "ITALO@EJEMPLO.PE"}
        )

        assert repetido.status_code == 409

    @pytest.mark.parametrize(
        ("campo", "valor"),
        [
            ("contrasena", "corta"),  # menos de 8 caracteres
            ("contrasena", "        "),  # solo espacios
            ("correo", "esto no es un correo"),
            ("nombre", "X"),  # menos de 2 caracteres
        ],
    )
    def test_rechaza_datos_invalidos(self, cliente, campo, valor):
        respuesta = cliente.post("/api/autenticacion/registro", json={**CREDENCIALES, campo: valor})

        assert respuesta.status_code == 422


class TestInicioDeSesion:
    def test_devuelve_un_token_valido(self, cliente, sesion):
        registrar_usuario(sesion, **CREDENCIALES)

        respuesta = cliente.post(
            "/api/autenticacion/sesion",
            json={"correo": CREDENCIALES["correo"], "contrasena": CREDENCIALES["contrasena"]},
        )

        assert respuesta.status_code == 200
        token = respuesta.json()["token_de_acceso"]

        # El token sirve de verdad para identificarse.
        yo = cliente.get("/api/autenticacion/yo", headers=cabeceras_con(token))
        assert yo.status_code == 200
        assert yo.json()["correo"] == CREDENCIALES["correo"]

    def test_rechaza_la_contrasena_incorrecta(self, cliente, sesion):
        registrar_usuario(sesion, **CREDENCIALES)

        respuesta = cliente.post(
            "/api/autenticacion/sesion",
            json={"correo": CREDENCIALES["correo"], "contrasena": "equivocada"},
        )

        assert respuesta.status_code == 401

    def test_da_el_mismo_mensaje_si_el_correo_no_existe(self, cliente, sesion):
        """Decisión de seguridad deliberada.

        Si el mensaje distinguiera «ese correo no existe» de «contraseña
        incorrecta», cualquiera podría averiguar qué correos están registrados
        en la plataforma probándolos uno a uno.
        """
        registrar_usuario(sesion, **CREDENCIALES)

        mala_contrasena = cliente.post(
            "/api/autenticacion/sesion",
            json={"correo": CREDENCIALES["correo"], "contrasena": "equivocada"},
        )
        correo_inexistente = cliente.post(
            "/api/autenticacion/sesion",
            json={"correo": "nadie@ejemplo.pe", "contrasena": "equivocada"},
        )

        assert mala_contrasena.status_code == correo_inexistente.status_code == 401
        assert mala_contrasena.json()["detail"] == correo_inexistente.json()["detail"]

    def test_no_deja_entrar_a_una_cuenta_desactivada(self, cliente, sesion):
        usuario = registrar_usuario(sesion, **CREDENCIALES)
        usuario.esta_activo = False
        sesion.commit()

        respuesta = cliente.post(
            "/api/autenticacion/sesion",
            json={"correo": CREDENCIALES["correo"], "contrasena": CREDENCIALES["contrasena"]},
        )

        assert respuesta.status_code == 401


class TestSesionActual:
    def test_sin_token_responde_401(self, cliente):
        assert cliente.get("/api/autenticacion/yo").status_code == 401

    def test_con_un_token_invalido_responde_401(self, cliente):
        respuesta = cliente.get("/api/autenticacion/yo", headers=cabeceras_con("inventado"))

        assert respuesta.status_code == 401


def respuesta_como_texto(cuerpo: dict) -> str:
    """Serializa la respuesta para poder buscar dentro secretos filtrados."""
    import json

    return json.dumps(cuerpo, ensure_ascii=False)
