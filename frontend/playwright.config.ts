/**
 * Configuración de las pruebas de extremo a extremo (E2E).
 *
 * ## Qué nivel de la pirámide cubre esto
 *
 * El cuarto: **UI / E2E**. Los otros tres ya existían —unitarias con pytest y
 * vitest, integración de API con los `test_rutas_*.py`, y carga con k6—, pero
 * ninguno recorre la aplicación como la recorre una persona.
 *
 * ## Por qué viven en `frontend/` y no en `pruebas/e2e/`
 *
 * Por resolución de módulos de Node: `@playwright/test` está en
 * `frontend/node_modules`, y Node busca `node_modules` subiendo desde el
 * archivo que hace el `import`. Un archivo en `pruebas/e2e/` no lo
 * encontraría, porque la raíz del repositorio no tiene `node_modules`. Se
 * probó y falla con `ERR_MODULE_NOT_FOUND`.
 *
 * ## Qué tiene que estar levantado
 *
 * Estas pruebas **no levantan nada**: corren contra el sistema real, que es el
 * sentido de una prueba de extremo a extremo. Hace falta:
 *
 *   - PostgreSQL con PostGIS   `docker compose up -d`
 *   - el backend en :8000      `cd backend && .venv/Scripts/python.exe -m uvicorn app.main:aplicacion --port 8000`
 *   - el frontend en :5173     `cd frontend && npm run dev`
 *
 * Y se ejecutan con:
 *
 *   cd frontend && npm run e2e
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',

  // En serie y con un solo trabajador: el endpoint del itinerario satura un
  // uvicorn de un trabajador (medido: 0,23 peticiones por segundo). Lanzar
  // pruebas en paralelo mediría la cola, no la aplicación, y las volvería
  // inestables por motivos que no son defectos.
  fullyParallel: false,
  workers: 1,

  // Sin reintentos: una prueba que solo pasa al segundo intento es una prueba
  // inestable, y eso hay que verlo, no esconderlo.
  retries: 0,

  // Armar el itinerario tarda entre 5 y 17 segundos según la carga. 90 s deja
  // margen sin llegar a ocultar un cuelgue.
  timeout: 90_000,
  expect: { timeout: 20_000 },

  reporter: [['list'], ['json', { outputFile: 'e2e-resultados.json' }]],

  use: {
    baseURL: 'http://localhost:5173',
    locale: 'es-PE',
    // Playwright no trae navegador descargado en este proyecto: se usa el Edge
    // del sistema, igual que en el guion de capturas.
    channel: 'msedge',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    actionTimeout: 20_000,
  },

  projects: [
    {
      name: 'escritorio',
      use: { ...devices['Desktop Chrome'], channel: 'msedge' },
    },
  ],
});
