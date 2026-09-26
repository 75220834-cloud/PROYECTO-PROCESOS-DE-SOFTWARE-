/**
 * Toma las capturas de pantalla del entregable de la Semana 6.
 *
 *   cd frontend && node capturar-pantallas.mjs
 *
 * Usa Playwright con el Microsoft Edge del sistema, para no descargar un
 * navegador completo. Escribe PNG reales en `docs/capturas/`.
 *
 * Resolución: 1600x1000 con `deviceScaleFactor: 2`, así que cada PNG sale a
 * 3200x2000 píxeles efectivos. Las capturas de página completa salen más altas.
 *
 * Requiere levantados: backend en :8000, frontend en :5173, PostGIS y la
 * preferencia cuyo id se pasa en PREFERENCIA.
 */

import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = dirname(fileURLToPath(import.meta.url));
const DESTINO = resolve(AQUI, '..', 'docs', 'capturas');
const APP = 'http://localhost:5173';
const API = 'http://localhost:8000';
const PREFERENCIA = process.env.PREFERENCIA || '3005';

mkdirSync(DESTINO, { recursive: true });

const hechas = [];
const fallidas = [];

async function capturar(pagina, nombre, descripcion, { completa = false } = {}) {
  try {
    await pagina.screenshot({
      path: resolve(DESTINO, nombre),
      fullPage: completa,
    });
    hechas.push(`${nombre} — ${descripcion}`);
    console.log(`  OK    ${nombre}`);
  } catch (error) {
    fallidas.push(`${nombre} — ${descripcion} — ${error.message}`);
    console.log(`  FALLO ${nombre}: ${error.message}`);
  }
}

/** Espera a que la página deje de cargar y a que el contenido real aparezca. */
async function ir(pagina, ruta, selectorEsperado, espera = 2500) {
  await pagina.goto(`${APP}${ruta}`, { waitUntil: 'networkidle', timeout: 60000 });
  if (selectorEsperado) {
    await pagina.waitForSelector(selectorEsperado, { timeout: 60000 }).catch(() => {});
  }
  await pagina.waitForTimeout(espera);
}

const navegador = await chromium.launch({ channel: 'msedge', headless: true });

const contexto = await navegador.newContext({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 2,
  locale: 'es-PE',
});

// El idioma se persiste en localStorage, así que se fija antes de cargar nada.
await contexto.addInitScript(() => {
  try {
    window.localStorage.setItem('rutaviva.idioma', 'es');
  } catch {
    /* modo privado: da igual, el idioma por defecto ya es español */
  }
});

const pagina = await contexto.newPage();

// --- 01 · Catálogo con recursos y el mapa visible -------------------------
await ir(pagina, '/explorar', 'text=/295|recursos/i', 4000);
await capturar(pagina, '01_catalogo.png', 'Catálogo con los 295 recursos y el mapa');

// --- 02 · Filtros aplicados ----------------------------------------------
// Los filtros viven en la URL, así que se aplican navegando: se ve el filtro
// activo en los controles y el total recalculado.
await ir(pagina, '/explorar?provincia=CONCEPCION&solo_validados=true', null, 4000);
await capturar(pagina, '02_filtros.png', 'Catálogo filtrado por Concepción y solo validados');

// --- 03 · Ficha de un recurso --------------------------------------------
await ir(pagina, '/recursos/209', 'h1', 3000);
await capturar(pagina, '03_ficha_recurso.png', 'Ficha con descripción del MINCETUR', {
  completa: true,
});

// --- 04 · El asistente de preferencias, dos pasos ------------------------
await ir(pagina, '/preferencias', null, 2500);
await capturar(pagina, '04a_preferencias_paso1.png', 'Asistente de preferencias, primer paso');

// Avanza pulsando el botón de siguiente, sea cual sea su texto exacto.
for (const texto of ['Siguiente', 'Continuar', 'siguiente']) {
  const boton = pagina.getByRole('button', { name: new RegExp(texto, 'i') });
  if (await boton.count()) {
    await boton.first().click().catch(() => {});
    break;
  }
}
await pagina.waitForTimeout(2000);
await capturar(pagina, '04b_preferencias_paso2.png', 'Asistente de preferencias, paso siguiente');

// --- 05 · Resultados con el porqué de cada recomendación -----------------
await ir(pagina, `/preferencias/${PREFERENCIA}/resultados`, null, 8000);
await capturar(pagina, '05_recomendaciones.png', 'Recomendaciones con su explicación', {
  completa: true,
});

// --- 06 · Itinerario con línea de tiempo y totales -----------------------
// Este cálculo tarda varios segundos: se espera de más a propósito.
await ir(pagina, `/preferencias/${PREFERENCIA}/itinerario`, null, 20000);
await capturar(pagina, '06_itinerario.png', 'Itinerario con línea de tiempo y totales del día', {
  completa: true,
});

// --- 07 · El itinerario en el mapa --------------------------------------
// Se baja hasta el mapa del itinerario para que quede centrado en el encuadre.
const mapa = pagina.locator('.leaflet-container').first();
if (await mapa.count()) {
  await mapa.scrollIntoViewIfNeeded().catch(() => {});
  await pagina.waitForTimeout(4000);
  await capturar(pagina, '07_itinerario_mapa.png', 'El itinerario dibujado en el mapa');
} else {
  fallidas.push('07_itinerario_mapa.png — no se encontró ningún contenedor de Leaflet');
}

// --- 08 · Un aviso visible ----------------------------------------------
// Los avisos del itinerario viven arriba de la página; se vuelve al principio.
await pagina.evaluate(() => window.scrollTo(0, 0));
await pagina.waitForTimeout(1500);
await capturar(pagina, '08_avisos.png', 'Avisos del itinerario, traducidos desde su código');

// --- 09 · La interfaz en inglés -----------------------------------------
const contextoEn = await navegador.newContext({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 2,
  locale: 'en-US',
});
await contextoEn.addInitScript(() => {
  try {
    window.localStorage.setItem('rutaviva.idioma', 'en');
  } catch {
    /* da igual */
  }
});
const paginaEn = await contextoEn.newPage();
await paginaEn.goto(`${APP}/explorar`, { waitUntil: 'networkidle', timeout: 60000 });
await paginaEn.waitForTimeout(4000);
await capturar(paginaEn, '09_ingles.png', 'La interfaz en inglés, mismo catálogo');
await contextoEn.close();

// --- 10 · Documentación interactiva del API -----------------------------
await pagina.goto(`${API}/docs`, { waitUntil: 'networkidle', timeout: 60000 });
await pagina.waitForSelector('.opblock', { timeout: 60000 }).catch(() => {});
await pagina.waitForTimeout(3000);
await capturar(pagina, '10_api_docs.png', 'Swagger UI con los 43 endpoints', { completa: true });

await navegador.close();

console.log('\n=== RESUMEN ===');
console.log(`Hechas  (${hechas.length}):`);
hechas.forEach((h) => console.log(`  - ${h}`));
console.log(`Fallidas (${fallidas.length}):`);
fallidas.forEach((f) => console.log(`  - ${f}`));
console.log(`\nDestino: ${DESTINO}`);
