/**
 * ESCENARIO (a) — Listar el catálogo.
 *
 * `GET /api/recursos` con paginación. Es el endpoint más visitado de la
 * aplicación: es lo primero que abre cualquiera que entre a `/explorar`, y el
 * único de los tres que **no necesita cuenta ni preferencia previa**.
 *
 * Qué ejercita: una consulta paginada sobre `recurso_turistico` (295 filas) con
 * su serialización a JSON. No toca PostGIS ni ningún modelo de IA.
 *
 * Niveles: 5, 15 y 30 usuarios concurrentes, 30 s cada uno.
 *
 *   docker run --rm -i -v "...:/carga" grafana/k6 run /carga/01-catalogo.js
 */

import { check, sleep } from 'k6';
import { ESTADISTICOS, escenariosEscalonados, medidorPorNivel, obtener } from './comun.js';

const NIVELES = [5, 15, 30];
const medir = medidorPorNivel(NIVELES);

export const options = {
  summaryTrendStats: ESTADISTICOS,
  scenarios: escenariosEscalonados(NIVELES, 30, 'catalogo'),
  // Umbral informativo: no hace fallar la ejecución, solo deja constancia.
  thresholds: {
    'http_req_failed': ['rate<0.01'],
  },
};

export function catalogo() {
  // Se alterna la página para que la caché de PostgreSQL no responda siempre lo
  // mismo. Con una sola página, la medición saldría mejor de lo que es.
  const pagina = 1 + (__ITER % 5);
  const respuesta = obtener(`/api/recursos?pagina=${pagina}&tamano_pagina=20`);

  medir(respuesta);

  check(respuesta, {
    'responde 200': (r) => r.status === 200,
    'trae los 295 recursos en el total': (r) => {
      try {
        return r.json('total') === 295;
      } catch {
        return false;
      }
    },
  });

  // Pausa breve: un visitante real no pide la página siguiente al instante.
  sleep(0.5);
}
