# RutaVivaMantaro

Plataforma web de turismo inteligente para la **Ruta del Valle del Mantaro**
(Junín, Perú). Reúne la oferta turística oficial de Huancayo, Concepción, Jauja
y Chupaca, registra las preferencias del visitante y construye un itinerario
con orden de visita, medio de transporte, tiempo y costo aproximado.

Proyecto del curso **Procesos de Software (ASUC01702, NRC 30173)** —
Universidad Continental, Huancayo. Ciclo 2026-20.

> **Estado actual: Fase 7 completada.** El catálogo tiene **295 recursos**
> importados del inventario oficial del MINCETUR, con un **79,32 % validado**.
> El visitante registra lo que quiere de su viaje —sin necesidad de cuenta—,
> recibe recomendaciones que **explican por qué** se le proponen, obtiene un
> itinerario de un día con mapa, horas y costo aproximado, coordina servicios
> con proveedores y valora la experiencia al terminar. Un asistente
> conversacional permite pedir todo eso hablando, sin cambiar de pantalla.

---

## 1. Qué necesitas instalado

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| Python | 3.11 | Backend |
| Node.js | 20 | Frontend |
| Docker Desktop | cualquiera reciente | Base de datos PostgreSQL + PostGIS |
| Git | cualquiera reciente | Control de versiones |
| Ollama | 0.3 o superior | Asistente conversacional (opcional: sin él, todo lo demás funciona) |

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

En **Git Bash sobre Windows** —ojo, es `Scripts`, no `bin`: Windows no crea
la carpeta `bin` ni cuando se usa una consola de tipo Unix—:

```bash
source .venv/Scripts/activate
```

En **Linux o macOS**:

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

### 2.6 Crear los usuarios de demostración

Crea una cuenta por cada rol del proyecto, para poder probar la aplicación sin
registrarlas a mano:

```bash
python -m app.utilidades.usuarios_semilla
```

| Correo | Rol | Contraseña |
|---|---|---|
| `visitante@rutavivamantaro.pe` | visitante | `RutaViva2026` |
| `proveedor@rutavivamantaro.pe` | proveedor | `RutaViva2026` |
| `operador@rutavivamantaro.pe` | operador | `RutaViva2026` |
| `gestor@rutavivamantaro.pe` | gestor | `RutaViva2026` |
| `administrador@rutavivamantaro.pe` | administrador | `RutaViva2026` |

**Son credenciales de desarrollo.** Están escritas aquí a propósito, para que
cualquiera del equipo pueda levantar el proyecto y entrar. El guion se niega a
ejecutarse si la variable `ENTORNO` del `.env` no dice `desarrollo`.

### 2.7 Crear los proveedores de demostración

Los servicios que se pueden coordinar —transporte, talleres, guías,
restaurantes— necesitan proveedores que los ofrezcan:

```bash
python -m app.utilidades.proveedores_semilla
```

**No son proveedores reales.** El proyecto no tiene convenios con nadie del
valle, así que todos llevan el sufijo «(demostración)» y teléfonos que empiezan
por `+51 900 000`, un rango que no corresponde a ningún número peruano.
Sirven para enseñar cómo funcionaría la coordinación, no para llamar.

### 2.8 Cargar el calendario festivo

Vuelca en la base las fiestas del valle. Las móviles —Semana Santa, Carnavales
y Corpus Christi— se **calculan** con el algoritmo de la Pascua, no se escriben
a mano:

```bash
python -m app.utilidades.cargar_calendario --desde 2026 --hasta 2028
```

### 2.9 Preparar el frontend

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

### 2.10 Instalar el asistente conversacional (opcional)

El asistente deja pedir las cosas hablando en vez de rellenando formularios.
**No añade ninguna capacidad**: todo lo que permite pedir se puede pedir
también por formulario. Si te lo saltas, la plataforma funciona entera; solo
verás un aviso en el panel del asistente diciendo que no está disponible.

Descarga Ollama de <https://ollama.com/download> e instálalo. En Windows, si
tienes `winget`:

```bash
winget install --id Ollama.Ollama
```

Después descarga el modelo. Son unos 4,4 GB, así que tarda:

```bash
ollama pull qwen2.5:7b-instruct
```

Comprueba que responde:

```bash
curl http://localhost:8000/api/asistente/estado
```

```json
{ "disponible": true, "modelo": "qwen2.5:7b-instruct", "motivo": null }
```

Si sale `"disponible": false`, el campo `motivo` dice qué falta: que Ollama no
esté arrancado, o que falte el modelo.

> **Sobre el rendimiento.** En un portátil sin GPU dedicada, cada respuesta
> tarda entre 25 y 40 segundos. Es normal: el modelo corre en la CPU. Se eligió
> `qwen2.5:7b-instruct` porque sabe llamar funciones, que es lo único que hace
> falta aquí; un modelo mayor no respondería mejor, solo más despacio.

