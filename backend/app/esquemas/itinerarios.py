"""Esquemas del itinerario geoespacial (Incremento 4)."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.esquemas.avisos import AvisoPublico


class SolicitudItinerario(BaseModel):
    """Petición para armar el itinerario de un día."""

    preferencia_id: int

    #: Día concreto que se quiere planificar. Si no se indica, el primero del
    #: viaje. Cada día se optimiza por separado porque el visitante duerme
    #: entre medias y el problema se parte de forma natural.
    fecha: date | None = None

    hora_inicio: time | None = None
    hora_fin: time | None = None

    #: Si se guarda en la base de datos o solo se calcula. Calcular sin
    #: guardar permite que el visitante pruebe combinaciones sin llenar la
    #: tabla de borradores que nunca va a mirar.
    guardar: bool = False

    titulo: str | None = Field(default=None, max_length=200)


class SolicitudViaje(BaseModel):
    """Petición para armar **todos** los días del viaje de una vez.

    No lleva fecha, a diferencia de :class:`SolicitudItinerario`: el viaje son
    todas las fechas de la preferencia, de la de inicio a la de fin. Pedirlos
    juntos es lo que permite que ningún día repita los lugares de otro, porque
    el reparto se decide con los días delante.
    """

    preferencia_id: int

    hora_inicio: time | None = None
    hora_fin: time | None = None

    #: Si se guardan los días en la base de datos o solo se calculan.
    guardar: bool = False


class TrasladoPublico(BaseModel):
    """El desplazamiento desde la parada anterior hasta esta."""

    modo: Literal["caminando", "combi", "colectivo", "taxi"]
    minutos: int
    distancia_km: float
    desnivel_m: float

    #: Rango, nunca un precio único: en el valle no hay tarifa oficial única.
    precio_min_soles: Decimal
    precio_max_soles: Decimal

    #: ``true`` cuando el precio salió de la fórmula de estimación y no de una
    #: tarifa consultada. La interfaz lo distingue con una marca visible.
    es_estimado: bool
    fuente: str
    fecha_referencia: date

    #: ``red_vial`` si la distancia se calculó sobre el grafo de OpenStreetMap;
    #: ``linea_recta`` si no había red cerca y hubo que estimarla. Con
    #: ``linea_recta`` la interfaz muestra el aviso de tramo estimado.
    origen_del_calculo: Literal["red_vial", "linea_recta"]

    #: Coordenadas ``[latitud, longitud]`` del camino, para dibujarlo en el
    #: mapa. Vacío cuando el tramo se estimó y no hay ruta que dibujar.
    trazado: list[tuple[float, float]] = Field(default_factory=list)


class ParadaPublica(BaseModel):
    """Una parada del itinerario, con su horario y cómo se llega a ella."""

    orden: int
    recurso_id: int
    nombre: str
    distrito: str
    categoria: str | None = None

    latitud: float
    longitud: float
    altitud_msnm: int | None = None

    hora_llegada: time
    hora_salida: time
    duracion_visita_min: int

    #: De 0 a 100 respecto al mejor resultado de esta búsqueda. No es una
    #: probabilidad.
    puntaje_relativo: int

    #: ``null`` en la primera parada: no se llega a ella desde ningún sitio.
    traslado: TrasladoPublico | None = None


class RespuestaItinerario(BaseModel):
    """El itinerario de un día, con sus totales y sus avisos."""

    #: ``null`` si se calculó sin guardar.
    itinerario_id: int | None = None
    preferencia_id: int
    fecha: date
    titulo: str

    #: ``modelo`` (OR-Tools) o ``reglas`` (vecino más cercano). Es la
    #: trazabilidad que exige la regla de oro de la IA del proyecto.
    generado_por: Literal["modelo", "reglas"]

    paradas: list[ParadaPublica] = Field(default_factory=list)

    tiempo_total_min: int
    costo_min_soles: Decimal
    costo_max_soles: Decimal
    distancia_total_km: float
    subida_total_m: float

    #: ``suave``, ``moderado`` o ``exigente``, según el desnivel positivo
    #: acumulado. Solo cuenta la subida: bajar lo que se ha subido no descansa
    #: las piernas.
    esfuerzo: Literal["suave", "moderado", "exigente"]

    #: ``true`` si algún tramo se calculó en línea recta. La interfaz muestra
    #: un aviso visible cuando lo es.
    hay_tramos_estimados: bool

    #: Avisos que el visitante tiene que leer: tramos estimados, altitud,
    #: esfuerzo del día, horarios desconocidos.
    avisos: list[AvisoPublico] = Field(default_factory=list)


class RespuestaViaje(BaseModel):
    """El viaje completo: un itinerario por cada día, sin lugares repetidos."""

    preferencia_id: int
    fecha_inicio: date
    fecha_fin: date

    #: Un día por cada fecha del viaje, en orden. El primero es el mejor día
    #: posible; cada siguiente es el mejor de lo que no se usó antes. Un día
    #: puede venir sin paradas si ya no quedaban lugares nuevos, y en ese caso
    #: trae el aviso que lo explica.
    dias: list[RespuestaItinerario] = Field(default_factory=list)


class SolicitudReordenar(SolicitudItinerario):
    """Nuevo orden de las paradas, para recalcular tras arrastrarlas.

    Hereda de :class:`SolicitudItinerario` en vez de ser un segundo modelo de
    cuerpo, para que la petición sea un único objeto JSON plano. Con dos
    modelos, FastAPI los anidaría bajo sus nombres de parámetro y el cliente
    tendría que enviar ``{"solicitud": {...}, "orden": {...}}``, que no se
    parece a nada de lo que envía el resto de la API.
    """

    #: Identificadores de recurso en el orden que quiere el visitante.
    recursos_en_orden: list[int] = Field(min_length=1, max_length=20)
