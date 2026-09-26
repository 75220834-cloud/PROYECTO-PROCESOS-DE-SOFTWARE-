# 18 — Análisis estático con SonarQube

**Qué explica este archivo:** el resultado del primer análisis real de SonarQube
sobre el proyecto, qué encontró, y los dos problemas de configuración que salieron
al ejecutarlo por primera vez.

**Fecha del análisis:** 25 de septiembre de 2026
**Servidor:** SonarQube **community 26.9.0** en Docker local, sin coste y sin nube
**Escáner:** `sonarsource/sonar-scanner-cli` en Docker
**Duración:** 11 min 40 s

---

## Antes de los números: esto estaba «preparado y no ejecutado», y no funcionaba

Durante ocho fases el proyecto declaró que `sonar-project.properties` estaba
**preparado y no ejecutado**, porque lanzarlo exigía un servidor y un token.

Al levantarlo y ejecutarlo, **el análisis falló dos veces antes de funcionar**:

### Fallo 1 — `sonar.sources` y `sonar.tests` se solapaban

```
ERROR File frontend/src/componentes/__pruebas__/InterruptorTema.prueba.tsx
can't be indexed twice. Please check that inclusion/exclusion patterns
produce disjoint sets for main and test files
```

Las pruebas del frontend viven **dentro** de `frontend/src`, que es una fuente
principal. Había que excluirlas de las fuentes para que los dos conjuntos fueran
disjuntos. De paso faltaba declarar `frontend/src/utilidades/__pruebas__`.

### Fallo 2 — la cobertura no se importaba, y el número parecía real

El análisis pasó, y SonarQube informó **13,4 % de cobertura** mientras pytest
declaraba 73,42 % y vitest 74,5 %.

No era un desacuerdo de criterio. Era que **no había importado casi nada**:

| Informe | Cómo venían las rutas | Por qué fallaba |
|---|---|---|
| `backend/coverage.xml` | `<source>` con la ruta **absoluta de Windows** (`D:\ESCRITORIO\...\backend\app`) y nombres de archivo relativos a ella | El escáner corre en un contenedor Linux con el proyecto en `/usr/src`; esa ruta no existe |
| `frontend/coverage/lcov.info` | `SF:src\componentes\...` — relativo a `frontend/` y con **barras invertidas** | Buscaba `/usr/src/src/componentes/...`, que tampoco existe |

Se resolvió con `normalizar_cobertura.py`, que reescribe **solo las rutas** y no
toca ningún número. Tras normalizar, la cobertura importada pasó de 13,4 % a
**68,1 %**.

> **La lección, que es la misma de siempre en este proyecto:** una configuración
> que nadie ha ejecutado no está «lista», está **sin comprobar**. Y un número que
> sale de una herramienta no es automáticamente cierto: el 13,4 % era plausible,
> estaba en un tablero de aspecto serio, y era falso.

---

## Los resultados

### Fiabilidad, seguridad y mantenibilidad

| Métrica | 1.ª ejecución | **Tras las correcciones** | Calificación |
|---|---|---|---|
| **Bugs** | 1 | **0** | Fiabilidad: **A** |
| **Vulnerabilidades** | 0 | **0** | Seguridad: **A** |
| **Puntos calientes de seguridad** | 0 | **0** | — |
| **Code smells** | 178 | **133** | Mantenibilidad: **A** |
| **CRITICAL** | 21 | **16** | — |
| **BLOCKER** | 0 | **0** | — |
| **Deuda técnica** | 885 min | **751 min = 12 h 31 min** | Ratio: **0,2 %** |
| **Duplicación** | 0,0 % | **0,0 %** | — |
| **Cobertura importada** | 68,1 % | **68,2 %** | — |

Las correcciones fueron tres, y están detalladas más abajo: extraer cinco
literales duplicados a constantes, quitar 38 `response_model` redundantes, y
marcar el falso positivo como *won't fix*. **−45 code smells y −134 minutos de
deuda.**

### Tamaño medido por SonarQube

| | |
|---|---|
| Líneas de código (ncloc) | **15 588** |
| Archivos analizados | **108** |
| Funciones | **694** |
| Complejidad ciclomática | **1 883** |
| Complejidad cognitiva | **1 181** |

### ⚠️ Las «0 vulnerabilidades» valen menos de lo que parecen

El propio tablero lo avisa, y hay que citarlo junto al número:

> **Limited security analysis.** SonarQube Community Build does not scan for
> critical injection vulnerabilities (SQL injection, XSS, and more).

**La edición community no busca inyección SQL ni XSS.** Así que el «0
vulnerabilidades» y la calificación **A** de seguridad **no significan que el
proyecto esté libre de inyección**: significan que esta herramienta, en esta
edición, no la buscó.

Lo que sostiene el argumento de que no hay inyección SQL no es SonarQube: es que
**todo el acceso a datos pasa por SQLAlchemy con consultas parametrizadas**, y no
hay concatenación de cadenas para construir SQL. Eso se puede enseñar leyendo
`servicios/` — y es lo que hay que decir en la defensa, no el A de Sonar.

