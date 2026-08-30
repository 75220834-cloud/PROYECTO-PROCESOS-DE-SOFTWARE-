# 01 — Visión y contexto

**Qué explica este archivo:** qué es RutaVivaMantaro, para qué curso se hizo,
qué problema real ataca, las siete brechas del análisis y los seis incrementos
que las cierran. Es el **porqué** del que cuelga todo lo demás.

---

## Qué es

Una plataforma web de turismo inteligente para la **Ruta del Valle del
Mantaro**, en Junín, Perú. Reúne la oferta turística oficial de cuatro
provincias —Huancayo, Concepción, Jauja y Chupaca—, registra lo que el
visitante quiere de su viaje y le construye un itinerario con orden de visita,
medio de transporte, tiempo y costo aproximado.

| | |
|---|---|
| **Curso** | Procesos de Software (ASUC01702, NRC 30173) |
| **Institución** | Universidad Continental, Huancayo |
| **Ciclo** | 2026-20 |
| **Repositorio** | `https://github.com/75220834-cloud/PROYECTO-PROCESOS-DE-SOFTWARE-` |

---

## El problema, en una frase

Planificar un viaje por el Valle del Mantaro obliga hoy al visitante a hacer
de analista: buscar qué hay en fuentes dispersas, decidir el orden sin saber
distancias ni costos, y llamar por teléfono a cada proveedor para averiguar si
puede atenderle. **El proceso existe, pero recae entero sobre él.**

---

## Las 7 brechas del análisis

Son el punto de partida. Cada una nombra algo que el proceso actual **no
hace**, y cada incremento del software existe para cerrar una o varias.

| # | Brecha | La cierra el incremento |
|---|---|---|
| 1 | No existe una fuente integrada, oficial y actualizada de la oferta de la ruta | 1 |
| 2 | El análisis y la priorización recaen en el visitante, sin criterios explícitos | 3 |
| 3 | Las preferencias del visitante no se registran ni se usan sistemáticamente | 2 y 3 |
| 4 | El proceso no incorpora la distribución geográfica ni el tiempo y costo de desplazamiento | 4 |
| 5 | La capacidad y condiciones del proveedor no son verificables al decidir | 5 |
| 6 | No existe punto único de coordinación ni registro de lo acordado | 5 |
| 7 | La retroalimentación no retorna estructurada al proceso ni al gestor | 6 |

> **La brecha 4 es nueva** respecto de la primera versión entregada de la
> Guía 1. Se añadió porque el proyecto incorpora ruteo geoespacial, y sin ella
> el software no trazaba con el análisis. Es un dato que conviene tener a mano:
> demuestra que el análisis se corrigió al chocar con la implementación, que es
> lo que se espera de un proceso iterativo.

---

## Los 6 incrementos

| # | Sprints | Qué construye | Brecha | Indicador |
|---|---|---|---|---|
| 1 | 1–2 | Catálogo único validado de la oferta | 1 | % de oferta con información validada y vigente |
| 2 | 3–4 | Registro de preferencias del visitante | 3 | Preferencias que llegan a itinerario |
| 3 | 5–7 | **Recomendación inteligente + predicción de afluencia** | 2 y 3 | % de recomendaciones sin error |
| 4 | 8–10 | **Ruteo geoespacial multimodal** | 4 | Itinerarios viables y trazables |
| 5 | 11–12 | Canal único de coordinación y disponibilidad | 5 y 6 | N.º de canales para confirmar un servicio |
| 6 | 13–14 | **Valoración de cierre analizada + evidencia** | 7 | % de experiencias con valoración registrada |

**Dependencias reales:** el 2 necesita el 1 · el 3 necesita el 1 y el 2 · el 4
necesita que el 1 esté georreferenciado.

Los detalles de cada uno —qué código, qué pruebas, qué endpoints— están en
[09-los-seis-incrementos.md](09-los-seis-incrementos.md).

