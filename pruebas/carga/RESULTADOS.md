# Resultados de las pruebas de carga

## ⚠️ Dónde se ejecutó esto — leer antes de citar cualquier número

**Estas mediciones se tomaron en una laptop, no en un servidor.** Es
indispensable declararlo así en el informe, porque cambia por completo la
interpretación de los números.

| | |
|---|---|
| **Máquina** | Laptop personal con Windows 11 Home Single Language 10.0.26200 |
| **Backend** | Proceso de `uvicorn` **de un solo trabajador**, sin `--workers`, sin servidor de producción delante (sin Gunicorn, sin Nginx) |
| **Base de datos** | PostgreSQL 16.4 + PostGIS 3.4 en un contenedor Docker **en la misma máquina** |
| **Generador de carga** | k6 v2.3.0 (go1.27.1, linux/amd64) en un contenedor Docker **en la misma máquina**, alcanzando el backend por `host.docker.internal` |
| **Red** | Ninguna. Todo es `localhost`: **no hay latencia de red en estos números** |
| **Fecha** | 25 de septiembre de 2026 |

### Qué significa eso, dicho sin adornos

1. **El generador de carga compite por CPU con lo que está midiendo.** k6, el
   backend, PostgreSQL y Docker Desktop corren en los mismos núcleos. En un
   entorno real el generador estaría en otra máquina.
2. **Un solo trabajador de `uvicorn`** significa que las peticiones que consumen
   CPU —recomendaciones e itinerarios— **se serializan**. Un despliegue real
   pondría varios trabajadores y los números de concurrencia serían distintos.
3. **La latencia de red es cero.** Cualquier despliegue real suma decenas o
   cientos de milisegundos que aquí no aparecen.
4. **No hay caché de HTTP, ni CDN, ni balanceador.**

> **Lo que estos números sí valen:** para comparar los tres escenarios entre sí,
> para localizar el cuello de botella del sistema, y para saber a partir de
> cuántos usuarios concurrentes degrada **en esta configuración**. No valen como
> capacidad de un despliegue en producción, porque no hay despliegue.

---

## Cómo reproducirlo

```bash
docker pull grafana/k6
```

```bash
curl -s -X POST http://localhost:8000/api/preferencias -H "Content-Type: application/json" -d '{"fecha_inicio":"2026-10-05","fecha_fin":"2026-10-07","distrito_origen":"HUANCAYO","presupuesto_soles":"450.00","intereses":["arqueologia","naturaleza","gastronomia"],"movilidad":"transporte_publico","ritmo":"moderado"}'
```

```bash
docker run --rm -v "$(pwd)/pruebas/carga:/carga" grafana/k6 run /carga/01-catalogo.js
```

```bash
docker run --rm -v "$(pwd)/pruebas/carga:/carga" -e PREFERENCIA=3005 grafana/k6 run /carga/02-recomendaciones.js
```

```bash
docker run --rm -v "$(pwd)/pruebas/carga:/carga" -e PREFERENCIA=3005 grafana/k6 run /carga/03-itinerario.js
```

*(En Git Bash sobre Windows hace falta `MSYS_NO_PATHCONV=1` delante, o Git Bash
convierte la ruta interna del contenedor. Y si la ruta del proyecto tiene
espacios, conviene copiar `pruebas/carga` a una ruta sin espacios.)*

---

## Escenario (a) — Listar el catálogo · `GET /api/recursos`

| | |
|---|---|
| Duración total | 1 min 40 s |
| Niveles de carga | 5 → 15 → 30 usuarios virtuales, 30 s cada uno |
| **Peticiones totales** | **2 942** |
| **Throughput** | **29,27 RPS** |
| **Tasa de error** | **0,00 %** (0 de 2 942) |
| Comprobaciones | 5 884 de 5 884 correctas |
| Datos recibidos | 20 MB |

### Latencia por nivel de carga

