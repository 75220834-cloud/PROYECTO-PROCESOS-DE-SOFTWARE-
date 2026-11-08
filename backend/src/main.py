"""Punto de entrada de la API de RutaVivaMantaro.

Se levanta con:
    uvicorn src.main:aplicacion --reload

La documentacion interactiva de todos los endpoints queda en
http://localhost:8000/docs (la genera FastAPI a partir de los esquemas
de Pydantic, sin escribirla a mano).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.configuracion import obtener_configuracion
from src.rutas import (
    asistente,
    autenticacion,
    catalogo,
    coordinacion,
    itinerarios,
    preferencias,
    recomendaciones,
    salud,
    valoraciones,
)

aplicacion = FastAPI(
    title="RutaVivaMantaro",
    description=(
        "API de la plataforma de turismo inteligente para la Ruta del Valle del Mantaro "
        "(Junin, Peru). Proyecto del curso Procesos de Software, Universidad Continental."
    ),
    version="0.1.0",
    docs_url="/docs",
)

# CORS: el navegador bloquea por seguridad que una pagina servida desde un
# origen (http://localhost:5173, el frontend de Vite) llame a otro
# (http://localhost:8000, la API). Esta lista autoriza explicitamente a quien
# puede llamar.
#
# Sale de la configuracion y ya no esta escrita aqui: al desplegar, el frontend
# vive en otro dominio, y con la lista fija en el codigo el navegador rechazaba
# todas sus llamadas. Sin la variable de entorno el valor por omision sigue
# siendo el frontend de desarrollo, asi que en local no cambia nada.
#
# Se siguen declarando los origenes uno a uno en vez de poner "*": con
# allow_credentials=True, un comodin seria exactamente el agujero que este
# middleware existe para evitar.
ORIGENES_PERMITIDOS = obtener_configuracion().lista_de_origenes

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

aplicacion.include_router(salud.enrutador)
aplicacion.include_router(catalogo.enrutador)
aplicacion.include_router(autenticacion.enrutador)
aplicacion.include_router(preferencias.enrutador)
aplicacion.include_router(recomendaciones.enrutador)
aplicacion.include_router(itinerarios.enrutador)
aplicacion.include_router(coordinacion.enrutador)
aplicacion.include_router(valoraciones.enrutador)
aplicacion.include_router(asistente.enrutador)


@aplicacion.get("/", tags=["salud"], summary="Mensaje de bienvenida")
def raiz() -> dict[str, str]:
    """Confirma que la API esta viva y orienta hacia la documentacion."""
    return {
        "mensaje": "API de RutaVivaMantaro",
        "documentacion": "/docs",
        "salud": "/api/salud",
    }
