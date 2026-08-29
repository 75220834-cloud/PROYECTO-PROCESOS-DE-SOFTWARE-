"""Servicio de recomendación (Incremento 3).

Junta las tres capas que cierran las brechas 2 y 3:

- **Capa 0 — filtros duros.** Lógica explícita, **no es IA**. Descarta lo que
  no cabe: sin coordenadas, fuera de presupuesto, incompatible con la
  movilidad declarada. Un recurso descartado aquí no llega a puntuarse.
- **Capa 1 — afinidad.** Ordena lo que sí cabe según los intereses.
- **Capa 2 — afluencia.** Añade a cada recomendación cuánta gente se espera.

**Por qué los filtros van primero y son reglas explícitas.** Porque son
restricciones, no preferencias. Un recurso sin coordenadas no puede entrar en
un itinerario por mucha afinidad que tenga: dejar que un modelo «decida» eso
sería confundir lo imposible con lo poco recomendable. Además, cada descarte
queda registrado con su motivo, y eso es lo que hace auditable el proceso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.ia.afinidad import RecursoParaPuntuar, calcular_afinidad
from app.ia.afluencia import PrediccionAfluencia, predecir_afluencia
from app.modelos.catalogo import RecursoTuristico
from app.modelos.preferencias import PreferenciaViaje

# ---------------------------------------------------------------------------
# Capa 0 — filtros duros
# ---------------------------------------------------------------------------

#: Alcance máximo, en kilómetros, según cómo se mueva el visitante.
#:
#: Son distancias en línea recta desde el distrito de origen, y sirven solo
#: para descartar lo inalcanzable. El cálculo real sobre la red vial llega en
#: el Incremento 4; hasta entonces esto es un filtro grueso y se dice así.
ALCANCE_POR_MOVILIDAD_KM: dict[str, float] = {
    "caminando": 8.0,  # una caminata larga, sin transporte
    "transporte_publico": 45.0,  # combis y colectivos dentro del valle
    "taxi": 60.0,  # cubre el valle entero
    "combinado": 60.0,
}

#: Coste mínimo estimado de visitar un recurso, en soles. Cubre entrada y
#: traslado local. Es una estimación del equipo, NO una tarifa oficial: sirve
#: para descartar presupuestos imposibles, no para cobrar.
COSTE_MINIMO_POR_RECURSO_SOLES = Decimal("8")


@dataclass
class RecursoDescartado:
    """Un recurso que no pasó los filtros duros, y por qué."""

    recurso_id: int
    nombre: str
    motivo: str


@dataclass
class Recomendacion:
    """Un recurso recomendado, con su puntaje, su explicación y su afluencia."""

    recurso_id: int
    nombre: str
    provincia: str
    distrito: str
    categoria: str | None
    latitud: float | None
    longitud: float | None
    distancia_km: float | None

    puntaje_afinidad: float
    #: El puntaje anterior, reescalado de 0 a 100 tomando como referencia el
    #: mejor resultado de ESTA busqueda. Existe solo para poder mostrarlo: una
    #: similitud coseno de 0,047 no le dice nada a nadie, mientras que "encaja
    #: un 80 % comparado con el que mejor encaja" si se entiende.
    #: NO es una probabilidad ni un porcentaje absoluto de nada.
    puntaje_relativo: int
    terminos_decisivos: list[str]
    intereses_cubiertos: list[str]

    afluencia: PrediccionAfluencia
    generado_por: str


@dataclass
class ResultadoRecomendacion:
    """Todo lo que devuelve una recomendación, incluido lo que se descartó."""

    recomendaciones: list[Recomendacion] = field(default_factory=list)
    descartados: list[RecursoDescartado] = field(default_factory=list)
    total_evaluados: int = 0
    #: 'modelo' o 'reglas'. Trazabilidad de la regla de oro de la IA.
    generado_por: str = "modelo"
    avisos: list[str] = field(default_factory=list)


def _coordenadas_del_distrito(sesion: Session, distrito: str) -> tuple[float, float] | None:
    """Punto medio de los recursos de un distrito, como referencia de origen.

    No existe una tabla de centros de distrito, así que se usa el centroide de
    sus recursos georreferenciados. Es una aproximación y se declara como tal:
    sirve para filtrar por distancia gruesa, no para calcular rutas.
    """
    punto = cast(RecursoTuristico.ubicacion, Geometry)

    fila = sesion.execute(
        select(func.avg(func.ST_Y(punto)), func.avg(func.ST_X(punto))).where(
            RecursoTuristico.distrito == distrito.upper(),
            RecursoTuristico.ubicacion.is_not(None),
        )
    ).one_or_none()

    if fila is None or fila[0] is None:
        return None

    return float(fila[0]), float(fila[1])


def aplicar_filtros_duros(
    recursos: list[tuple[RecursoTuristico, float | None, float | None, float | None]],
    preferencia: PreferenciaViaje,
) -> tuple[
    list[tuple[RecursoTuristico, float | None, float | None, float | None]],
    list[RecursoDescartado],
    list[str],
]:
    """Capa 0. Descarta lo que no cabe en las restricciones del visitante.

    Los cuatro filtros, y por qué cada uno:

    1. **Sin coordenadas.** No puede entrar en un itinerario, por mucha
       afinidad que tenga. Son 61 de los 295 recursos del catálogo.
    2. **No validado.** Si no pasó la validación DataOps, sus datos no son
       fiables y no se recomienda algo de lo que no respondemos.
    3. **Fuera de alcance.** Según cómo declaró que se mueve. Nadie llega
       caminando a un recurso a 40 km.
    4. **Presupuesto insuficiente.** Si no da ni para visitar un solo recurso,
       no hay nada que recomendar y se dice claramente.

    Devuelve los aceptados, los descartados con su motivo, y los avisos.
    Guardar los descartes no es un lujo: es lo que permite explicarle al
    visitante por qué no aparece un sitio que esperaba ver.
    """
    aceptados = []
    descartados: list[RecursoDescartado] = []
    avisos: list[str] = []

    alcance_km = ALCANCE_POR_MOVILIDAD_KM.get(preferencia.movilidad, 60.0)

    # Filtro de presupuesto. Se aplica al conjunto, no recurso a recurso:
    # el coste de un recurso concreto no se conoce (el inventario no publica
    # precios de entrada), pero sí se puede decir si el presupuesto declarado
    # no alcanza ni para el mínimo estimado de una sola visita.
    presupuesto = Decimal(preferencia.presupuesto_soles)
    visitas_costeables = int(presupuesto // COSTE_MINIMO_POR_RECURSO_SOLES)

    if visitas_costeables == 0:
        avisos.append(
            f"Con un presupuesto de S/ {presupuesto:.0f} no alcanza para el coste "
            f"mínimo estimado de una visita (S/ {COSTE_MINIMO_POR_RECURSO_SOLES:.0f}, "
            "entrada y traslado local aproximados). Se muestran los recursos de "
            "acceso libre y cercanos."
        )
    else:
        avisos.append(
            f"Con S/ {presupuesto:.0f} alcanzaría para unas {visitas_costeables} visitas, "
            f"a un coste mínimo estimado de S/ {COSTE_MINIMO_POR_RECURSO_SOLES:.0f} cada una. "
            "Es una estimación del equipo, no una tarifa oficial."
        )

    for recurso, latitud, longitud, distancia_km in recursos:
        if latitud is None or longitud is None:
            descartados.append(
                RecursoDescartado(
                    recurso.id,
                    recurso.nombre,
                    "sin coordenadas: no puede entrar en un itinerario",
                )
            )
            continue

        if not recurso.esta_validado:
            descartados.append(
                RecursoDescartado(recurso.id, recurso.nombre, "no pasó la validación del catálogo")
            )
            continue

        if distancia_km is not None and distancia_km > alcance_km:
            descartados.append(
                RecursoDescartado(
                    recurso.id,
                    recurso.nombre,
                    (
                        f"a {distancia_km:.0f} km, fuera del alcance de "
                        f"{alcance_km:.0f} km para «{preferencia.movilidad}»"
                    ),
                )
            )
            continue

        aceptados.append((recurso, latitud, longitud, distancia_km))

    return aceptados, descartados, avisos


# ---------------------------------------------------------------------------
# Orquestación de las tres capas
# ---------------------------------------------------------------------------


def recomendar(
    sesion: Session,
    preferencia: PreferenciaViaje,
    usar_modelo_recomendacion: bool = True,
    usar_modelo_afluencia: bool = True,
    limite: int = 20,
) -> ResultadoRecomendacion:
    """Recomienda recursos para una preferencia de viaje.

    Recorre las tres capas en orden: filtra lo imposible, ordena lo posible y
    anota cuánta gente se espera en cada sitio.
    """
    resultado = ResultadoRecomendacion(
        generado_por="modelo" if usar_modelo_recomendacion else "reglas"
    )

    origen = _coordenadas_del_distrito(sesion, preferencia.distrito_origen)

    if origen is None:
        resultado.avisos.append(
            f"No hay recursos georreferenciados en {preferencia.distrito_origen}, "
            "así que no se puede filtrar por distancia. Se evalúa todo el valle."
        )

    punto = cast(RecursoTuristico.ubicacion, Geometry)

    columnas_base = [
        RecursoTuristico,
        func.ST_Y(punto).label("latitud"),
        func.ST_X(punto).label("longitud"),
    ]

    if origen is not None:
        latitud_origen, longitud_origen = origen

        # ST_Distance sobre geografía devuelve metros medidos sobre el
        # elipsoide: es distancia real en línea recta, no una aproximación
        # sobre un plano. Se divide entre mil para tenerla en kilómetros.
        distancia_km = (
            func.ST_Distance(
                RecursoTuristico.ubicacion,
                func.ST_GeogFromText(f"SRID=4326;POINT({longitud_origen} {latitud_origen})"),
            )
            / 1000.0
        ).label("distancia_km")

        filas = [
            (recurso, latitud, longitud, float(km) if km is not None else None)
            for recurso, latitud, longitud, km in sesion.execute(
                select(*columnas_base, distancia_km)
            )
        ]
    else:
        # Sin origen conocido no se puede medir distancia. Se deja en None y
        # el filtro de alcance simplemente no descarta a nadie.
        filas = [
            (recurso, latitud, longitud, None)
            for recurso, latitud, longitud in sesion.execute(select(*columnas_base))
        ]

    resultado.total_evaluados = len(filas)

    # --- Capa 0 -----------------------------------------------------------
    aceptados, descartados, avisos_de_filtros = aplicar_filtros_duros(filas, preferencia)
    resultado.descartados = descartados
    resultado.avisos.extend(avisos_de_filtros)

    if not aceptados:
        resultado.avisos.append(
            "Ningún recurso del catálogo cumple las restricciones indicadas. "
            "Prueba a ampliar el alcance cambiando cómo te mueves."
        )
        return resultado

    # --- Capa 1 -----------------------------------------------------------
    para_puntuar = [
        RecursoParaPuntuar(
            id=recurso.id,
            nombre=recurso.nombre,
            categoria=recurso.categoria,
            tipo=recurso.tipo,
            subtipo=recurso.subtipo,
            descripcion=recurso.descripcion_es,
            distrito=recurso.distrito,
        )
        for recurso, _, _, _ in aceptados
    ]

    afinidades = {
        afinidad.recurso_id: afinidad
        for afinidad in calcular_afinidad(
            para_puntuar,
            list(preferencia.intereses),
            distrito_origen=preferencia.distrito_origen,
            usar_modelo=usar_modelo_recomendacion,
        )
    }

    # NOTA sobre el filtro por fecha que pide el plan de trabajo.
    # No se puede aplicar todavía: el inventario del MINCETUR no publica
    # horarios de atención, así que la tabla horario_atencion está vacía y no
    # hay con qué decidir si un recurso abre el día del viaje. Se aplicará en
    # el Incremento 4, cuando el ruteo necesite las ventanas de tiempo y haya
    # que conseguir esos horarios de otra fuente. Inventarlos ahora sería
    # descartar recursos por un dato imaginado.

    # --- Capa 2 -----------------------------------------------------------
    # Se predice para el primer día del viaje: es el que el visitante tiene en
    # la cabeza cuando mira los resultados.
    dia_de_referencia: date = preferencia.fecha_inicio

    recomendaciones: list[Recomendacion] = []

    for recurso, latitud, longitud, distancia_km in aceptados:
        afinidad = afinidades[recurso.id]

        recomendaciones.append(
            Recomendacion(
                recurso_id=recurso.id,
                nombre=recurso.nombre,
                provincia=recurso.provincia,
                distrito=recurso.distrito,
                categoria=recurso.categoria,
                latitud=latitud,
                longitud=longitud,
                distancia_km=round(distancia_km, 1) if distancia_km is not None else None,
                puntaje_afinidad=afinidad.puntaje,
                puntaje_relativo=0,  # se calcula al final, cuando se conoce el maximo
                terminos_decisivos=afinidad.terminos_decisivos,
                intereses_cubiertos=afinidad.intereses_cubiertos,
                afluencia=predecir_afluencia(
                    dia_de_referencia, recurso.distrito, usar_modelo=usar_modelo_afluencia
                ),
                generado_por=afinidad.calculado_por,
            )
        )

    # Se ordena por afinidad y, a igualdad, por cercanía: entre dos sitios que
    # interesan lo mismo, gana el que está más cerca.
    recomendaciones.sort(
        key=lambda r: (-r.puntaje_afinidad, r.distancia_km if r.distancia_km is not None else 1e9)
    )

    # Un recurso con afinidad cero no responde a nada de lo que pidió el
    # visitante. Mostrarlo sería ruido disfrazado de recomendación.
    con_afinidad = [r for r in recomendaciones if r.puntaje_afinidad > 0]

    if not con_afinidad:
        resultado.avisos.append(
            "Ningún recurso coincide con los intereses marcados. Se muestran los "
            "más cercanos para que puedas explorar."
        )
        con_afinidad = recomendaciones

    seleccionadas = con_afinidad[:limite]

    # El puntaje relativo se calcula ahora, cuando ya se sabe cual fue el mejor
    # de esta busqueda. Se hace sobre la lista recortada para que el primero
    # que ve el visitante sea siempre el 100 %.
    mejor = max((r.puntaje_afinidad for r in seleccionadas), default=0.0)

    for recomendacion in seleccionadas:
        recomendacion.puntaje_relativo = (
            round(100 * recomendacion.puntaje_afinidad / mejor) if mejor > 0 else 0
        )

    resultado.recomendaciones = seleccionadas

    return resultado
