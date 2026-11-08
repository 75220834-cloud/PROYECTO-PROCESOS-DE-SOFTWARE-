# ADR-017 — El núcleo de cálculo se separa en dominio, puertos y adaptadores

| | |
|---|---|
| **Estado** | Aceptada, con alcance parcial declarado |
| **Fecha** | 8 de noviembre de 2026 |
| **Incremento** | Transversal — no añade funcionalidad |
| **Atributo de calidad principal** | **Mantenibilidad** (modificabilidad y capacidad de prueba) |
| **Atributos secundarios** | Analizabilidad (la dependencia se puede comprobar con una máquina) |
| **Interruptor** | Ninguno. No es una decisión de modelo |
| **Lo verifica** | `backend/pruebas/test_dominio_sin_frameworks.py` |

---

## Contexto

La asignatura evalúa, con 6 puntos sobre 20:

> Estructura en GitHub la Arquitectura Hexagonal (`/src/domain/`, `/src/ports/`,
> `/src/adapters/`) demostrando cero acoplamiento de frameworks en el Dominio y
> tags de versión.

La versión anterior sacó 2 de 6, y el motivo era correcto: **la arquitectura no
era hexagonal**. Era un monolito modular en capas. El informe académico lo
declaró así en vez de fingir lo contrario, pero declararlo no lo arregla.

### Lo que se midió antes de mover nada

Sobre el commit `d7126b9`, medido y no estimado:

- **Cero** importaciones de FastAPI, Pydantic o Alembic en `servicios/` e `ia/`.
  La separación entre la entrada y el cálculo ya existía de hecho, aunque sin
  nombre: los enrutadores nunca se habían filtrado hacia abajo.
- **Nueve** módulos de lógica importaban SQLAlchemy y los modelos del ORM.
- **Cuarenta y siete** firmas recibían `sesion: Session`.
- **Tres** módulos (`red_vial`, `afinidad`, `sentimiento`) no importaban
  SQLAlchemy en absoluto: su única atadura eran enumeraciones.
- **Nueve** `StrEnum` de dominio puro vivían dentro de archivos de SQLAlchemy.

El diagnóstico completo está en
[`docs/plan-migracion-hexagonal.md`](../plan-migracion-hexagonal.md).

## Decisión

Se adopta la estructura hexagonal con las tres carpetas que pide el criterio, y
**se migra primero el núcleo de cálculo**, no las nueve dependencias de base de
datos.

### Dónde va `src/`, y por qué no en la raíz

El criterio escribe `/src/domain/`, lo que sugiere la raíz del repositorio. Se
decidió `backend/src/domain/` por una razón de despliegue, no de gusto: en
Render el *Root Directory* del servicio es `backend`. Un `src/` colgando de la
raíz quedaría fuera de lo que Render copia y **el API dejaría de arrancar**.

El `README.md` de la raíz lleva el árbol visible para que las tres carpetas se
vean sin navegar.

### Qué es dominio y qué no

En `src/domain/` quedan los módulos que calculan: el ruteo peatonal sobre la red
vial, la afinidad por TF-IDF, el análisis de sentimiento, los avisos, la
temporada, el tiempo de recorrido y los objetos de valor.

En `src/adapters/outbound/` queda lo que toca el mundo: la lectura del modelo de
elevación de Copernicus y la descarga, el guardado y la recuperación del grafo
vial.

### Por qué OR-Tools y scikit-learn SÍ pueden aparecer en el dominio

Es la decisión que más se va a preguntar en la defensa, así que queda escrita.

OR-Tools, scikit-learn, NumPy, OSMnx, NetworkX y pysentimiento **son librerías
de cálculo, no de infraestructura**. No hablan con la red, ni con el disco, ni
con la base de datos. Esconderlas detrás de un puerto no desacoplaría nada
real: añadiría una capa de indirección que hay que mantener y que no permite
sustituir nada que alguien vaya a querer sustituir.

El acoplamiento que importa es el que ata el cálculo a **cómo se guardan o se
entregan los datos**. Eso sí está prohibido, y lo comprueba una máquina.

