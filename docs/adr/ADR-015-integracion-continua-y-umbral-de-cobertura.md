# ADR-015 — La integración continua ejecuta las comprobaciones y la cobertura se exige, no solo se mide

| | |
|---|---|
| **Estado** | Aceptada e implementada |
| **Fecha** | 4 de septiembre de 2026 |
| **Alcance** | `.github/workflows/integracion-continua.yml`, `backend/pyproject.toml` |
| **Atributo de calidad principal** | **Mantenibilidad** (las reglas de calidad las comprueba una máquina) |
| **Atributos secundarios** | Portabilidad (se instala desde cero en un Ubuntu limpio) |
| **Nota de origen** | [`2026-09-04-que-se-automatizo-y-que-sigue-siendo-manual.md`](../decisiones/2026-09-04-que-se-automatizo-y-que-sigue-siendo-manual.md) |

---

## Contexto

Hasta el 4 de septiembre de 2026, las comprobaciones de calidad se ejecutaban
**a mano en la laptop** antes de cada commit. Funcionaba mientras nadie se
olvidara. El problema de un control manual no es que falle: **es que no deja
constancia**. Nadie podía comprobar, mirando el repositorio, si las pruebas
pasaron antes de un commit concreto.

Y había un agujero peor. `pyproject.toml` decía:

```toml
addopts = "-v --cov=app --cov-report=term-missing"
```

Eso **imprime** el porcentaje de cobertura. **No lo comprueba.** `pytest` devolvía
éxito con el 73 % y habría devuelto el mismo éxito con el 20 %. La regla del 60 %
existía en el plan de trabajo, en la documentación y en mi cabeza, y **en ningún
sitio la comprobaba una máquina**.

## Decisión

**1. La cobertura se exige.** Tres líneas:

```toml
[tool.coverage.report]
fail_under = 60
```

Comprobado por los dos lados, que es la única forma de creerse un umbral:

| Qué se ejecutó | Cobertura | Salida de pytest |
|---|---|---|
| La suite completa | 73,42 % | **0** — «Required test coverage of 60.0% reached» |
| Solo `test_seguridad.py` | 1,38 % | **1** — «FAIL … not reached» |

**2. GitHub Actions ejecuta todo en cada push y cada *pull request* a `main`**, en
dos trabajos paralelos: backend (con servicio `postgis/postgis:16-3.4`, la misma
imagen de `docker-compose.yml`) y frontend.

El valor no está en el tiempo ahorrado —cinco órdenes en la terminal cuestan
poco— sino en cuatro cosas que un control manual no puede dar:

- **Deja constancia** pública por commit, con fecha y registro por paso.
- **Prueba sobre una máquina limpia**: si el proyecto funcionaba por algo que
  quedó instalado en la laptop hace meses, aquí se cae.
- **Comprueba la cadena de migraciones desde una base vacía**, que en el día a día
  no se comprueba nunca. En un proyecto donde ya hubo que escribir a mano el cambio
  de una restricción `CHECK` porque Alembic no las detecta, no es teórico.
- **No depende de que nadie se acuerde**, que es de lo que dependía.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Dejar la cobertura solo medida** | Una regla que ninguna herramienta comprueba acaba incumpliéndose sin que nadie se entere. |
| **Poner `fail_under` en 73** (la cobertura real) | Obligaría a subir la cobertura en cualquier cambio que toque código nuevo, que no es lo pactado. El umbral es el mínimo comprometido, no la marca actual. |
| **Un solo trabajo secuencial** | El frontend no necesita base de datos: esperar a PostGIS sin motivo alarga la ejecución. En paralelo, el total es el del trabajo más lento (177 s contra 31 s). |
| **`npm install` en lugar de `npm ci`** | `npm install` puede actualizar el *lock*; dos ejecuciones instalarían cosas distintas y un fallo dejaría de ser reproducible. |
| **Instalar `pysentimiento` en la CI** | Arrastra PyTorch (~2,5 GB) y **descarga su modelo por red**. Las pruebas del proyecto no tocan la red por decisión declarada. Coste medido: se salta **1** prueba y el módulo queda en 96 %. |
| **Incluir `prettier --check`** | Riesgo de fallar por finales de línea (CRLF/LF), no por calidad. Se deja fuera **y se dice**, en vez de meterlo y descubrirlo en rojo. |
| **Añadir un paso de despliegue** | No hay a dónde desplegar: PostGIS no viene en las plantillas gestionadas y los 4,4 GB de Ollama no caben en ningún plan gratuito. Y los servicios de nube de pago están prohibidos por el plan. |

## Consecuencias

**Positivas, medidas en la primera ejecución real**

[Run 33940471717](https://github.com/75220834-cloud/PROYECTO-PROCESOS-DE-SOFTWARE-/actions/runs/33940471717),
**verde al primer intento**, `run_attempt: 1`, **3 min 3 s**.

| Trabajo | Duración | Paso más caro |
|---|---|---|
| Backend | 177 s | instalar dependencias (55 s), pruebas (81 s) |
| Frontend | 31 s | vitest (7 s) |

- **La regla de oro (1.6) dio un beneficio que no se buscaba:** como cada
  funcionalidad con modelo tiene alternativa por reglas, **el proyecto se comprueba
  entero sin descargar un solo modelo**.
- Las pruebas tardan **81 s en GitHub y 191 s en la laptop**, no porque la máquina
  sea más rápida sino porque **no tiene la red vial descargada** y los traslados se
  calculan en línea recta. Que la suite pase igual es consecuencia directa de
  ADR-006: las pruebas afirman sobre `origen_del_calculo` en vez de dar por hecho
  que hay red.

**Negativas, y asumidas**

- **La CI mide algo menos de cobertura que la laptop**, por lo mismo.
- **Un paso que no existe en local:** aplicar `99_extensiones.sql` a mano. En la
  laptop lo monta Docker en `/docker-entrypoint-initdb.d/`; en GitHub el contenedor
  del servicio arranca **antes** de que exista el código descargado.
- **El trabajo del frontend no puede usar una descarga parcial del repositorio**,
  porque la prueba de avisos lee un archivo de Python del backend (ADR-013).
- Consume minutos del plan de GitHub (ilimitados en repositorios públicos).

### Lo que sigue siendo manual, y por qué

| Actividad | Motivo |
|---|---|
| **Cargar los datos** | Descargan del MINCETUR, OpenStreetMap y Copernicus. Hacerlo en cada push sería pegarle a servidores del Estado por una coma. |
| **Probar con las manos** | **Es lo que más fallos ha encontrado.** El botón muerto, el itinerario duplicado y el asistente negando Concepción no los cazó ninguna prueba. |
| **El asistente con Ollama** | 4,4 GB. Sus 33 pruebas ya corren sin él. |
| **El modelo de sentimiento** | PyTorch y descarga por red. Se salta 1 prueba. |
| **SonarQube** | Preparado y no ejecutado: exige servidor y token. |
| **Prettier** | Riesgo de falso rojo por finales de línea. |
| **El despliegue** | No existe. |

## Relacionado

- [17 — Integración y despliegue](../referencia/17-integracion-y-despliegue.md)
- [ADR-006 — Dos modos de cálculo de distancia](ADR-006-dos-modos-de-calculo-de-distancia.md)
- [ADR-011 — Se acepta pysentimiento](ADR-011-se-acepta-pysentimiento-con-umbral-de-confianza.md)
