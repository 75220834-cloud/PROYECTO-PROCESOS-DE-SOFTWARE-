/**
 * Piezas compartidas por los tres escenarios de carga.
 *
 * ## Por qué los niveles de carga son escenarios separados y no una rampa
 *
 * Una rampa continua (`ramping-vus`) mezcla en un solo percentil las mediciones
 * de 5 usuarios y las de 30. Con eso se puede decir «el p95 fue X», pero NO se
 * puede responder a la pregunta que importa: **¿a partir de cuántos usuarios
 * empieza a degradar?**
 *
 * Por eso cada nivel es un escenario `constant-vus` que arranca cuando el
 * anterior ya terminó, y cada uno escribe en su propia métrica. Así el resumen
 * final imprime una fila por nivel y la degradación se lee directamente.
 *
 * ## Dónde corre esto
 *
 * Contra `http://host.docker.internal:8000`, que es cómo un contenedor de Docker
 * Desktop alcanza un puerto de la máquina anfitriona. El backend NO corre en
 * Docker: corre como proceso de Python en la laptop.
 */

import http from 'k6/http';
import { Trend, Rate } from 'k6/metrics';
import exec from 'k6/execution';

/** El backend, visto desde dentro del contenedor de k6. */
export const BASE = __ENV.BASE || 'http://host.docker.internal:8000';

/** La preferencia que usan los escenarios (b) y (c). Se pasa por variable. */
export const PREFERENCIA = Number(__ENV.PREFERENCIA || 0);

/** Estadísticos del resumen. Sin esto k6 no imprime p50 ni p99. */
export const ESTADISTICOS = ['min', 'med', 'avg', 'p(90)', 'p(95)', 'p(99)', 'max'];

/**
 * Crea una métrica de latencia y una de error por cada nivel de carga.
 *
 * Devuelve una función `medir(respuesta)` que escribe en la métrica del nivel
 * que corresponda al escenario en curso.
 */
export function medidorPorNivel(niveles) {
  const latencias = {};
  const errores = {};

  for (const n of niveles) {
    const etiqueta = String(n).padStart(2, '0');
    latencias[etiqueta] = new Trend(`latencia_${etiqueta}vu`, true);
    errores[etiqueta] = new Rate(`errores_${etiqueta}vu`);
  }

  return function medir(respuesta) {
    // `exec.scenario.name` vale «nivel_05», «nivel_15»… El nivel es el sufijo.
    const etiqueta = exec.scenario.name.split('_')[1];

    if (latencias[etiqueta]) {
      latencias[etiqueta].add(respuesta.timings.duration);
      errores[etiqueta].add(respuesta.status !== 200);
    }
  };
}

/**
 * Construye los escenarios: un `constant-vus` por nivel, uno detrás de otro.
 *
 * Se deja un hueco de 5 s entre niveles para que la cola de peticiones del
 * nivel anterior se vacíe. Sin ese hueco, las primeras mediciones de un nivel
 * llevarían dentro la congestión del anterior.
 */
export function escenariosEscalonados(niveles, segundosPorNivel, funcion) {
  const escenarios = {};
  let arranque = 0;

  for (const n of niveles) {
    const etiqueta = String(n).padStart(2, '0');
    escenarios[`nivel_${etiqueta}`] = {
      executor: 'constant-vus',
      vus: n,
      duration: `${segundosPorNivel}s`,
      startTime: `${arranque}s`,
      exec: funcion,
      tags: { nivel: etiqueta },
      gracefulStop: '30s',
    };
    arranque += segundosPorNivel + 5;
  }

  return escenarios;
}

/** GET con la cabecera de idioma que manda la interfaz de verdad. */
export function obtener(ruta) {
  return http.get(`${BASE}${ruta}`, {
    headers: { 'Accept-Language': 'es' },
    tags: { ruta },
  });
}

/** POST de JSON, como lo manda la interfaz. */
export function publicar(ruta, cuerpo) {
  return http.post(`${BASE}${ruta}`, JSON.stringify(cuerpo), {
    headers: { 'Content-Type': 'application/json', 'Accept-Language': 'es' },
    tags: { ruta },
  });
}
