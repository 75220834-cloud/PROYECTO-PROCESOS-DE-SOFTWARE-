# Datos para las vistas C4 de RutaVivaMantaro

**Qué es este archivo:** los datos crudos para generar los diagramas C4 de
niveles 1, 2 y 3. **No contiene diagramas**: contiene las listas de elementos y
sus relaciones explícitas, en el formato `A --[protocolo, qué dato]--> B`.

**Todo está extraído del código, no supuesto.** Las versiones salen de
`pip list` y de `package.json`; el grafo de dependencias del nivel 3 sale de
analizar los `import` con el módulo `ast` de Python; los sistemas externos salen
de buscar las URL reales en el código fuente.

**Fecha de extracción:** 25 de septiembre de 2026

---

## NIVEL 1 — Contexto

### Personas (actores)

Los cinco roles están cerrados en el código, en `RolUsuario`
(`app/modelos/usuario.py`), como `StrEnum` y no como tabla, porque el conjunto lo
fija el análisis de las siete brechas.

| Actor | Necesita cuenta | Qué hace |
|---|---|---|
| **Visitante anónimo** | **No** | Recorre el catálogo, declara preferencias, recibe recomendaciones, arma su itinerario y valora. Es el actor principal y **no requiere registro** (ADR-003) |
| **Visitante registrado** | Sí | Lo mismo, y además guarda sus viajes y reclama la preferencia que creó sin cuenta |
| **Proveedor** | Sí | Publica servicios y disponibilidad; responde y confirma solicitudes de coordinación |
| **Operador** | Sí | Ve todas las solicitudes del canal de coordinación |
| **Gestor** | Sí | Consulta el tablero de evidencia y los seis indicadores |
| **Administrador** | Sí | Acceso total |

### Relaciones actor → sistema

```
Visitante anónimo      --[HTTPS/HTML+JS, navegador]--> RutaVivaMantaro
Visitante anónimo      --[HTTPS/JSON, preferencias de viaje: fechas, presupuesto, distrito de salida, intereses, ritmo]--> RutaVivaMantaro
RutaVivaMantaro        --[HTTPS/JSON, recomendaciones con su explicación + itinerario con horas, distancias, costos aprox. y avisos]--> Visitante anónimo
Visitante registrado   --[HTTPS/JSON + JWT Bearer, credenciales y itinerarios a guardar]--> RutaVivaMantaro
Proveedor              --[HTTPS/JSON + JWT Bearer, servicios, disponibilidad y cambios de estado de solicitudes]--> RutaVivaMantaro
Operador               --[HTTPS/JSON + JWT Bearer, consulta de solicitudes]--> RutaVivaMantaro
Gestor                 --[HTTPS/JSON + JWT Bearer, consulta del tablero de evidencia e indicadores]--> RutaVivaMantaro
RutaVivaMantaro        --[HTTPS/JSON, seis indicadores con su salvedad declarada]--> Gestor
```

### Sistemas externos

Verificados como URL reales en el código fuente del backend y del frontend.

| Sistema externo | Qué es | Cuándo se contacta |
|---|---|---|
| **MINCETUR — Inventario Nacional de Recursos Turísticos** | CSV de datos abiertos del Estado peruano | Solo en la carga (`cargar_catalogo`), **no en tiempo de petición** |
| **MINCETUR — Fichas web del inventario** | 295 páginas HTML, una por recurso | Solo en la carga (`cargar_fichas`), a 1 petición/s, con caché en disco |
| **MINCETUR — Directorio Nacional de Prestadores Calificados** | 3 CSV: hospedajes, agencias, restaurantes | Solo en la carga (`cargar_prestadores`) |
| **OpenStreetMap / Overpass API** | Red vial del valle (40 071 nodos, 111 704 aristas) | Solo en la preparación (`preparar_red_vial`), vía OSMnx |
| **Copernicus GLO-30 DEM** (`copernicus-dem-30m.s3.amazonaws.com`) | Modelo digital de elevación, 30 m | Solo en la preparación (`descargar_dem`) |
| **OpenStreetMap — servidor de teselas** (`tile.openstreetmap.org`) | Imágenes del mapa | **En tiempo de ejecución, desde el navegador del visitante** |
| **Google Maps** (`google.com/maps/search/`) | Enlace de búsqueda para ubicar prestadores reales | Enlace que abre el visitante; el sistema no consume su API |
| **Ollama** | Servidor local del modelo `qwen2.5:7b-instruct` | En tiempo de ejecución, **opcional** |