| Usuarios | p50 | p90 | p95 | p99 | máx |
|---|---|---|---|---|---|
| **5** | 10,11 ms | 12,87 ms | 14,87 ms | 49,03 ms | 53,99 ms |
| **15** | 9,90 ms | 15,33 ms | 19,03 ms | 73,46 ms | 319,85 ms |
| **30** | 10,52 ms | 15,47 ms | 21,29 ms | **150,46 ms** | 313,62 ms |

### Degradación

**No degrada en la mediana.** El p50 se queda plano en ~10 ms de 5 a 30
usuarios: el endpoint no está ni cerca de saturarse.

**Sí degrada en la cola.** El p99 se multiplica por 3: 49 → 73 → 150 ms. Es el
patrón de una cola que empieza a formarse sin llegar a desbordar.

> **Advertencia sobre el throughput:** los 29,27 RPS **no son la capacidad
> máxima**. El guion incluye `sleep(0.5)` entre iteraciones para imitar a un
> visitante real, así que el ritmo está marcado por esa pausa, no por el
> servidor. Para medir capacidad máxima habría que quitar la pausa.

---

## Escenario (b) — Generar recomendaciones · `POST /api/recomendaciones`

| | |
|---|---|
| Duración total | 1 min 49 s |
| Niveles de carga | 5 → 10 → 20 usuarios virtuales, 30 s cada uno |
| **Peticiones totales** | **102** |
| **Throughput** | **0,93 RPS** |
| **Tasa de error** | **0,00 %** (0 de 102) |
| Comprobaciones | 408 de 408 correctas |

### Latencia por nivel de carga

| Usuarios | p50 | p90 | p95 | p99 | máx |
|---|---|---|---|---|---|
| **5** | 5,25 s | 5,60 s | 5,70 s | 5,74 s | 5,75 s |
| **10** | 9,93 s | 10,73 s | 10,93 s | 11,97 s | 12,36 s |
| **20** | **16,49 s** | **27,70 s** | **30,26 s** | 30,55 s | 30,62 s |

### Degradación

**Degrada desde el primer nivel, y de forma lineal.** Al doblar los usuarios se
dobla la latencia: 5,25 → 9,93 → 16,49 s de mediana.

**El throughput se queda clavado en ~0,93 RPS en los tres niveles.** Esa es la
firma inequívoca de un recurso saturado: añadir usuarios no produce más trabajo
terminado, solo alarga la cola.

**Conclusión medida:** la capacidad de este endpoint, en esta configuración, es
de **aproximadamente una recomendación por segundo**. La saturación empieza
**por debajo de 5 usuarios concurrentes** — con una sola petición aislada el
endpoint responde en **1,74 s**, y con 5 usuarios ya tarda 5,25 s.

**Por qué:** cada petición ajusta un TF-IDF en memoria sobre los 295 recursos
(ADR-004: no hay modelo entrenado que cargar), y eso es trabajo de CPU que un
único trabajador de `uvicorn` no puede paralelizar.

---

## Escenario (c) — Armar el itinerario · `POST /api/itinerarios` — el más pesado

| | |
|---|---|
| Duración total | 4 min 43 s |
| Niveles de carga | 1 → 2 → 4 usuarios virtuales, 90 s cada uno |
| **Peticiones totales** | **66** |
| **Throughput** | **0,23 RPS** |
| **Tasa de error** | **0,00 %** (0 de 66) |
| Comprobaciones | 264 de 264 correctas |

Los niveles son bajos a propósito: con peticiones de varios segundos, subir a 20
usuarios no mediría el sistema, mediría la cola.

### Latencia por nivel de carga

| Usuarios | p50 | p90 | p95 | p99 | máx |
|---|---|---|---|---|---|
| **1** | 5,10 s | 5,65 s | 5,72 s | 5,82 s | 5,85 s |
| **2** | 7,82 s | 8,71 s | 9,16 s | 9,51 s | 9,59 s |
| **4** | **15,56 s** | **16,92 s** | **17,10 s** | 17,33 s | 17,39 s |

