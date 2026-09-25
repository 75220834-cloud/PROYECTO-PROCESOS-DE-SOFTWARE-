/**
 * ESCENARIO (b) — Generar recomendaciones.
 *
 * `POST /api/recomendaciones` sobre una preferencia ya creada.
 *
 * Qué ejercita, y por eso es más caro que el catálogo: lee los 295 recursos,
 * aplica los filtros duros de la preferencia, **ajusta un TF-IDF en memoria en
 * cada petición** (ADR-004: no hay modelo entrenado que cargar), calcula la
 * similitud coseno, estima la afluencia de cada candidato con las reglas de
 * calendario, y devuelve cada recomendación con los términos que más pesaron.
 *
 * Niveles: 5, 10 y 20 usuarios concurrentes, 30 s cada uno. Se queda por debajo
 * del catálogo porque cada petición cuesta del orden de un segundo y con 30
 * usuarios la cola crece más rápido de lo que se vacía.
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

const NIVELES = [5, 10, 20];
const medir = medidorPorNivel(NIVELES);

export const options = {
  summaryTrendStats: ESTADISTICOS,
  scenarios: escenariosEscalonados(NIVELES, 30, 'recomendaciones'),
  thresholds: {
    'http_req_failed': ['rate<0.01'],
  },
};

export function setup() {
  if (!PREFERENCIA) {
    throw new Error(
      'Falta la variable PREFERENCIA. Crea una preferencia con ' +
        'POST /api/preferencias y pasa su id: -e PREFERENCIA=3005',
    );
  }
  return { preferencia: PREFERENCIA };
}

export function recomendaciones(datos) {
  const respuesta = publicar('/api/recomendaciones', {
    preferencia_id: datos.preferencia,
    limite: 20,
  });

  medir(respuesta);

  check(respuesta, {
    'responde 200': (r) => r.status === 200,
    'devuelve recomendaciones': (r) => {
      try {
        return r.json('recomendaciones').length > 0;
      } catch {
        return false;
      }
    },
    'cada recomendacion dice por que': (r) => {
      try {
        // Es la promesa que cierra la brecha 2: si esto deja de venir, la
        // recomendación se vuelve una lista sin justificación.
        return r.json('recomendaciones')[0].puntaje_afinidad !== undefined;
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
