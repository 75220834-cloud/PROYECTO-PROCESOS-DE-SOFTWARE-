# 19 — Matriz de registro de ejecución de pruebas

**Qué explica este archivo:** una fila por archivo de prueba, con su nivel en la
pirámide, cuántos casos tiene, si pasó, y si necesita PostgreSQL levantado.

**Los números no están contados a ojo sobre el código.** Salen de los informes
que producen las cuatro herramientas al ejecutarse:

| Herramienta | Informe | Cómo se genera |
|---|---|---|
| pytest | `informe-backend.xml` (JUnit) | `pytest --junitxml=informe-backend.xml` |
| pytest sin base | `informe-backend-sin-bd.xml` | lo mismo con `POSTGRES_HOST=no.existe.invalid` |
| vitest | `informe-frontend.json` | `vitest run --reporter=json` |
| Playwright | `frontend/e2e-resultados.json` | reportero `json` en `playwright.config.ts` |
| k6 | salida en `pruebas/carga/RESULTADOS.md` | k6 no produce informe por archivo |

**Fecha de ejecución: 25 de septiembre de 2026.**

La columna «¿Necesita PostgreSQL?» se deduce comparando las dos ejecuciones de
pytest: si al quitar la base un caso se salta, ese caso la necesitaba.

---

## La matriz

| ID | Nivel | Archivo | Qué fija | N.º de casos | Resultado | ¿PostgreSQL? |
|---|---|---|---|---|---|---|
| U-01 | Unitaria | `pruebas/test_afinidad_y_afluencia.py` | TF-IDF y las 7 reglas de afluencia | 37 | PASA | No |
| U-02 | Unitaria | `pruebas/test_asistente.py` | Las 5 funciones del asistente, sin Ollama | 33 | PASA | Sí (todos) |
| U-03 | Unitaria | `pruebas/test_calendario.py` | Butcher: Semana Santa y Carnavales | 42 | PASA | No |
| U-04 | Unitaria | `pruebas/test_catalogo.py` | Importación, índices, deduplicación | 23 | PASA | Parcial (8 de 23) |
| U-05 | Unitaria | `pruebas/test_coordinacion.py` | Estados, permisos, cupo, registro | 45 | PASA | Sí (todos) |
| U-06 | Unitaria | `pruebas/test_costos.py` | La fórmula de tarifas y su rango | 24 | PASA | No |
| U-07 | Unitaria | `pruebas/test_fichas_y_temporada.py` | Lector de fichas, horarios, fechas de fiesta | 30 | PASA | No |
| U-08 | **Integración-API** | `pruebas/test_rutas_autenticacion.py` | Registro, acceso, errores indistinguibles | 17 | PASA | Sí (todos) |
| U-09 | **Integración-API** | `pruebas/test_rutas_catalogo.py` | Filtros, paginación, GeoJSON, 404 | 17 | PASA | Sí (todos) |
| U-10 | **Integración-API** | `pruebas/test_rutas_itinerarios.py` | Armar, reordenar, guardar idempotente, avisos | 33 | PASA (1 saltada) | Sí (todos) |
| U-11 | **Integración-API** | `pruebas/test_rutas_preferencias.py` | Los seis pasos, sin cuenta, reclamar | 28 | PASA | Sí (todos) |
| U-12 | **Integración-API** | `pruebas/test_rutas_recomendaciones.py` | Filtros duros, descartes con motivo | 25 | PASA | Sí (todos) |
| U-13 | Unitaria | `pruebas/test_ruteo.py` | OR-Tools, presupuesto, recorrido abierto | 33 | PASA | No |
| U-14 | **Integración-API** | `pruebas/test_salud.py` | Los tres componentes se reportan | 4 | PASA | No |
| U-15 | Unitaria | `pruebas/test_seguridad.py` | Hash argon2id, JWT, expiración | 15 | PASA | No |
| U-16 | Unitaria | `pruebas/test_sentimiento.py` | Las dos vías, negadores, temas, umbral 0,70 | 51 | PASA | No |
| U-17 | Unitaria | `pruebas/test_tiempo_recorrido.py` | Tobler, esfuerzo, aviso de altitud | 30 | PASA | No |
| U-18 | Unitaria | `pruebas/test_validacion_catalogo.py` | Reglas de validación e indicador 1 | 20 | PASA | Parcial (5 de 20) |
| U-19 | Unitaria | `pruebas/test_valoraciones.py` | Valorar, tablero, los 6 indicadores | 43 | PASA | Sí (todos) |
| U-20 | Unitaria | `frontend/…/InterruptorTema.prueba.tsx` | Que el tema cambie y persista | 4 | PASA | No |
| U-21 | Unitaria | `frontend/…/LineaDeTiempo.prueba.tsx` | Traslados, y no `<li>` dentro de `<li>` | 18 | PASA | No |
| U-22 | Unitaria | `frontend/…/PanelConversacion.prueba.tsx` | Auditabilidad, sin Ollama, dos idiomas | 19 | PASA | No |
| U-23 | Unitaria | `frontend/…/SelectorIdioma.prueba.tsx` | Que el idioma cambie y persista | 2 | PASA | No |
| U-24 | Unitaria | `frontend/…/TarjetaRecomendacion.prueba.tsx` | Que se muestre **por qué** se recomienda | 9 | PASA | No |
| U-25 | Unitaria | `frontend/…/TarjetaRecurso.prueba.tsx` | El sello de validado o incompleto | 5 | PASA | No |
| U-26 | Unitaria | `frontend/…/TarjetaServicio.prueba.tsx` | Que la capacidad sea verificable (brecha 5) | 12 | PASA | No |
| U-27 | Unitaria | `frontend/…/TarjetaSolicitud.prueba.tsx` | Que el historial se vea (brecha 6) | 17 | PASA | No |
| U-28 | Unitaria | `frontend/…/TotalesDelDia.prueba.tsx` | Que el costo lleve «aprox.» | 8 | PASA | No |
| U-29 | Unitaria | `frontend/…/AsistentePreferencias.prueba.tsx` | Los seis pasos sin iniciar sesión | 9 | PASA | No |
| U-30 | Unitaria | `frontend/…/avisos.prueba.ts` | Que todo código tenga traducción en ambos idiomas | 19 | PASA | No |
| U-31 | Unitaria | `frontend/…/formato.prueba.ts` | Formato de nombres y categorías | 9 | PASA | No |
| U-32 | Unitaria | `frontend/…/formatoFase2.prueba.ts` | Formato de fechas y presupuesto | 7 | PASA | No |
| U-33 | Unitaria | `frontend/…/formatoFase4.prueba.ts` | Formato de distancias, tiempos y costos | 10 | PASA | No |
| C-34 | **Carga** | `pruebas/carga/01-catalogo.js` | `GET /api/recursos` a 5, 15 y 30 usuarios | 2 942 peticiones | PASA (0 errores) | Sí |
| C-35 | **Carga** | `pruebas/carga/02-recomendaciones.js` | `POST /api/recomendaciones` a 5, 10 y 20 | 102 peticiones | PASA (0 errores) | Sí |
| C-36 | **Carga** | `pruebas/carga/03-itinerario.js` | `POST /api/itinerarios` a 1, 2 y 4 | 66 peticiones | PASA (0 errores) | Sí |
| E-37 | **E2E** | `frontend/e2e/e2e-01-catalogo.spec.ts` | HU-01: catálogo filtrado y sello de validación | 5 | PASA | Sí |
| E-38 | **E2E** | `frontend/e2e/e2e-02-preferencias.spec.ts` | HU-03: los seis pasos sin cuenta | 2 | PASA | Sí |
| E-39 | **E2E** | `frontend/e2e/e2e-03-recomendaciones.spec.ts` | HU-04: el porqué y los descartados | 2 | PASA | Sí |
| E-40 | **E2E** | `frontend/e2e/e2e-04-itinerario.spec.ts` | HU-05/06: paradas, totales y aviso de estimación | 3 | PASA | Sí |

