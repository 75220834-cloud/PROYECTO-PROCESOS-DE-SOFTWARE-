# Qué se automatizó y qué sigue siendo manual

**Fecha:** 4 de septiembre de 2026
**Fase:** 8 (posterior a los seis incrementos)
**Estado:** implementado

---

## La decisión

Las comprobaciones que hasta hoy se hacían **a mano antes de cada commit**
pasan a ejecutarlas GitHub Actions, solo, en una máquina limpia, en cada push
y en cada propuesta de cambio contra `main`.

Y con el mismo cambio se tapó un agujero que llevaba abierto desde la Fase 2:
la cobertura del backend **se medía pero no se exigía**.

---

## El agujero, primero, porque es lo más grave de esta nota

`pyproject.toml` decía esto:

```toml
addopts = "-v --cov=app --cov-report=term-missing"
```

Eso imprime el porcentaje de cobertura. **No lo comprueba.** `pytest` devolvía
éxito con el 73 % y habría devuelto exactamente el mismo éxito con el 20 %.

La regla del 60 % existía en tres sitios —el plan de trabajo, el archivo 12 de
la documentación de referencia y mi cabeza— y en ninguno de los tres la
comprueba una máquina.

El arreglo son tres líneas:

```toml
[tool.coverage.report]
fail_under = 60
```

Comprobado por los dos lados, que es la única forma de creerse un umbral:

| Qué se ejecutó | Cobertura | Salida de pytest |
|---|---|---|
| La suite completa | 73,42 % | **0** — «Required test coverage of 60.0% reached» |
| Solo `test_seguridad.py` | 1,38 % | **1** — «FAIL Required test coverage of 60.0% not reached» |

Un umbral que nunca se ha visto fallar no es un umbral: es un comentario.

> **La lección, que es la misma que la de las dos limitaciones falsas:** una
> regla que ninguna herramienta comprueba acaba siendo una regla que se
> incumple sin que nadie se entere. Con la diferencia de que aquí no hacía
> falta ir a comprobar ninguna fuente externa —bastaba leer con atención el
> archivo de configuración propio.

---

## Qué pasó de manual a automático

Estas seis actividades se hacían a mano. Ahora las hace GitHub, y **además**
se siguen pudiendo hacer a mano: no se ha quitado nada.

| Actividad | Cómo se hacía | Cómo se hace ahora |
|---|---|---|
| **Levantar la base de datos** | `docker compose up -d`, y acordarse de mirar que estuviera *healthy* | Un servicio del flujo, con `pg_isready` como condición de arranque |
| **Aplicar las migraciones** | `alembic upgrade head` sobre una base que ya existía | Sobre una base **vacía**, la cadena entera, en cada push |
| **Correr las 550 pruebas** | `pytest -q` antes de cada commit | En cada push, sobre una máquina limpia |
| **Comprobar la cobertura** | Mirar el número que salía por pantalla | `fail_under = 60`: el flujo se pone rojo solo |
| **Estilo del backend** | `ruff check` y `black --check` | Dos pasos del flujo |
| **Pruebas y tipos del frontend** | `vitest run`, `eslint src/`, `tsc --noEmit` | Un trabajo aparte, en paralelo con el backend |

### Lo que se gana no es tiempo

Escribir cinco órdenes en la terminal cuesta poco. Lo que se gana es otra cosa:

**1. Deja constancia.** Antes, nadie podía comprobar —mirando el repositorio—
si las pruebas pasaron antes de un commit concreto. Ahora cada commit lleva su
resultado al lado, con su registro completo y con fecha.

**2. Prueba sobre una máquina limpia.** Es lo más valioso, y lo que un control
manual no puede dar por definición. La máquina de GitHub no tiene nada
instalado de antes. Si el proyecto funcionaba por algo que quedó en la laptop
hace seis meses, aquí se cae.

**3. Comprueba la cadena de migraciones desde cero.** En el día a día uno
aplica la última migración sobre una base que ya tiene las anteriores. Que
todas juntas funcionen **partiendo de vacío** no se comprobaba nunca. En un
proyecto donde ya hubo que escribir a mano el cambio de una restricción
`CHECK` —porque Alembic no las detecta—, esto no es una comprobación teórica.

**4. No depende de que yo me acuerde.** Que es de lo que dependía.

---

## Qué sigue siendo manual, y por qué

Esta es la mitad honesta de la nota. No todo se automatizó, y en la mayoría de
los casos **no por falta de tiempo**.

### 1. Cargar los datos — y esto es a propósito

Los seis guiones de carga (`cargar_catalogo`, `cargar_fichas`,
`cargar_prestadores`, `cargar_calendario`, `preparar_red_vial`,
`descargar_dem`) **no se ejecutan en la CI**, y no deben ejecutarse.

Descargan del MINCETUR, de OpenStreetMap y de Copernicus. Meterlos en un flujo
que corre en cada push significaría **pegarle a servidores del Estado peruano
y a la API de OpenStreetMap cada vez que alguien sube una coma**. `cargar_fichas`
pide 295 páginas a una máquina del MINCETUR, esperando un segundo entre cada
una precisamente para no molestar.

Es el mismo principio que ya está escrito en las pruebas: *ninguna prueba toca
la red*. Automatizar esto sería trasladarle a un tercero el coste de nuestra
comodidad.

### 2. Probar con las manos

**Es lo que más fallos ha encontrado en todo el proyecto**, y no se puede
automatizar sin reescribirlo como otra cosa.

