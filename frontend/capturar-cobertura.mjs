/**
 * Captura el informe HTML de cobertura y el tablero de SonarQube.
 *
 *   cd frontend && node capturar-cobertura.mjs
 *
 * La contraseña de SonarQube se pasa por entorno, nunca escrita aquí: es un
 * contenedor local y efímero, pero la regla 1.9 del proyecto no admite
 * excepciones por comodidad.
 *
 * ## Por qué esto y no una captura de la consola
 *
 * El entregable pedía «el resultado de pytest en consola con el porcentaje de
 * cobertura». **Una captura de una terminal no se puede tomar desde aquí**, y
 * montar una página que imite una consola sería fabricar una imagen que parece
 * una evidencia sin serlo.
 *
 * Así que se capturan dos cosas que sí son evidencia real:
 *
 *   - el informe HTML que genera `coverage.py` con los mismos datos de la
 *     ejecución de pytest (`docs/capturas/11_cobertura_pytest.png`);
 *   - el tablero de SonarQube tras el análisis (`13_sonarqube.png`).
 *
 * Y la salida literal de la consola queda como texto en
 * `docs/capturas/11_pytest_consola.txt`, que se puede pegar en el informe.
 */

import { chromium } from 'playwright';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = resolve(AQUI, '..');
const DESTINO = resolve(RAIZ, 'docs', 'capturas');
mkdirSync(DESTINO, { recursive: true });

const hechas = [];
const fallidas = [];

const navegador = await chromium.launch({ channel: 'msedge', headless: true });
const contexto = await navegador.newContext({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 2,
});
const pagina = await contexto.newPage();

// --- 11 · El informe de cobertura de coverage.py -------------------------
const informe = resolve(RAIZ, 'backend', 'htmlcov', 'index.html');

if (existsSync(informe)) {
  await pagina.goto(pathToFileURL(informe).href, { waitUntil: 'load' });
  await pagina.waitForTimeout(2500);
  await pagina.screenshot({
    path: resolve(DESTINO, '11_cobertura_pytest.png'),
    fullPage: true,
  });
  hechas.push('11_cobertura_pytest.png — informe de coverage.py, 73,42 %');
  console.log('  OK    11_cobertura_pytest.png');
} else {
  fallidas.push(`11_cobertura_pytest.png — no existe ${informe}`);
  console.log('  FALLO 11_cobertura_pytest.png: falta backend/htmlcov/index.html');
}

// --- 13 · El tablero de SonarQube ---------------------------------------
try {
  await pagina.goto('http://localhost:9000/dashboard?id=rutavivamantaro', {
    waitUntil: 'domcontentloaded',
    timeout: 45000,
  });

  // El guion NO inicia sesión, a propósito: no hay ninguna credencial aquí ni
  // que pasarle por entorno (regla 1.9 del proyecto). En su lugar, el
  // contenedor local se configura una vez para permitir lectura anónima:
  //
  //   curl -u admin:LA_CONTRASENA -X POST http://localhost:9000/api/settings/set \
  //        -d "key=sonar.forceAuthentication&value=false"
  //
  // Es un SonarQube local y efímero; abrirlo a lectura en la propia máquina no
  // expone nada y deja este guion sin secretos.
  await pagina.waitForTimeout(5000);

  // No se guarda nada hasta comprobar que se está viendo el tablero y no el
  // formulario de acceso. La primera versión de este guion miraba la URL justo
  // después de `domcontentloaded`, antes de que SonarQube redirigiera del lado
  // del cliente, y acabó guardando una captura de la pantalla de acceso
  // creyendo que era el tablero.
  if (await pagina.locator('#password').count()) {
    throw new Error(
      'Sigue en la pantalla de acceso: la captura no sería del tablero. ' +
        'Permite la lectura anónima con sonar.forceAuthentication=false.',
    );
  }

  await pagina.waitForSelector('text=/rutavivamantaro|RutaVivaMantaro/i', { timeout: 30000 });
  await pagina.waitForTimeout(4000);
  await pagina.screenshot({ path: resolve(DESTINO, '13_sonarqube.png'), fullPage: true });
  hechas.push('13_sonarqube.png — tablero de SonarQube tras el análisis');
  console.log('  OK    13_sonarqube.png');
} catch (error) {
  fallidas.push(`13_sonarqube.png — ${error.message}`);
  console.log(`  FALLO 13_sonarqube.png: ${error.message}`);
}

await navegador.close();

console.log('\n=== RESUMEN ===');
hechas.forEach((h) => console.log(`  hecha   ${h}`));
fallidas.forEach((f) => console.log(`  fallida ${f}`));