## Alternativas consideradas

**Renombrar las carpetas y no mover nada.** Llamar `domain/` a `servicios/`
habría cumplido la letra del criterio en una tarde. Se descarta: el criterio
pide «demostrando cero acoplamiento», y `servicios/` importa SQLAlchemy en nueve
módulos. Sería declarar hexagonal lo que no lo es, que es exactamente el defecto
que esta migración viene a corregir.

**Crear las tres carpetas vacías o casi vacías.** Se descarta por lo mismo. El
dominio migrado son **2 275 líneas en 13 módulos**, medidas al terminar.

**Migrar las nueve dependencias de base de datos en la misma entrega.** Son 47
firmas que invertir y dos módulos con PostGIS incrustado dentro de la consulta
SQL (`recomendador.py` y `validacion_catalogo.py` hacen `cast(..., Geometry)`).
Se descarta por riesgo: el sistema está desplegado y la entrega es esta semana.
Queda declarado abajo como trabajo pendiente, con su alcance.

## Consecuencias

### A favor

- «Cero acoplamiento de frameworks en el Dominio» pasa de ser una afirmación de
  un informe a un hecho que se comprueba en cada envío al repositorio.
- La prueba de `construir_y_guardar` mejoró al migrarse: antes parcheaba el
  módulo de elevación por su ruta de importación; ahora recibe su propia
  implementación del puerto por parámetro. La prueba ya no tiene que saber de
  qué archivo salía la implementación real.
- Los objetos de valor dejaron de depender del ORM. `Interes`, `Sentimiento` o
  `ModoTransporte` se pueden usar sin levantar SQLAlchemy.

### En contra, y declarado

- **La migración está incompleta.** `src/servicios/`, `src/rutas/`,
  `src/modelos/` y `src/esquemas/` siguen existiendo con su estructura anterior.
  No son todavía adaptadores: son las capas de antes, que esperan las fases 3 a
  6 del plan.
- **Hay un solo puerto declarado.** `FuenteDeAltitud` es un puerto de verdad y
  está en uso, pero los repositorios de los agregados —que son la mayor parte
  del trabajo— no existen aún.
- **Dos nombres de carpeta están en inglés** (`domain`, `ports`, `adapters`) en
  un proyecto cuya regla es nombrarlo todo en español. Se acepta la excepción
  porque el criterio de evaluación nombra esas tres carpetas literalmente.

### Lo que falta, con su alcance

| Fase | Qué | Tamaño |
|---|---|---|
| 3 | Puertos de repositorio y adaptadores de persistencia | 9 módulos, 47 firmas |
| 4 | Los enrutadores a `adapters/inbound/http/` | 9 + 9 archivos |
| 5 | El cliente de Ollama detrás de un puerto | 1 módulo |
| 6 | Raíz de composición con inyección por `Depends` | 1 archivo |

## Cómo se comprueba

`backend/pruebas/test_dominio_sin_frameworks.py` recorre todos los módulos de
`src/domain/` y falla si alguno importa FastAPI, Starlette, SQLAlchemy,
GeoAlchemy2, psycopg, Alembic, Pydantic o un cliente HTTP; y falla también si
alguno importa hacia afuera (`src.adapters`, `src.modelos`, `src.rutas`,
`src.esquemas`, `src.servicios`, `src.ia`, `src.base_datos`).

Lee los imports con el módulo `ast` y no con búsqueda de texto. La diferencia
importa en los dos sentidos: un comentario que mencione SQLAlchemy no la engaña,
y un import real no se le escapa aunque esté dentro de una función.

Incluye una prueba que comprueba que **el dominio no está vacío**. Sin ella,
borrar la carpeta entera dejaría la suite en verde y el criterio «cero
acoplamiento» se cumpliría por no tener nada que acoplar.

Tiene un paso con nombre propio en la integración continua, además de correr
dentro de la suite, para que el registro diga en una línea si la arquitectura
sigue siendo cierta.