---

## 3. Recorrido de demostración

Diez minutos para ver la plataforma entera. Cada paso corresponde a uno de los
incrementos.

### Paso 1 — El catálogo (Incremento 1)

Entra en **Explorar**. Son 295 recursos del inventario oficial del MINCETUR.
Filtra por provincia o categoría, y abre cualquiera para ver su ficha.

Fíjate en el distintivo de **validado**: 234 de los 295 pasaron la validación
—tienen coordenadas dentro del valle, nombre y categoría—. Los demás se
muestran marcados, no se ocultan.

### Paso 2 — Las preferencias y las recomendaciones (Incrementos 2 y 3)

Pulsa **Planificar**. Son seis pasos y **no hace falta cuenta**.

Prueba con: sale de `HUANCAYO`, 1 día, S/ 150, le interesan `artesania` y
`gastronomia`, se mueve en `transporte_publico`, ritmo `moderado`.

En los resultados, cada recomendación **explica por qué** se propone. Esa
explicación no es decorativa: es el requisito que impide que el sistema sea una
caja negra.

En la esquina verás la **afluencia esperada** del día que elijas. Prueba con un
domingo de febrero y con un martes de mayo: cambia.

### Paso 3 — El itinerario (Incremento 4)

Desde los resultados, **Armar itinerario**. Sale el orden de visita, el mapa, la
hora de llegada a cada parada, el tiempo de traslado y el costo aproximado.

Mira los **avisos de arriba**. Dicen cosas incómodas a propósito: que un tramo
se estimó en línea recta porque no hay carretera registrada cerca, que una
parada está a más de 3 500 m y conviene aclimatarse, o que el día quedó corto y
por qué.

Los precios llevan siempre **«aprox.»** y su fecha de referencia. No son tarifas
oficiales: no existe ninguna fuente publicada de tarifas para el valle, así que
se estiman con una fórmula documentada en `docs/decisiones/`.

### Paso 4 — Coordinar (Incremento 5)

Entra en **Coordinar**. Los proveedores están marcados como **demostración**
porque el proyecto no tiene convenios con nadie del valle: sus teléfonos no
corresponden a ningún número real.

Pide un servicio. Verás la solicitud con su estado. Entra con
`proveedor@rutavivamantaro.pe` para verla desde el otro lado y cambiarle el
estado: cada cambio queda registrado con quién y cuándo.

### Paso 5 — Valorar (Incremento 6)

Desde el itinerario, **Valorar**. Escribe un comentario de verdad, con matices.
El sistema detecta el sentimiento y los temas de los que habla.

Luego entra con `gestor@rutavivamantaro.pe` y abre el **Panel**, pestaña
**Evidencia**. Ahí está lo que pedía la brecha 7: la retroalimentación de vuelta
en el proceso, agrupada por tema y con su porcentaje de negativos, que es el
número que dice **dónde actuar**.

El tablero avisa por sí solo cuando hay pocas valoraciones para fiarse.

### Paso 6 — El asistente (Fase 7)

Pulsa el botón redondo de abajo a la derecha, en cualquier pantalla.

**La prueba que conviene enseñar:** pídele un lugar que no existe.

```
Quiero visitar el Palacio de la Cultura de Jauja, ¿cómo llego?
```

Consulta el catálogo, no lo encuentra y lo dice. No lo inventa, y tampoco
propone otro parecido de memoria.

Compáralo con uno que sí existe:

```
Busca el Convento de Ocopa
```

Debajo de cada respuesta aparece **qué funciones se ejecutaron** para
construirla. Es lo que hace la conversación auditable: si pone «consultó el
catálogo», esa respuesta salió de la base de datos.

---

## 4. Comprobar que todo funciona

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
igual: el asistente es opcional y no aporta ninguna capacidad exclusiva. Para
habilitarlo, vuelve al paso 2.10.

Comprueba también que las pruebas pasan:

```bash
cd backend && .venv/Scripts/python.exe -m pytest
```

```bash
cd frontend && npm run probar
```

---

## 5. Comandos de trabajo

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
| `python -m app.utilidades.usuarios_semilla` | Crea un usuario de demostración por cada rol |
| `python -m app.utilidades.cargar_calendario` | Carga las festividades del valle en la base de datos |
| `jupyter notebook notebooks/` | Abre los cuadernos de experimentación de los modelos |

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

