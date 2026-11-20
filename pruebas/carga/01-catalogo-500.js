/**
 * ESCENARIO (a) — Listar el catalogo, A ALTA CARGA.
 *
 * Copia de 01-catalogo.js con los niveles subidos hasta 500 usuarios
 * concurrentes, para medir el umbral que exige la Guia de Trabajo 10:
 * latencia p95 por debajo de 800 ms con 500 usuarios.
 *
 * El original (5, 15 y 30 usuarios) NO se toca: sigue siendo la medicion
 * de referencia del informe de la semana 6.
 *
 * Niveles: 50, 150, 300 y 500 usuarios concurrentes, 30 s cada uno.
 * Duracion total aproximada: 2 minutos.
 */

import { check, sleep } from 'k6';
import { ESTADISTICOS, escenariosEscalonados, medidorPorNivel, obtener } from './comun.js';

const NIVELES = [50, 150, 300, 500];
const medir = medidorPorNivel(NIVELES);

export const options = {
  summaryTrendStats: ESTADISTICOS,
  scenarios: escenariosEscalonados(NIVELES, 30, 'catalogo'),
  thresholds: {
    'http_req_failed': ['rate<0.01'],
    'http_req_duration': ['p(95)<800'],
  },
};

export function catalogo() {
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

  sleep(0.5);
}
