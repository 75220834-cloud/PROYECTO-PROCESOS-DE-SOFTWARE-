"""Dependencias de autenticación para los endpoints.

FastAPI llama a estas funciones antes de ejecutar un endpoint que las declare,
y les pasa la petición. Es la forma de decir "este endpoint necesita un
usuario con sesión iniciada" sin repetir la comprobación en cada uno.

Hay dos niveles a propósito:

- ``UsuarioOpcional``: si hay token válido devuelve el usuario, y si no,
  ``None`` — sin fallar. Lo usan los endpoints que funcionan con y sin cuenta,
  como el de crear una preferencia de viaje.
- ``UsuarioRequerido``: exige sesión iniciada y responde 401 si no la hay.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.configuracion import Configuracion, obtener_configuracion
from app.modelos.usuario import RolUsuario, Usuario
from app.servicios.seguridad import leer_token_de_acceso
from app.servicios.usuarios import obtener_por_id

SesionBD = Annotated[Session, Depends(obtener_sesion)]

#: La configuracion del proyecto, inyectada como dependencia. Se pide asi y no
#: llamando a obtener_configuracion() dentro del endpoint para que las pruebas
#: puedan sustituirla y comprobar el comportamiento con los interruptores de
#: modelo apagados.
ConfiguracionInyectada = Annotated[Configuracion, Depends(obtener_configuracion)]

#: auto_error=False hace que, si no viene cabecera de autorización, FastAPI
#: entregue None en vez de responder 403 por su cuenta. Es lo que permite
#: tener endpoints que funcionan con y sin sesión.
esquema_bearer = HTTPBearer(auto_error=False, description="Token JWT de la sesión")

CredencialesOpcionales = Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)]


def obtener_usuario_opcional(
    sesion: SesionBD,
    credenciales: CredencialesOpcionales,
) -> Usuario | None:
    """Devuelve el usuario de la sesión, o ``None`` si no hay sesión.

    Nunca falla. Un token caducado o manipulado se trata igual que no traer
    ninguno: el visitante sigue pudiendo usar la aplicación sin cuenta.
    """
    if credenciales is None:
        return None

    contenido = leer_token_de_acceso(credenciales.credentials)
    if contenido is None:
        return None

    identificador = contenido.get("sub")
    if identificador is None:
        return None

    try:
        return obtener_por_id(sesion, int(identificador))
    except (TypeError, ValueError):
        return None


def obtener_usuario_requerido(
    usuario: Annotated[Usuario | None, Depends(obtener_usuario_opcional)],
) -> Usuario:
    """Exige que haya una sesión iniciada."""
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Necesitas iniciar sesión para hacer esto",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


UsuarioOpcional = Annotated[Usuario | None, Depends(obtener_usuario_opcional)]
UsuarioRequerido = Annotated[Usuario, Depends(obtener_usuario_requerido)]


def exigir_rol(*roles_permitidos: str):
    """Construye una dependencia que exige uno de los roles indicados.

    Se usa así en un endpoint:

        def panel(usuario: Annotated[Usuario, Depends(exigir_rol('gestor'))]):

    El administrador entra siempre, sin tener que listarlo en cada endpoint.
    """
    permitidos = set(roles_permitidos) | {RolUsuario.ADMINISTRADOR.value}

    def comprobar(usuario: UsuarioRequerido) -> Usuario:
        if usuario.rol not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para acceder a esto",
            )
        return usuario

    return comprobar
