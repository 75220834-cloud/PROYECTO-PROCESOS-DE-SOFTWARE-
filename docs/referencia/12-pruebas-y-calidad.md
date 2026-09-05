# 12 — Pruebas y calidad

**Qué explica este archivo:** las 697 pruebas del proyecto, qué cubre cada
archivo, la filosofía que siguen y las herramientas de calidad que se ejecutan.

---

## Los números

| | Cantidad | Cobertura |
|---|---|---|
| **Backend** | 549 pasan, 1 saltada | **73 %** |
| **Frontend** | 148 pasan | — |
| **Total** | **697** | |

El mínimo que exige el proyecto es **60 % en el backend**, y desde el 4 de
septiembre de 2026 **se exige de verdad**: `pyproject.toml` lleva
`fail_under = 60` en la configuración de cobertura, así que `pytest` devuelve
error si el total baja de ahí.

> Antes solo se **medía**. El porcentaje salía por pantalla y pytest devolvía
> éxito aunque hubiera bajado al 20 %. La regla existía en la documentación y
> en ningún sitio más. Ver
> [la nota del 4 de septiembre](../decisiones/2026-09-04-que-se-automatizo-y-que-sigue-siendo-manual.md).

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
```

```bash
cd frontend && npm run probar
```

---

## La filosofía

### 1. Base de datos real, no simulada

Las pruebas que necesitan base usan **PostgreSQL con PostGIS de verdad**,
porque el proyecto se apoya en funciones geográficas —`ST_X`, `ST_Y`, índices
GIST— que ninguna base simulada implementa. Simularlas daría pruebas que pasan
mientras el código real falla.

A cambio, **cada prueba corre dentro de una transacción que se deshace al
terminar**, así que nunca alteran el catálogo real. Y si la base no está
levantada, esas pruebas **se saltan con un aviso claro** en vez de fallar.

### 2. Nada de red

Ninguna prueba descarga nada. Las del lector de fichas trabajan sobre **HTML
escrito a mano** que reproduce la forma real.

> Una prueba que descarga una página del Estado para comprobarse a sí misma es
> una prueba que falla el día que se cae ese servidor, y que además lo castiga
> cada vez que alguien ejecuta la suite.

### 3. Se afirma sobre datos, no sobre texto

Desde la Fase 7, las pruebas comprueban **códigos de aviso** y sus parámetros,
no frases. Ver [11](11-idiomas-y-avisos.md).

### 4. Cada fallo encontrado deja una prueba

No se arregla un fallo sin fijarlo. Ver [15](15-historial-de-fallos.md): cada
entrada tiene su prueba de regresión.

---

## Backend — los 19 archivos

| Archivo | Qué fija | Necesita BD |
|---|---|---|
| `test_salud.py` | Los tres componentes se reportan | sí |
| `test_catalogo.py` | Importación, índices, deduplicación | sí |
| `test_validacion_catalogo.py` | Las reglas de validación y el indicador 1 | sí |
| `test_rutas_catalogo.py` | Filtros, paginación, GeoJSON, 404 | sí |
| `test_seguridad.py` | Hash argon2, JWT, expiración | no |
| `test_rutas_autenticacion.py` | Registro, acceso, **que los dos errores sean iguales** | sí |
| `test_rutas_preferencias.py` | Los seis pasos, sin cuenta, reclamar | sí |
| `test_afinidad_y_afluencia.py` | TF-IDF, las 7 reglas de afluencia | no |
| `test_calendario.py` | **Butcher**: Semana Santa y Carnavales de varios años | no |
| `test_rutas_recomendaciones.py` | Filtros duros, descartes con motivo, explicación | sí |
| `test_tiempo_recorrido.py` | **Tobler**, esfuerzo, aviso de altitud | no |
| `test_costos.py` | La fórmula de tarifas y su rango | no |
| `test_ruteo.py` | OR-Tools, presupuesto, **que no sea un tour cerrado** | sí |
| `test_rutas_itinerarios.py` | Armar, reordenar, guardar idempotente, avisos | sí |
| `test_coordinacion.py` | Disponibilidad, estados, permisos, registro | sí |
| `test_sentimiento.py` | Las dos vías, negadores, temas, umbral 0,70 | no |
| `test_valoraciones.py` | Valorar, tablero, los 6 indicadores | sí |
| `test_asistente.py` | Las 5 funciones, **sin necesitar Ollama** | sí |
| `test_fichas_y_temporada.py` | Lector de fichas, horarios, fechas de fiestas | no |

**267 de las 549 no tocan PostgreSQL.** Es consecuencia de la separación por
capas: la IA y los cálculos se prueban solos.

---

## Frontend — los 14 archivos

| Área | Qué fija |
|---|---|
| `TarjetaServicio` | Que la capacidad sea **verificable**: sin eso la brecha 5 sigue abierta |
| `TarjetaSolicitud` | Que el historial se vea: la brecha 6 |
| `TarjetaRecomendacion` | Que se muestre **por qué** se recomienda |
| `LineaDeTiempo` | Traslados, y que no haya `<li>` dentro de `<li>` |
| `TotalesDelDia` | Que el costo lleve «aprox.» |
| `PanelConversacion` | Auditabilidad, sin Ollama, los dos idiomas |
| `SelectorIdioma`, `InterruptorTema` | Que cambien y persistan |
| `AsistentePreferencias` | **Los seis pasos sin iniciar sesión** |
| `utilidades/avisos` | **Que todo código tenga traducción en los dos idiomas** |

La última es la más importante del frontend: lee la lista de códigos del
archivo de Python y falla si a alguno le falta su frase.

---

## Las herramientas de calidad

### Backend

| Herramienta | Para qué |
|---|---|
| **ruff** | Linter. Detecta imports sin usar, nombres indefinidos, orden de imports. |
| **black** | Formato, línea de 100. |
| **pytest-cov** | Cobertura. |

```bash
cd backend
.venv/Scripts/python.exe -m ruff check app/ pruebas/ alembic/
.venv/Scripts/python.exe -m black --check app/ pruebas/ alembic/
```

### Frontend

| Herramienta | Para qué |
|---|---|
| **TypeScript** | Modo estricto. Cada cambio de tipo del API lista los sitios a tocar. |
| **ESLint 10** | Configuración plana, reglas de React Hooks. |
| **Prettier** | Formato. |
| **Vitest** | Pruebas, con jsdom. |

```bash
cd frontend
npx tsc --noEmit -p tsconfig.app.json
npx eslint src/
npx prettier --check "src/**/*.{ts,tsx,css,json}"
```

**Estado actual: todo limpio.**

### SonarQube

`sonar-project.properties` está **preparado y NO ejecutado**, como pide el
plan: lanzarlo exige un servidor y un token que este proyecto no tiene.

Declara qué se analiza, qué se excluye —entornos, migraciones autogeneradas,
cuadernos, datos pesados— y de dónde leer la cobertura. Sus rutas están
verificadas: todas existen.

---

## Detalles que costaron encontrar

**`scrollIntoView` no existe en jsdom.** Cualquier componente que baje solo a
lo último revienta al montarse en pruebas. Se añade a la preparación común
(`src/configuracion_pruebas.ts`) como función vacía: es una limitación del
entorno, no del componente.

**Las pruebas parten de una base vacía.** El `conftest` hace `TRUNCATE` de
todas las tablas antes de entregar la sesión, para que se puedan afirmar
totales exactos sin que los 295 recursos reales las estropeen. Ese borrado
también se deshace.

**Se nombran todas las tablas en el `TRUNCATE`** aunque `CASCADE` arrastraría a
varias: si mañana alguien quita una clave ajena, el `CASCADE` dejaría datos
vivos entre pruebas y los fallos serían de los que solo aparecen según el orden
de ejecución.

---

## Antes de dar algo por terminado

```bash
cd backend && .venv/Scripts/python.exe -m ruff check app/ pruebas/ && .venv/Scripts/python.exe -m black --check -q app/ pruebas/ && .venv/Scripts/python.exe -m pytest -q
```

```bash
cd frontend && npx tsc --noEmit -p tsconfig.app.json && npx eslint src/ && npx prettier --check "src/**/*.{ts,tsx,css,json}" && npx vitest run
```

Si los dos pasan, se puede hacer commit.

**Y al subirlo, GitHub Actions los vuelve a ejecutar solo**, en una máquina
limpia y con la base de datos construida desde cero. No sustituye a la lista
de arriba: la respalda, y deja constancia pública de cada ejecución. Ver
[17 — Integración y despliegue](17-integracion-y-despliegue.md).

Dos matices, para no citar de más:

- La integración continua **no ejecuta Prettier** (riesgo de fallar por
  finales de línea, no por calidad), ni el asistente con Ollama, ni el modelo
  de sentimiento. Se salta **una** prueba, y está medido.
- A cambio comprueba dos cosas que la laptop no comprueba nunca: que el
  proyecto **se instala desde cero** y que **las 11 migraciones se aplican
  sobre una base vacía**.

---

## Relacionado

- [15 — Historial de fallos](15-historial-de-fallos.md)
- [13 — Instalación y operación](13-instalacion-y-operacion.md)
- [17 — Integración y despliegue](17-integracion-y-despliegue.md)
