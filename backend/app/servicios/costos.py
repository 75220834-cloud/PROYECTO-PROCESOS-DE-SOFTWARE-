"""Matriz de costos multimodal: cuánto cuesta y cuánto tarda ir de A a B.

## El problema de datos, dicho sin adornos

El plan pide *«cargar las tarifas conocidas de CONTEXTO_PROYECTO.md»*. Al ir a
buscarlas resulta que **ese documento no publica ni una sola tarifa con valor
numérico**. Lo que publica es la lista de las que están *sin verificar*:

> «tarifas Huancayo–Jauja y Huancayo–Chupaca · taxi a Ocopa y a Huaytapallana»
> — CONTEXTO_PROYECTO.md, sección «Datos NO verificados»

Y antes advierte que *«las tarifas de Huancayo cambian y no hay tarifa oficial
única»*.

Así que hay tres caminos, y solo uno es defendible:

1. Poner números de memoria y presentarlos como tarifas. **Prohibido** por la
   regla de no inventar tarifas, y sería lo peor que podría hacer este módulo.
2. No calcular costos. Deja el Incremento 4 sin la restricción de presupuesto,
   que es justo la brecha que hay que cerrar.
3. **Calcular el costo con una fórmula explícita y publicada aquí, marcar todo
   resultado como estimado, y guardar la fórmula como «fuente».** Es lo que se
   hace.

La diferencia entre 1 y 3 no es cosmética. Un número inventado se presenta como
un hecho y no se puede discutir. Una estimación con fórmula visible se puede
revisar, criticar y **sustituir**: en cuanto alguien consulte una tarifa real,
se inserta en ``tarifa_transporte`` y este módulo la prefiere automáticamente
sobre su propia estimación.

## Cómo se decide el modo

| Situación | Modo |
|---|---|
| Mismo distrito y ≤ 2,5 km | caminando (Tobler) |
| El visitante dijo «caminando» | caminando siempre |
| Distinto distrito, transporte público | combi hasta 15 km, colectivo más allá |
| El visitante dijo «taxi» | taxi |
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.itinerario import OrigenDelCalculo
from app.modelos.transporte import ModoTransporte, TarifaTransporte
from app.servicios.red_vial import Traslado, distancia_en_linea_recta_m, obtener_red_vial

# ---------------------------------------------------------------------------
# Reglas de elección del modo
# ---------------------------------------------------------------------------

#: Hasta esta distancia dentro del mismo distrito se va a pie. Son unos 30
#: minutos en llano según Tobler: el límite razonable para no coger transporte.
DISTANCIA_MAXIMA_A_PIE_KM = 2.5

#: A partir de aquí, entre distritos, el servicio deja de ser combi urbana y
#: pasa a ser colectivo interdistrital.
DISTANCIA_DE_COLECTIVO_KM = 15.0

# ---------------------------------------------------------------------------
# La fórmula de estimación, y sus supuestos declarados
# ---------------------------------------------------------------------------

#: Parámetros de la estimación de tarifa: ``modo -> (base_min, base_max,
#: por_km_min, por_km_max)``, todo en soles.
#:
#: **ESTOS NÚMEROS SON UN SUPUESTO DEL EQUIPO, NO UNA TARIFA CONSULTADA.**
#: No proceden de ninguna fuente oficial, porque no existe: el propio contexto
#: del proyecto dice que no hay tarifa oficial única en Huancayo. Se eligieron
#: como orden de magnitud del transporte público urbano e interdistrital
#: peruano, y se expresan como rango precisamente porque el valor exacto se
#: desconoce.
#:
#: Todo costo que salga de aquí viaja marcado con ``es_estimado=True`` y llega
#: a la interfaz con la palabra «aprox.» y la fecha. En cuanto alguien consulte
#: una tarifa real y la inserte en ``tarifa_transporte``, esta estimación deja
#: de usarse para ese trayecto.
PARAMETROS_DE_ESTIMACION: dict[str, tuple[str, str, str, str]] = {
    ModoTransporte.COMBI: ("1.00", "1.50", "0.10", "0.15"),
    ModoTransporte.COLECTIVO: ("2.00", "3.00", "0.15", "0.25"),
    ModoTransporte.TAXI: ("5.00", "8.00", "1.50", "2.50"),
    ModoTransporte.CAMINANDO: ("0.00", "0.00", "0.00", "0.00"),
}

#: Texto que se guarda como fuente de un costo estimado. Es deliberadamente
#: explícito: quien lea la base de datos tiene que ver de un vistazo que ahí no
#: hay una consulta a nadie, sino una fórmula.
FUENTE_ESTIMADA = (
    "Estimación del equipo por distancia (tarifa base + soles por kilómetro). "
    "No procede de una fuente oficial: CONTEXTO_PROYECTO.md declara que no hay "
    "tarifa oficial única en el valle y lista estas tarifas como no verificadas."
)

#: Velocidades medias de circulación, en km/h, para estimar la duración de un
#: traslado motorizado. También son un supuesto, y por eso son conservadoras:
#: se prefiere que el itinerario sobre tiempo a que el visitante llegue tarde.
VELOCIDAD_MEDIA_KMH: dict[str, float] = {
    ModoTransporte.COMBI: 22.0,  # para mucho, recoge y deja pasajeros
    ModoTransporte.COLECTIVO: 40.0,  # carretera interdistrital
    ModoTransporte.TAXI: 35.0,
}

#: Minutos que se pierden esperando el vehículo. Sin esto, un itinerario con
#: seis traslados en combi se equivoca en más de una hora.
ESPERA_POR_MODO_MIN: dict[str, int] = {
    ModoTransporte.COMBI: 10,
    ModoTransporte.COLECTIVO: 15,
    ModoTransporte.TAXI: 5,
    ModoTransporte.CAMINANDO: 0,
}


@dataclass
class CostoDeTraslado:
    """Lo que cuesta un traslado, con su procedencia y su incertidumbre."""

    modo: str
    distancia_km: float
    minutos: int
    desnivel_m: float
    subida_m: float

    precio_min_soles: Decimal
    precio_max_soles: Decimal

    #: 'red_vial' o 'linea_recta': cómo se calculó la distancia.
    origen_del_calculo: str

    #: True si el precio salió de la fórmula y no de una tarifa consultada.
    es_estimado: bool
    fuente: str
    fecha_referencia: date

    #: Coordenadas del camino, para dibujarlo. Vacío si fue en línea recta.
    trazado: list[tuple[float, float]]

    @property
    def precio_medio_soles(self) -> Decimal:
        """Punto medio del rango. Solo para sumar totales, nunca para mostrar."""
        return (self.precio_min_soles + self.precio_max_soles) / 2


def elegir_modo(distancia_km: float, mismo_distrito: bool, movilidad: str) -> str:
    """Decide cómo se cubre un traslado según la movilidad declarada.

    ``movilidad`` es lo que el visitante eligió en el asistente de
    preferencias: ``caminando``, ``transporte_publico``, ``taxi`` o
    ``combinado``.
    """
    if movilidad == "caminando":
        return ModoTransporte.CAMINANDO

    if movilidad == "taxi":
        return ModoTransporte.TAXI

    # 'transporte_publico' y 'combinado': se va a pie si está al lado, y en
    # transporte si no.
    if mismo_distrito and distancia_km <= DISTANCIA_MAXIMA_A_PIE_KM:
        return ModoTransporte.CAMINANDO

    if distancia_km <= DISTANCIA_DE_COLECTIVO_KM:
        return ModoTransporte.COMBI

    return ModoTransporte.COLECTIVO


def estimar_precio(modo: str, distancia_km: float) -> tuple[Decimal, Decimal]:
    """Aplica la fórmula de estimación y devuelve el rango de precio.

    Se redondea a medio sol hacia arriba porque en el transporte del valle no
    circulan monedas de céntimo para estos importes: un pasaje se cobra en
    soles y medios soles.
    """
    base_min, base_max, km_min, km_max = PARAMETROS_DE_ESTIMACION[modo]

    distancia = Decimal(str(round(distancia_km, 2)))

    minimo = Decimal(base_min) + Decimal(km_min) * distancia
    maximo = Decimal(base_max) + Decimal(km_max) * distancia

    return _redondear_a_medio_sol(minimo), _redondear_a_medio_sol(maximo)


def _redondear_a_medio_sol(importe: Decimal) -> Decimal:
    """Redondea hacia arriba al múltiplo de 0,50 soles más cercano."""
    if importe <= 0:
        return Decimal("0.00")

    medios = (importe * 2).to_integral_value(rounding="ROUND_CEILING")
    return (medios / 2).quantize(Decimal("0.01"))


def _buscar_tarifa_publicada(
    sesion: Session, distrito_origen: str, distrito_destino: str, modo: str
) -> TarifaTransporte | None:
    """Busca una tarifa guardada para ese trayecto, en cualquier sentido.

    Se consulta en los dos sentidos porque el pasaje de Huancayo a Jauja y el
    de Jauja a Huancayo son el mismo servicio, y guardar las dos filas sería
    duplicar el mismo dato con el riesgo de que se desactualicen por separado.
    """
    origen = distrito_origen.upper()
    destino = distrito_destino.upper()

    return sesion.scalars(
        select(TarifaTransporte)
        .where(
            TarifaTransporte.modo == modo,
            (
                (TarifaTransporte.distrito_origen == origen)
                & (TarifaTransporte.distrito_destino == destino)
            )
            | (
                (TarifaTransporte.distrito_origen == destino)
                & (TarifaTransporte.distrito_destino == origen)
            ),
        )
        .limit(1)
    ).first()


def calcular_traslado(
    sesion: Session,
    latitud_origen: float,
    longitud_origen: float,
    altitud_origen: float | None,
    distrito_origen: str,
    latitud_destino: float,
    longitud_destino: float,
    altitud_destino: float | None,
    distrito_destino: str,
    movilidad: str,
    fecha: date,
    usar_red: bool = True,
) -> CostoDeTraslado:
    """Calcula el traslado completo entre dos recursos: modo, tiempo y costo.

    Es la entrada principal del módulo y la que usa el optimizador de rutas.

    Con ``usar_red=False`` no se consulta el grafo y la caminata se estima con
    línea recta × factor de rodeo. Lo usa el optimizador para llenar su matriz
    de N² traslados, donde buscar N² caminos mínimos sobre 40 000 nodos
    tardaría minutos. Los tramos de la solución final sí se calculan con
    ``usar_red=True``.
    """
    recta_km = (
        distancia_en_linea_recta_m(
            latitud_origen, longitud_origen, latitud_destino, longitud_destino
        )
        / 1000.0
    )

    mismo_distrito = distrito_origen.upper() == distrito_destino.upper()
    modo = elegir_modo(recta_km, mismo_distrito, movilidad)

    if modo == ModoTransporte.CAMINANDO:
        return _traslado_a_pie(
            latitud_origen,
            longitud_origen,
            altitud_origen,
            latitud_destino,
            longitud_destino,
            altitud_destino,
            recta_km,
            fecha,
            usar_red,
        )

    return _traslado_motorizado(
        sesion,
        modo,
        recta_km,
        latitud_origen,
        longitud_origen,
        latitud_destino,
        longitud_destino,
        distrito_origen,
        distrito_destino,
        altitud_origen,
        altitud_destino,
        fecha,
        usar_red,
    )


def _traslado_a_pie(
    latitud_origen: float,
    longitud_origen: float,
    altitud_origen: float | None,
    latitud_destino: float,
    longitud_destino: float,
    altitud_destino: float | None,
    recta_km: float,
    fecha: date,
    usar_red: bool = True,
) -> CostoDeTraslado:
    """Traslado caminando: la distancia sale de la red vial, el precio es cero."""
    red = obtener_red_vial() if usar_red else None

    if red is None:
        # Sin grafo preparado no hay ruteo posible. Se degrada al mismo
        # cálculo de línea recta que se usa fuera de cobertura, y se marca
        # igual, para que el aviso al visitante sea el mismo.
        traslado = _traslado_recto_sin_red(recta_km, altitud_origen, altitud_destino)
    else:
        traslado = red.calcular_traslado_caminando(
            latitud_origen,
            longitud_origen,
            altitud_origen,
            latitud_destino,
            longitud_destino,
            altitud_destino,
        )

    return CostoDeTraslado(
        modo=ModoTransporte.CAMINANDO,
        distancia_km=round(traslado.distancia_m / 1000.0, 2),
        minutos=int(round(traslado.minutos)),
        desnivel_m=traslado.desnivel_m,
        subida_m=traslado.subida_m,
        precio_min_soles=Decimal("0.00"),
        precio_max_soles=Decimal("0.00"),
        origen_del_calculo=traslado.origen_del_calculo,
        # Caminar no cuesta dinero: eso no es una estimación, es un hecho.
        es_estimado=False,
        fuente="Caminata calculada con la función de Tobler (1993) sobre el "
        "modelo de elevación Copernicus GLO-30.",
        fecha_referencia=fecha,
        trazado=traslado.trazado,
    )


def _traslado_recto_sin_red(
    recta_km: float, altitud_origen: float | None, altitud_destino: float | None
) -> Traslado:
    """Caminata estimada cuando no hay grafo cargado."""
    from app.ia.tiempo_recorrido import calcular_tramo_caminando
    from app.servicios.red_vial import FACTOR_DE_RODEO

    metros = recta_km * 1000.0 * FACTOR_DE_RODEO
    tramo = calcular_tramo_caminando(metros, altitud_origen, altitud_destino)

    return Traslado(
        distancia_m=round(metros, 1),
        minutos=tramo.minutos,
        desnivel_m=tramo.desnivel_m,
        subida_m=max(0.0, tramo.desnivel_m),
        origen_del_calculo=OrigenDelCalculo.LINEA_RECTA,
        trazado=[],
    )


def _traslado_motorizado(
    sesion: Session,
    modo: str,
    recta_km: float,
    latitud_origen: float,
    longitud_origen: float,
    latitud_destino: float,
    longitud_destino: float,
    distrito_origen: str,
    distrito_destino: str,
    altitud_origen: float | None,
    altitud_destino: float | None,
    fecha: date,
    usar_red: bool,
) -> CostoDeTraslado:
    """Traslado en combi, colectivo o taxi.

    La distancia sale de la carretera real siempre que se pueda: el grafo se
    descargó con ``network_type="all"``, así que las vías rodadas están dentro.
    Solo cuando no hay red cerca se cae a la línea recta corregida, y entonces
    se marca —eso es lo que dispara el aviso de tramo estimado en la interfaz—.

    El precio prefiere siempre una tarifa guardada; solo estima si no la hay.
    Son dos decisiones **independientes**: un tramo puede tener la distancia
    calculada sobre la carretera real y el precio estimado, que es de hecho el
    caso habitual hoy.
    """
    distancia_km, origen_del_calculo, trazado = _distancia_por_carretera(
        recta_km,
        latitud_origen,
        longitud_origen,
        latitud_destino,
        longitud_destino,
        usar_red,
    )

    desnivel = (
        altitud_destino - altitud_origen
        if altitud_origen is not None and altitud_destino is not None
        else 0.0
    )

    tarifa = _buscar_tarifa_publicada(sesion, distrito_origen, distrito_destino, modo)

    if tarifa is not None:
        return CostoDeTraslado(
            modo=modo,
            distancia_km=distancia_km,
            minutos=tarifa.duracion_estimada_min,
            desnivel_m=round(desnivel, 1),
            subida_m=0.0,  # en vehículo el desnivel lo sube el motor
            precio_min_soles=Decimal(str(tarifa.precio_min_soles)),
            precio_max_soles=Decimal(str(tarifa.precio_max_soles)),
            origen_del_calculo=origen_del_calculo,
            es_estimado=bool(tarifa.es_estimado),
            fuente=tarifa.fuente,
            fecha_referencia=tarifa.fecha_referencia,
            trazado=trazado,
        )

    minimo, maximo = estimar_precio(modo, distancia_km)

    minutos = int(
        round(distancia_km / VELOCIDAD_MEDIA_KMH[modo] * 60.0 + ESPERA_POR_MODO_MIN[modo])
    )

    return CostoDeTraslado(
        modo=modo,
        distancia_km=distancia_km,
        minutos=minutos,
        desnivel_m=round(desnivel, 1),
        subida_m=0.0,
        precio_min_soles=minimo,
        precio_max_soles=maximo,
        origen_del_calculo=origen_del_calculo,
        es_estimado=True,
        fuente=FUENTE_ESTIMADA,
        fecha_referencia=fecha,
        trazado=trazado,
    )


def _distancia_por_carretera(
    recta_km: float,
    latitud_origen: float,
    longitud_origen: float,
    latitud_destino: float,
    longitud_destino: float,
    usar_red: bool,
) -> tuple[float, str, list[tuple[float, float]]]:
    """Distancia rodada entre dos puntos, con su procedencia y su trazado."""
    from app.servicios.red_vial import FACTOR_DE_RODEO

    red = obtener_red_vial() if usar_red else None

    if red is not None:
        busqueda = red.buscar_camino(
            latitud_origen, longitud_origen, latitud_destino, longitud_destino
        )

        if busqueda.camino is not None:
            metros, trazado = red.longitud_del_camino_m(busqueda.camino)
            return round(metros / 1000.0, 2), OrigenDelCalculo.RED_VIAL, trazado

        if busqueda.hay_cobertura:
            # Mismo nodo: los dos puntos están sobre la red y prácticamente en
            # el mismo sitio. No hay rodeo que corregir ni nada que avisar.
            return round(busqueda.recta_m / 1000.0, 2), OrigenDelCalculo.RED_VIAL, []

    # Sin red cerca (o sin grafo cargado): línea recta corregida por el factor
    # de rodeo medido. Las carreteras rodean igual que los caminos.
    return round(recta_km * FACTOR_DE_RODEO, 2), OrigenDelCalculo.LINEA_RECTA, []