### Quality Gate propio, sobre el CÓDIGO TOTAL

El perfil «Sonar way» que viene por omisión **solo mide código nuevo**, y en un
primer análisis eso se cumple trivialmente porque no hay línea base. Un Quality
Gate que pasa sin evaluar nada no dice nada.

Se creó una puerta propia, `RutaVivaMantaro`, con tres condiciones sobre el
**código total** —no sobre el nuevo—, y se asignó al proyecto:

| Condición | Estado | Actual | Umbral |
|---|---|---|---|
| `coverage` (código total) | **OK** | **68,2 %** | ≥ 60 % |
| `duplicated_lines_density` (total) | **OK** | **0,0 %** | ≤ 3 % |
| `blocker_violations` | **OK** | **0** | = 0 |
| `new_coverage` \* | OK | 100,0 % | ≥ 80 % |
| `new_duplicated_lines_density` \* | OK | 0,0 % | ≤ 3 % |
| `new_violations` \* | OK | 0 | = 0 |

\* SonarQube añade solas las tres condiciones de «Clean as You Code» al crear una
puerta. No se quitaron: miden algo distinto y complementario.

**ESTADO: OK en las seis.**

#### La primera vez falló, y el motivo es instructivo

Con la puerta recién creada, `new_violations` daba **6** y la puerta salía en
ERROR. Las seis eran `python:S8409` —`response_model` redundante— en líneas que
**yo había tocado ese mismo día** al añadir los `responses=`. No eran defectos
nuevos: eran seis de los 44 preexistentes que pasaron a contar como «código
nuevo» porque se editó su línea.

> **Tocar una línea convierte sus problemas viejos en problemas nuevos.** Es
> exactamente lo que «Clean as You Code» busca, y hay que saberlo antes de
> prometer que una puerta va a estar en verde.

---

## El único «bug», y por qué es un falso positivo

`backend/pruebas/test_seguridad.py:41` — regla `python:S5863`, *Assertions should
not be given twice the same argument*, esfuerzo estimado 5 min:

```python
def test_la_misma_contrasena_da_hashes_distintos(self):
    assert hashear_contrasena(CONTRASENA) != hashear_contrasena(CONTRASENA)
```

SonarQube ve la misma expresión a los dos lados del `!=` y supone una tautología.
**Aquí es justo lo contrario:** la prueba llama dos veces a la misma función
**a propósito**, para comprobar que argon2id genera una sal aleatoria distinta
cada vez y por tanto dos hashes distintos. Si esa aserción fallara, una tabla de
hashes precalculados rompería a todos los usuarios con la misma contraseña de
golpe.

**No se corrige.** Es la prueba la que tiene razón y la regla la que no puede
saberlo. Queda declarado aquí para que nadie la «arregle» más adelante.

Con eso, **la calificación de fiabilidad C se debe enteramente a un falso
positivo en una prueba**, no a un defecto del código de producción.

---

## Los 178 code smells, por regla

| Severidad | Cantidad |
|---|---|
| CRITICAL | 21 |
| MAJOR | 24 |
| MINOR | 130 |
| INFO | 3 |
| BLOCKER | **0** |

Las reglas que más aparecen:

| Regla | N.º | Qué dice |
|---|---|---|
| `typescript:S6754` | 38 | El valor de `useState` debe desestructurarse con nombres simétricos |
| `python:S8409` | 38 | Las rutas de FastAPI no deben declarar `response_model` redundante |
| `typescript:S6759` | 36 | Las props de React deben ser de solo lectura |
| `python:S3776` | 11 | **Complejidad cognitiva demasiado alta** |
| `python:S1192` | 9 | **Literales de cadena duplicados** |
| `typescript:S6819` | 6 | Preferir una etiqueta semántica antes que un `role` de ARIA |

**Los 21 CRITICAL son casi todos `S3776` y `S1192`**: funciones largas y cadenas
repetidas. Ninguno es un fallo de corrección ni de seguridad.

**`python:S8409` (38 avisos) merece una decisión, no un arreglo automático.**
Dice que `response_model` es redundante cuando el tipo de retorno ya lo declara.
Es cierto en FastAPI moderno, pero quitarlo de 38 endpoints es un cambio que toca
todo el contrato del API y que habría que hacer con las pruebas delante.

---

## Lo que el análisis confirma, y lo que no

**Confirma**, con una herramienta independiente:

- **0 vulnerabilidades y 0 puntos calientes de seguridad.** Calificación A.
- **0,0 % de duplicación.** Ni un bloque duplicado en 15 588 líneas.
- **Ratio de deuda técnica del 0,2 %**, que es muy bajo. Las 14 h 45 min de deuda
  estimada se reparten entre 178 avisos menores.
- **0 issues BLOCKER.**

**No confirma, y conviene no decirlo:**

- **Que el código esté probado**: el 68,1 % es la cobertura que SonarQube pudo
  importar, y solo cubre los archivos que las pruebas tocan. No es una medida
  independiente: es la misma que produjeron pytest y vitest, leída por Sonar.