---

## El modelo de proceso, y el argumento que lo sostiene

**Desarrollo iterativo e incremental, gestionado con Scrum, con Agile DevOps,
Continuous Discovery y DataOps sobre el catálogo y los modelos. MLOps diferido
y condicionado.**

Matriz de decisión ponderada (sobre 5): tradicional **1,92** · Scrum solo
**3,88** · **compuesta 4,96**.

Comparación de 7 modelos (sobre 30): Cascada 7 · Incremental 18 · Kanban 19 ·
Espiral 21 · DataOps/MLOps 22 · DevOps 24 · Scrum 26.

### El argumento sobre MLOps — es el eje del trabajo

> **Incorporar modelos de IA no es lo mismo que incorporar MLOps.**
>
> Los modelos se incorporan desde el Incremento 3: se entrenan **una vez** con
> fuentes externas estables —inventario del MINCETUR, series públicas de
> visitantes, red vial abierta— y su evaluación cabe dentro del sprint. No
> necesitan histórico de usuarios propio.
>
> MLOps gobierna el **reentrenamiento continuo** de modelos que aprenden de
> datos que el propio sistema genera. Eso aparece cuando el Incremento 6
> acumule valoraciones propias. Antes de eso, MLOps sería infraestructura sin
> datos que la justifiquen.

**Esto no se contradice nunca.** Si en el futuro alguien propone MLOps desde el
sprint 1, está rompiendo la coherencia de los dos documentos entregados.

La tabla `valoracion` **es** esos datos propios. Que ahora existan no significa
que haya que hacer MLOps: significa que a partir de aquí empieza a haber un
motivo para plantearlo, que es exactamente lo que sostienen los documentos.

---

## Las reglas que gobiernan el proyecto

No son estilo: son restricciones que se han cumplido en cada commit y que hay
que poder defender.

| Regla | Qué significa |
|---|---|
| **Todo en español** | Variables, funciones, archivos, tablas, columnas, endpoints, comentarios, mensajes de commit. Solo se exceptúan los nombres de bibliotecas de terceros y las palabras reservadas del lenguaje. |
| **Regla de oro de la IA** | Toda funcionalidad con modelo tiene una **alternativa por reglas explícitas**, conmutable con una variable del `.env`. Ver [07](07-inteligencia-artificial.md). |
| **El asistente nunca genera datos** | Solo llama a funciones del backend y redacta con lo que devuelven. Ver [08](08-asistente-conversacional.md). |
| **Honestidad con los datos** | Todo dato estimado se marca como tal, con su fuente y su fecha. Lo que la fuente no publica se queda vacío y se dice. Ver [06](06-fuentes-de-datos.md). |
| **Pruebas desde la fase 1** | Una fase no está hecha si sus pruebas no pasan. Ver [12](12-pruebas-y-calidad.md). |
| **Un commit por tarea** | Conventional Commits en español, con la brecha entre corchetes. Todo a `main`, sin ramas. |

### Lo que el proyecto decidió NO hacer

- No inventar atractivos, tarifas, horarios ni estadísticas.
- No usar servicios de nube de pago.
- No implementar MLOps.
- No implementar realidad aumentada.
- No convertir a microservicios.

---

## Estado actual

| | |
|---|---|
| Fases completadas | **8 de 8** (0 a 7) |
| Commits | 98, todos en `main` |
| Pruebas | **549 backend** (73 % cobertura) + **148 frontend** |
| Endpoints | 43, todos documentados en `/docs` |
| Idiomas | Español e inglés, 581 claves simétricas |

---

## Relacionado

- [02 — Arquitectura](02-arquitectura.md)
- [09 — Los seis incrementos](09-los-seis-incrementos.md)
- [16 — Pendientes y limitaciones](16-pendientes-y-limitaciones.md)
- `docs/decisiones/2026-08-29-la-aplicacion-funciona-sin-cuenta.md`
