"""Puerto: de dónde salen las altitudes del terreno.

El cálculo de pendientes necesita saber a qué altura está cada punto. De dónde
sale ese dato —un modelo digital de elevación descargado de Copernicus, una
tabla en memoria, un servicio ajeno— no es asunto suyo.

Este puerto declara lo único que el cálculo necesita pedir. El adaptador
``src.adapters.outbound.elevacion_copernicus`` lo implementa leyendo teselas
GeoTIFF del disco y descargándolas si faltan; una prueba lo implementa con un
diccionario de tres entradas. Ninguno de los dos aparece en el dominio.

## Por qué ``None`` es un valor legítimo y no un error

Fuera de la cobertura del modelo no hay altitud, y eso no es un fallo: es la
respuesta correcta. Quien pregunta tiene que decidir qué hacer sin ese dato
—aquí se cae al cálculo en línea recta y se declara en el itinerario— en lugar
de recibir un cero que parecería el nivel del mar.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FuenteDeAltitud(Protocol):
    """Responde a qué altura sobre el nivel del mar está un punto."""

    def altitud(self, latitud: float, longitud: float) -> float | None:
        """Metros sobre el nivel del mar, o ``None`` si el punto no tiene dato."""
        ...

    def altitudes(self, puntos: list[tuple[float, float]]) -> list[float | None]:
        """Lo mismo para varios puntos, en el mismo orden en que se pidieron.

        Existe como operación aparte porque la implementación real abre y cierra
        teselas de disco: preguntar de una vez por cuarenta mil nodos y
        preguntar cuarenta mil veces no cuestan lo mismo, aunque el resultado
        sea idéntico.
        """
        ...
