# 20 — Registro de defectos

**Qué explica este archivo:** los defectos del proyecto en formato de registro
formal, para la gestión de defectos que pide la consigna.

Es la misma lista de [15 — Historial de fallos](15-historial-de-fallos.md), que
cuenta **cómo** se encontró y se arregló cada uno, reexpresada aquí en tabla con
severidad, estado y commit. El 15 se lee; este se consulta.

**Regla de conteo**, la misma que ya estaba documentada: *un defecto es un
encabezado de nivel 3 con nombre propio, o una fila de tabla en las secciones de
fallos del archivo 15*. No se cuentan las líneas de prosa ni los ejemplos en
viñetas.

**Fecha de corte: 25 de septiembre de 2026.**

---

## Los defectos

### Severidad, cómo se asigna

| Severidad | Criterio |
|---|---|
| **Crítico** | El sistema afirma algo falso, niega algo cierto, o rompe un indicador |
| **Mayor** | Funcionalidad que no hace lo que dice, o dato que se pierde |
| **Menor** | Redacción, formato, entorno, o molestia sin consecuencia en el dato |

### Tabla

| ID | Descripción | Severidad | Detectado en | Estado | Commit | ¿Regresión? |
|---|---|---|---|---|---|---|
| D-01 | OR-Tools devolvía 1 parada donde las reglas encontraban 3: el día se modelaba como circuito cerrado | **Crítico** | Uso | Cerrado | `f2de3a6` | Sí, 2 pruebas |
| D-02 | El asistente negaba que Concepción tuviera atractivos; tiene trece. `ILIKE` es sensible a tildes | **Crítico** | Uso | Cerrado | *(sin hash propio)*\* | Sí |
| D-03 | Dos limitaciones declaradas eran falsas: el MINCETUR sí publica horarios y descripciones, en la ficha web | **Crítico** | Revisión | Cerrado | `837f4a4`, `86cdf91` | Sí, 30 pruebas |
| D-04 | Latitud y longitud intercambiadas en el CSV del MINCETUR, en el archivo entero | **Crítico** | Verificación | Cerrado | `293b714` | Sí, en ambos sentidos |
| D-05 | El mismo RUC en dos directorios (un hotel que también es restaurante) violaba la clave única | Mayor | Verificación | Cerrado | `ce9ecbe` | Sí |
| D-06 | «Julio» tomado como mes cuando era el nombre del fundador | Mayor | Verificación | Cerrado | `55fd4f0` | Sí |
| D-07 | La historia del pueblo aportaba meses falsos a la fecha de la fiesta | Mayor | Verificación | Cerrado | `55fd4f0` | Sí |
| D-08 | Guardar un itinerario no era idempotente: inflaba el denominador del indicador 6 | **Crítico** | Uso | Cerrado | `73fe563` | Sí, 3 pruebas |
| D-09 | «Mejor» y «peor valorados» mostraban los mismos recursos | Mayor | Uso | Cerrado | `73fe563` | Sí |
| D-10 | Los tramos motorizados nunca se ruteaban: el aviso «no hay red vial cerca» era literalmente falso | **Crítico** | Verificación | Cerrado | `844a454` | Sí |
| D-11 | `sin_horario` se contaba antes de truncar: decía «30 de los 20 recursos» | Mayor | Verificación | Cerrado | `844a454` | Sí |
| D-12 | Tramos del mismo nodo marcados como estimados sin serlo | Mayor | Verificación | Cerrado | `844a454` | Sí |
| D-13 | Comparación de sentimiento amañada: las reglas veían la puntuación y el modelo no | **Crítico** | Revisión | Cerrado | `73fe563` | Sí |
| D-14 | El botón principal de la portada no hacía nada desde la Fase 0 | Mayor | Uso | Cerrado | `fd4cce8` | Sí |
| D-15 | `<li>` dentro de `<li>` en la línea de tiempo: HTML inválido | Menor | Revisión | Cerrado | `73fe563` | Sí |
| D-16 | Números del mapa ilegibles en modo oscuro | Menor | Verificación | Cerrado | `5dfa877` | Sí, 9 rutas |
| D-17 | La ficha ignoraba `descripcion_en` estando en inglés | Mayor | Revisión | Cerrado | `50db2e6` | Sí |
| D-18 | Expresiones regulares sin `r"..."`: dejaron de reconocer nada **sin dar ningún error** | **Crítico** | Verificación | Cerrado | `55fd4f0` | Sí |
| D-19 | Alembic no detecta cambios en restricciones `CHECK` | Menor | Verificación | Cerrado | `55fd4f0` | No (limitación de la herramienta, documentada) |
| D-20 | Un `uvicorn` huérfano servía código viejo en el puerto 8000 | Menor | Uso | Cerrado | — (entorno) | No |
| D-21 | La caché de Vite servía un módulo vacío | Menor | Uso | Cerrado | — (entorno) | No |
| D-22 | Fixtures de prueba equivocadas: Tobler 2,96 cuando eran 3,55; ids 101/103 cuando eran 100/102 | Menor | Revisión | Cerrado | varios | Sí |
| **D-23** | `verificar_fase4` reventaba con `AttributeError` desde el cambio de avisos de la Fase 7 | Mayor | Verificación | **Cerrado** | `29d564c` | No — ese archivo tiene 0 % de cobertura |
| **D-24** | `sonar-project.properties` estaba «preparado y no ejecutado» y **no funcionaba**: `sonar.sources` y `sonar.tests` se solapaban | Mayor | Verificación | **Cerrado** | `f879c3f` | No |
| **D-25** | SonarQube informaba 13,4 % de cobertura frente al 73,42 % real: rutas absolutas de Windows en `coverage.xml` y barras invertidas en `lcov.info` | Mayor | Verificación | **Cerrado** | `f879c3f` | No — lo evita `normalizar_cobertura.py` |
| **D-26** | El contrato OpenAPI declaraba solo 200/201/422 aunque el código lanza 404, 403, 409 y 401 | Mayor | Revisión | **Cerrado** | `9f8d32c` | Sí — el mapa se validó contra el API en vivo |
| **D-27** | La tarjeta del catálogo muestra «Concepcion» **sin tilde**: no usa el mapeo `provincias` de `es.json` | Menor | Prueba (E2E-01) | **ABIERTO** | — | La E2E compara sin tildes para no fallar por él |
| **D-28** | Cinco errores del API mandan **prosa en español** en vez de un código, así que no se traducen (contradice el ADR-013) | Mayor | Revisión | **ABIERTO** | — | No |

