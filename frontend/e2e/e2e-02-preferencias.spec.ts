/**
 * E2E-02 · HU-03 — «Como visitante quiero declarar mis preferencias de viaje
 * sin tener que crear una cuenta».
 *
 * Cierra la **brecha 3**: las preferencias del visitante no se registran en
 * ninguna parte del proceso.
 *
 * Es la prueba que sostiene el [ADR-003](../../docs/adr/ADR-003-la-aplicacion-funciona-sin-cuenta.md):
 * el recorrido entero, los seis pasos, **sin iniciar sesión**. Si algún día
 * alguien añade un «necesitas cuenta para esto», esta prueba se cae.
 *
 * El contexto de Playwright arranca sin cookies ni `localStorage`, así que no
 * hay forma de que arrastre una sesión de otra prueba.
 */

import { expect, test } from '@playwright/test';

import { dentroDe } from './ayudas';

test.describe('E2E-02 · Los seis pasos sin iniciar sesión', () => {
  test('completa el asistente y devuelve un identificador de preferencia', async ({ page }) => {
    await page.goto('/preferencias');

    // Se comprueba explícitamente que NO hay sesión: el encabezado ofrece
    // iniciarla, no cerrarla.
    await expect(page.getByRole('link', { name: /Iniciar sesión/i })).toBeVisible();

    // --- Paso 1 · ¿Cuándo viajas? ------------------------------------------
    await expect(page.getByRole('heading', { name: /¿Cuándo viajas\?/ })).toBeVisible();
    await page.getByLabel('Fecha de inicio').fill(dentroDe(10));
    await page.getByLabel('Fecha de fin').fill(dentroDe(12));
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // --- Paso 2 · ¿Desde dónde sales? --------------------------------------
    await expect(page.getByRole('heading', { name: /¿Desde dónde sales\?/ })).toBeVisible();
    await page.getByLabel('Distrito de origen').selectOption('HUANCAYO');
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // --- Paso 3 · ¿Cuál es tu presupuesto? ---------------------------------
    await expect(page.getByRole('heading', { name: /¿Cuál es tu presupuesto\?/ })).toBeVisible();
    await page.getByLabel('Presupuesto en soles').fill('450');
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // --- Paso 4 · ¿Qué te interesa? ----------------------------------------
    await expect(page.getByRole('heading', { name: /¿Qué te interesa\?/ })).toBeVisible();
    await page.getByRole('button', { name: 'Arqueología' }).click();
    await page.getByRole('button', { name: 'Naturaleza' }).click();
    await page.getByRole('button', { name: 'Gastronomía' }).click();
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // --- Paso 5 · ¿Cómo prefieres moverte? ---------------------------------
    await expect(page.getByRole('heading', { name: /¿Cómo prefieres moverte\?/ })).toBeVisible();
    await page.getByRole('button', { name: /Transporte público/ }).click();
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // --- Paso 6 · ¿A qué ritmo? --------------------------------------------
    await expect(page.getByRole('heading', { name: /¿A qué ritmo\?/ })).toBeVisible();
    await page.getByRole('button', { name: /Moderado/ }).click();

    // Y el aviso que resume la promesa del ADR-003.
    await expect(page.getByText(/No necesitas crear una cuenta/)).toBeVisible();

    await page.getByRole('button', { name: 'Guardar mis preferencias' }).click();

    // --- El resultado: un identificador, sin haber creado cuenta -----------
    await page.waitForURL(/\/preferencias\/\d+$/, { timeout: 30_000 });

    const id = /\/preferencias\/(\d+)$/.exec(page.url())?.[1];
    expect(id, 'la URL final no trae el identificador de la preferencia').toBeTruthy();
    expect(Number(id)).toBeGreaterThan(0);

    // Sigue sin haber sesión al terminar: el identificador es lo único que
    // permite volver a la preferencia.
    await expect(page.getByRole('link', { name: /Iniciar sesión/i })).toBeVisible();
  });

  test('el asistente no deja avanzar sin completar el paso', async ({ page }) => {
    await page.goto('/preferencias');

    const siguiente = page.getByRole('button', { name: 'Siguiente' });

    // El paso 1 NO bloquea: el asistente llega con las fechas ya puestas
    // (hoy + 7 y hoy + 9), el presupuesto en 200, movilidad «combinado» y
    // ritmo «moderado». Solo el distrito y los intereses nacen vacíos.
    //
    // Las dos primeras versiones de esta prueba no lo sabían: una esperaba un
    // mensaje de error tras pulsar, y otra que el botón naciera inerte. Las
    // dos fallaron por el mismo motivo, que era un supuesto mío sobre la
    // interfaz.
    await expect(siguiente).toBeEnabled();
    await siguiente.click();

    // El paso 2 sí bloquea: sin distrito de origen no se puede continuar.
    await expect(page.getByRole('heading', { name: /¿Desde dónde sales\?/ })).toBeVisible();
    await expect(siguiente).toBeDisabled();
    await expect(page.getByRole('alert')).toHaveText('Elige el distrito desde el que sales.');

    // Al elegirlo, el error desaparece y el botón se habilita.
    await page.getByLabel('Distrito de origen').selectOption('HUANCAYO');
    await expect(page.getByRole('alert')).toBeHidden();
    await expect(siguiente).toBeEnabled();
  });
});
