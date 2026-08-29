"""Hasheo de contraseñas y emisión de tokens de sesión.

Este módulo concentra todo lo que tiene que ver con credenciales, para que sea
el único sitio que revisar cuando se audite la seguridad del proyecto.

Dos decisiones que conviene poder defender:

**Por qué argon2 y no SHA-256.** Un hash como SHA-256 está diseñado para ser
*rápido*, que es exactamente lo contrario de lo que se quiere aquí: quien roba
la base de datos puede probar miles de millones de contraseñas por segundo.
argon2 está diseñado para ser deliberadamente lento y consumir memoria, de
modo que probar contraseñas a lo bruto resulte impracticable. Ganó la
Competición de Hasheo de Contraseñas de 2015 y es la recomendación actual de
OWASP.

**Por qué la sal es automática.** argon2 genera una sal aleatoria por
contraseña y la guarda dentro del propio hash. Por eso dos usuarios con la
misma contraseña tienen hashes distintos, y no sirve de nada precalcular una
tabla de hashes conocidos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.configuracion import obtener_configuracion

# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------

#: Contexto de hasheo. deprecated="auto" permite migrar de algoritmo en el
#: futuro sin invalidar las contraseñas ya guardadas.
contexto_de_hasheo = CryptContext(schemes=["argon2"], deprecated="auto")

#: Longitud mínima de contraseña. Ocho caracteres es el mínimo que recomienda
#: OWASP; se prefiere exigir longitud antes que "una mayúscula y un símbolo",
#: porque las reglas de composición empujan a la gente a usar variantes
#: predecibles como "Contrasena1!".
LONGITUD_MINIMA_DE_CONTRASENA = 8


def hashear_contrasena(contrasena: str) -> str:
    """Convierte una contraseña en su hash argon2.

    La contraseña en claro no se guarda, no se registra en los logs y no sale
    nunca de esta función.
    """
    return contexto_de_hasheo.hash(contrasena)


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    """Comprueba si una contraseña corresponde a un hash.

    Devuelve False ante un hash con formato inválido en vez de lanzar una
    excepción: un registro corrupto en la base de datos no debe tumbar el
    inicio de sesión de todo el mundo.
    """
    try:
        return contexto_de_hasheo.verify(contrasena, hash_guardado)
    except Exception:  # noqa: BLE001 - hash ilegible o algoritmo desconocido
        return False


# ---------------------------------------------------------------------------
# Tokens de sesión (JWT)
# ---------------------------------------------------------------------------

ALGORITMO_DEL_TOKEN = "HS256"


def crear_token_de_acceso(
    id_usuario: int,
    rol: str,
    minutos_de_validez: int | None = None,
) -> str:
    """Emite un token JWT firmado que identifica al usuario.

    El token lleva dentro el identificador y el rol, firmados con la clave
    secreta del servidor. Así el backend puede saber quién hace cada petición
    sin consultar la base de datos.

    Ojo con una idea equivocada frecuente: el contenido de un JWT **no está
    cifrado**, solo firmado. Cualquiera puede leerlo; lo que no puede es
    modificarlo sin invalidar la firma. Por eso aquí no va nada sensible.
    """
    configuracion = obtener_configuracion()
    minutos = minutos_de_validez or configuracion.minutos_expiracion_token

    ahora = datetime.now(UTC)

    contenido: dict[str, Any] = {
        # "sub" (subject) es el campo estándar para el identificador del
        # usuario. Va como texto porque así lo exige la especificación.
        "sub": str(id_usuario),
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
    }

    return jwt.encode(contenido, configuracion.clave_secreta, algorithm=ALGORITMO_DEL_TOKEN)


def leer_token_de_acceso(token: str) -> dict[str, Any] | None:
    """Comprueba la firma de un token y devuelve su contenido.

    Devuelve ``None`` si el token está caducado, mal firmado o manipulado. La
    biblioteca verifica la expiración por su cuenta.
    """
    configuracion = obtener_configuracion()

    try:
        return jwt.decode(token, configuracion.clave_secreta, algorithms=[ALGORITMO_DEL_TOKEN])
    except JWTError:
        return None
