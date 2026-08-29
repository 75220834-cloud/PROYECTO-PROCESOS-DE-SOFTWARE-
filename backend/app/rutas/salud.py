"""Endpoint de salud: informa si la API, la base de datos y Ollama responden.

Sirve para dos cosas concretas:
1. Comprobar de un vistazo que el entorno de desarrollo esta completo.
2. Que el frontend pueda avisar al visitante cuando el asistente
   conversacional no esta disponible, en vez de fallar en silencio
   (exigencia de la Fase 7).
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.configuracion import Configuracion, obtener_configuracion
from app.esquemas.salud import SaludComponente, SaludGeneral

enrutador = APIRouter(prefix="/api", tags=["salud"])

VERSION_APLICACION = "0.1.0"

# Annotated es la forma recomendada de declarar dependencias en FastAPI: se
# define una vez el tipo "una sesion que FastAPI debe inyectar" y se reutiliza.
# Es mas legible que repetir Depends(...) en cada endpoint y evita el problema
# de poner una llamada a funcion como valor por defecto de un parametro.
SesionBD = Annotated[Session, Depends(obtener_sesion)]
ConfiguracionInyectada = Annotated[Configuracion, Depends(obtener_configuracion)]


def _revisar_base_datos(sesion: Session) -> SaludComponente:
    """Comprueba que PostgreSQL responde y que PostGIS esta instalado.

    No basta con que la conexion se abra: sin PostGIS no se pueden guardar
    coordenadas ni calcular distancias, que es el nucleo del proyecto.
    """
    try:
        version_postgis = sesion.execute(text("SELECT postgis_version();")).scalar_one()
        return SaludComponente(estado="operativo", detalle=f"PostGIS {version_postgis}")
    except Exception as error:  # noqa: BLE001 - queremos reportar cualquier fallo
        return SaludComponente(estado="no_disponible", detalle=str(error).splitlines()[0][:200])


def _revisar_ollama(configuracion: Configuracion) -> SaludComponente:
    """Comprueba que el servidor local de Ollama responde y que el modelo esta descargado.

    Se consulta /api/tags, que lista los modelos disponibles. Si Ollama esta
    apagado la peticion falla rapido gracias al tiempo limite de 3 segundos;
    sin ese limite, el endpoint de salud se quedaria colgado.
    """
    try:
        respuesta = httpx.get(f"{configuracion.ollama_url}/api/tags", timeout=3.0)
        respuesta.raise_for_status()
        modelos = [modelo["name"] for modelo in respuesta.json().get("models", [])]
    except Exception as error:  # noqa: BLE001
        return SaludComponente(
            estado="no_disponible",
            detalle=f"No se pudo contactar a Ollama en {configuracion.ollama_url}: {error}"[:200],
        )

    if configuracion.ollama_modelo not in modelos:
        return SaludComponente(
            estado="no_disponible",
            detalle=(
                f"Ollama responde pero el modelo '{configuracion.ollama_modelo}' "
                f"no esta descargado. Disponibles: {', '.join(modelos) or 'ninguno'}"
            )[:200],
        )

    return SaludComponente(
        estado="operativo", detalle=f"Modelo {configuracion.ollama_modelo} listo"
    )


@enrutador.get("/salud", response_model=SaludGeneral, summary="Estado de la plataforma")
def consultar_salud(sesion: SesionBD, configuracion: ConfiguracionInyectada) -> SaludGeneral:
    """Devuelve el estado de la API, de la base de datos y de Ollama.

    Siempre responde 200: el endpoint informa, no falla. Un 500 aqui haria
    imposible distinguir "el servicio de salud esta roto" de "un componente
    esta caido", que es justo lo que se quiere saber.
    """
    base_datos = _revisar_base_datos(sesion)
    ollama = _revisar_ollama(configuracion)

    componentes_caidos = [
        componente for componente in (base_datos, ollama) if componente.estado != "operativo"
    ]

    return SaludGeneral(
        aplicacion="RutaVivaMantaro",
        version=VERSION_APLICACION,
        entorno=configuracion.entorno,
        estado_general="operativo" if not componentes_caidos else "degradado",
        api=SaludComponente(estado="operativo", detalle=f"FastAPI version {VERSION_APLICACION}"),
        base_datos=base_datos,
        ollama=ollama,
    )
