/**
 * E2E-04 · HU-05 y HU-06 — «Como visitante quiero un itinerario del día con
 * horas y traslados, y quiero saber qué partes son estimaciones».
 *
 * Cierra la **brecha 4**: el proceso no incorpora el tiempo ni el costo de
 * desplazamiento.
 *
 * Es la prueba más importante de las cuatro, porque comprueba el eje entero del
 * proyecto: que el itinerario **dice lo que estima**. Un itinerario con horas
 * bonitas y sin avisos sería exactamente la aplicación que este proyecto dice
 * no querer ser.
 *
 * El aviso que se comprueba no es decorativo: sale del ADR-006 (dos modos de
 * cálculo de distancia, y el sistema declara cuál usó) y viaja como
 * `{codigo, parametros}` según el ADR-013.
 */

import { expect, test } from '@playwright/test';

import { crearPreferencia } from './ayudas';

test.describe('E2E-04 · El itinerario del día', () => {
  test('arma el itinerario con paradas ordenadas, horas y totales', async ({ page, request }) => {
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/itinerario`);

    // El cálculo encadena TF-IDF, caminos mínimos sobre el grafo de OSM,
    // Tobler y OR-Tools. Medido: entre 5 y 17 s según la carga.
    const plan = page.getByRole('heading', { name: 'El plan del día' });
    await expect(plan).toBeVisible({ timeout: 75_000 });

    // --- Las paradas, en orden y con horas --------------------------------
    // «Parada N de M: nombre» es el `aria-label` de cada parada, no texto
    // visible: se busca por etiqueta accesible. La primera versión de esta
    // prueba usaba getByText y no encontraba nada.
    const paradas = page.getByLabel(/Parada \d+ de \d+:/);
    await expect(paradas.first()).toBeVisible();

    const cuantas = await paradas.count();
    expect(cuantas, 'el itinerario no trajo ninguna parada').toBeGreaterThan(0);

    // Las paradas están numeradas de forma creciente y sin saltos.
    for (let i = 0; i < cuantas; i += 1) {
      const etiqueta = (await paradas.nth(i).getAttribute('aria-label')) ?? '';
      const numero = Number(/Parada (\d+) de/.exec(etiqueta)?.[1] ?? '0');
      expect(numero, `la parada ${i} no está en la posición ${i + 1}`).toBe(i + 1);
    }

    // Y hay horas de llegada y de salida, que se pintan como «HH:MM – HH:MM».
    await expect(page.getByText(/\d{2}:\d{2}\s*[–-]\s*\d{2}:\d{2}/).first()).toBeVisible();

    // --- Los totales del día ----------------------------------------------
    await expect(page.getByText('DURACIÓN')).toBeVisible();
    await expect(page.getByText('TRASLADOS')).toBeVisible();
    await expect(page.getByText('RECORRIDO')).toBeVisible();
    await expect(page.getByText('ESFUERZO')).toBeVisible();

    // El costo SIEMPRE lleva «aprox.» y un rango, nunca un número solo: no
    // existe fuente publicada de tarifas del valle (ADR-008).
    //
    // Se usa `.first()` porque hay varios: el total del día y el de cada
    // traslado. Que salgan cinco es la señal correcta, no un problema.
    const precios = page.getByText(/aprox\.\s*S\/\s*[\d.]+\s*[–-]\s*[\d.]+/);
    await expect(precios.first()).toBeVisible();
    expect(await precios.count(), 'ningún precio lleva rango con «aprox.»').toBeGreaterThan(0);
  });

  test('hay al menos un aviso visible, y marca algo como estimado o no garantizado', async ({
    page,
    request,
  }) => {
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/itinerario`);

    await expect(page.getByRole('heading', { name: 'El plan del día' })).toBeVisible({
      timeout: 75_000,
    });

    // El bloque de avisos del día.
    const avisos = page.getByText('Antes de salir, ten en cuenta');
    await expect(avisos).toBeVisible();

    const bloque = avisos.locator('..');
    const texto = (await bloque.textContent()) ?? '';

    // Tiene que haber al menos un aviso con contenido, no el título solo.
    const contenido = texto.replace('Antes de salir, ten en cuenta', '').trim();
    expect(contenido.length, 'el bloque de avisos está vacío').toBeGreaterThan(20);

    // Y al menos uno tiene que marcar un dato como estimación o como no
    // garantizado. Es la promesa del proyecto: decir cuándo no se sabe.
    expect(
      contenido,
      `ningún aviso marca una estimación. Avisos mostrados: ${contenido.slice(0, 200)}`,
    ).toMatch(
      /estimad|aproximad|no se conoce|no publica|no podemos garantizar|confirma|aclimat|línea recta/i,
    );
  });

  test('cada día del viaje trae un plan distinto, sin repetir lugares', async ({
    page,
    request,
  }) => {
    // Es la prueba del defecto que se reportó mirando la pantalla: el Día 2 y
    // el Día 3 traían **el mismo plan** que el Día 1, con los mismos lugares y
    // las mismas horas. Pasaba porque cada pestaña pedía su día por separado y
    // el servidor no podía saber qué había en los otros.
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/itinerario`);

    await expect(page.getByRole('heading', { name: 'El plan del día' })).toBeVisible({
      timeout: 120_000,
    });

    const nombresDelDiaVisible = async () => {
      const etiquetas = await page.getByLabel(/Parada \d+ de \d+:/).all();
      return Promise.all(
        etiquetas.map(async (parada) => (await parada.getAttribute('aria-label')) ?? ''),
      );
    };

    const dia1 = await nombresDelDiaVisible();
    expect(dia1.length, 'el día 1 no trajo paradas').toBeGreaterThan(0);

    // Cambiar de día no pide nada al servidor: los días ya vinieron juntos.
    await page.getByRole('button', { name: 'Día 2' }).click();

    // Se espera a que la lista cambie de verdad antes de comparar, para no
    // comparar el día 1 consigo mismo por haber leído demasiado pronto.
    await expect
      .poll(async () => (await nombresDelDiaVisible()).join('|'), { timeout: 30_000 })
      .not.toBe(dia1.join('|'));

    const dia2 = await nombresDelDiaVisible();

    // Lo que de verdad importa: ningún lugar del día 1 reaparece en el día 2.
    const soloNombre = (etiqueta: string) => etiqueta.replace(/^Parada \d+ de \d+:\s*/, '');
    const delDia1 = new Set(dia1.map(soloNombre));
    const repetidos = dia2.map(soloNombre).filter((nombre) => delDia1.has(nombre));

    expect(repetidos, `el día 2 repite lugares del día 1: ${repetidos.join(', ')}`).toEqual([]);
  });

  test('el itinerario se dibuja en el mapa', async ({ page, request }) => {
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/itinerario`);

    await expect(page.getByRole('heading', { name: 'El plan del día' })).toBeVisible({
      timeout: 75_000,
    });

    const mapa = page.locator('.leaflet-container');
    await expect(mapa).toBeVisible();

    // Y tiene marcadores: un mapa vacío diría «Cuando haya paradas, aparecerán
    // aquí sobre el mapa», que es otro estado distinto.
    await expect(page.getByText('Cuando haya paradas, aparecerán aquí sobre el mapa.')).toBeHidden();
    await expect(mapa.locator('.leaflet-marker-icon').first()).toBeVisible();
  });
});
