"""Configuracion de la aplicacion, leida desde el archivo .env.

Usamos pydantic-settings en lugar de leer variables de entorno a mano porque
valida los tipos al arrancar: si alguien escribe POSTGRES_PUERTO=abc, la
aplicacion falla de inmediato con un mensaje claro, en vez de romperse mas
tarde dentro de una peticion.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# El archivo .env vive en la raiz del repositorio, un nivel por encima de
# backend/. Lo resolvemos desde la ubicacion de este archivo para que funcione
# sin importar desde que carpeta se lance el servidor.
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_ENV = RAIZ_REPOSITORIO / ".env"


class Configuracion(BaseSettings):
    """Todas las variables de configuracion del backend."""

    model_config = SettingsConfigDict(
        env_file=RUTA_ENV,
        env_file_encoding="utf-8",
        # Ignora variables del .env que este backend no usa (por ejemplo las
        # que empiezan con VITE_ y son solo para el frontend).
        extra="ignore",
    )

    # --- Base de datos -----------------------------------------------------
    postgres_usuario: str = "rutaviva"
    postgres_contrasena: str = "cambia_esta_contrasena"
    postgres_base: str = "rutavivamantaro"
    postgres_host: str = "localhost"
    postgres_puerto: int = 5432

    # --- Aplicacion --------------------------------------------------------
    entorno: str = "desarrollo"
    clave_secreta: str = "clave_insegura_solo_para_desarrollo"
    minutos_expiracion_token: int = 1440

    # --- Ollama (asistente conversacional local) ---------------------------
    ollama_url: str = "http://localhost:11434"
    ollama_modelo: str = "qwen2.5:7b-instruct"

    # --- Interruptores de modelo (regla de oro de la IA) -------------------
    # Cada funcionalidad con modelo tiene una alternativa por reglas
    # explicitas. Poniendo estas variables en false, el sistema completo
    # sigue funcionando sin ningun modelo entrenado. Es el mecanismo de
    # control de riesgo declarado en el documento academico.
    usar_modelo_recomendacion: bool = True
    usar_modelo_afluencia: bool = True
    usar_modelo_sentimiento: bool = True

    @property
    def url_base_datos(self) -> str:
        """Cadena de conexion de SQLAlchemy para PostgreSQL con el driver psycopg 3."""
        return (
            f"postgresql+psycopg://{self.postgres_usuario}:{self.postgres_contrasena}"
            f"@{self.postgres_host}:{self.postgres_puerto}/{self.postgres_base}"
        )


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve la configuracion, leyendola del disco una sola vez.

    lru_cache guarda el resultado: el archivo .env se lee en la primera llamada
    y las siguientes reutilizan el mismo objeto. Ademas permite sustituir la
    configuracion en las pruebas sobreescribiendo esta funcion.
    """
    return Configuracion()
