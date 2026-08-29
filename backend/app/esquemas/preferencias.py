"""Esquemas de las preferencias de viaje del visitante."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modelos.preferencias import INTERESES_VALIDOS

#: Tope de duración de un viaje. Treinta días es holgado para un recorrido por
#: el valle; más que eso indica casi siempre un error al elegir las fechas, y
#: dejarlo pasar haría que el ruteo del Incremento 4 intentara resolver un
#: problema enorme sin sentido.
DIAS_MAXIMOS_DE_VIAJE = 30


class DatosPreferencia(BaseModel):
    """Lo que el visitante responde en el asistente de seis pasos."""

    # Paso 1 — ¿Cuándo viajas?
    fecha_inicio: date
    fecha_fin: date

    # Paso 2 — ¿Desde dónde sales?
    distrito_origen: str = Field(min_length=2, max_length=80)

    # Paso 3 — ¿Cuál es tu presupuesto?
    presupuesto_soles: Decimal = Field(ge=0, le=100_000, decimal_places=2)

    # Paso 4 — ¿Qué te interesa?
    intereses: list[str] = Field(min_length=1, max_length=len(INTERESES_VALIDOS))

    # Paso 5 — ¿Cómo prefieres moverte?
    movilidad: Literal["caminando", "transporte_publico", "taxi", "combinado"]
    requiere_accesibilidad: bool = False

    # Paso 6 — ¿A qué ritmo?
    ritmo: Literal["relajado", "moderado", "intenso"]

    idioma: Literal["es", "en"] = "es"

    @model_validator(mode="after")
    def comprobar_las_fechas(self) -> DatosPreferencia:
        """La fecha de fin no puede ser anterior a la de inicio."""
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio")

        duracion = (self.fecha_fin - self.fecha_inicio).days + 1
        if duracion > DIAS_MAXIMOS_DE_VIAJE:
            raise ValueError(
                f"El viaje no puede durar más de {DIAS_MAXIMOS_DE_VIAJE} días "
                f"(has indicado {duracion})"
            )

        return self

    @model_validator(mode="after")
    def comprobar_los_intereses(self) -> DatosPreferencia:
        """Todos los intereses deben ser de la lista conocida, y sin repetir."""
        desconocidos = sorted(set(self.intereses) - INTERESES_VALIDOS)
        if desconocidos:
            raise ValueError(
                f"Intereses no reconocidos: {', '.join(desconocidos)}. "
                f"Los válidos son: {', '.join(sorted(INTERESES_VALIDOS))}"
            )

        # Se quitan los repetidos conservando el orden en que se marcaron.
        self.intereses = list(dict.fromkeys(self.intereses))
        return self

    @model_validator(mode="after")
    def normalizar_el_distrito(self) -> DatosPreferencia:
        """El distrito se guarda como en el catálogo: mayúsculas y sin tildes."""
        from app.servicios.catalogo import normalizar_texto

        self.distrito_origen = normalizar_texto(self.distrito_origen)
        return self


class PreferenciaPublica(BaseModel):
    """Una preferencia de viaje tal como se devuelve al frontend."""

    id: int
    usuario_id: int | None
    fecha_inicio: date
    fecha_fin: date
    duracion_dias: int
    distrito_origen: str
    presupuesto_soles: Decimal
    intereses: list[str]
    movilidad: str
    requiere_accesibilidad: bool
    idioma: str
    ritmo: str
    creado_en: datetime

    model_config = {"from_attributes": True}


class ListaDePreferencias(BaseModel):
    """Las preferencias guardadas de un usuario, para la página Mis viajes."""

    total: int
    elementos: list[PreferenciaPublica]


class CatalogoDeOpciones(BaseModel):
    """Valores que el frontend necesita para dibujar el asistente.

    Se sirven desde el backend en vez de escribirlos en el frontend para que
    exista una sola fuente de verdad: si mañana se añade un interés, aparece
    solo en la interfaz.
    """

    intereses: list[str]
    movilidades: list[str]
    ritmos: list[str]
    distritos: list[str]