### Relaciones sistema ↔ sistemas externos

```
RutaVivaMantaro (carga)  --[HTTPS/GET CSV, descarga el inventario nacional (6 155 filas)]--> MINCETUR Inventario
MINCETUR Inventario      --[CSV cp1252, 295 recursos de las 4 provincias con lat/lon y FECHA_DE_CORTE]--> RutaVivaMantaro (carga)
RutaVivaMantaro (carga)  --[HTTPS/GET HTML, 1 peticion/s con User-Agent identificado]--> MINCETUR Fichas web
MINCETUR Fichas web      --[HTML, descripcion, horario, tipo de ingreso, epoca propicia y conteos de visitantes]--> RutaVivaMantaro (carga)
RutaVivaMantaro (carga)  --[HTTPS/GET CSV x3]--> MINCETUR Directorio de Prestadores
MINCETUR Directorio      --[CSV latin-1, 162 prestadores con RUC, direccion, telefono y n.º de certificado]--> RutaVivaMantaro (carga)
RutaVivaMantaro (carga)  --[HTTP/Overpass QL via OSMnx]--> OpenStreetMap Overpass API
OpenStreetMap Overpass   --[grafo vial: 40 071 nodos, 111 704 aristas]--> RutaVivaMantaro (carga)
RutaVivaMantaro (carga)  --[HTTPS/GET GeoTIFF]--> Copernicus GLO-30 DEM
Copernicus GLO-30 DEM    --[raster de elevacion 30 m, para la funcion de Tobler]--> RutaVivaMantaro (carga)
Navegador del visitante  --[HTTPS/GET PNG, teselas del mapa]--> OpenStreetMap tile server
Navegador del visitante  --[HTTPS, enlace de busqueda del prestador]--> Google Maps
RutaVivaMantaro (API)    --[HTTP/JSON localhost:11434, mensajes + definicion de 5 funciones]--> Ollama
Ollama                   --[HTTP/JSON, que funcion llamar y con que argumentos, o el texto redactado]--> RutaVivaMantaro (API)
```

> **Dato que conviene señalar en el informe:** de los ocho sistemas externos,
> **seis se contactan solo en la carga de datos, no en tiempo de petición**. En
> ejecución el sistema solo depende de las teselas de OpenStreetMap (desde el
> navegador) y, opcionalmente, de Ollama. Es lo que permite que la aplicación
> funcione con conectividad limitada, que es una restricción declarada del
> proyecto.

---

## NIVEL 2 — Contenedores

Cuatro unidades desplegables. Versiones verificadas con `pip list`,
`package.json`, `docker exec … psql` y `ollama --version`.

| Contenedor | Tecnología exacta | Versión | Puerto | Se despliega como |
|---|---|---|---|---|
| **Interfaz web** (`frontend/`) | React + TypeScript, servido por Vite en desarrollo | React **19.2.8**, TypeScript **6.0.3**, Vite **8.2.2**, Tailwind **4.3.3** | **5173** | Proceso Node (`npm run dev`) o estáticos compilados (`npm run construir`) |
| **API** (`backend/`) | FastAPI sobre Uvicorn (ASGI), Python 3.14 | FastAPI **0.141.1**, Uvicorn **0.52.4**, Python **3.14.0**, SQLAlchemy **2.0.52**, Pydantic **2.13.5** | **8000** | Proceso Python |
| **Base de datos** | PostgreSQL con PostGIS, en Docker | PostgreSQL **16.4**, PostGIS **3.4** (`USE_GEOS=1 USE_PROJ=1 USE_STATS=1`), imagen `postgis/postgis:16-3.4` | **5432** | Contenedor Docker `rutaviva_postgres` |
| **Servidor de modelo** | Ollama con `qwen2.5:7b-instruct` (~4,4 GB) | Ollama **0.34.4** | **11434** | Servicio local, **opcional** |

