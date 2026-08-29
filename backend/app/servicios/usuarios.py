"""Registro, autenticación y consulta de usuarios."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.usuario import RolUsuario, Usuario
from app.servicios.seguridad import hashear_contrasena, verificar_contrasena


class CorreoYaRegistrado(Exception):
    """Se intentó registrar un correo que ya existe."""


def normalizar_correo(correo: str) -> str:
    """Deja el correo en minúsculas y sin espacios.

    Sin esto, "Italo@X.com" e "italo@x.com" crearían dos cuentas distintas y
    el usuario no entendería por qué su contraseña "no funciona".
    """
    return correo.strip().lower()


def buscar_por_correo(sesion: Session, correo: str) -> Usuario | None:
    """Devuelve el usuario con ese correo, o ``None`` si no existe."""
    return sesion.scalars(
        select(Usuario).where(Usuario.correo == normalizar_correo(correo))
    ).first()


def registrar_usuario(
    sesion: Session,
    correo: str,
    contrasena: str,
    nombre: str,
    rol: str = RolUsuario.VISITANTE,
    idioma_preferido: str = "es",
) -> Usuario:
    """Crea una cuenta nueva.

    Lanza ``CorreoYaRegistrado`` si el correo ya está en uso.
    """
    correo_normalizado = normalizar_correo(correo)

    if buscar_por_correo(sesion, correo_normalizado) is not None:
        raise CorreoYaRegistrado(correo_normalizado)

    usuario = Usuario(
        correo=correo_normalizado,
        hash_contrasena=hashear_contrasena(contrasena),
        nombre=nombre.strip(),
        rol=rol,
        idioma_preferido=idioma_preferido,
    )

    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)

    return usuario


def autenticar(sesion: Session, correo: str, contrasena: str) -> Usuario | None:
    """Comprueba unas credenciales y devuelve el usuario si son correctas.

    Devuelve ``None`` tanto si el correo no existe como si la contraseña es
    incorrecta, **a propósito**: distinguir ambos casos permitiría averiguar
    qué correos están registrados en la plataforma probándolos uno a uno.
    """
    usuario = buscar_por_correo(sesion, correo)

    if usuario is None:
        # Se gasta el mismo tiempo que en una verificación real. Si se
        # devolviera aquí de inmediato, la diferencia de tiempo de respuesta
        # revelaría qué correos existen: es un ataque de temporización.
        verificar_contrasena(contrasena, "$argon2id$v=19$m=65536,t=3,p=4$c2FsZmFsc2E$" + "x" * 43)
        return None

    if not usuario.esta_activo:
        return None

    if not verificar_contrasena(contrasena, usuario.hash_contrasena):
        return None

    return usuario


def obtener_por_id(sesion: Session, id_usuario: int) -> Usuario | None:
    """Devuelve el usuario con ese identificador."""
    return sesion.get(Usuario, id_usuario)
