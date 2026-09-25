/**
 * E2E-03 · HU-04 — «Como visitante quiero que me recomienden lugares según lo
 * que declaré, y saber POR QUÉ me recomiendan cada uno».
 *
 * Cierra la **brecha 2**: la oferta no se ajusta al perfil del visitante.
 *
 * Lo que de verdad está en juego aquí no es que salga una lista: es que cada
 * recomendación **se pueda explicar**. Una lista sin justificación no cierra la
 * brecha 2, solo la disimula. Por eso esta prueba comprueba los términos que
 * pesaron y los intereses cubiertos, no solo que haya tarjetas.
 *
 * También comprueba la lista de **descartados con su motivo**, que es la otra
 * mitad de la honestidad: decir qué se dejó fuera y por qué.
 */

import { expect, test } from '@playwright/test';

import { crearPreferencia } from './ayudas';

test.describe('E2E-03 · Recomendaciones con su porqué', () => {
  test('cada recomendación muestra puntaje, términos que pesaron e intereses', async ({
    page,
    request,
  }) => {
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/resultados`);

    await expect(page.getByRole('heading', { name: 'Lo que te proponemos' })).toBeVisible();

    // El cálculo tarda: se espera a que desaparezca el mensaje de espera.
    await expect(page.getByText('Calculando tus recomendaciones…')).toBeHidden({ timeout: 60_000 });

    const tarjetas = page.getByRole('listitem').filter({ hasText: 'Pesaron:' });
    await expect(tarjetas.first()).toBeVisible({ timeout: 60_000 });

    const cuantas = await tarjetas.count();
    expect(cuantas, 'no salió ninguna recomendación').toBeGreaterThan(0);

    for (let i = 0; i < cuantas; i += 1) {
      const texto = (await tarjetas.nth(i).textContent()) ?? '';

      // 1. Los términos que pesaron: la descomposición del numerador del
      //    coseno, no una explicación inventada después (ADR-004).
      expect(texto, `la recomendación ${i} no dice qué términos pesaron`).toMatch(/Pesaron:\s*\S+/);

      // 2. Los intereses cubiertos.
      expect(texto, `la recomendación ${i} no dice por qué encaja`).toMatch(/Porque te interesa/);
    }

    // Y la respuesta declara con qué vía se generó: modelo o reglas. Es la
    // regla de oro hecha interfaz.
    await expect(
      page.getByText(/Calculado con (el modelo de afinidad|las reglas explícitas)/),
    ).toBeVisible();
  });

  test('existe la lista de descartados, con su motivo', async ({ page, request }) => {
    const preferencia = await crearPreferencia(request);
    await page.goto(`/preferencias/${preferencia}/resultados`);

    await expect(page.getByText('Calculando tus recomendaciones…')).toBeHidden({ timeout: 60_000 });

    const encabezado = page.getByText(/\d+ recursos descartados/);
    await expect(encabezado).toBeVisible({ timeout: 60_000 });

    // Se despliega la lista.
    await page.getByRole('button', { name: 'Ver' }).first().click();

    // Cada descarte trae su motivo redactado desde un código del backend
    // (ADR-013): sin coordenadas, fuera de alcance, sin validar…
    const motivos = page.getByText(
      /sin coordenada|fuera del alcance|no pasó la validación|no puede|no tiene/i,
    );
    await expect(motivos.first()).toBeVisible();
  });
});
