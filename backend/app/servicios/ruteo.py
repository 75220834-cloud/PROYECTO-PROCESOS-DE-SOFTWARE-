"""Construcción del itinerario: qué visitar, en qué orden y a qué hora.

Cierra la **brecha 4**: *el proceso no incorporaba la distribución geográfica ni
el tiempo y costo de desplazamiento*. Hasta aquí el sistema sabía recomendar
recursos; ahora sabe además ordenarlos en un día real.

## El problema, formalmente

Es un **problema de ruteo con ventanas de tiempo** (VRPTW) en su variante
*prize-collecting*: no hay que visitar todo, hay que elegir. Un día tiene diez
horas y el recomendador devuelve veinte recursos; caben seis o siete.

- **Restricciones duras:** horario de atención de cada recurso, hora de inicio
  y fin del día, duración de cada visita, presupuesto de traslado.
- **Objetivo:** maximizar el puntaje de afinidad acumulado.

## La regla de oro de la IA, aplicada aquí

Como toda funcionalidad con modelo del proyecto, el ruteo tiene su alternativa
por reglas y se elige con una variable de configuración:

- ``usar_modelo_recomendacion = True`` → **OR-Tools**, búsqueda VRPTW.
- ``usar_modelo_recomendacion = False`` → **vecino más cercano** con
  verificación de horarios.

El itinerario guarda en ``generado_por`` cuál de los dos lo produjo, y la
interfaz lo enseña.

## Por qué la matriz se aproxima y la ruta final se refina

Optimizar necesita la distancia entre **todos** los pares de candidatos: con 20
recursos son 380 traslados. Calcular cada uno sobre el grafo de 40 000 nodos
llevaría minutos, y una petición web no puede durar minutos.

Así que se hacen dos pasadas:

1. **Optimizar** sobre una matriz aproximada (línea recta × 1,26, el factor de
   rodeo medido, más Tobler con las altitudes reales de los extremos). Es
   rápida y suficiente para *ordenar*.
2. **Refinar** solo los tramos que la solución realmente usa —seis o siete—
   sobre el grafo real, y volver a cuadrar los horarios con esos tiempos.

Si al refinar el día se pasa de la hora de fin, se recorta y se avisa. Nunca se
entrega un horario que se sabe que no cuadra.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ia.tiempo_recorrido import (
    clasificar_esfuerzo,
    necesita_aviso_de_altitud,
)
from app.modelos.catalogo import HorarioAtencion, RecursoTuristico
from app.modelos.itinerario import (
    EstadoItinerario,
    Itinerario,
    OrigenDelCalculo,
    ParadaItinerario,
)
from app.modelos.preferencias import PreferenciaViaje
from app.servicios.costos import CostoDeTraslado, calcular_traslado

registro = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# La jornada
# ---------------------------------------------------------------------------

#: A qué hora empieza y termina un día de visitas. En el valle amanece hacia
#: las 5:45 y anochece hacia las 18:15 durante todo el año —está a 12° del
#: ecuador, la duración del día apenas varía—, así que 8:00–18:00 deja margen
#: por los dos lados sin prometer visitas de noche.
HORA_INICIO_PREDETERMINADA = time(8, 0)
HORA_FIN_PREDETERMINADA = time(18, 0)

#: Cuántas paradas como máximo se proponen en un día, según el ritmo elegido.
#: No es una restricción del tiempo —de eso ya se encarga la ventana horaria—
#: sino de las ganas: siete paradas en un día caben, pero quien pidió ritmo
#: relajado no las quiere.
PARADAS_MAXIMAS_POR_RITMO: dict[str, int] = {
    "relajado": 3,
    "moderado": 5,
    "intenso": 8,
}

#: Cuánto dura una visita cuando el catálogo no lo dice, por categoría del
#: inventario del MINCETUR.
#:
#: **Es un supuesto declarado, no un dato.** El inventario nacional no publica
#: duraciones de visita: la columna ``duracion_visita_min`` existe desde la
#: Fase 1 y está vacía en los 295 recursos. Se usan estos valores por defecto
#: porque un optimizador de horarios necesita alguna duración, y suponer un
#: número igual para una capilla y para un nevado sería peor. En cuanto un
#: recurso tenga su duración cargada, se usa la suya.
DURACION_PREDETERMINADA_MIN: dict[str, int] = {
    "1. SITIOS NATURALES": 90,
    "2. MANIFESTACIONES CULTURALES": 60,
    "3. FOLCLORE": 60,
    "4. REALIZACIONES TÉCNICAS, CIENTÍFICAS Y ARTÍSTICAS CONTEMPORÁNEAS": 60,
    "5. ACONTECIMIENTOS PROGRAMADOS": 120,
}

#: Duración de visita si ni siquiera se conoce la categoría.
DURACION_DE_RESERVA_MIN = 60

#: Qué parte del presupuesto diario se puede gastar en traslados. El resto se
#: reserva para entradas, comida y lo imprevisto.
#:
#: También es un supuesto del equipo. Se declara aquí para que se pueda
#: discutir en la defensa en vez de quedar escondido dentro de una fórmula.
PROPORCION_DE_TRASLADO = Decimal("0.35")

#: Cuánto pesa un punto de afinidad frente a un minuto de viaje en la función
#: objetivo. Saltarse un recurso de afinidad 100 «cuesta» 100 × este peso.
#:
#: **El valor está medido, no elegido a ojo.** Con la preferencia de prueba
#: (Huancayo, arqueología + naturaleza + gastronomía, ritmo moderado, S/450 a
#: tres días) sale esta tabla:
#:
#: ==========  =======  ========  =======  ==========
#: Peso        Paradas  Afinidad  km       min viaje
#: ==========  =======  ========  =======  ==========
#: 1           5        263        14,8     71
#: 2           5        288        38,9     107
#: **3**       **5**    **302**   **57,1**  **151**
#: 5           5        302        57,1     151
#: 10          5        302        57,1     151
#: 20          5        302        57,1     151
#: *reglas*    5        263        14,8     71
#: ==========  =======  ========  =======  ==========
#:
#: A partir de 3 la afinidad se satura en 302: subir más el peso no mejora el
#: objetivo y solo añade kilómetros. Se toma **el peso más bajo que alcanza el
#: óptimo**, para que el tiempo de viaje siga desempatando entre soluciones de
#: igual afinidad.
#:
#: (Esta tabla se volvió a medir después de corregir el modelo de circuito
#: cerrado a recorrido abierto. Con el circuito cerrado, el mismo peso 3 daba
#: 72,9 km y 172 minutos para la misma afinidad: el regreso a la primera parada
#: estaba pagándose en tiempo y en dinero.)
#:
#: La tabla también deja ver el canje que el visitante paga: +39 puntos de
#: afinidad sobre la alternativa por reglas cuestan +42 km y +80 minutos de
#: combi. El objetivo que fija el plan de trabajo es maximizar la afinidad, así
#: que se respeta; pero el itinerario muestra los tiempos y el costo de cada
#: traslado para que esa decisión no quede escondida.
PESO_DE_LA_AFINIDAD = 3

#: Cuántos candidatos como máximo entran al optimizador. Con 20, la matriz
#: tiene 380 traslados: se llena en menos de un segundo. Con 60 serían 3 540 y
#: la petición empezaría a notarse.
MAXIMO_CANDIDATOS = 20

#: Segundos que se le dan al optimizador.
#:
#: **También está medido.** La búsqueda local guiada no demuestra optimalidad,
#: así que agota siempre el límite: este número no es un tope, es el costo. Se
#: probó con dos perfiles distintos:
#:
#: ==========  =======  ========  ==========
#: Límite (s)  Paradas  Afinidad  Total (s)
#: ==========  =======  ========  ==========
#: 1           5 y 7    272 y 340  3,7 y 2,3
#: **2**       5 y 7    272 y 340  2,9 y 3,2
#: 3           5 y 7    272 y 340  3,9 y 4,2
#: 5           5 y 7    272 y 340  6,0 y 6,3
#: ==========  =======  ========  ==========
#:
#: **El resultado es idéntico en los cuatro casos**: con estos tamaños de
#: problema (20 candidatos) el solucionador converge en el primer segundo y el
#: resto del límite se tira. Se deja en 2 y no en 1 para tener margen si el
#: problema se complica, pero sabiendo que 5 no compraba nada.
#:
#: La diferencia importa: el plan de trabajo exige que un itinerario se calcule
#: en menos de 10 segundos, y con el límite en 5 el peor perfil medido tardaba
#: 8,0 s. Eso es poco margen para una máquina más lenta que la de desarrollo.
SEGUNDOS_DE_BUSQUEDA = 2


# ---------------------------------------------------------------------------
# Tipos de entrada y salida
# ---------------------------------------------------------------------------


@dataclass
class CandidatoARutear:
    """Un recurso que el recomendador propuso, listo para entrar en la ruta."""

    recurso_id: int
    nombre: str
    distrito: str
    categoria: str | None
    latitud: float
    longitud: float
    altitud_m: float | None
    puntaje_relativo: int
    duracion_visita_min: int
    #: Ventana de atención ese día, o ``None`` si no se conoce el horario.
    apertura: time | None = None
    cierre: time | None = None

    @property
    def tiene_horario_conocido(self) -> bool:
        return self.apertura is not None and self.cierre is not None


@dataclass
class ParadaCalculada:
    """Una parada de la ruta, ya con horas y con el traslado que la precede."""

    candidato: CandidatoARutear
    orden: int
    hora_llegada: time
    hora_salida: time
    traslado: CostoDeTraslado | None


@dataclass
class ItinerarioCalculado:
    """El resultado completo del ruteo de un día."""

    paradas: list[ParadaCalculada] = field(default_factory=list)
    generado_por: str = "modelo"
    avisos: list[str] = field(default_factory=list)

    tiempo_total_min: int = 0
    costo_min_soles: Decimal = Decimal("0.00")
    costo_max_soles: Decimal = Decimal("0.00")
    distancia_total_km: float = 0.0
    subida_total_m: float = 0.0

    @property
    def esfuerzo(self) -> str:
        return clasificar_esfuerzo(self.subida_total_m)

    @property
    def hay_tramos_estimados(self) -> bool:
        return any(
            parada.traslado is not None
            and parada.traslado.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA
            for parada in self.paradas
        )


# ---------------------------------------------------------------------------
# Preparación de los candidatos
# ---------------------------------------------------------------------------


def duracion_de_visita(recurso: RecursoTuristico) -> int:
    """Cuánto se queda el visitante en un recurso, en minutos."""
    if recurso.duracion_visita_min:
        return recurso.duracion_visita_min

    if recurso.categoria:
        return DURACION_PREDETERMINADA_MIN.get(recurso.categoria, DURACION_DE_RESERVA_MIN)

    return DURACION_DE_RESERVA_MIN


def _horario_del_dia(
    sesion: Session, recurso_ids: list[int], fecha: date
) -> dict[int, tuple[time, time]]:
    """Ventana de atención de cada recurso para el día de la semana de ``fecha``.

    Devuelve solo los recursos que **tienen** horario cargado. Los que no
    aparecen no es que abran siempre: es que no se sabe, y quien llame decide
    qué hacer con eso.

    ``date.weekday()`` da 0 para lunes y 6 para domingo, que es exactamente el
    convenio de la columna ``dia_semana``.
    """
    if not recurso_ids:
        return {}

    filas = sesion.execute(
        select(
            HorarioAtencion.recurso_id,
            HorarioAtencion.hora_apertura,
            HorarioAtencion.hora_cierre,
        ).where(
            HorarioAtencion.recurso_id.in_(recurso_ids),
            HorarioAtencion.dia_semana == fecha.weekday(),
        )
    ).all()

    horarios: dict[int, tuple[time, time]] = {}

    for recurso_id, apertura, cierre in filas:
        # Si un recurso tiene varios tramos ese día (mañana y tarde), se toma
        # la envolvente. Modelar la pausa del mediodía exigiría ventanas
        # múltiples por nodo, y no hay ni un solo horario cargado con el que
        # comprobar que eso funciona.
        if recurso_id in horarios:
            anterior_apertura, anterior_cierre = horarios[recurso_id]
            horarios[recurso_id] = (
                min(anterior_apertura, apertura),
                max(anterior_cierre, cierre),
            )
        else:
            horarios[recurso_id] = (apertura, cierre)

    return horarios


def preparar_candidatos(
    sesion: Session,
    recomendaciones: list,
    fecha: date,
) -> list[CandidatoARutear]:
    """Convierte las recomendaciones en candidatos con horario y duración.

    Descarta las que no tienen coordenadas: sin ubicación no se puede rutear, y
    el 20,7 % del catálogo del MINCETUR no la trae.
    """
    con_coordenadas = [
        r for r in recomendaciones if r.latitud is not None and r.longitud is not None
    ]

    if not con_coordenadas:
        return []

    ids = [r.recurso_id for r in con_coordenadas]

    recursos = {
        recurso.id: recurso
        for recurso in sesion.scalars(select(RecursoTuristico).where(RecursoTuristico.id.in_(ids)))
    }

    horarios = _horario_del_dia(sesion, ids, fecha)

    candidatos: list[CandidatoARutear] = []

    for recomendacion in con_coordenadas:
        recurso = recursos.get(recomendacion.recurso_id)
        if recurso is None:
            continue

        apertura, cierre = horarios.get(recurso.id, (None, None))

        candidatos.append(
            CandidatoARutear(
                recurso_id=recurso.id,
                nombre=recurso.nombre,
                distrito=recurso.distrito,
                categoria=recurso.categoria,
                latitud=recomendacion.latitud,
                longitud=recomendacion.longitud,
                altitud_m=float(recurso.altitud_msnm) if recurso.altitud_msnm else None,
                puntaje_relativo=recomendacion.puntaje_relativo,
                duracion_visita_min=duracion_de_visita(recurso),
                apertura=apertura,
                cierre=cierre,
            )
        )

    return candidatos


# ---------------------------------------------------------------------------
# La matriz de traslados
# ---------------------------------------------------------------------------


def construir_matriz(
    sesion: Session,
    candidatos: list[CandidatoARutear],
    movilidad: str,
    fecha: date,
) -> list[list[CostoDeTraslado | None]]:
    """Calcula el traslado entre cada par de candidatos.

    La diagonal queda a ``None``: no hay traslado de un sitio a sí mismo.

    Se usa la aproximación rápida (sin tocar el grafo) porque son N² cálculos.
    Los tramos que la solución acabe usando se recalculan después sobre la red
    real en :func:`refinar_traslados`.
    """
    tamano = len(candidatos)
    matriz: list[list[CostoDeTraslado | None]] = [[None] * tamano for _ in range(tamano)]

    for i, origen in enumerate(candidatos):
        for j, destino in enumerate(candidatos):
            if i == j:
                continue

            matriz[i][j] = calcular_traslado(
                sesion,
                origen.latitud,
                origen.longitud,
                origen.altitud_m,
                origen.distrito,
                destino.latitud,
                destino.longitud,
                destino.altitud_m,
                destino.distrito,
                movilidad,
                fecha,
                usar_red=False,
            )

    return matriz


# ---------------------------------------------------------------------------
# Utilidades de horario
# ---------------------------------------------------------------------------


def _a_minutos(momento: time) -> int:
    return momento.hour * 60 + momento.minute


def _a_hora(minutos: int) -> time:
    """Convierte minutos desde medianoche en una hora del día.

    Se topa en 23:59 en vez de desbordar al día siguiente: un itinerario que se
    pasara de medianoche es un error de cálculo, y prefiero que se vea.
    """
    minutos = max(0, min(minutos, 23 * 60 + 59))
    return time(minutos // 60, minutos % 60)


def _ventana_de_atencion(
    candidato: CandidatoARutear, inicio_dia: int, fin_dia: int
) -> tuple[int, int]:
    """Ventana en la que se puede EMPEZAR la visita a un recurso, en minutos.

    Se resta la duración de la visita al cierre: llegar a un museo diez minutos
    antes de que cierre no es visitarlo. Si el recurso no tiene horario
    cargado, la única ventana honesta es la del día entero.
    """
    if not candidato.tiene_horario_conocido:
        return inicio_dia, fin_dia

    apertura = max(inicio_dia, _a_minutos(candidato.apertura))
    ultimo_inicio = min(fin_dia, _a_minutos(candidato.cierre) - candidato.duracion_visita_min)

    # Si la ventana sale invertida, el recurso no da tiempo ese día. Se
    # devuelve degenerada y quien la use la descarta.
    return apertura, max(apertura, ultimo_inicio)


def _es_visitable_ese_dia(candidato: CandidatoARutear, inicio_dia: int, fin_dia: int) -> bool:
    """Si al recurso le cabe la visita completa dentro de su horario."""
    if not candidato.tiene_horario_conocido:
        return True

    inicio_posible = max(_a_minutos(candidato.apertura), inicio_dia)
    fin_posible = min(_a_minutos(candidato.cierre), fin_dia)

    return fin_posible - inicio_posible >= candidato.duracion_visita_min


def _minuto_de_apertura(candidato: CandidatoARutear, inicio_dia: int) -> int:
    """Primer minuto en que se puede empezar la visita a un recurso."""
    if not candidato.tiene_horario_conocido:
        return inicio_dia

    return max(inicio_dia, _a_minutos(candidato.apertura))


# ---------------------------------------------------------------------------
# Camino A — optimización con OR-Tools
# ---------------------------------------------------------------------------


def resolver_con_ortools(
    candidatos: list[CandidatoARutear],
    matriz: list[list[CostoDeTraslado | None]],
    inicio_dia: int,
    fin_dia: int,
    paradas_maximas: int,
    presupuesto_traslado: Decimal,
    segundos_de_busqueda: int = SEGUNDOS_DE_BUSQUEDA,
) -> list[int] | None:
    """Resuelve el VRPTW y devuelve el orden de los índices visitados.

    Devuelve ``None`` si el solucionador no encuentra solución, para que quien
    llame pueda caer en la alternativa por reglas en vez de no entregar nada.

    ## Cómo se traduce «maximizar afinidad» a un solucionador que minimiza

    OR-Tools minimiza. El recurso estándar para un problema de recolección de
    premios es hacer **opcional** cada visita con ``AddDisjunction`` y ponerle
    una penalización por no hacerla. Saltarse un recurso de afinidad 90 cuesta
    900; visitarlo cuesta los minutos de viaje. Minimizar esa suma es lo mismo
    que maximizar la afinidad recogida dentro del tiempo disponible.

    ## Por qué hay un nodo de fin de día que no existe

    OR-Tools está pensado para vehículos de reparto, que **vuelven al almacén**.
    Si se le dice que el vehículo empieza y termina en el nodo 0, resuelve un
    circuito cerrado: el regreso a la primera parada consume tiempo y dinero
    del presupuesto.

    Un día de turismo no es un circuito. El visitante termina donde termina y
    se va a su alojamiento; no vuelve al primer museo. Modelarlo como circuito
    cerrado tenía un efecto medible y grave: con la preferencia de prueba en
    taxi, el optimizador entregaba **una sola parada** mientras la alternativa
    por reglas encontraba tres dentro del mismo presupuesto. El optimizador
    quedaba peor que su propia línea base, que es justo lo contrario de para lo
    que existe.

    La solución estándar es añadir un nodo ficticio de fin al que se llega
    gratis desde cualquier sitio, y decirle al gestor que el vehículo termina
    ahí. Así el recorrido queda abierto y el regreso deja de costar.
    """
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    reales = len(candidatos)

    #: Índice del nodo ficticio de fin de día. No es un lugar: es «se acabó».
    fin_del_dia = reales

    def es_ficticio(nodo: int) -> bool:
        return nodo >= reales

    # El vehículo (el visitante) empieza en el candidato 0 y termina en el nodo
    # ficticio. El candidato 0 no es un depósito: es el primer sitio al que va.
    gestor = pywrapcp.RoutingIndexManager(reales + 1, 1, [0], [fin_del_dia])
    modelo = pywrapcp.RoutingModel(gestor)

    def traslado_entre(i: int, j: int) -> CostoDeTraslado | None:
        """El traslado de i a j, o ``None`` si alguno es el nodo ficticio."""
        if es_ficticio(i) or es_ficticio(j):
            return None
        return matriz[i][j]

    # --- Costo del arco: minutos de viaje ---------------------------------
    def minutos_de_arco(indice_origen: int, indice_destino: int) -> int:
        traslado = traslado_entre(
            gestor.IndexToNode(indice_origen), gestor.IndexToNode(indice_destino)
        )
        return 0 if traslado is None else int(traslado.minutos)

    referencia_costo = modelo.RegisterTransitCallback(minutos_de_arco)
    modelo.SetArcCostEvaluatorOfAllVehicles(referencia_costo)

    # --- Dimensión de tiempo: viaje + visita ------------------------------
    def tiempo_transcurrido(indice_origen: int, indice_destino: int) -> int:
        i = gestor.IndexToNode(indice_origen)
        j = gestor.IndexToNode(indice_destino)

        if es_ficticio(i):
            return 0

        traslado = traslado_entre(i, j)
        viaje = 0 if traslado is None else int(traslado.minutos)

        # La visita al ORIGEN se consume antes de salir hacia el destino. Al ir
        # hacia el fin del día, el viaje es cero pero la visita sigue contando:
        # la última parada también dura lo que dura.
        return viaje + candidatos[i].duracion_visita_min

    referencia_tiempo = modelo.RegisterTransitCallback(tiempo_transcurrido)

    modelo.AddDimension(
        referencia_tiempo,
        # Holgura: cuánto se puede esperar en un sitio si se llega antes de que
        # abra. Se admite toda la jornada; sin holgura, un recurso que abre a
        # las 10 haría inviable cualquier ruta que llegue antes.
        fin_dia - inicio_dia,
        fin_dia,  # capacidad: el día no puede terminar más tarde
        False,  # el tiempo NO arranca en cero, arranca a la hora de inicio
        "Tiempo",
    )
    dimension_tiempo = modelo.GetDimensionOrDie("Tiempo")

    for nodo, candidato in enumerate(candidatos):
        apertura, ultimo_inicio = _ventana_de_atencion(candidato, inicio_dia, fin_dia)
        dimension_tiempo.CumulVar(gestor.NodeToIndex(nodo)).SetRange(apertura, ultimo_inicio)

    # El día arranca a la hora de inicio y termina como muy tarde a la de fin.
    dimension_tiempo.CumulVar(modelo.Start(0)).SetRange(inicio_dia, fin_dia)
    dimension_tiempo.CumulVar(modelo.End(0)).SetRange(inicio_dia, fin_dia)

    # --- Dimensión de dinero: presupuesto de traslado ---------------------
    # OR-Tools trabaja con enteros, así que el dinero va en céntimos. Se usa el
    # precio MÁXIMO del rango: si el presupuesto solo alcanza con suerte, el
    # itinerario no es viable y no hay que proponerlo.
    def centimos_de_arco(indice_origen: int, indice_destino: int) -> int:
        traslado = traslado_entre(
            gestor.IndexToNode(indice_origen), gestor.IndexToNode(indice_destino)
        )
        return 0 if traslado is None else int(traslado.precio_max_soles * 100)

    referencia_dinero = modelo.RegisterTransitCallback(centimos_de_arco)
    modelo.AddDimension(
        referencia_dinero,
        0,  # sin holgura: el dinero gastado no se recupera
        max(1, int(presupuesto_traslado * 100)),
        True,  # empieza en cero: al salir no se ha gastado nada
        "Dinero",
    )

    # --- Dimensión de conteo: tope de paradas por ritmo -------------------
    # Cada arco recorrido suma uno. Con el nodo ficticio al final, el número de
    # arcos coincide exactamente con el de paradas visitadas: el recorrido
    # 0 -> 5 -> 15 -> fin tiene tres arcos y tres paradas.
    def una_parada(indice_origen: int, indice_destino: int) -> int:
        del indice_origen, indice_destino
        return 1

    referencia_conteo = modelo.RegisterTransitCallback(una_parada)
    modelo.AddDimension(referencia_conteo, 0, paradas_maximas, True, "Paradas")

    # --- Visitas opcionales, penalizadas por su afinidad ------------------
    for nodo, candidato in enumerate(candidatos):
        if nodo == 0:
            # El nodo de salida no se puede saltar: es donde empieza el día.
            continue

        if not _es_visitable_ese_dia(candidato, inicio_dia, fin_dia):
            # Cerrado ese día: penalización cero para que saltárselo salga
            # gratis y el solucionador no fuerce lo imposible.
            modelo.AddDisjunction([gestor.NodeToIndex(nodo)], 0)
            continue

        penalizacion = max(1, candidato.puntaje_relativo) * PESO_DE_LA_AFINIDAD
        modelo.AddDisjunction([gestor.NodeToIndex(nodo)], penalizacion)

    # --- Búsqueda ---------------------------------------------------------
    parametros = pywrapcp.DefaultRoutingSearchParameters()
    parametros.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    # La búsqueda local guiada escapa de los óptimos locales en los que se
    # queda atrapado el vecino más cercano. Sin ella, la primera solución se
    # entrega tal cual y el optimizador no aporta nada sobre las reglas.
    parametros.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    parametros.time_limit.FromSeconds(segundos_de_busqueda)

    solucion = modelo.SolveWithParameters(parametros)

    if solucion is None:
        return None

    orden: list[int] = []
    indice = modelo.Start(0)

    while not modelo.IsEnd(indice):
        nodo = gestor.IndexToNode(indice)
        # El nodo ficticio no es una parada: no se devuelve.
        if not es_ficticio(nodo):
            orden.append(nodo)
        indice = solucion.Value(modelo.NextVar(indice))

    return orden


# ---------------------------------------------------------------------------
# Camino B — alternativa por reglas: vecino más cercano
# ---------------------------------------------------------------------------


def resolver_con_reglas(
    candidatos: list[CandidatoARutear],
    matriz: list[list[CostoDeTraslado | None]],
    inicio_dia: int,
    fin_dia: int,
    paradas_maximas: int,
    presupuesto_traslado: Decimal,
) -> list[int]:
    """Vecino más cercano con verificación de horarios y presupuesto.

    Es la alternativa explícita que exige la regla de oro de la IA del
    proyecto: si el optimizador falla o se desactiva, el sistema **sigue
    entregando un itinerario**, peor pero correcto.

    El algoritmo es deliberadamente simple, y por eso se explica en una frase:
    *empieza en el recurso de mayor afinidad y, desde donde esté, va al más
    cercano al que llegue a tiempo y con dinero.*

    Su debilidad conocida es la del vecino más cercano de siempre: como decide
    mirando un solo paso adelante, puede dejar para el final un recurso al otro
    lado del valle. El optimizador existe precisamente para eso.
    """
    if not candidatos:
        return []

    orden = [0]
    visitados = {0}

    momento = _minuto_de_apertura(candidatos[0], inicio_dia)
    momento += candidatos[0].duracion_visita_min

    gastado = Decimal("0.00")

    while len(orden) < paradas_maximas:
        actual = orden[-1]
        mejor: int | None = None
        mejor_minutos = 0

        for siguiente, candidato in enumerate(candidatos):
            if siguiente in visitados:
                continue

            traslado = matriz[actual][siguiente]
            if traslado is None:
                continue

            if gastado + traslado.precio_max_soles > presupuesto_traslado:
                continue

            llegada = momento + traslado.minutos
            inicio_visita = max(llegada, _minuto_de_apertura(candidato, inicio_dia))
            fin_visita = inicio_visita + candidato.duracion_visita_min

            if fin_visita > fin_dia:
                continue

            # La verificación de horarios que pide el plan de trabajo.
            if candidato.tiene_horario_conocido and fin_visita > _a_minutos(candidato.cierre):
                continue

            if mejor is None or traslado.minutos < mejor_minutos:
                mejor = siguiente
                mejor_minutos = traslado.minutos

        if mejor is None:
            break

        elegido = matriz[actual][mejor]
        if elegido is None:  # no puede pasar: el bucle ya lo comprobó
            break

        llegada = momento + elegido.minutos
        inicio_visita = max(llegada, _minuto_de_apertura(candidatos[mejor], inicio_dia))

        momento = inicio_visita + candidatos[mejor].duracion_visita_min
        gastado += elegido.precio_max_soles

        orden.append(mejor)
        visitados.add(mejor)

    return orden


# ---------------------------------------------------------------------------
# Segunda pasada: refinar los tramos elegidos sobre la red real
# ---------------------------------------------------------------------------


def refinar_traslados(
    sesion: Session,
    candidatos: list[CandidatoARutear],
    orden: list[int],
    movilidad: str,
    fecha: date,
) -> list[CostoDeTraslado]:
    """Recalcula sobre el grafo real los tramos que la solución usa.

    Devuelve un traslado por cada par consecutivo del recorrido, así que la
    lista tiene un elemento menos que ``orden``. Son seis o siete cálculos, no
    los N² de la matriz: aquí sí se puede pagar el camino mínimo real.
    """
    traslados: list[CostoDeTraslado] = []

    for posicion in range(len(orden) - 1):
        origen = candidatos[orden[posicion]]
        destino = candidatos[orden[posicion + 1]]

        traslados.append(
            calcular_traslado(
                sesion,
                origen.latitud,
                origen.longitud,
                origen.altitud_m,
                origen.distrito,
                destino.latitud,
                destino.longitud,
                destino.altitud_m,
                destino.distrito,
                movilidad,
                fecha,
                usar_red=True,
            )
        )

    return traslados


def armar_horario(
    candidatos: list[CandidatoARutear],
    orden: list[int],
    traslados: list[CostoDeTraslado],
    inicio_dia: int,
    fin_dia: int,
) -> tuple[list[ParadaCalculada], list[str]]:
    """Cuadra las horas con los tiempos reales y recorta lo que ya no cabe.

    Es la parte que hace honesta la segunda pasada: si al usar los tiempos del
    grafo el día se pasa de la hora de fin, **se corta ahí** y se avisa. Nunca
    se entrega un horario que ya se sabe que no cuadra.
    """
    paradas: list[ParadaCalculada] = []
    avisos: list[str] = []

    momento = inicio_dia
    recortadas = 0

    for posicion, indice in enumerate(orden):
        candidato = candidatos[indice]
        traslado = traslados[posicion - 1] if posicion > 0 else None

        if traslado is not None:
            momento += traslado.minutos

        llegada = max(momento, _minuto_de_apertura(candidato, inicio_dia))
        salida = llegada + candidato.duracion_visita_min

        pasa_del_dia = salida > fin_dia
        cierra_antes = candidato.tiene_horario_conocido and salida > _a_minutos(candidato.cierre)

        if pasa_del_dia or cierra_antes:
            recortadas = len(orden) - posicion
            break

        paradas.append(
            ParadaCalculada(
                candidato=candidato,
                orden=posicion,
                hora_llegada=_a_hora(llegada),
                hora_salida=_a_hora(salida),
                traslado=traslado,
            )
        )

        momento = salida

    if recortadas:
        avisos.append(
            f"Se quitaron {recortadas} "
            f"{'parada' if recortadas == 1 else 'paradas'} al recalcular los traslados sobre "
            "la red vial real: con los tiempos exactos ya no cabían antes de las "
            f"{_a_hora(fin_dia).strftime('%H:%M')}."
        )

    return paradas, avisos


# ---------------------------------------------------------------------------
# La función que lo junta todo
# ---------------------------------------------------------------------------


def construir_itinerario(
    sesion: Session,
    preferencia: PreferenciaViaje,
    recomendaciones: list,
    fecha: date,
    usar_modelo: bool = True,
    hora_inicio: time = HORA_INICIO_PREDETERMINADA,
    hora_fin: time = HORA_FIN_PREDETERMINADA,
) -> ItinerarioCalculado:
    """Construye el itinerario de un día a partir de las recomendaciones.

    ``usar_modelo`` decide el camino: OR-Tools o vecino más cercano. Es la
    misma variable de configuración que gobierna el recomendador, porque las
    dos son la misma decisión de riesgo: *si el modelo no está disponible o no
    convence, el sistema entrega la alternativa por reglas y sigue en pie*.
    """
    resultado = ItinerarioCalculado(generado_por="modelo" if usar_modelo else "reglas")

    inicio_dia = _a_minutos(hora_inicio)
    fin_dia = _a_minutos(hora_fin)

    candidatos = preparar_candidatos(sesion, recomendaciones, fecha)

    if not candidatos:
        resultado.avisos.append(
            "Ninguna de las recomendaciones tiene coordenadas, así que no se "
            "puede armar una ruta. El inventario del MINCETUR no georreferencia "
            "todos sus recursos."
        )
        return resultado

    # Se limita el número de candidatos que entran al optimizador: la matriz
    # crece con el cuadrado y por encima de esto la espera deja de compensar.
    candidatos = sorted(candidatos, key=lambda c: -c.puntaje_relativo)[:MAXIMO_CANDIDATOS]

    # Se cuenta DESPUÉS de recortar: el aviso habla de los recursos que
    # realmente se consideraron, no de los que se descartaron por el camino.
    sin_horario = sum(1 for c in candidatos if not c.tiene_horario_conocido)

    paradas_maximas = min(PARADAS_MAXIMAS_POR_RITMO.get(preferencia.ritmo, 5), len(candidatos))

    presupuesto_traslado = _presupuesto_de_traslado_del_dia(preferencia)

    matriz = construir_matriz(sesion, candidatos, preferencia.movilidad, fecha)

    orden: list[int] | None = None

    if usar_modelo:
        try:
            orden = resolver_con_ortools(
                candidatos,
                matriz,
                inicio_dia,
                fin_dia,
                paradas_maximas,
                presupuesto_traslado,
                # Se lee la constante del modulo en cada llamada, y no se deja
                # como valor por defecto del parametro, para que las pruebas
                # puedan bajarla. Un valor por defecto se fija al definir la
                # funcion y ya no hay forma de cambiarlo.
                SEGUNDOS_DE_BUSQUEDA,
            )
        except Exception as error:  # noqa: BLE001
            # Que el optimizador falle no puede dejar al visitante sin
            # itinerario: para eso existe la alternativa por reglas.
            registro.warning("OR-Tools falló, se usa la alternativa por reglas: %s", error)
            orden = None

        if orden is None:
            resultado.generado_por = "reglas"
            resultado.avisos.append(
                "El optimizador no encontró una solución con estas restricciones, "
                "así que el itinerario se armó con la alternativa por reglas "
                "(vecino más cercano)."
            )

    if orden is None:
        orden = resolver_con_reglas(
            candidatos, matriz, inicio_dia, fin_dia, paradas_maximas, presupuesto_traslado
        )

    if not orden:
        resultado.avisos.append(
            "No se pudo armar ningún itinerario con el tiempo y el presupuesto " "indicados."
        )
        return resultado

    # --- Segunda pasada: tramos reales y horario definitivo ---------------
    traslados = refinar_traslados(sesion, candidatos, orden, preferencia.movilidad, fecha)

    resultado.paradas, avisos_de_horario = armar_horario(
        candidatos, orden, traslados, inicio_dia, fin_dia
    )
    resultado.avisos.extend(avisos_de_horario)

    _acumular_totales(resultado, inicio_dia)
    _agregar_avisos_de_calidad(resultado, sin_horario, len(candidatos))
    _explicar_si_el_dia_quedo_corto(
        resultado,
        candidatos,
        matriz,
        orden,
        paradas_maximas,
        presupuesto_traslado,
        preferencia,
    )

    return resultado


def _explicar_si_el_dia_quedo_corto(
    resultado: ItinerarioCalculado,
    candidatos: list[CandidatoARutear],
    matriz: list[list[CostoDeTraslado | None]],
    orden: list[int],
    paradas_maximas: int,
    presupuesto_traslado: Decimal,
    preferencia: PreferenciaViaje,
) -> None:
    """Dice POR QUÉ el itinerario tiene menos paradas de las que cabrían.

    Un itinerario de una sola parada, sin explicación, parece un fallo del
    sistema. Casi siempre no lo es: es el presupuesto de traslado, que con
    ``movilidad = taxi`` se agota en un solo trayecto largo. El visitante no
    tiene forma de deducirlo, así que hay que decírselo, y decirle además qué
    puede cambiar para que quepan más.

    Solo se emite cuando el presupuesto es **de verdad** el que corta: se
    comprueba que quede sitio en el día y que el traslado más barato que sale
    de la última parada ya no cabe en lo que sobra del dinero.
    """
    # Este caso va PRIMERO, antes de comprobar si el día está lleno. Con un
    # solo candidato el tope de paradas también vale uno, así que el día
    # parecería «lleno» y el visitante se quedaría sin explicación ninguna.
    #
    # Y no es que el dinero no llegue: es que no hay adónde ir. Pasa con
    # `movilidad = caminando`, cuyo alcance son 8 km, en distritos con poca
    # oferta cercana.
    if len(candidatos) < 2:
        moverse = (
            "moverte en transporte en vez de a pie"
            if preferencia.movilidad == "caminando"
            else "ampliar la zona"
        )
        resultado.avisos.append(
            f"Desde {preferencia.distrito_origen.title()} solo hay un recurso al "
            "alcance con los intereses y la forma de moverte que indicaste, así que "
            f"no hay recorrido que armar. Añadir intereses, o {moverse}, abriría "
            "muchas más opciones."
        )
        return

    if len(resultado.paradas) >= paradas_maximas:
        return  # el día está lleno: no falta nada que explicar

    if not orden or len(orden) >= len(candidatos):
        return  # no quedan candidatos a los que ir

    gastado = resultado.costo_max_soles
    disponible = presupuesto_traslado - gastado

    visitados = set(orden)
    ultimo = orden[len(resultado.paradas) - 1] if resultado.paradas else orden[0]

    precios_restantes = [
        traslado.precio_max_soles
        for destino, traslado in enumerate(matriz[ultimo])
        if destino not in visitados and traslado is not None
    ]

    if not precios_restantes:
        return

    if min(precios_restantes) <= disponible:
        return  # el dinero no es lo que corta; será el horario o el ritmo

    cuantas = len(resultado.paradas)
    plural = "parada" if cuantas == 1 else "paradas"

    consejo = (
        "Moverte en combi o colectivo en vez de en taxi abarataría mucho los traslados."
        if preferencia.movilidad == "taxi"
        else "Ampliar el presupuesto del viaje permitiría añadir más paradas."
    )

    # «Se acabó el presupuesto» sería falso cuando no se ha gastado nada: lo
    # que pasa entonces es que no alcanza ni para el primer traslado.
    if gastado == 0:
        motivo = (
            f"el traslado más barato desde ahí cuesta hasta "
            f"S/ {min(precios_restantes):.2f} y el presupuesto de traslado del día "
            f"es de S/ {presupuesto_traslado:.2f}"
        )
    else:
        motivo = (
            f"se agotó el presupuesto de traslado del día: S/ {presupuesto_traslado:.2f}, "
            f"de los que ya se usan hasta S/ {gastado:.2f}"
        )

    resultado.avisos.append(
        f"El itinerario tiene {cuantas} {plural} y no más porque {motivo}. Esa cifra "
        f"es la parte de tu presupuesto total reservada para transporte. {consejo}"
    )


def _presupuesto_de_traslado_del_dia(preferencia: PreferenciaViaje) -> Decimal:
    """Cuánto se puede gastar en traslados en un día.

    Reparte el presupuesto total entre los días del viaje y reserva la mayor
    parte para entradas, comida e imprevistos.
    """
    dias = max(1, (preferencia.fecha_fin - preferencia.fecha_inicio).days + 1)

    por_dia = Decimal(str(preferencia.presupuesto_soles)) / dias

    return (por_dia * PROPORCION_DE_TRASLADO).quantize(Decimal("0.01"))


def _acumular_totales(resultado: ItinerarioCalculado, inicio_dia: int) -> None:
    """Suma los totales del día a partir de las paradas ya cuadradas."""
    for parada in resultado.paradas:
        traslado = parada.traslado
        if traslado is None:
            continue

        resultado.costo_min_soles += traslado.precio_min_soles
        resultado.costo_max_soles += traslado.precio_max_soles
        resultado.distancia_total_km += traslado.distancia_km
        resultado.subida_total_m += traslado.subida_m

    if resultado.paradas:
        ultima = resultado.paradas[-1]
        resultado.tiempo_total_min = _a_minutos(ultima.hora_salida) - inicio_dia

    resultado.distancia_total_km = round(resultado.distancia_total_km, 2)
    resultado.subida_total_m = round(resultado.subida_total_m, 1)


def _agregar_avisos_de_calidad(
    resultado: ItinerarioCalculado, sin_horario: int, total_candidatos: int
) -> None:
    """Añade los avisos que el visitante tiene que ver sí o sí.

    Son tres, y ninguno es decorativo: dos afectan a la seguridad y uno a la
    confianza que se puede depositar en los tiempos mostrados.
    """
    if resultado.hay_tramos_estimados:
        estimados = sum(
            1
            for p in resultado.paradas
            if p.traslado is not None
            and p.traslado.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA
        )
        resultado.avisos.append(
            f"{estimados} de los traslados son una estimación: no hay red vial "
            "registrada en OpenStreetMap cerca de esos puntos, así que la "
            "distancia se calculó en línea recta corregida. El tiempo real puede "
            "ser bastante mayor."
        )

    altitudes = [p.candidato.altitud_m for p in resultado.paradas if p.candidato.altitud_m]

    if altitudes and necesita_aviso_de_altitud(max(altitudes)):
        resultado.avisos.append(
            f"El punto más alto del día está a {max(altitudes):.0f} m s.n.m. Si "
            "vienes de la costa, dedica el primer día a aclimatarte, bebe agua y "
            "no subas deprisa."
        )

    if resultado.esfuerzo != "suave":
        resultado.avisos.append(
            f"Día {resultado.esfuerzo}: {resultado.subida_total_m:.0f} m de subida " "acumulada."
        )

    if sin_horario:
        # Se redacta distinto cuando solo hay un recurso: «1 de los 1 recursos
        # considerados no tienen horario» es la clase de frase que delata que
        # nadie leyó el mensaje que escribió.
        if total_candidatos == 1:
            cuenta = "El único recurso considerado no tiene"
            alcance = "Para él"
        elif sin_horario == total_candidatos:
            cuenta = f"Ninguno de los {total_candidatos} recursos considerados tiene"
            alcance = "Para ellos"
        else:
            cuenta = f"{sin_horario} de los {total_candidatos} recursos considerados no tienen"
            alcance = "Para esos"

        resultado.avisos.append(
            f"{cuenta} horario de atención publicado en el inventario del "
            f"MINCETUR. {alcance}, el itinerario solo garantiza que la visita cabe "
            "dentro del día: confirma el horario antes de ir."
        )


# ---------------------------------------------------------------------------
# Reordenar a mano: el visitante arrastra las paradas
# ---------------------------------------------------------------------------


def construir_itinerario_en_orden(
    sesion: Session,
    preferencia: PreferenciaViaje,
    recomendaciones: list,
    fecha: date,
    recursos_en_orden: list[int],
    hora_inicio: time = HORA_INICIO_PREDETERMINADA,
    hora_fin: time = HORA_FIN_PREDETERMINADA,
) -> ItinerarioCalculado:
    """Recalcula el itinerario respetando el orden que pidió el visitante.

    Es lo que se ejecuta cuando alguien arrastra una parada a otro sitio. **No
    reoptimiza**: si el visitante decidió ir primero a Jauja, va primero a
    Jauja, aunque el optimizador prefiriera otra cosa. Reordenar por debajo lo
    que la persona acaba de ordenar a mano sería lo más frustrante que podría
    hacer esta pantalla.

    Lo que sí hace es **recalcular las consecuencias**: horas, traslados,
    costo, esfuerzo. Y si con el orden nuevo el día ya no cabe, lo recorta y lo
    dice, igual que en el camino automático.
    """
    resultado = ItinerarioCalculado(generado_por="reglas")

    inicio_dia = _a_minutos(hora_inicio)
    fin_dia = _a_minutos(hora_fin)

    candidatos = preparar_candidatos(sesion, recomendaciones, fecha)
    por_recurso = {c.recurso_id: c for c in candidatos}

    # Se respeta el orden pedido y se ignoran los identificadores que ya no
    # están entre las recomendaciones, en vez de fallar: la pantalla puede
    # haberse quedado con una lista vieja.
    elegidos = [por_recurso[i] for i in recursos_en_orden if i in por_recurso]

    if not elegidos:
        resultado.avisos.append(
            "Ninguno de los recursos indicados sigue estando entre las "
            "recomendaciones de esta preferencia."
        )
        return resultado

    descartados = len(recursos_en_orden) - len(elegidos)
    if descartados:
        resultado.avisos.append(
            f"Se omitieron {descartados} "
            f"{'parada' if descartados == 1 else 'paradas'} que ya no están entre las "
            "recomendaciones de esta preferencia."
        )

    orden = list(range(len(elegidos)))

    traslados = refinar_traslados(sesion, elegidos, orden, preferencia.movilidad, fecha)

    resultado.paradas, avisos_de_horario = armar_horario(
        elegidos, orden, traslados, inicio_dia, fin_dia
    )
    resultado.avisos.extend(avisos_de_horario)

    _acumular_totales(resultado, inicio_dia)

    sin_horario = sum(1 for c in elegidos if not c.tiene_horario_conocido)
    _agregar_avisos_de_calidad(resultado, sin_horario, len(elegidos))

    _avisar_si_se_paso_del_presupuesto(resultado, preferencia)

    return resultado


def _avisar_si_se_paso_del_presupuesto(
    resultado: ItinerarioCalculado, preferencia: PreferenciaViaje
) -> None:
    """Avisa si el orden que eligió el visitante se sale del presupuesto.

    En el camino automático el presupuesto es una restricción dura y no se
    puede incumplir. Aquí manda el visitante, así que no se le impide: se le
    dice. Bloquear un orden que la persona ha pedido a propósito sería
    tratarla como si no supiera lo que hace.
    """
    presupuesto = _presupuesto_de_traslado_del_dia(preferencia)

    if resultado.costo_max_soles > presupuesto:
        resultado.avisos.append(
            f"Con este orden, los traslados pueden costar hasta "
            f"S/ {resultado.costo_max_soles:.2f}, por encima de los "
            f"S/ {presupuesto:.2f} que corresponden a un día con tu presupuesto."
        )


# ---------------------------------------------------------------------------
# Guardar el itinerario
# ---------------------------------------------------------------------------


def guardar_itinerario(
    sesion: Session,
    preferencia: PreferenciaViaje,
    calculado: ItinerarioCalculado,
    fecha: date,
    titulo: str,
    usuario_id: int | None = None,
) -> Itinerario:
    """Persiste un itinerario calculado y devuelve la fila creada.

    No hace ``commit``: eso lo decide quien llama, para que la operación entera
    del endpoint sea una sola transacción.
    """
    itinerario = Itinerario(
        preferencia_id=preferencia.id,
        usuario_id=usuario_id,
        titulo=titulo,
        fecha=fecha,
        tiempo_total_min=calculado.tiempo_total_min,
        # Se guarda el máximo del rango, no el medio: para un total que sirva
        # de presupuesto, el número útil es el peor caso.
        costo_total_soles=calculado.costo_max_soles,
        distancia_total_km=calculado.distancia_total_km,
        desnivel_total_m=calculado.subida_total_m,
        estado=EstadoItinerario.GUARDADO,
        generado_por=calculado.generado_por,
        avisos="\n".join(calculado.avisos) if calculado.avisos else None,
    )

    for parada in calculado.paradas:
        traslado = parada.traslado

        itinerario.paradas.append(
            ParadaItinerario(
                recurso_id=parada.candidato.recurso_id,
                orden=parada.orden,
                hora_llegada=parada.hora_llegada,
                hora_salida=parada.hora_salida,
                modo_traslado=traslado.modo if traslado else None,
                tiempo_traslado_min=traslado.minutos if traslado else 0,
                distancia_traslado_km=traslado.distancia_km if traslado else 0,
                desnivel_traslado_m=traslado.desnivel_m if traslado else 0,
                costo_traslado_min_soles=traslado.precio_min_soles if traslado else 0,
                costo_traslado_max_soles=traslado.precio_max_soles if traslado else 0,
                origen_del_calculo=(
                    traslado.origen_del_calculo if traslado else OrigenDelCalculo.RED_VIAL
                ),
            )
        )

    sesion.add(itinerario)
    sesion.flush()  # para que el itinerario tenga id antes de responder

    return itinerario


def titulo_por_defecto(paradas: list[ParadaCalculada], fecha: date) -> str:
    """Un título legible para un itinerario que el visitante no ha nombrado.

    Se usan los distritos y no la fecha sola porque «Huancayo y Chupaca» dice
    de qué fue el día, y «12 de setiembre» no.
    """
    if not paradas:
        return f"Itinerario del {fecha.strftime('%d/%m/%Y')}"

    distritos: list[str] = []
    for parada in paradas:
        distrito = parada.candidato.distrito.title()
        if distrito not in distritos:
            distritos.append(distrito)

    if len(distritos) == 1:
        return f"Un día en {distritos[0]}"

    if len(distritos) == 2:
        return f"{distritos[0]} y {distritos[1]}"

    if len(distritos) == 3:
        return f"{distritos[0]}, {distritos[1]} y {distritos[2]}"

    restantes = len(distritos) - 2
    plural = "distrito" if restantes == 1 else "distritos"

    return f"{distritos[0]}, {distritos[1]} y {restantes} {plural} más"
