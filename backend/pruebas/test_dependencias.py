"""Pruebas de las dependencias de autenticación de los endpoints.

Son cuatro piezas pequeñas de las que depende **todo** el control de acceso
del backend, así que conviene que estén fijadas una por una y no solo de
refilón al probar un endpoint concreto.

## Las dos reglas que se comprueban aquí

**``obtener_usuario_opcional`` nunca falla.** Un token caducado, manipulado,
sin identificador dentro o con un identificador que no es un número se tratan
exactamente igual que no traer token: el visitante sigue usando la aplicación
sin cuenta. Si alguna de esas rutas lanzara una excepción, un token viejo en
el navegador de alguien tumbaría la página de inicio en vez de limitarse a no
reconocerlo.

**El administrador entra siempre.** ``exigir_rol`` añade el administrador al
conjunto de roles permitidos sin que haya que listarlo en cada endpoint. Es
cómodo y es la clase de cosa que se rompe en silencio al reescribir la
función: nadie notaría que el administrador dejó de entrar hasta que un
administrador lo intentara.

## Los tokens mal formados se firman de verdad

Para probar «token válido con contenido inútil» no sirve inventarse una
cadena: la firma fallaría antes y se estaría probando otra rama. Así que esos
tokens se firman con la clave real del servidor y lo que se altera es su
**contenido**. Es lo que pasaría con un token emitido por una versión anterior
del sistema, o por un servicio que puso otra cosa en ``sub``.

## Nota sobre ``exigir_rol``

A día de hoy **ningún endpoint la usa**: el panel de gestión todavía no
existe. Se prueba igual porque es código de autorización ya escrito y
exportado, y porque la prueba documenta la regla del administrador para quien
lo conecte. Queda anotado aquí para que la decisión sea explícita: si el panel
no llega, la función se borra, no se deja cubierta y sin usar.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from pruebas.conftest import necesita_base_de_datos
from src.base_datos import obtener_sesion
from src.configuracion import obtener_configuracion
from src.modelos.usuario import RolUsuario, Usuario
from src.servicios.seguridad import ALGORITMO_DEL_TOKEN, crear_token_de_acceso
from src.servicios.usuarios import registrar_usuario
from src.utilidades.dependencias import (
    exigir_rol,
    obtener_usuario_opcional,
    obtener_usuario_requerido,
)

pytestmark = necesita_base_de_datos

CONTRASENA = "contrasena_de_prueba"


def _token_firmado(contenido: dict) -> str:
    """Firma un token con la clave real pero con el contenido que se quiera.

    Así la firma es válida y lo que se prueba es cómo se trata un contenido
    que no sirve, que es una rama distinta de «token manipulado».
    """
    ahora = datetime.now(UTC)
    configuracion = obtener_configuracion()

    return jwt.encode(
        {"iat": ahora, "exp": ahora + timedelta(minutes=30), **contenido},
        configuracion.clave_secreta,
        algorithm=ALGORITMO_DEL_TOKEN,
    )


def _credenciales(token: str) -> HTTPAuthorizationCredentials:
    """Lo que FastAPI entrega cuando llega una cabecera Authorization."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _usuario(sesion: Session, rol: str) -> Usuario:
    return registrar_usuario(
        sesion,
        correo=f"{rol}@prueba.pe",
        contrasena=CONTRASENA,
        nombre=f"Usuario {rol}",
        rol=rol,
    )


# ---------------------------------------------------------------------------
# obtener_usuario_opcional: nunca falla
# ---------------------------------------------------------------------------


class TestUsuarioOpcional:
    def test_sin_cabecera_de_autorizacion_no_hay_usuario(self, sesion: Session) -> None:
        assert obtener_usuario_opcional(sesion, None) is None

    def test_con_un_token_valido_devuelve_el_usuario(self, sesion: Session) -> None:
        usuario = _usuario(sesion, RolUsuario.VISITANTE)
        token = crear_token_de_acceso(usuario.id, usuario.rol)

        encontrado = obtener_usuario_opcional(sesion, _credenciales(token))

        assert encontrado is not None
        assert encontrado.id == usuario.id

    def test_un_token_manipulado_se_trata_como_no_traer_ninguno(self, sesion: Session) -> None:
        """No se responde 401: se sigue sin cuenta, que es lo que se pidió."""
        assert obtener_usuario_opcional(sesion, _credenciales("esto.no.es.un.jwt")) is None

    def test_un_token_caducado_se_trata_como_no_traer_ninguno(self, sesion: Session) -> None:
        usuario = _usuario(sesion, RolUsuario.VISITANTE)
        caducado = crear_token_de_acceso(usuario.id, usuario.rol, minutos_de_validez=-1)

        assert obtener_usuario_opcional(sesion, _credenciales(caducado)) is None

    def test_un_token_bien_firmado_pero_sin_identificador_dentro(self, sesion: Session) -> None:
        """El campo «sub» es el que dice de quién es el token.

        Sin él, el token está correctamente firmado y no identifica a nadie.
        """
        token = _token_firmado({"rol": RolUsuario.GESTOR.value})

        assert obtener_usuario_opcional(sesion, _credenciales(token)) is None

    def test_un_identificador_que_no_es_un_numero_no_rompe_la_consulta(
        self, sesion: Session
    ) -> None:
        """Pasarle esto a ``sesion.get()`` daría un error de SQLAlchemy.

        Se filtra antes, y el resultado es «no hay usuario», que es la
        respuesta correcta.
        """
        token = _token_firmado({"sub": "administrador"})

        assert obtener_usuario_opcional(sesion, _credenciales(token)) is None

    def test_un_identificador_nulo_tampoco_rompe_la_consulta(self, sesion: Session) -> None:
        token = _token_firmado({"sub": None})

        assert obtener_usuario_opcional(sesion, _credenciales(token)) is None

    def test_un_usuario_borrado_despues_de_emitir_el_token(self, sesion: Session) -> None:
        """La cuenta ya no está, pero su token sigue siendo válido unos minutos.

        El token no se puede retirar; lo que se comprueba es que el backend
        consulta la base y no se cree el contenido del token sin más.
        """
        usuario = _usuario(sesion, RolUsuario.VISITANTE)
        token = crear_token_de_acceso(usuario.id, usuario.rol)

        sesion.delete(usuario)
        sesion.commit()

        assert obtener_usuario_opcional(sesion, _credenciales(token)) is None


