# RutaVivaMantaro

Plataforma web de turismo inteligente para la **Ruta del Valle del Mantaro**
(Junín, Perú). Reúne la oferta turística oficial de Huancayo, Concepción, Jauja
y Chupaca, registra las preferencias del visitante y construye un itinerario
con orden de visita, medio de transporte, tiempo y costo aproximado.

Proyecto del curso **Procesos de Software (ASUC01702, NRC 30173)** —
Universidad Continental, Huancayo. Ciclo 2026-20.

> **Estado actual: Fase 1 completada.** El catálogo tiene **295 recursos**
> importados del inventario oficial del MINCETUR, con un **79,32 % validado**.
> El registro de preferencias del visitante llega en la Fase 2.

---

## 1. Qué necesitas instalado

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| Python | 3.11 | Backend |
| Node.js | 20 | Frontend |
| Docker Desktop | cualquiera reciente | Base de datos PostgreSQL + PostGIS |
| Git | cualquiera reciente | Control de versiones |
| Ollama | 0.3 o superior | Asistente conversacional (solo desde la Fase 7) |

Comprueba lo que tienes con:

```bash
python --version && node --version && docker --version && git --version
```

---

## 2. Instalación paso a paso

### 2.1 Clonar el repositorio

```bash
git clone https://github.com/75220834-cloud/PROYECTO-PROCESOS-DE-SOFTWARE-.git
```

### 2.2 Crear el archivo de configuración

El archivo `.env` guarda las contraseñas y no se sube al repositorio. Se crea a
partir de la plantilla incluida:

```bash
cp .env.ejemplo .env
```

Ábrelo y cambia dos valores:

- `POSTGRES_CONTRASENA` — cualquier contraseña que elijas.
- `CLAVE_SECRETA` — genera una aleatoria con el comando de abajo y pégala.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2.3 Levantar la base de datos

Arranca PostgreSQL 16 con la extensión PostGIS 3.4 dentro de un contenedor. La
primera vez descarga la imagen (unos 400 MB) y tarda un par de minutos.

```bash
docker compose up -d
```

Comprueba que PostGIS quedó instalado:

```bash
docker exec rutaviva_postgres psql -U rutaviva -d rutavivamantaro -c "SELECT postgis_version();"
```

Debe responder `3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`.

### 2.4 Preparar el backend

Un *entorno virtual* es una carpeta con su propia copia de Python y sus
paquetes, aislada del resto del sistema.

```bash
cd backend
```

```bash
python -m venv .venv
```

Actívalo. En **Windows PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

En **Git Bash o Linux**:

```bash
source .venv/bin/activate
```

Instala las dependencias:

```bash
pip install -e ".[desarrollo]"
```

Levanta la API:

```bash
uvicorn app.main:aplicacion --reload
```

Abre <http://localhost:8000/docs> para ver la documentación interactiva de
todos los endpoints, que FastAPI genera sola a partir del código.

### 2.5 Cargar el catálogo

Descarga el inventario del MINCETUR desde el navegador y colócalo en
`backend/datos/crudos/`:

```
https://www.mincetur.gob.pe/Datos_abiertos/DGET/Inventario_recursos_turisticos.csv
```

Después, con el entorno virtual activado y la base de datos levantada, aplica
las migraciones y carga los datos:

```bash
alembic upgrade head
```

```bash
python -m app.utilidades.cargar_catalogo
```

El guion importa los recursos de las cuatro provincias de la ruta, ejecuta la
validación y muestra el indicador del Incremento 1. Debe terminar con algo
parecido a esto:

```
  Filas de las 4 provincias      : 295
  Recursos insertados            : 295
  Sin coordenadas en la fuente   : 61
  Columnas lat/lon               : INTERCAMBIADAS en la fuente, corregidas
  PORCENTAJE VALIDADO            : 79.32 %
```

Se puede ejecutar las veces que haga falta: identifica cada recurso por su
código del MINCETUR, así que actualiza en vez de duplicar.

### 2.6 Preparar el frontend

En otra terminal:

```bash
cd frontend
```

```bash
npm install
```

```bash
npm run dev
```

Abre <http://localhost:5173>.

---

## 3. Comprobar que todo funciona

Con el backend levantado:

```bash
curl http://localhost:8000/api/salud
```

Devuelve el estado de los tres componentes de la plataforma:

```json
{
  "estado_general": "operativo",
  "api": { "estado": "operativo", "detalle": "FastAPI version 0.1.0" },
  "base_datos": { "estado": "operativo", "detalle": "PostGIS 3.4 USE_GEOS=1" },
  "ollama": { "estado": "operativo", "detalle": "Modelo qwen2.5:7b-instruct listo" }
}
```

Si `ollama` aparece como `no_disponible`, el resto de la plataforma funciona
igual: el asistente conversacional es opcional hasta la Fase 7. Para
habilitarlo, arranca Ollama y descarga el modelo:

```bash
ollama pull qwen2.5:7b-instruct
```

---

## 4. Comandos de trabajo

### Backend — desde `backend/`, con el entorno virtual activado

| Comando | Qué hace |
|---|---|
| `uvicorn app.main:aplicacion --reload` | Levanta la API y la recarga al guardar |
| `pytest` | Ejecuta las pruebas y muestra la cobertura |
| `ruff check app tests` | Revisa errores y estilo |
| `black app tests` | Formatea el código |
| `alembic upgrade head` | Aplica las migraciones pendientes a la base de datos |
| `alembic revision --autogenerate -m "..."` | Genera una migración nueva a partir de los modelos |
| `python -m app.utilidades.cargar_catalogo` | Importa el inventario del MINCETUR y valida el catálogo |