Bibliotecas relevantes del contenedor API, con versión verificada: GeoAlchemy2
**0.20.0**, psycopg **3.3.4**, Alembic **1.19.1**, httpx **0.28.1**,
scikit-learn **1.9.0**, OR-Tools **9.15.6755**, OSMnx **2.1.1**, NetworkX
**3.6.1**, rasterio **1.5.1**, pysentimiento **0.7.3**, PyTorch **2.13.0**,
passlib **1.7.4**, python-jose **3.5.0**.

### Relaciones entre contenedores

```
Navegador               --[HTTP/1.1, HTML + JS + CSS empaquetado]--> Interfaz web :5173
Interfaz web :5173      --[HTTP/1.1 JSON REST, 43 operaciones; JWT HS256 en cabecera Authorization: Bearer]--> API :8000
API :8000               --[HTTP/1.1 JSON, respuestas con avisos como {codigo, parametros}]--> Interfaz web :5173
API :8000               --[TCP/5432, protocolo PostgreSQL via psycopg 3, SQL + consultas PostGIS (ST_X, ST_Y, ST_DWithin, indices GIST)]--> Base de datos :5432
Base de datos :5432     --[filas; geografia como GEOGRAPHY(POINT, 4326)]--> API :8000
API :8000               --[HTTP/1.1 JSON, /api/chat con definicion de 5 funciones]--> Ollama :11434
Ollama :11434           --[HTTP/1.1 JSON, tool_calls o texto]--> API :8000
Navegador               --[HTTPS, teselas PNG]--> OpenStreetMap tile server
Alembic (CLI)           --[TCP/5432, DDL de las 11 migraciones]--> Base de datos :5432
```

### Notas de despliegue, verificadas

- **La interfaz nunca habla con la base de datos.** Todo pasa por el API.
- **El API arranca sin Ollama.** `GET /api/asistente/estado` informa si está y por
  qué no, y la interfaz cae al formulario de preferencias (ADR-014).
- **El API no arranca sin la base de datos**, pero `GET /api/salud` informa del
  estado de los tres componentes por separado.
- **No hay contenedor de despliegue real.** No existe `Dockerfile` para el backend
  ni para el frontend: ambos corren como procesos locales. Declarado en
  `docs/referencia/17-integracion-y-despliegue.md`.

---

## NIVEL 3 — Componentes del contenedor API

Archivos `.py` por paquete, sin contar `__init__.py`. **Total: 52 archivos** de
código de aplicación.

| Componente | Archivos | Módulos |
|---|---|---|
| **`rutas/`** — enrutadores FastAPI | **9** | `asistente`, `autenticacion`, `catalogo`, `coordinacion`, `itinerarios`, `preferencias`, `recomendaciones`, `salud`, `valoraciones` |
| **`servicios/`** — lógica de negocio | **13** | `avisos`, `catalogo`, `coordinacion`, `costos`, `elevacion`, `evidencia`, `recomendador`, `red_vial`, `ruteo`, `seguridad`, `temporada`, `usuarios`, `validacion_catalogo` |
| **`ia/`** — modelos y sus alternativas por reglas | **6** | `afinidad`, `afluencia`, `asistente`, `calendario`, `sentimiento`, `tiempo_recorrido` |
| **`modelos/`** — tablas SQLAlchemy | **8** | `afluencia`, `catalogo`, `coordinacion`, `itinerario`, `preferencias`, `transporte`, `usuario`, `valoracion` |
| **`esquemas/`** — contratos Pydantic | **9** | `autenticacion`, `avisos`, `catalogo`, `coordinacion`, `itinerarios`, `preferencias`, `recomendaciones`, `salud`, `valoraciones` |
| **`utilidades/`** — guiones de carga y dependencias | **12** | `cargar_calendario`, `cargar_catalogo`, `cargar_fichas`, `cargar_prestadores`, `dependencias`, `descargar_dem`, `fichas_mincetur`, `medir_cobertura_osm`, `preparar_red_vial`, `proveedores_semilla`, `usuarios_semilla`, `verificar_fase4` |
| **raíz de `app/`** — arranque y configuración | **3** | `base_datos`, `configuracion`, `main` |

### Quién llama a quién (extraído del grafo de `import` con `ast`)

