"""Comprueba, con datos reales, la lista de verificación del Incremento 4.

Se ejecuta desde ``backend/``:

    python -m app.utilidades.verificar_fase4

No sustituye a las pruebas automáticas: las pruebas comprueban el algoritmo
sobre casos controlados, y esto comprueba el sistema entero sobre los 295
recursos del catálogo real. Las dos cosas hacen falta, y fallan por motivos
distintos.

Devuelve 0 si todo pasa y 1 si algo falla, para poder encadenarlo.
"""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from decimal import Decimal

from app.base_datos import FabricaDeSesiones
from app.modelos.itinerario import OrigenDelCalculo
from app.modelos.preferencias import INTERESES_VALIDOS, PreferenciaViaje
from app.servicios.recomendador import recomendar
from app.servicios.ruteo import (
    PROPORCION_DE_TRASLADO,
    construir_itinerario,
)

#: Tope que fija el plan de trabajo: «un itinerario de 4 paradas en Huancayo se
#: calcula en menos de 10 segundos».
SEGUNDOS_MAXIMOS = 10.0

#: Perfiles con los que se prueba. Se eligen distintos entre sí a propósito:
#: distinto distrito de origen, distinta movilidad y distinto ritmo, para que
#: el itinerario recorra caminos de código diferentes.
PERFILES = [
    (
        "Huancayo, cultura, transporte público",
        "HUANCAYO",
        ["arqueologia", "iglesias_conventos"],
        "transporte_publico",
        "moderado",
        "500",
    ),
    (
        "Huancayo, naturaleza, taxi",
        "HUANCAYO",
        ["naturaleza", "aventura"],
        "taxi",
        "moderado",
        "600",
    ),
    (
        "Chupaca, artesanía, caminando",
        "CHUPACA",
        ["artesania", "gastronomia"],
        "caminando",
        "relajado",
        "300",
    ),
    (
        "Jauja, todo, ritmo intenso",
        "JAUJA",
        ["arqueologia", "naturaleza", "ferias_fiestas"],
        "combinado",
        "intenso",
        "800",
    ),
]


def _preferencia(distrito, intereses, movilidad, ritmo, presupuesto) -> PreferenciaViaje:
    """Una preferencia en memoria, sin guardarla: solo se necesita para calcular.

    Se validan los intereses a mano porque aqui se construye el modelo de
    SQLAlchemy directamente, saltandose la validacion de Pydantic que aplica el
    endpoint. Sin esta comprobacion, un interes inexistente se colaria en
    silencio y el script estaria midiendo con una entrada que la API rechazaria.
    Paso: el perfil de Jauja usaba «folclore», que no esta en la lista.
    """
    invalidos = set(intereses) - set(INTERESES_VALIDOS)
    if invalidos:
        raise ValueError(
            f"Intereses no reconocidos: {', '.join(sorted(invalidos))}. "
            f"Los validos son: {', '.join(sorted(INTERESES_VALIDOS))}"
        )

    hoy = date(2026, 9, 12)

    return PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=hoy,
        fecha_fin=hoy + timedelta(days=2),
        distrito_origen=distrito,
        presupuesto_soles=Decimal(presupuesto),
        intereses=intereses,
        movilidad=movilidad,
        requiere_accesibilidad=False,
        idioma="es",
        ritmo=ritmo,
    )


