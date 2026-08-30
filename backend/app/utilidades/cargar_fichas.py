"""Vuelca a la base lo que traen las fichas web del MINCETUR.

    python -m app.utilidades.cargar_fichas

Descarga las 295 fichas —despacio, y guardándolas en disco— y escribe en la
base lo que el CSV del inventario no trae:

- la **descripción** de cada recurso,
- su **horario de visita**, en `horario_atencion`,
- el **tipo de ingreso** (libre o pagado),
- los **conteos reales de visitantes**, en `afluencia_historica`,
- y para las 36 fiestas del catálogo, **cuándo se celebran**.

El razonamiento de por qué esto no estaba y ahora sí está en
`utilidades/fichas_mincetur.py`. Lo corto: el CSV no lo publica, la ficha web
sí, y su dirección ya estaba guardada desde la Fase 1.

## Lo que no hace

No inventa nada. Lo que la ficha no diga se queda nulo, y al terminar el guion
dice de cuántas fichas faltó cada cosa. Ese recuento es un dato honesto sobre
la calidad de la fuente, y es el que hay que citar en la documentación en vez
de decir «ahora tenemos horarios».
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime, time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.base_datos import FabricaDeSesiones
from app.modelos.afluencia import AfluenciaHistorica
from app.modelos.catalogo import HorarioAtencion, RecursoTuristico
from app.utilidades.fichas_mincetur import (
    abrir_cliente,
    codigo_de_la_url,
    cuando_se_celebra,
    descargar_ficha,
    interpretar_horario,
    leer_ficha,
)

#: La categoría del inventario que agrupa las fiestas y ferias. Para estos
#: recursos, «cuándo» no es un detalle: es la mitad de la información.
CATEGORIA_DE_FIESTAS = "5."

FUENTE = "Ficha del Inventario Nacional de Recursos Turísticos, MINCETUR"


def _a_hora(texto: str) -> time:
    """«07:00» a un `time`."""
    horas, minutos = texto.split(":")

    return time(int(horas), int(minutos))


def volcar(sesion: Session, *, solo: int | None = None) -> Counter[str]:
    """Lee las fichas y escribe lo que traen. Devuelve el recuento.

    Es idempotente: vuelve a escribir los mismos valores y reemplaza los
    horarios y los conteos en vez de acumularlos.
    """
    consulta = select(RecursoTuristico).where(RecursoTuristico.url_ficha.is_not(None))
    recursos = list(sesion.scalars(consulta))

    if solo is not None:
        recursos = recursos[:solo]

    cuenta: Counter[str] = Counter()
    ahora = datetime.now(UTC)

    with abrir_cliente() as cliente:
        for recurso in recursos:
            html = descargar_ficha(recurso.url_ficha or "", cliente)

            if html is None:
                cuenta["ficha_no_disponible"] += 1
                continue

            codigo = codigo_de_la_url(recurso.url_ficha or "") or "?"
            ficha = leer_ficha(html, codigo)

            cuenta["fichas_leidas"] += 1
            recurso.ficha_leida_en = ahora

            # --- Descripción ----------------------------------------------
            if ficha.descripcion:
                recurso.descripcion_es = ficha.descripcion
                cuenta["con_descripcion"] += 1

            # --- Tipo de ingreso y época ----------------------------------
            if ficha.tipo_de_ingreso:
                recurso.tipo_de_ingreso = ficha.tipo_de_ingreso
                cuenta["con_ingreso"] += 1

            if ficha.epoca_propicia:
                recurso.epoca_propicia = ficha.epoca_propicia
                cuenta["con_epoca"] += 1

            # --- Horario ---------------------------------------------------
            horas = interpretar_horario(ficha.horario_en_texto)

            if horas is not None:
                apertura, cierre = horas

                # Se reemplazan, no se acumulan: volver a ejecutar el guion no
                # puede dejar el recurso con siete horarios repetidos por día.
                sesion.execute(
                    delete(HorarioAtencion).where(HorarioAtencion.recurso_id == recurso.id)
                )

                # La ficha da un horario y una época —«Todo el Año»—, pero no
                # dice qué días de la semana cierra. Se aplica a los siete
                # porque es lo único que la fuente permite afirmar; suponer que
                # cierra los lunes sería inventarlo.
                for dia in range(7):
                    sesion.add(
                        HorarioAtencion(
                            recurso_id=recurso.id,
                            dia_semana=dia,
                            hora_apertura=_a_hora(apertura),
                            hora_cierre=_a_hora(cierre),
                        )
                    )

                cuenta["con_horario"] += 1
            elif ficha.horario_en_texto:
                # La ficha traía algo pero no se supo leer. Se cuenta aparte:
                # si este número sube, la expresión regular se quedó corta.
                cuenta["horario_no_entendido"] += 1

            # --- Visitantes ------------------------------------------------
            if ficha.visitantes:
                sesion.execute(
                    delete(AfluenciaHistorica).where(AfluenciaHistorica.recurso_id == recurso.id)
                )

                # La ficha da el total del año, no el mes. Se guarda con mes
                # nulo en vez de repartirlo entre doce: repartirlo sería
                # inventarse una estacionalidad que la fuente no mide.
                for anio, tipo, cantidad, fuente in ficha.visitantes:
                    sesion.add(
                        AfluenciaHistorica(
                            recurso_id=recurso.id,
                            anio=anio,
                            mes=None,  # la ficha da el total del año, no el mes
                            tipo_de_visitante=tipo,
                            visitantes=cantidad,
                            fuente=f"{fuente} — {FUENTE}",
                        )
                    )

                cuenta["con_visitantes"] += 1

            # --- Cuándo se celebra, solo para las fiestas -------------------
            if (recurso.categoria or "").startswith(CATEGORIA_DE_FIESTAS):
                cuenta["fiestas"] += 1
                frase, meses = cuando_se_celebra(ficha.descripcion)

                if meses:
                    recurso.dias_de_celebracion = frase
                    recurso.meses_de_celebracion = meses
                    cuenta["fiestas_con_fecha"] += 1
                else:
                    # Se limpia por si una ejecución anterior había acertado y
                    # ahora no: dejar la fecha vieja sería peor que no tenerla.
                    recurso.dias_de_celebracion = None
                    recurso.meses_de_celebracion = []
                    cuenta["fiestas_sin_fecha"] += 1

            for ausente in ficha.ausentes:
                cuenta[f"falta_{ausente}"] += 1

    sesion.commit()

    return cuenta


def principal(argumentos: list[str] | None = None) -> int:
    """Punto de entrada del guion."""
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--solo",
        type=int,
        default=None,
        help="Procesa solo las primeras N fichas. Para probar sin bajarlas todas.",
    )
    opciones = analizador.parse_args(argumentos)

    with FabricaDeSesiones() as sesion:
        cuenta = volcar(sesion, solo=opciones.solo)

        leidas = cuenta["fichas_leidas"]

        print("Fichas del inventario del MINCETUR")
        print(f"  Leídas: {leidas}   No disponibles: {cuenta['ficha_no_disponible']}")
        print()
        print("  Lo que aportaron:")

        for etiqueta, clave in (
            ("descripción", "con_descripcion"),
            ("horario", "con_horario"),
            ("tipo de ingreso", "con_ingreso"),
            ("época propicia", "con_epoca"),
            ("visitantes", "con_visitantes"),
        ):
            cuantas = cuenta[clave]
            porcentaje = 100 * cuantas / leidas if leidas else 0
            print(f"    {etiqueta:16} {cuantas:4} de {leidas}  ({porcentaje:.0f} %)")

        print()
        print(f"  Fiestas del catálogo: {cuenta['fiestas']}")
        print(f"    con fecha en la ficha : {cuenta['fiestas_con_fecha']}")
        print(f"    sin fecha             : {cuenta['fiestas_sin_fecha']}")

        if cuenta["horario_no_entendido"]:
            print()
            print(
                f"  AVISO: {cuenta['horario_no_entendido']} fichas traían un horario "
                "que no se supo interpretar."
            )

        print()
        print("  Lo que la ficha NO dice se queda nulo. No se rellena a ojo.")

    return 0


if __name__ == "__main__":
    sys.exit(principal())