### Degradación

**Saturado desde 1 usuario.** Con un solo usuario virtual la mediana es de 5,10 s
y el throughput de 0,23 RPS; con 4 usuarios el throughput **sigue siendo 0,23
RPS** y la latencia se triplica. El sistema no tiene capacidad ociosa que
aprovechar.

### El coste de arrancar en frío, medido

| Petición | Tiempo |
|---|---|
| **Primera después de reiniciar el backend** | **11,01 s** |
| Segunda (con la red vial ya en memoria) | 5,15 s |

La diferencia son los **28 MB del grafo de la red vial**, que se cargan una vez
por proceso con `lru_cache`. En un despliegue con varios trabajadores, **cada
trabajador pagaría esos 11 s en su primera petición** y mantendría su propia
copia de 28 MB en memoria. Es un dato de diseño relevante que solo se ve
midiendo.

---

## Resumen comparado de los tres escenarios

| | (a) Catálogo | (b) Recomendaciones | (c) Itinerario |
|---|---|---|---|
| Peticiones | 2 942 | 102 | 66 |
| **Throughput** | 29,27 RPS* | **0,93 RPS** | **0,23 RPS** |
| p50 al nivel más bajo | 10,11 ms | 5,25 s | 5,10 s |
| p95 al nivel más alto | 21,29 ms | 30,26 s | 17,10 s |
| Tasa de error | 0,00 % | 0,00 % | 0,00 % |
| ¿Degrada? | Solo en la cola (p99) | Sí, lineal, desde <5 usuarios | Sí, saturado desde 1 usuario |

\* marcado por la pausa del guion, no por el servidor.

### El cuello de botella, localizado

**Tres órdenes de magnitud separan el catálogo del itinerario**: 10 ms contra
5 100 ms. El catálogo es una consulta SQL paginada; el itinerario encadena
TF-IDF, caminos mínimos sobre un grafo de 40 071 nodos, la función de Tobler
sobre un raster de elevación y un VRPTW resuelto con OR-Tools.

**No es un problema de base de datos ni de consultas: es CPU en el proceso de
Python.** Se ve en que el throughput no sube al añadir usuarios.

### Qué haría falta para mejorarlo, si algún día hubiera despliegue

Sin prometer nada, porque **nada de esto se ha implementado ni medido**:

1. **Varios trabajadores de `uvicorn`.** Es la medida más directa: las
   peticiones de CPU dejarían de serializarse. Coste: 28 MB de red vial por
   trabajador y 11 s de arranque en frío cada uno.
2. **Cachear el itinerario por (preferencia, fecha).** El mismo par produce el
   mismo resultado mientras no cambien los datos.
3. **Precalcular la matriz de distancias** entre los 295 recursos, en vez de
   resolver caminos mínimos en cada petición.
4. **Mover el cálculo a una tarea en segundo plano** y devolver el itinerario
   cuando esté, en vez de hacer esperar la petición HTTP.

Las cuatro son hipótesis razonables. Ninguna está medida, y por eso se presentan
como hipótesis.

---

## Cero errores en 3 110 peticiones

Las tres ejecuciones sumaron **3 110 peticiones con 0 fallos**, y las 6 556
comprobaciones de contenido pasaron todas. Eso incluye las que verifican las
promesas del sistema bajo carga:

- que cada recomendación trae su puntaje de afinidad (la brecha 2);
- que cada traslado declara si salió de la red vial o de una línea recta
  corregida (ADR-006);
- que la respuesta dice con qué vía se generó, modelo o reglas (la regla de oro).

**El sistema se degrada en tiempo, no en corrección.** Bajo 20 usuarios
concurrentes tarda 30 segundos, pero no devuelve un error ni deja de declarar lo
que estima.
