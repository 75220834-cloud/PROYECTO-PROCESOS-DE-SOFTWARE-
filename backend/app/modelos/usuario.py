"""Tabla de usuarios de la plataforma.

Nota importante de diseño: **la aplicación se puede usar sin cuenta.** Un
visitante puede armar su itinerario completo sin registrarse; la cuenta solo
sirve para guardarlo y volver a él. Por eso las preferencias admiten
``usuario_id`` nulo y esta tabla no es un requisito para nada del recorrido
principal.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.base_datos import Base


class RolUsuario(StrEnum):
    """Los cinco perfiles que participan en el proceso.

    Se usa StrEnum y no una tabla de roles porque el conjunto está cerrado por
    el análisis del proyecto: son exactamente los actores identificados en las
    siete brechas. Una tabla añadiría una consulta por petición sin aportar
    flexibilidad que nadie va a usar.
    """

    VISITANTE = "visitante"
    OPERADOR = "operador"
    PROVEEDOR = "proveedor"
    GESTOR = "gestor"
    ADMINISTRADOR = "administrador"


class Usuario(Base):
    """Una persona registrada en la plataforma."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)

    # El correo identifica al usuario. Se guarda siempre en minúsculas para
    # que "Italo@X.com" e "italo@x.com" no creen dos cuentas distintas.
    correo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # NUNCA la contraseña, solo su hash argon2. El nombre de la columna lo
    # deja explícito para que nadie se confunda al leer el modelo.
    hash_contrasena: Mapped[str] = mapped_column(String(255), nullable=False)

    nombre: Mapped[str] = mapped_column(String(160), nullable=False)

    rol: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RolUsuario.VISITANTE, index=True
    )

    idioma_preferido: Mapped[str] = mapped_column(String(5), nullable=False, default="es")

    esta_activo: Mapped[bool] = mapped_column(nullable=False, default=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # La restricción vive también en la base de datos, no solo en Python:
        # así ningún script de carga ni consulta manual puede meter un rol
        # inventado sin que PostgreSQL lo rechace.
        CheckConstraint(
            "rol IN ('visitante', 'operador', 'proveedor', 'gestor', 'administrador')",
            name="ck_usuario_rol",
        ),
        CheckConstraint("idioma_preferido IN ('es', 'en')", name="ck_usuario_idioma"),
    )

    def __repr__(self) -> str:
        return f"<Usuario {self.correo} ({self.rol})>"