```
main (raiz)      --[monta los enrutadores con include_router]--> rutas
rutas            --[llama funciones de negocio, pasa la sesion]--> servicios
rutas            --[invoca modelos y alternativas por reglas]--> ia
rutas            --[valida entrada y serializa salida]--> esquemas
rutas            --[consulta y persiste]--> modelos
rutas            --[obtiene sesion y usuario autenticado]--> utilidades (dependencias)
rutas            --[lee configuracion y abre sesion]--> (raiz)
servicios        --[usa afinidad, afluencia, calendario, sentimiento, Tobler]--> ia
servicios        --[consulta y persiste]--> modelos
servicios        --[lee configuracion, usa el motor]--> (raiz)
ia               --[lee las tablas que necesita]--> modelos
ia               --[usa servicios/avisos para emitir {codigo, parametros}]--> servicios
esquemas         --[reexpresa los modelos como contratos publicos]--> modelos
esquemas         --[serializa el dataclass Aviso de servicios/avisos]--> servicios
modelos          --[heredan de Base]--> (raiz) base_datos
utilidades       --[escriben en las tablas]--> modelos
utilidades       --[reutilizan la logica de negocio, no la duplican]--> servicios
utilidades       --[usan calendario y sentimiento en las cargas]--> ia
utilidades       --[abren sesion con FabricaDeSesiones]--> (raiz)
```

### Lo que este grafo demuestra, y conviene decir en el informe

- **`modelos/` no importa nada del proyecto salvo `base_datos`.** Es la capa más
  interna: no conoce servicios, ni rutas, ni IA.
- **`servicios/` y `ia/` no importan `rutas/`.** La dependencia va en un solo
  sentido: **no hay ciclos entre capas**.
- **`ia/` importa `servicios/`** únicamente para `servicios/avisos`, que es el
  emisor de `{codigo, parametros}` (ADR-013). Es una dependencia hacia una utilidad
  transversal, no hacia lógica de negocio.
- **`utilidades/` importa `servicios/`** a propósito: los guiones de carga
  reutilizan la validación y el cálculo en vez de duplicarlos, de modo que cargar
  el catálogo aplica exactamente las mismas reglas que el API.
- **267 de las 550 pruebas no necesitan PostgreSQL** — corregido: **296 de 550**,
  medido el 20 de septiembre de 2026. Es consecuencia directa de esta separación:
  `ia/` y los cálculos se prueban solos.

### Componentes externos al grafo

| Elemento | Dónde vive | Por qué está aparte |
|---|---|---|
| **11 migraciones Alembic** | `backend/alembic/versions/` | Se ejecutan con `alembic upgrade head`, no se importan desde la aplicación |
| **19 archivos de prueba** | `backend/pruebas/` | 550 pruebas |
| **Cuaderno de experimentos** | `backend/notebooks/` | La medición que sostiene ADR-004 y ADR-005 |

---

## Base de datos — 17 tablas del proyecto

Verificado con `information_schema.tables`: 21 tablas en el esquema `public`, de
las cuales **17 son del proyecto**, 1 es `alembic_version` y 3 son de PostGIS
(`spatial_ref_sys`, `geometry_columns`, `geography_columns`).

`afluencia_historica`, `cambio_de_estado`, `disponibilidad_servicio`,
`festividad`, `horario_atencion`, `itinerario`, `parada_itinerario`,
`preferencia_viaje`, `proveedor`, `recurso_turistico`, `registro_de_evidencia`,
`registro_validacion`, `servicio`, `solicitud_coordinacion`, `tarifa_transporte`,
`usuario`, `valoracion`.

### Volumen real en el momento de la extracción

| Tabla | Filas |
|---|---|
| `recurso_turistico` | 295 |
| `horario_atencion` | 1 456 (208 recursos distintos) |
| `afluencia_historica` | 414 (207 recursos, **0 con mes**: son totales anuales) |
| `proveedor` | 167 (162 reales + **5 de demostración**) |
| `festividad` | 69 (2026–2028) |
| `valoracion` | 5 |
| `itinerario` | 3 |
| `solicitud_coordinacion` | 1 |

> Los volúmenes de valoraciones, itinerarios y solicitudes son de demostración y
> **no son estadísticamente significativos**. El propio tablero lo avisa antes que
> los números.