# ---------------------------------------------------------------------------
# obtener_usuario_requerido: aquí sí se exige sesión
# ---------------------------------------------------------------------------


class TestUsuarioRequerido:
    def test_sin_usuario_responde_401_y_dice_como_arreglarlo(self) -> None:
        with pytest.raises(HTTPException) as fallo:
            obtener_usuario_requerido(None)

        assert fallo.value.status_code == 401
        assert "iniciar sesión" in fallo.value.detail
        assert fallo.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_con_usuario_lo_devuelve_tal_cual(self, sesion: Session) -> None:
        usuario = _usuario(sesion, RolUsuario.VISITANTE)

        assert obtener_usuario_requerido(usuario) is usuario


# ---------------------------------------------------------------------------
# exigir_rol, montada en una aplicación de verdad
# ---------------------------------------------------------------------------


@pytest.fixture
def cliente_del_panel(sesion: Session) -> TestClient:
    """Una aplicación mínima con un endpoint que solo admite gestores.

    Se monta aquí y no se usa la aplicación real porque ningún endpoint del
    proyecto declara todavía ``exigir_rol``. Lo que se prueba es la cadena
    completa tal como la ejecutaría FastAPI: cabecera Authorization, token,
    consulta a la base y comprobación del rol.
    """
    panel = FastAPI()

    @panel.get("/panel")
    def ver_el_panel(
        usuario: Annotated[Usuario, Depends(exigir_rol(RolUsuario.GESTOR))],
    ) -> dict:
        return {"rol": usuario.rol}

    panel.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(panel) as cliente:
        yield cliente


def _cabecera(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token_de_acceso(usuario.id, usuario.rol)}"}


class TestExigirRol:
    def test_el_rol_listado_entra(self, cliente_del_panel: TestClient, sesion: Session) -> None:
        gestor = _usuario(sesion, RolUsuario.GESTOR)

        respuesta = cliente_del_panel.get("/panel", headers=_cabecera(gestor))

        assert respuesta.status_code == 200
        assert respuesta.json() == {"rol": RolUsuario.GESTOR.value}

    def test_el_administrador_entra_sin_estar_listado(
        self, cliente_del_panel: TestClient, sesion: Session
    ) -> None:
        """La regla cómoda, y la que se rompería en silencio.

        El endpoint solo pide «gestor». El administrador entra igual porque
        ``exigir_rol`` lo añade siempre, para no tener que repetirlo en cada
        endpoint del proyecto.
        """
        administrador = _usuario(sesion, RolUsuario.ADMINISTRADOR)

        respuesta = cliente_del_panel.get("/panel", headers=_cabecera(administrador))

        assert respuesta.status_code == 200

    def test_un_rol_que_no_toca_recibe_403_y_no_404(
        self, cliente_del_panel: TestClient, sesion: Session
    ) -> None:
        """403 y no 404: el recurso existe, lo que falta es permiso."""
        visitante = _usuario(sesion, RolUsuario.VISITANTE)

        respuesta = cliente_del_panel.get("/panel", headers=_cabecera(visitante))

        assert respuesta.status_code == 403
        assert "permiso" in respuesta.json()["detail"]

    def test_sin_sesion_responde_401_antes_de_mirar_el_rol(
        self, cliente_del_panel: TestClient
    ) -> None:
        """401 y no 403: la diferencia entre «no sé quién eres» y «no puedes»."""
        respuesta = cliente_del_panel.get("/panel")

        assert respuesta.status_code == 401
        assert respuesta.headers["www-authenticate"] == "Bearer"

    def test_se_pueden_listar_varios_roles(self, sesion: Session) -> None:
        """Dos roles permitidos, y el administrador además de los dos."""
        comprobar = exigir_rol(RolUsuario.GESTOR, RolUsuario.OPERADOR)

        gestor = _usuario(sesion, RolUsuario.GESTOR)
        operador = _usuario(sesion, RolUsuario.OPERADOR)
        proveedor = _usuario(sesion, RolUsuario.PROVEEDOR)

        assert comprobar(gestor) is gestor
        assert comprobar(operador) is operador

        with pytest.raises(HTTPException) as fallo:
            comprobar(proveedor)

        assert fallo.value.status_code == 403