---

## Resumen por nivel de la pirámide

Esto es lo que hay que dibujar:

| Nivel | Casos | Archivos | Herramienta |
|---|---|---|---|
| **Unitaria** | **574** | 28 | pytest (426) + vitest (148) |
| **Integración-API** | **124** | 6 | pytest con `TestClient` de FastAPI |
| **Carga** | **3 110 peticiones** | 3 | k6 v2.3.0 en Docker |
| **E2E / UI** | **12** | 4 | Playwright con Edge |

```
                    ╱╲
                   ╱  ╲      E2E  ·  12 casos  ·  4 archivos
                  ╱────╲
                 ╱      ╲    CARGA · 3 110 peticiones · 3 escenarios
                ╱────────╲
               ╱          ╲  INTEGRACIÓN-API · 124 casos · 6 archivos
              ╱────────────╲
             ╱              ╲ UNITARIAS · 574 casos · 28 archivos
            ╱────────────────╲
```

La forma es la correcta: muchas unitarias abajo, pocas E2E arriba.

### Dos cifras que conviene no confundir

- **698 casos de prueba** en total entre unitarias y de integración (574 + 124).
  De ellos, **550 son del backend** y **148 del frontend**.
- **3 110 peticiones** de carga no son 3 110 «casos»: son peticiones HTTP
  repetidas contra tres endpoints, con **6 556 comprobaciones de contenido**.
  Ponerlas en el mismo eje que un caso unitario exageraría ese nivel.

### Reparto de la dependencia de PostgreSQL

| | Casos |
|---|---|
| No necesitan PostgreSQL | **296** |
| Sí lo necesitan | **254** |
| **Total backend** | **550** |

Medido ejecutando la suite con la configuración apuntando a un host
inexistente: `296 passed, 254 skipped`.

---

## Cómo regenerar esta matriz

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q --junitxml=../informe-backend.xml
```

```bash
cd backend && POSTGRES_HOST=no.existe.invalid .venv/Scripts/python.exe -m pytest -q -o addopts="" --junitxml=../informe-backend-sin-bd.xml
```

```bash
cd frontend && npx vitest run --reporter=json --outputFile=../informe-frontend.json
```

```bash
cd frontend && npm run e2e
```

Los tres informes quedan ignorados por git: son artefactos de una ejecución,
no código.

---

## Relacionado

- [12 — Pruebas y calidad](12-pruebas-y-calidad.md)
- [20 — Registro de defectos](20-registro-de-defectos.md)
- [`pruebas/carga/RESULTADOS.md`](../../pruebas/carga/RESULTADOS.md)