El botón de la portada que no hacía nada desde la Fase 0, el itinerario que se
duplicaba al entrar a valorar, el asistente negando que Concepción tuviera
atractivos: **ninguno lo cazó una prueba**. Los tres salieron usando la
aplicación.

Se podrían escribir pruebas de extremo a extremo con Playwright, y cubrirían
el botón muerto. No habrían cubierto los otros dos, porque el problema no era
que la pantalla no respondiera: era que respondía **algo incorrecto que solo
se nota si sabes cuál era la respuesta correcta**.

### 3. El asistente conversacional

Ollama necesita el modelo `qwen2.5:7b-instruct`, que son **4,4 GB**.
Descargarlo en cada ejecución es inviable, y el plan gratuito de GitHub
Actions no da para tenerlo cacheado.

**Coste real: ninguno.** Las 33 pruebas del asistente ya estaban escritas para
correr sin Ollama —comprueban las cinco funciones que el modelo puede llamar,
que es donde está la lógica— porque el modelo no aporta ningún dato: solo
elige qué función responde y redacta con lo que ella devuelve.

### 4. El análisis de sentimiento con modelo

`pysentimiento` arrastra PyTorch (~2,5 GB) y **descarga su modelo por red la
primera vez que se usa**. No se instala en la CI.

**Coste medido: una prueba se salta.** Las otras 50 del módulo corren igual,
porque están escritas contra la alternativa por reglas, y `sentimiento.py`
se queda en 96 % de cobertura de todas formas.

> Este es el beneficio inesperado de la regla de oro (1.6). La alternativa por
> reglas se pedía como control de riesgo —«que el sistema funcione sin ningún
> modelo entrenado»—. Resulta que además es lo que permite **comprobar el
> proyecto entero sin descargar un solo modelo**. No se diseñó para esto.

### 5. SonarQube

Sigue **preparado y no ejecutado**, como pide el plan. `sonar-project.properties`
está escrito y con las rutas verificadas, pero lanzarlo exige un servidor y un
token que este proyecto no tiene, y montarlo entraría en «servicios de nube de
pago», que está prohibido.

### 6. El despliegue

**No hay despliegue.** Este flujo es de integración continua, no de entrega
continua: comprueba que el código está sano, y ahí se detiene. Nadie publica
nada en ningún sitio.

Lo que haría falta para que existiera, y por qué hoy no puede existir, está en
[17 — Integración y despliegue](../referencia/17-integracion-y-despliegue.md).
El resumen: PostGIS y los 4,4 GB de Ollama no caben en ningún plan gratuito.

### 7. Prettier

Los otros cinco controles de calidad están en el flujo; `prettier --check` no.

El motivo es concreto: Windows escribe CRLF y Linux LF. El `.gitattributes`
normaliza a LF en el repositorio, así que **probablemente pasaría sin
problemas**. Pero «probablemente» no es motivo suficiente para meter un paso
que, si falla, lo hace por algo que no tiene nada que ver con la calidad del
código. Se deja fuera y se dice que está fuera, en vez de meterlo y descubrirlo
en rojo.

---

## Lo que la CI mide y la laptop no, y al revés

Los dos números no coinciden, y conviene saber por qué antes de que alguien lo
pregunte en la defensa.

**La CI comprueba dos cosas que la laptop no:** que las migraciones funcionan
desde una base vacía, y que el proyecto se instala desde cero sin depender de
nada que ya estuviera puesto.

**La laptop mide algo más de cobertura.** La CI no tiene la red vial descargada
—son 28 MB que el repositorio no guarda, por la decisión de guardar *las
instrucciones para obtener los datos, no los datos*—. Sin ella, los traslados
se calculan en línea recta y unas cuantas líneas de `red_vial.py` no se
recorren.

Las pruebas pasan igual porque el sistema está escrito para admitir las dos
situaciones **y decir cuál usó**: `origen_del_calculo` vale `red_vial` o
`linea_recta`, y las pruebas afirman sobre ese campo en vez de dar por hecho
que hay red.

> Es la primera vez que la honestidad del sistema sobre lo que sabe y lo que
> estima da un beneficio de ingeniería y no solo de discurso: **es lo que hace
> que el proyecto se pueda probar en una máquina que no tiene los datos.**

---

## El coste

- **Un archivo**, `.github/workflows/integracion-continua.yml`. Comentado de
  forma desproporcionada respecto a su longitud, a propósito: hay que
  defenderlo oralmente.
- **Tres líneas** en `pyproject.toml`.
- **Minutos del plan gratuito de GitHub.** El plan da 2 000 al mes para
  repositorios privados y son ilimitados en los públicos.
- **Un paso que no existe en la laptop**: aplicar `99_extensiones.sql` a mano.
  En local lo monta Docker en `/docker-entrypoint-initdb.d/`; en GitHub el
  contenedor del servicio arranca **antes** de que exista el código
  descargado, así que no hay nada que montar. Se aplica el archivo real del
  repositorio, no una copia de sus órdenes, para que añadir una extensión
  mañana no exija tocar dos sitios.

---

## Relacionado

- [17 — Integración y despliegue](../referencia/17-integracion-y-despliegue.md)
- [12 — Pruebas y calidad](../referencia/12-pruebas-y-calidad.md)
- [15 — Historial de fallos](../referencia/15-historial-de-fallos.md)
- [El asistente no cierra ninguna brecha](2026-08-29-el-asistente-no-cierra-ninguna-brecha.md)
