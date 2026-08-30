"""Endpoints del asistente conversacional (Fase 7).

    GET  /api/asistente/estado    ¿está Ollama disponible?
    POST /api/asistente/mensaje   una vuelta de conversación

**El asistente no cierra ninguna brecha nueva.** Es capa de interacción: una
forma alternativa de llegar a lo que ya hacen los Incrementos 2, 3 y 4. Si se
apaga, no se pierde ninguna capacidad del sistema.

Por eso el endpoint de estado existe y es lo primero que consulta la interfaz:
para poder ofrecer el camino por formulario **antes** de que alguien escriba un
mensaje y se quede esperando.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.ia.asistente import comprobar_disponibilidad, conversar
from app.utilidades.dependencias import ConfiguracionInyectada, SesionBD

enrutador = APIRouter(prefix="/api/asistente", tags=["asistente"])

#: Cuántos mensajes de la conversación se aceptan. Con veinte cabe una
#: planificación entera; más allá, el contexto del modelo se llena y empieza a
#: olvidar lo del principio sin avisar.
MENSAJES_MAXIMOS = 20


class MensajeDeConversacion(BaseModel):
    """Un turno de la conversación."""

    rol: str = Field(pattern="^(user|assistant)$")
    contenido: str = Field(min_length=1, max_length=4000)


class PeticionAlAsistente(BaseModel):
    """La conversación completa hasta ahora.

    Se manda entera en cada petición y no se guarda en el servidor: el
    asistente no tiene memoria propia. Es deliberado —una conversación es de
    quien la tiene, no del sistema— y además evita tener que expirar sesiones.
    """

    mensajes: list[MensajeDeConversacion] = Field(min_length=1, max_length=MENSAJES_MAXIMOS)
    idioma: str = Field(default="es", pattern="^(es|en)$")


class FuncionUsada(BaseModel):
    """Qué función se ejecutó y con qué argumentos.

    Va en la respuesta para que la conversación sea **auditable**: se puede
    comprobar que lo que dijo el asistente sale de datos del catálogo y no de
    su imaginación.
    """

    nombre: str
    argumentos: dict = Field(default_factory=dict)


class RespuestaDelAsistentePublica(BaseModel):
    """Lo que el asistente contesta."""

    mensaje: str
    funciones_usadas: list[FuncionUsada] = Field(default_factory=list)
    #: Preferencia creada durante la conversación, si se creó alguna. La
    #: interfaz la usa para enlazar al itinerario completo.
    preferencia_id: int | None = None
    esta_disponible: bool = True
    #: Por qué no está disponible, en palabras que se puedan enseñar.
    aviso: str | None = None


class EstadoDelAsistente(BaseModel):
    """Si el asistente se puede usar, y si no, por qué."""

    disponible: bool
    modelo: str
    motivo: str | None = None


@enrutador.get(
    "/estado",
    response_model=EstadoDelAsistente,
    summary="Comprueba si el asistente está disponible",
)
def consultar_estado(configuracion: ConfiguracionInyectada) -> EstadoDelAsistente:
    """Dice si Ollama responde y tiene el modelo.

    La interfaz lo consulta al cargar para decidir si enseña el botón del
    asistente o el aviso con el camino por formulario. **No falla en
    silencio**: si no está, se dice y se dice por qué.
    """
    disponible, motivo = comprobar_disponibilidad(
        configuracion.ollama_url, configuracion.ollama_modelo
    )

    return EstadoDelAsistente(
        disponible=disponible, modelo=configuracion.ollama_modelo, motivo=motivo
    )


@enrutador.post(
    "/mensaje",
    response_model=RespuestaDelAsistentePublica,
    status_code=status.HTTP_200_OK,
    summary="Envía un mensaje al asistente",
)
def enviar_mensaje(
    peticion: PeticionAlAsistente,
    sesion: SesionBD,
    configuracion: ConfiguracionInyectada,
) -> RespuestaDelAsistentePublica:
    """Una vuelta de conversación, con llamada a funciones del backend.

    El modelo elige qué función responde a lo que se le pide, el backend la
    ejecuta contra la base de datos, y el modelo redacta con ese resultado.
    **Nunca inventa datos**: solo puede hablar de lo que devolvieron las
    funciones.

    Si Ollama no está, se responde 200 con ``esta_disponible = false`` y el
    motivo. No es un error del cliente ni del servidor: es una capacidad
    opcional que no está, y la interfaz tiene que poder enseñarlo con calma.
    """
    respuesta = conversar(
        sesion,
        [{"role": m.rol, "content": m.contenido} for m in peticion.mensajes],
        url_ollama=configuracion.ollama_url,
        modelo=configuracion.ollama_modelo,
        idioma=peticion.idioma,
    )

    return RespuestaDelAsistentePublica(
        mensaje=respuesta.mensaje,
        funciones_usadas=[
            FuncionUsada(nombre=f["nombre"], argumentos=f["argumentos"])
            for f in respuesta.funciones_usadas
        ],
        preferencia_id=respuesta.preferencia_id,
        esta_disponible=respuesta.esta_disponible,
        aviso=respuesta.aviso,
    )
