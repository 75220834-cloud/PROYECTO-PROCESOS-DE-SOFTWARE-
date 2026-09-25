/**
 * ESCENARIO (c) — Armar el itinerario. **El más pesado de los tres.**
 *
 * `POST /api/itinerarios` con `guardar: false`, para medir el cálculo sin
 * escribir en la base.
 *
 * Qué ejercita, encadenado en una sola petición:
 *
 *   1. todo lo del escenario (b): filtros + TF-IDF + afluencia;
 *   2. carga de la red vial (28 MB en memoria de proceso, cacheada con
 *      `lru_cache`, así que solo la primera petición la paga);
 *   3. un camino mínimo sobre el grafo de OSM por cada par de paradas
 *      candidatas, o línea recta × 1,26 si alguno está a más de 500 m de la red
 *      (ADR-006);
 *   4. la función de Tobler sobre el modelo de elevación para el tiempo a pie;
 *   5. **OR-Tools resolviendo un VRPTW de recolección de premios** (ADR-007);
 *   6. estimación de costos con rango, fecha y fuente (ADR-008);
 *   7. los avisos del día como {codigo, parametros} (ADR-013).
 *
 * Medido a mano antes de la prueba de carga: **9,53 s** en la primera petición
 * (con la red vial aún sin cargar) y del orden de 2,5–6,8 s después.
 *
 * Niveles: 1, 2 y 4 usuarios concurrentes, 90 s cada uno. Son pocos a propósito.
 * Con peticiones de varios segundos, cada usuario concurrente añade segundos de
 * cola; subir a 20 no mediría el sistema, mediría la cola. Y 90 s en vez de 30
 * para que haya suficientes muestras por nivel.
 *
 * Necesita PREFERENCIA=<id> en el entorno.
 */

import { check } from 'k6';
import {
  ESTADISTICOS,
  PREFERENCIA,
  escenariosEscalonados,
  medidorPorNivel,
  publicar,
} from './comun.js';

const NIVELES = [1, 2, 4];
const medir = medidorPorNivel(NIVELES);

export const options = {
  summaryTrendStats: ESTADISTICOS,
  scenarios: escenariosEscalonados(NIVELES, 90, 'itinerario'),
  thresholds: {
    'http_req_failed': ['rate<0.01'],
  },
};

export function setup() {
  if (!PREFERENCIA) {
    throw new Error('Falta la variable PREFERENCIA. Pásala con -e PREFERENCIA=3005');
  }
  return { preferencia: PREFERENCIA };
}

export function itinerario(datos) {
  // Se rota la fecha entre los tres días del viaje: cada día da un itinerario
  // distinto porque cambian los horarios y la afluencia. Pedir siempre el mismo
  // día mediría el mismo cálculo una y otra vez.
  const dia = 5 + (__ITER % 3);

  const respuesta = publicar('/api/itinerarios', {
    preferencia_id: datos.preferencia,
    fecha: `2026-10-0${dia}`,
    guardar: false,
  });

  medir(respuesta);

  check(respuesta, {
    'responde 200': (r) => r.status === 200,
    'arma al menos una parada': (r) => {
      try {
        return r.json('paradas').length > 0;
      } catch {
        return false;
      }
    },
    'cada traslado dice si es estimado': (r) => {
      try {
        const paradas = r.json('paradas');
        const conTraslado = paradas.filter((p) => p.traslado !== null);
        // ADR-006: el sistema siempre declara si el tramo salió de la red vial
        // o de una línea recta corregida. Si esto falla, el itinerario está
        // presentando una estimación como si fuera un cálculo.
        return conTraslado.every((p) =>
          ['red_vial', 'linea_recta'].includes(p.traslado.origen_del_calculo),
        );
      } catch {
        return false;
      }
    },
    'declara con que via se genero': (r) => {
      try {
        return ['modelo', 'reglas'].includes(r.json('generado_por'));
      } catch {
        return false;
      }
    },
  });
}
