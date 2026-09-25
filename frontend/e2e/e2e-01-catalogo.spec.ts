/**
 * E2E-01 · HU-01 — «Como visitante quiero explorar el catálogo de la ruta
 * filtrado por provincia, y saber de cada recurso si su dato está validado».
 *
 * Cierra la **brecha 1**: no existe una fuente integrada, oficial y actualizada
 * de la oferta de la ruta.
 *
 * Qué comprueba que ningún otro nivel de la pirámide comprueba: que el filtro
 * de la URL, la consulta del backend, la lista y el mapa **dicen todos lo
 * mismo**. Las pruebas de API comprueban el endpoint; las de componente
 * comprueban la tarjeta; ninguna comprueba que al filtrar por Concepción no se
 * quede un marcador de Huancayo en el mapa.
 */

import { expect, test } from '@playwright/test';

const PROVINCIA = 'CONCEPCION';

/**
 * La comparación ignora las tildes a propósito, y eso es un hallazgo.
 *
 * `es.json` declara `provincias.concepcion = "Concepción"`, pero la tarjeta del
 * catálogo no usa ese mapeo: muestra `formatearNombrePropio(recurso.provincia)`,
 * que title-casea el dato crudo del MINCETUR y deja **«Concepcion» sin tilde**.
 * Así que la misma provincia se escribe de dos formas distintas según dónde se
 * mire.
 *
 * Esta prueba comprueba la invariante que importa —que solo salgan recursos de
 * esa provincia— y no la ortografía, para no fallar por un defecto que está
 * registrado aparte.
 */
function sinTildes(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

test.describe('E2E-01 · Catálogo filtrado por provincia', () => {
  test('el catálogo carga con los 295 recursos y el mapa visible', async ({ page }) => {
    await page.goto('/explorar');

    // El indicador del Incremento 1, que viene del backend.
    const total = page.getByText('Recursos en el catálogo').locator('..');
    await expect(total).toContainText('295');

    // El mapa existe y ha pintado sus teselas.
    const mapa = page.locator('.leaflet-container');
    await expect(mapa).toBeVisible();

    // Y dice cuántos puede dibujar, que no son los 295: 61 no tienen
    // coordenada en la fuente oficial y el sistema lo declara en vez de
    // inventarles una.
    await expect(page.getByText(/Se muestran \d+ recursos en el mapa/)).toBeVisible();
  });

  test('al filtrar por provincia, la lista solo trae recursos de esa provincia', async ({
    page,
  }) => {
    await page.goto('/explorar');

    await page.getByLabel('Provincia').selectOption(PROVINCIA);

    // El filtro viaja en la URL: es lo que permite compartir una búsqueda.
    await expect(page).toHaveURL(new RegExp(`provincia=${PROVINCIA}`));

    const listado = page.getByRole('region', { name: 'Listado de recursos' });
    const tarjetas = listado.getByRole('listitem');
    await expect(tarjetas.first()).toBeVisible();

    const cuantas = await tarjetas.count();
    expect(cuantas).toBeGreaterThan(0);

    // TODAS las tarjetas, no solo la primera.
    for (let i = 0; i < cuantas; i += 1) {
      const texto = sinTildes((await tarjetas.nth(i).textContent()) ?? '');
      expect(texto, `la tarjeta ${i} no es de ${PROVINCIA}`).toContain('Concepcion');
    }
  });

  test('el mapa también se filtra, y declara cuántos puede dibujar', async ({ page }) => {
    await page.goto('/explorar');
    const aviso = page.getByText(/Se muestran \d+ recursos en el mapa/);
    await expect(aviso).toBeVisible();

    const leerCantidad = async () => {
      const texto = (await aviso.textContent()) ?? '';
      return Number(/Se muestran (\d+) recursos/.exec(texto)?.[1] ?? '0');
    };

    const sinFiltro = await leerCantidad();

    await page.getByLabel('Provincia').selectOption(PROVINCIA);
    await expect(page).toHaveURL(new RegExp(`provincia=${PROVINCIA}`));

    // Se espera a que el número cambie: si el mapa no se refiltrara, este
    // `expect` fallaría por tiempo, que es justo lo que se quiere detectar.
    await expect
      .poll(leerCantidad, { message: 'el mapa no se refiltró al elegir provincia' })
      .toBeLessThan(sinFiltro);

    const conFiltro = await leerCantidad();
    expect(conFiltro).toBeGreaterThan(0);
  });

  test('cada recurso dice si está validado, o queda marcado como incompleto', async ({ page }) => {
    await page.goto('/explorar');
    await page.getByLabel('Provincia').selectOption(PROVINCIA);
    await expect(page).toHaveURL(new RegExp(`provincia=${PROVINCIA}`));

    const tarjetas = page.getByRole('region', { name: 'Listado de recursos' }).getByRole('listitem');
    await expect(tarjetas.first()).toBeVisible();

    const cuantas = await tarjetas.count();
    let validados = 0;
    let incompletos = 0;

    for (let i = 0; i < cuantas; i += 1) {
      const texto = (await tarjetas.nth(i).textContent()) ?? '';
      const esValidado = texto.includes('Validado');
      const esIncompleto = texto.includes('Incompleto');

      // El sello es obligatorio: una tarjeta sin sello dejaría al visitante
      // sin saber si el dato está comprobado. Es la promesa del Incremento 1.
      expect(
        esValidado || esIncompleto,
        `la tarjeta ${i} no lleva sello de validación: ${texto.slice(0, 80)}`,
      ).toBe(true);

      if (esValidado) validados += 1;
      if (esIncompleto) incompletos += 1;
    }

    expect(validados + incompletos).toBe(cuantas);
  });

  test('marcar «solo validados» reduce la lista y deja solo sellos verdes', async ({ page }) => {
    await page.goto(`/explorar?provincia=${PROVINCIA}`);

    const listado = page.getByRole('region', { name: 'Listado de recursos' });
    await expect(listado.getByRole('listitem').first()).toBeVisible();
    const antes = await listado.getByRole('listitem').count();

    // Se usa `click()` y se comprueba la URL, no `check()`. La casilla está
    // gobernada por el parámetro de la URL, así que su estado no cambia en el
    // mismo tic del clic y `check()` falla con «Clicking the checkbox did not
    // change its state». Lo que importa comprobar es el efecto, no el `checked`.
    await page.getByLabel(/Mostrar solo los recursos que pasaron la validación/).click();
    await expect(page).toHaveURL(/solo_validados=true/);

    await expect(listado.getByRole('listitem').first()).toBeVisible();
    const tarjetas = listado.getByRole('listitem');
    const despues = await tarjetas.count();

    expect(despues).toBeLessThanOrEqual(antes);

    for (let i = 0; i < despues; i += 1) {
      await expect(tarjetas.nth(i)).toContainText('Validado');
      await expect(tarjetas.nth(i)).not.toContainText('Incompleto');
    }
  });
});
