"""Endpoints de registro, inicio de sesión y sesión actual.

- ``POST /api/autenticacion/registro``  crea una cuenta
- ``POST /api/autenticacion/sesion``    inicia sesión
- ``GET  /api/autenticacion/yo``        devuelve quién tiene la sesión abierta
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.configuracion import obtener_configuracion
from app.esquemas.autenticacion import (
    RespuestaSesion,
    SolicitudInicioSesion,
    SolicitudRegistro,
    UsuarioPublico,
)
from app.modelos.usuario import Usuario
from app.servicios.seguridad import crear_token_de_acceso
from app.servicios.usuarios import CorreoYaRegistrado, autenticar, registrar_usuario
from app.utilidades.dependencias import SesionBD, UsuarioRequerido

enrutador = APIRouter(prefix="/api/autenticacion", tags=["autenticacion"])


def _construir_respuesta(usuario: Usuario) -> RespuestaSesion:
    """Arma la respuesta con el token y los datos públicos del usuario."""
    configuracion = obtener_configuracion()

    return RespuestaSesion(
        token_de_acceso=crear_token_de_acceso(usuario.id, usuario.rol),
        expira_en_minutos=configuracion.minutos_expiracion_token,
        usuario=UsuarioPublico.model_validate(usuario),
    )


@enrutador.post(
    "/registro",
    response_model=RespuestaSesion,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una cuenta",
)
def registrar(solicitud: SolicitudRegistro, sesion: SesionBD) -> RespuestaSesion:
    """Registra un usuario nuevo y le abre la sesión de inmediato.

    Se devuelve el token junto con la cuenta creada para que el visitante no
    tenga que iniciar sesión otra vez justo después de registrarse.

    Todas las cuentas creadas aquí son de rol *visitante*. Los roles de
    operador, proveedor y gestor los asigna un administrador: si se pudieran
    elegir al registrarse, cualquiera se haría gestor.
    """
    try:
        usuario = registrar_usuario(
            sesion,
            correo=solicitud.correo,
            contrasena=solicitud.contrasena,
            nombre=solicitud.nombre,
            idioma_preferido=solicitud.idioma_preferido,
        )
    except CorreoYaRegistrado as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        ) from error

    return _construir_respuesta(usuario)


@enrutador.post("/sesion", response_model=RespuestaSesion, summary="Inicia sesión")
def iniciar_sesion(solicitud: SolicitudInicioSesion, sesion: SesionBD) -> RespuestaSesion:
    """Comprueba las credenciales y devuelve un token de sesión."""
    usuario = autenticar(sesion, solicitud.correo, solicitud.contrasena)

    if usuario is None:
        # El mismo mensaje tanto si el correo no existe como si la contraseña
        # es incorrecta. Distinguirlos permitiría averiguar qué correos están
        # registrados probándolos uno a uno.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _construir_respuesta(usuario)


@enrutador.get("/yo", response_model=UsuarioPublico, summary="Datos de la sesión actual")
def obtener_sesion_actual(usuario: UsuarioRequerido) -> UsuarioPublico:
    """Devuelve los datos del usuario con la sesión abierta.

    El frontend lo usa al cargar para saber si el token guardado sigue siendo
    válido, sin tener que pedir la contraseña otra vez.
    """
    return UsuarioPublico.model_validate(usuario)
