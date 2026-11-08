"""Cómo viaja un aviso por el API.

El razonamiento de por qué los avisos son código y parámetros en vez de frases
está en `app/servicios/avisos.py`. Aquí solo está la forma que toman al salir
por HTTP.

Se declara en su propio archivo porque lo usan tres esquemas distintos
—itinerarios, recomendaciones y valoraciones— y meterlo en cualquiera de ellos
obligaría a los otros dos a importar de un módulo que no les corresponde.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AvisoPublico(BaseModel):
    """Un aviso, sin redactar.

    La interfaz lo convierte en frase con ``t('avisos.' + codigo, parametros)``.
    """

    # Los servicios construyen `servicios.avisos.Aviso`, que es una dataclass,
    # no un modelo de Pydantic. Sin esto habría que convertir a mano en cada
    # ruta, y olvidarlo en una sola daría un 500 en producción en vez de un
    # error al arrancar. Con `from_attributes` la conversión es automática.
    model_config = ConfigDict(from_attributes=True)

    #: Qué se avisa. Coincide con una clave bajo ``avisos`` en los archivos de
    #: idioma del frontend.
    codigo: str = Field(examples=["altitud"])

    #: Los datos que la frase necesita. Van sin tipar a propósito: cada aviso
    #: lleva los suyos, y declarar una unión de veintinueve formas distintas
    #: haría el esquema ilegible sin impedir ningún error real —el que importa,
    #: que un parámetro falte, lo detecta la prueba de traducciones—.
    parametros: dict[str, Any] = Field(default_factory=dict, examples=[{"metros": 3706}])
