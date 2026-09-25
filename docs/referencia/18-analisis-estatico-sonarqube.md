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

| Métrica | Valor | Calificación |
|---|---|---|
| **Bugs** | **1** | Fiabilidad: **C** |
| **Vulnerabilidades** | **0** | Seguridad: **A** |
| **Puntos calientes de seguridad** | **0** | — |
| **Code smells** | **178** | Mantenibilidad: **A** |
| **Deuda técnica** | **885 min = 14 h 45 min** | Ratio de deuda: **0,2 %** |
| **Duplicación** | **0,0 %** (0 bloques duplicados) | — |
| **Cobertura importada** | **68,1 %** (líneas 68,1 %, ramas 68,3 %) | — |

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

### Quality Gate: **OK** — pero léase la letra pequeña

El Quality Gate pasó, **evaluando una sola condición**:

| Condición | Estado | Actual | Umbral |
|---|---|---|---|
| `new_violations` | OK | 0 | 0 |

Es el perfil «Sonar way», que mide **código nuevo**. En un primer análisis no hay
línea base contra la que comparar, así que «0 violaciones nuevas» se cumple
trivialmente. **El Quality Gate en verde aquí no significa que el código esté
limpio: significa que no hay nada que comparar todavía.** A partir del segundo
análisis sí empezará a decir algo.

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
