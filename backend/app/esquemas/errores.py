"""Cómo viaja un error del API, y las respuestas que los endpoints declaran.

## Por qué existe este archivo

Hasta el 25 de septiembre de 2026 el contrato OpenAPI **solo declaraba 200, 201
y 422**, aunque el código lanzaba 404 dieciocho veces, 401 y 403 nueve cada uno
y 409 cuatro. Quien generara un cliente a partir del contrato no sabría que esos
errores existen.

Aquí se declara la forma del error una sola vez y se reutiliza en los
decoradores, en vez de repetir el mismo diccionario en cuarenta sitios.

## La forma del error

Desde la Fase 7 (ver `servicios/avisos.py` y el ADR-013) el backend **no redacta
frases**: manda un código y la interfaz escribe el texto en el idioma que toque.
Los errores siguen esa misma regla:

```json
{ "detail": { "codigo": "sin_recurso" } }
```

Algunos añaden datos al lado del código. `servicio_no_disponible` manda además
la lista de motivos, cada uno con su propio código y parámetros:

```json
{ "detail": { "codigo": "servicio_no_disponible", "motivos": [ ... ] } }
```

## La excepción que todavía no cumple la regla, declarada

**Cinco sitios siguen mandando prosa en español** en vez de un código:

- `utilidades/dependencias.py` — el 401 («Necesitas iniciar sesión para hacer
  esto») y el 403 («Tu rol no tiene permiso para acceder a esto»);
- `rutas/itinerarios.py` — el 422 de fecha fuera del viaje, construido con una
  *f-string*;
- `rutas/coordinacion.py` — dos `detail=str(error)` que reenvían el mensaje de
  la excepción del servicio.

Esas cinco **no se traducen**: salen en español aunque la interfaz esté en
inglés, porque `traducirError` no encuentra la clave y muestra el mensaje tal
cual. Es deuda conocida y está anotada en el registro de defectos.

Por eso `detail` se declara como *código o cadena*: describir solo la forma con
código sería declarar un contrato que el código no cumple todavía.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DetalleConCodigo(BaseModel):
    """El detalle de un error que sí sigue la regla del código."""

    # `extra="allow"` porque algunos errores acompañan el código con datos:
    # `servicio_no_disponible` manda `motivos`. Prohibirlos aquí obligaría a
    # declarar una clase por cada error que lleve algo más.
    model_config = ConfigDict(extra="allow")

    codigo: str = Field(
        description="Código del error. La interfaz lo traduce con `avisos.<codigo>`.",
        examples=["sin_recurso", "servicio_ajeno", "ya_valoraste"],
    )


class ErrorDeLaApi(BaseModel):
    """La respuesta de error del API.

    `detail` es un objeto con `codigo` en la mayoría de los casos, y una cadena
    en los cinco sitios que todavía mandan prosa (ver el docstring del módulo).
    """

    detail: DetalleConCodigo | str


def _respuesta(descripcion: str) -> dict[str, Any]:
    return {"model": ErrorDeLaApi, "description": descripcion}


#: Falta la sesión. Lo emite la dependencia `UsuarioRequerido`.
NO_AUTENTICADO = {401: _respuesta("Hace falta iniciar sesión")}

#: Hay sesión, pero el rol no alcanza, o el recurso es de otra persona.
SIN_PERMISO = {403: _respuesta("El rol no tiene permiso, o el recurso es ajeno")}

#: No existe lo que se pide. También se usa, a propósito, cuando existe pero no
#: es de quien pregunta: responder 403 confirmaría que el identificador existe.
NO_ENCONTRADO = {404: _respuesta("No existe, o no es accesible para quien pregunta")}

#: El estado actual impide la operación: ya valoraste, el correo ya está
#: registrado, la transición de estado no es válida, no quedan plazas.
CONFLICTO = {409: _respuesta("El estado actual no permite esta operación")}

#: Atajos para las combinaciones que más se repiten.
CON_SESION = {**NO_AUTENTICADO, **SIN_PERMISO}
CON_SESION_Y_BUSQUEDA = {**CON_SESION, **NO_ENCONTRADO}