- **Que el Quality Gate en verde valide nada** en este primer análisis.
- **Que no haya bugs**: dice que hay 1 y es un falso positivo, lo que significa
  que el análisis estático **no encontró ningún bug real**. Eso no es lo mismo que
  no haberlos.

---

## Cómo reproducirlo

```bash
docker run -d --name rutaviva_sonarqube -p 9000:9000 -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true sonarqube:community
```

```bash
cd backend && .venv/Scripts/python.exe -m pytest --cov-report=xml
```

```bash
cd frontend && npx vitest run --coverage --coverage.reporter=lcov
```

```bash
python normalizar_cobertura.py
```

```bash
docker run --rm -v "$(pwd):/usr/src" -e SONAR_HOST_URL=http://host.docker.internal:9000 -e SONAR_TOKEN=EL_TOKEN sonarsource/sonar-scanner-cli
```

El tablero queda en `http://localhost:9000/dashboard?id=rutavivamantaro`, y hay
una captura en [`docs/capturas/13_sonarqube.png`](../capturas/13_sonarqube.png).

---

## Relacionado

- [12 — Pruebas y calidad](12-pruebas-y-calidad.md)
- [17 — Integración y despliegue](17-integracion-y-despliegue.md)
- [15 — Historial de fallos](15-historial-de-fallos.md)

---

## Las tres correcciones aplicadas, y lo que se aceptó

### Corregido — 5 literales duplicados (`python:S1192`)

| Dónde | Qué era |
|---|---|
| `ia/asistente.py` ×4 | Las categorías del MINCETUR («1. SITIOS NATURALES»…) repetidas entre 4 y 8 veces. Extraídas a `CATEGORIA_*` |
| `ia/calendario.py` ×1 | «CONTEXTO_PROYECTO.md, sección 9» repetida 5 veces. Extraída a `FUENTE_CONTEXTO` |

**Por qué no es cosmético:** un dedazo en una de esas copias produce un filtro
que no casa con nada y devuelve cero resultados, que es el escenario que empuja
al modelo a inventarse un lugar (fallo 3 del ADR-014).

### Corregido — 38 `response_model` redundantes (`python:S8409`)

FastAPI infiere el modelo de la anotación de retorno; declararlo además es
duplicar. Se quitaron **solo** donde la expresión era idéntica a la anotación,
comprobado con `ast.unparse`.

**La verificación que hace seguro este cambio:** se generó el contrato OpenAPI
antes y después y se comparó. **Es idéntico byte a byte.** Si hubiera cambiado
un solo carácter, el cambio se habría revertido.

### Aceptado — 4 literales de idioma ORM (`python:S1192`)

`"SET NULL"`, `"usuario.id"` y `"all, delete-orphan"` en `modelos/`. Son
**idiomas de SQLAlchemy**: `ondelete="SET NULL"` se lee solo, y esconderlo tras
una constante haría el modelo *más* difícil de leer, no menos.

### Aceptado — 12 funciones con complejidad cognitiva alta (`python:S3776`)

| Grupo | Archivos | Decisión |
|---|---|---|
| **Guiones de carga (ETL)** | `cargar_fichas` (33), `fichas_mincetur` (31), `verificar_fase4` (33), `cargar_prestadores` (18), `descargar_dem` (18) | **Aceptado.** Son parseadores de una fuente irregular: su ramificación es el problema, no el código. Refactorizarlos arriesga romper una carga difícil de reverificar |
| **Servicios de negocio** | `ruteo` (28 y 21), `catalogo` (22), `recomendador` (16) | **Aceptado por ahora, declarado como la deuda prioritaria.** `ruteo.py:666` con 28 es la peor |
| **Asistente** | `asistente` (21 y 16) | **Aceptado.** Es la máquina de llamada a funciones; partirla dispersaría las seis reglas |
| **TypeScript** | `api.ts` (16) | **Aceptado.** Roza el umbral de 15 |

> **La deuda prioritaria, dicha con el dato delante:** los dos archivos con más
> complejidad —`cargar_fichas` (33) y `fichas_mincetur` (31)— son exactamente los
> que produjeron tres de los defectos del registro (D-06, D-07 y D-18, incluido
> el de las expresiones regulares que **falló en silencio**). La complejidad y el
> historial de fallos coinciden. Si hubiera tiempo para refactorizar una sola
> cosa, es esa.

### No corregido a propósito — el falso positivo

`test_seguridad.py:41` está marcado en SonarQube como **won't fix**, con este
comentario en el propio issue:

> FALSO POSITIVO. La prueba llama dos veces a `hashear_contrasena()` A
> PROPÓSITO, para comprobar que argon2id genera una sal aleatoria distinta en
> cada llamada y por tanto dos hashes distintos. […] Si esa aserción fallara,
> una tabla de hashes precalculados rompería a la vez a todos los usuarios con
> la misma contraseña.

Al marcarlo, los bugs pasan de 1 a **0** y la fiabilidad de **C** a **A**. No es
maquillaje: la C se debía enteramente a un falso positivo en una prueba.