\* **D-02 no tiene un commit propio que se pueda citar.** La corrección con
`unaccent` viaja dentro de los commits del asistente, y buscarla por mensaje
devuelve commits que no son el suyo. Se deja el hueco declarado en vez de
rellenarlo con un hash aproximado: un registro de defectos con un commit
equivocado es peor que uno con una celda vacía.

---

## Conteo

### Por severidad

| Severidad | Cantidad |
|---|---|
| **Crítico** | **8** |
| **Mayor** | **13** |
| **Menor** | **7** |
| **Total** | **28** |

### Por estado

| Estado | Cantidad |
|---|---|
| **Cerrado** | **26** |
| **Abierto** | **2** (D-27, D-28) |

### Por dónde se detectó — el dato que más enseña

| Dónde | Cantidad |
|---|---|
| **Verificación** (guiones y comprobaciones a mano) | 11 |
| **Uso** (abrir la aplicación y usarla) | 6 |
| **Revisión** (leer el código o la documentación) | 6 |
| **Prueba automática** | **1** |

> **Una sola de las 28 la encontró una prueba automática.** Y es D-27, que la
> encontró una prueba E2E escrita ayer. Las 550 pruebas unitarias y de
> integración del backend no cazaron ninguno de los 28: cazan las regresiones
> *después*, que es su trabajo, pero no fue así como aparecieron.
>
> Es el argumento más fuerte a favor de probar con las manos, y conviene decirlo
> con el número delante en vez de como intuición.

---

## Densidad de defectos

Con los KLOC de producción medidos —sin dependencias ni migraciones
autogeneradas— el 25 de septiembre de 2026:

| | Defectos | KLOC | **Densidad** |
|---|---|---|---|
| **Global** | **28** | **14,765** | **1,90 def/KLOC** |
| Backend | 21 | 8,501 | 2,47 def/KLOC |
| Frontend | 7 | 6,264 | 1,12 def/KLOC |

Antes de esta semana eran 22 defectos y **1,49 def/KLOC**. Sube a 1,90 porque se
añaden seis, **no porque el código haya empeorado**: cinco de los seis nuevos se
encontraron ejecutando por primera vez herramientas que estaban preparadas y sin
ejecutar (SonarQube, las E2E) o revisando el contrato con atención.

> **La densidad de defectos de un proyecto sube cuando se empieza a mirar.** Un
> proyecto con densidad 0 no es un proyecto sin defectos: es un proyecto sin
> registro de defectos.

### Sensibilidad del conteo, declarada

La sección «fallos de redacción» del archivo 15 describe los plurales como una
clase con cuatro o cinco ejemplos en viñetas, que la regla de conteo no cuenta.
Contándolos por separado serían **32–33 defectos** y **2,17–2,24 def/KLOC**. El
reparto backend/frontend es un juicio de clasificación, no está en el archivo 15.

---

## Los dos defectos abiertos, con su plan

### D-27 · «Concepcion» sin tilde

**Qué pasa:** `es.json` declara `provincias.concepcion = "Concepción"`, pero
`TarjetaRecurso.tsx` muestra `formatearNombrePropio(recurso.provincia)`, que
title-casea el dato crudo del MINCETUR y deja la provincia sin tilde. La misma
provincia se escribe de dos formas según dónde se mire.

**Por qué sigue abierto:** es cosmético y el arreglo tiene una decisión detrás
que no es obvia —¿se normalizan solo las cuatro provincias, o también los 56
distritos, que no tienen mapeo?—. Cerrarlo a medias sería peor.

### D-28 · Cinco errores del API mandan prosa

**Dónde:** `utilidades/dependencias.py` (el 401 y el 403),
`rutas/itinerarios.py` (el 422 de fecha fuera del viaje) y dos `detail=str(error)`
en `rutas/coordinacion.py`.

**Qué pasa:** esos cinco **no se traducen**. Salen en español aunque la interfaz
esté en inglés, porque `traducirError` no encuentra la clave y muestra el mensaje
tal cual.

**Por qué sigue abierto:** cerrarlo exige cinco códigos nuevos en
`CODIGOS_CONOCIDOS` y diez claves nuevas de traducción, y es un cambio de
comportamiento del API. No es una corrección de una línea, y meterlo sin las
traducciones haría que la prueba de simetría de idiomas fallara.

**Está declarado en el propio esquema** (`esquemas/errores.py`), donde `detail`
se tipa como *código o cadena* en vez de solo código: describir un contrato que
el código no cumple sería peor que declarar la excepción.

---

## Relacionado

- [15 — Historial de fallos](15-historial-de-fallos.md) — el cómo de cada uno
- [19 — Matriz de registro de pruebas](19-matriz-de-registro-de-pruebas.md)
- [18 — Análisis estático con SonarQube](18-analisis-estatico-sonarqube.md)