def main() -> int:
    # La consola de Windows usa cp1252 por omision y revienta con los guiones
    # largos y las tildes. Se fuerza UTF-8 en la salida antes de escribir nada.
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 78)
    print("VERIFICACIÓN DEL INCREMENTO 4 — RUTEO GEOESPACIAL MULTIMODAL")
    print("=" * 78)
    print()

    fallos: list[str] = []
    tiempos: list[float] = []

    with FabricaDeSesiones() as sesion:
        for etiqueta, distrito, intereses, movilidad, ritmo, presupuesto in PERFILES:
            preferencia = _preferencia(distrito, intereses, movilidad, ritmo, presupuesto)

            inicio = time.perf_counter()
            recomendacion = recomendar(sesion, preferencia, limite=40)
            itinerario = construir_itinerario(
                sesion, preferencia, recomendacion.recomendaciones, preferencia.fecha_inicio
            )
            tardanza = time.perf_counter() - inicio
            tiempos.append(tardanza)

            print(f"── {etiqueta}")
            print(f"   paradas    : {len(itinerario.paradas)}")
            print(f"   generado   : {itinerario.generado_por}")
            print(f"   tiempo     : {tardanza:.2f} s")
            print(
                f"   costo      : S/ {itinerario.costo_min_soles} – "
                f"{itinerario.costo_max_soles}"
            )
            print(f"   distancia  : {itinerario.distancia_total_km} km")
            print(f"   esfuerzo   : {itinerario.esfuerzo} ({itinerario.subida_total_m:.0f} m)")

            # --- Comprobación 1: menos de 10 segundos ---------------------
            if tardanza > SEGUNDOS_MAXIMOS:
                fallos.append(f"{etiqueta}: tardó {tardanza:.1f} s (tope {SEGUNDOS_MAXIMOS} s)")

            # --- Comprobación 2: nunca se supera el presupuesto -----------
            dias = (preferencia.fecha_fin - preferencia.fecha_inicio).days + 1
            tope = (Decimal(presupuesto) / dias * PROPORCION_DE_TRASLADO).quantize(Decimal("0.01"))

            if itinerario.costo_max_soles > tope:
                fallos.append(
                    f"{etiqueta}: costo máximo S/ {itinerario.costo_max_soles} "
                    f"supera el presupuesto de traslado del día S/ {tope}"
                )
            else:
                print(f"   presupuesto: S/ {itinerario.costo_max_soles} de S/ {tope}  OK")

            # --- Comprobación 3: las horas avanzan y caben en el día ------
            anterior_salida = None
            for parada in itinerario.paradas:
                if anterior_salida is not None and parada.hora_llegada < anterior_salida:
                    fallos.append(
                        f"{etiqueta}: la parada {parada.orden + 1} llega a las "
                        f"{parada.hora_llegada} antes de que acabe la anterior "
                        f"({anterior_salida})"
                    )
                anterior_salida = parada.hora_salida

            # --- Comprobación 4: ningún recurso repetido ------------------
            ids = [p.candidato.recurso_id for p in itinerario.paradas]
            if len(ids) != len(set(ids)):
                fallos.append(f"{etiqueta}: hay recursos repetidos en el itinerario")

            # --- Comprobación 5: cada traslado con fuente y fecha ---------
            for parada in itinerario.paradas:
                traslado = parada.traslado
                if traslado is None:
                    continue
                if not traslado.fuente or not traslado.fecha_referencia:
                    fallos.append(
                        f"{etiqueta}: un traslado salió sin fuente o sin fecha de referencia"
                    )
                if traslado.precio_max_soles < traslado.precio_min_soles:
                    fallos.append(f"{etiqueta}: un traslado tiene el rango de precio invertido")

            estimados = sum(
                1
                for p in itinerario.paradas
                if p.traslado is not None
                and p.traslado.origen_del_calculo == OrigenDelCalculo.LINEA_RECTA
            )
            reales = sum(1 for p in itinerario.paradas if p.traslado is not None) - estimados
            print(f"   tramos     : {reales} sobre la red vial, {estimados} estimados")

            # --- Comprobación 6: los tramos estimados se avisan -----------
            hay_aviso = any("estimaci" in a.lower() for a in itinerario.avisos)
            if estimados > 0 and not hay_aviso:
                fallos.append(f"{etiqueta}: hay tramos estimados y no se avisa de ello")

            print()

    print("=" * 78)
    print("RESUMEN")
    print("=" * 78)
    print(f"  Perfiles probados     : {len(PERFILES)}")
    print(f"  Tiempo máximo         : {max(tiempos):.2f} s  (tope {SEGUNDOS_MAXIMOS} s)")
    print(f"  Tiempo medio          : {sum(tiempos) / len(tiempos):.2f} s")
    print()

    if fallos:
        print(f"  {len(fallos)} COMPROBACIÓN(ES) FALLIDA(S):")
        for fallo in fallos:
            print(f"    - {fallo}")
        return 1

    print("  Todas las comprobaciones pasan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