### Frontend — desde `frontend/`

| Comando | Qué hace |
|---|---|
| `npm run dev` | Levanta el servidor de desarrollo |
| `npm run probar` | Ejecuta las pruebas |
| `npm run revisar` | Pasa ESLint |
| `npm run formatear` | Formatea con Prettier |
| `npm run construir` | Compila la versión de producción |

### Base de datos

| Comando | Qué hace |
|---|---|
| `docker compose up -d` | Levanta PostgreSQL |
| `docker compose down` | Lo apaga **conservando** los datos |
| `docker compose down -v` | Lo apaga **borrando** los datos |

---

## 5. Estructura del repositorio

```
PROYECTO-PROCESOS-DE-SOFTWARE-/
├── backend/
│   ├── app/
│   │   ├── main.py            punto de entrada de FastAPI
│   │   ├── configuracion.py   variables de entorno e interruptores de modelo
│   │   ├── base_datos.py      conexión y sesiones de SQLAlchemy
│   │   ├── modelos/           tablas (SQLAlchemy)
│   │   ├── esquemas/          entrada y salida (Pydantic)
│   │   ├── rutas/             endpoints de la API
│   │   ├── servicios/         lógica de negocio
│   │   ├── ia/                modelos y sus alternativas por reglas
│   │   └── utilidades/
│   ├── datos/                 CSV fuente y datos derivados (no versionados)
│   ├── notebooks/             cuadernos de experimentación
│   ├── scripts_sql/           extensiones que crea Docker al arrancar
│   └── tests/
├── frontend/
│   └── src/
│       ├── componentes/       piezas reutilizables de la interfaz
│       ├── paginas/           una por ruta
│       ├── servicios/         llamadas a la API
│       ├── hooks/             lógica de estado reutilizable
│       ├── i18n/              es.json y en.json
│       └── estilos/
├── docs/
│   ├── decisiones/            una nota por decisión de proceso
│   └── indicadores/           qué mide cada indicador y dónde se ve
└── docker-compose.yml
```

---

## 6. Reglas del proyecto

### 6.1 Todo en español

Variables, funciones, archivos, carpetas, tablas, endpoints, comentarios y
mensajes de commit van en español. La única excepción son los nombres de
bibliotecas de terceros y las palabras reservadas del lenguaje — incluido el
prefijo `use` de los ganchos de React, explicado en
[esta nota de decisión](docs/decisiones/2026-08-28-prefijo-use-en-los-ganchos.md).

### 6.2 Cada modelo de IA tiene una alternativa por reglas

Toda funcionalidad que use un modelo puede desactivarse con una variable del
`.env` y seguir funcionando con reglas explícitas:

```
USAR_MODELO_RECOMENDACION=false
USAR_MODELO_AFLUENCIA=false
USAR_MODELO_SENTIMIENTO=false
```

Es el mecanismo de control de riesgo declarado en el documento académico: si un
modelo no supera su línea base en la etapa de pruebas, se entrega la
alternativa por reglas y el modelo vuelve al backlog. Los itinerarios guardan
en el campo `generado_por` si los produjo el modelo o las reglas.

### 6.3 El asistente conversacional no inventa datos

El modelo de Ollama solo llama funciones del backend y redacta la respuesta con
lo que esas funciones devuelven. Un lugar que no esté en el catálogo oficial no
puede aparecer en la respuesta.

### 6.4 El diseño visual viene de Stitch

La paleta, las tipografías y las formas salen del sistema de diseño
**«Mantaro Moderno»**, definido en Stitch junto con las 26 pantallas del
proyecto. El código copia esos valores; no los inventa. Cualquier cambio se
hace primero en Stitch. Ver
[la nota de decisión](docs/decisiones/2026-08-29-sistema-de-diseno-mantaro-moderno.md).

### 6.5 Honestidad con los datos

Las tarifas de transporte de Huancayo cambian y no existe una tarifa oficial
única. Se guardan siempre con precio mínimo, precio máximo, fecha de referencia
y fuente, y se muestran con la palabra «aprox.» y la fecha visible.

---

## 7. Fuente de los datos

El catálogo proviene del **Inventario Nacional de Recursos Turísticos** del
MINCETUR (Dirección General de Estrategia Turística):

```
https://www.mincetur.gob.pe/Datos_abiertos/DGET/Inventario_recursos_turisticos.csv
```

Se filtra por `REGIÓN = JUNIN` y las provincias de Huancayo, Concepción, Jauja
y Chupaca. La columna `FECHA_DE_CORTE` sostiene el indicador del Incremento 1:
*porcentaje de oferta con información validada y vigente*.

El archivo se descarga aparte y se coloca en `backend/datos/crudos/`, que no se
versiona por su tamaño.

---

## 8. Equipo

| Integrante | Rol |
|---|---|
| Reyes Cordero, Ítalo Eduardo | Ingeniero de Desarrollo y Prototipado |
| Surihuaqui Hurtado, Jackelin | Ingeniera de Proceso |
| Huaman Lazaro, Jefferson | Ingeniero de Calidad y Mejora |

Docente: Guevara Jimenez, Jorge Alfredo.