## 6. Estructura del repositorio

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
│   └── pruebas/               pruebas automáticas (pytest)
├── frontend/
│   └── src/
│       ├── componentes/       piezas reutilizables de la interfaz
│       ├── paginas/           una por ruta
│       ├── servicios/         llamadas a la API
│       ├── hooks/             lógica de estado reutilizable
│       ├── utilidades/        funciones puras de formato
│       ├── i18n/              es.json y en.json
│       └── estilos/
├── docs/
│   ├── decisiones/            una nota por decisión de proceso
│   └── indicadores/           qué mide cada indicador y dónde se ve
├── docker-compose.yml
└── sonar-project.properties   preparado, no ejecutado (ver la sección 7.8)
```

---

## 7. Reglas del proyecto

### 7.1 Todo en español

Variables, funciones, archivos, carpetas, tablas, endpoints, comentarios y
mensajes de commit van en español. La única excepción son los nombres de
bibliotecas de terceros y las palabras reservadas del lenguaje — incluido el
prefijo `use` de los ganchos de React, explicado en
[esta nota de decisión](docs/decisiones/2026-08-28-prefijo-use-en-los-ganchos.md).

### 7.2 Cada modelo de IA tiene una alternativa por reglas

Toda funcionalidad que use un modelo puede desactivarse con una variable del
`.env` y seguir funcionando con reglas explícitas:

```
USAR_MODELO_RECOMENDACION=false
USAR_MODELO_AFLUENCIA=false
USAR_MODELO_SENTIMIENTO=false
```

Es el mecanismo de control de riesgo declarado en el documento académico: si un
modelo no supera su línea base en la etapa de pruebas, se entrega la
alternativa por reglas y el modelo vuelve al backlog.

Estado real de cada modelo, tras los experimentos del Incremento 3:

| Capa | Modelo | Estado | Motivo |
|---|---|---|---|
| Afinidad | TF-IDF + coseno | **Aceptado** | Las reglas dan 2-3 puntajes distintos y dejan decenas de empates; el modelo ordena de verdad |
| Afluencia | LightGBM | **Descartado por ahora** | No hay datos históricos del valle; se entregan las reglas de calendario |
| Sentimiento | pysentimiento | Pendiente (Fase 6) | — |

Los detalles y los números están en
[la nota de decisión](docs/decisiones/2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md)
y en el cuaderno `backend/notebooks/01_incremento3_afinidad_y_afluencia.ipynb`,
ejecutado y con sus salidas guardadas.

Cada respuesta de la API lleva un campo `generado_por` que dice si la produjo
el modelo o las reglas.

### 7.3 Cada recomendación explica por qué

Ninguna recomendación se muestra como un número a secas. Cada una indica qué
intereses cubre, qué términos pesaron en su puntaje y cuánta gente se espera
ese día, con el motivo. La respuesta de la API incluye además **lo que se
descartó y por qué**, y si el cálculo salió del modelo o de las reglas.

Es lo que cierra la brecha 2: *el análisis y la priorización recaían en el
visitante, sin criterios explícitos*.

### 7.4 El asistente conversacional no inventa datos

El modelo de Ollama solo llama funciones del backend y redacta la respuesta con
lo que esas funciones devuelven. Un lugar que no esté en el catálogo oficial no
puede aparecer en la respuesta.

### 7.5 No hace falta cuenta para usar la aplicación

El visitante completa el asistente de preferencias y obtiene su viaje **sin
registrarse**. La cuenta se ofrece al final, solo para guardarlo, y entonces
la preferencia que hizo como anónimo se asocia sola a la cuenta nueva. Ver
[la nota de decisión](docs/decisiones/2026-08-29-la-aplicacion-funciona-sin-cuenta.md).

Las contraseñas se guardan con **argon2id** y su sal aleatoria. Nunca se
almacenan ni se registran en claro.

### 7.6 El diseño visual viene de Stitch

La paleta, las tipografías y las formas salen del sistema de diseño
**«Mantaro Moderno»**, definido en Stitch junto con las 26 pantallas del
proyecto. El código copia esos valores; no los inventa. Cualquier cambio se
hace primero en Stitch. Ver
[la nota de decisión](docs/decisiones/2026-08-29-sistema-de-diseno-mantaro-moderno.md).

### 7.7 Honestidad con los datos

Las tarifas de transporte de Huancayo cambian y no existe una tarifa oficial
única. Se guardan siempre con precio mínimo, precio máximo, fecha de referencia
y fuente, y se muestran con la palabra «aprox.» y la fecha visible.

---

## 8. Fuente de los datos

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

## 9. Equipo

| Integrante | Rol |
|---|---|
| Reyes Cordero, Ítalo Eduardo | Ingeniero de Desarrollo y Prototipado |
| Surihuaqui Hurtado, Jackelin | Ingeniera de Proceso |
| Huaman Lazaro, Jefferson | Ingeniero de Calidad y Mejora |

Docente: Guevara Jimenez, Jorge Alfredo.
