"""Esquemas de registro, inicio de sesión y usuario."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.servicios.seguridad import LONGITUD_MINIMA_DE_CONTRASENA


class SolicitudRegistro(BaseModel):
    """Datos para crear una cuenta nueva."""

    # EmailStr valida el formato del correo antes de que llegue a la lógica.
    correo: EmailStr
    contrasena: str = Field(
        min_length=LONGITUD_MINIMA_DE_CONTRASENA,
        max_length=128,
        description=f"Al menos {LONGITUD_MINIMA_DE_CONTRASENA} caracteres",
    )
    nombre: str = Field(min_length=2, max_length=160)
    idioma_preferido: Literal["es", "en"] = "es"

    @field_validator("contrasena")
    @classmethod
    def contrasena_no_puede_ser_solo_espacios(cls, valor: str) -> str:
        """Caso borde: ocho espacios cumplen la longitud mínima pero no valen."""
        if not valor.strip():
            raise ValueError("La contraseña no puede estar formada solo por espacios")
        return valor

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < 2:
            raise ValueError("El nombre debe tener al menos dos caracteres")
        return limpio


class SolicitudInicioSesion(BaseModel):
    """Credenciales para iniciar sesión."""

    correo: EmailStr
    contrasena: str


class UsuarioPublico(BaseModel):
    """Datos de un usuario que sí se pueden mostrar.

    Nótese lo que NO está aquí: el hash de la contraseña. Al declarar un
    esquema de salida explícito, es imposible que se filtre por accidente
    aunque alguien devuelva el objeto completo del modelo.
    """

    id: int
    correo: str
    nombre: str
    rol: str
    idioma_preferido: str
    creado_en: datetime

    model_config = {"from_attributes": True}


class RespuestaSesion(BaseModel):
    """Lo que devuelven el registro y el inicio de sesión."""

    token_de_acceso: str
    tipo_de_token: Literal["bearer"] = "bearer"
    expira_en_minutos: int
    usuario: UsuarioPublico
