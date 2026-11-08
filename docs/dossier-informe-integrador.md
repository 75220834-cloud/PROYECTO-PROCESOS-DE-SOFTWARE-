# Dossier de datos para el Informe Académico Integrador (S12)

**Para qué es este archivo:** es la fuente de datos verificados que necesita
quien redacte el *Informe Académico Integrador del Proyecto de Asignatura*
(Semana 12, 20 puntos). Cada cifra de aquí está medida, con su fecha y con el
comando que la produce.

**Fecha de corte de todas las mediciones:** 6 de noviembre de 2026.
**Estado del repositorio:** rama `main`, commit `d7126b9`, 125 commits.

---

## 0. LO PRIMERO: siete datos de la plantilla que son de relleno

La plantilla `S12-PSW-INFORME ACADÉMICO INTEGRADOR` viene rellena con un
proyecto de ejemplo (sensores, telemetría, alertas georreferenciadas). **Nada
de eso es este proyecto.** Si se copia, el informe describe un sistema que no
existe. Estos siete son los que más fácil se cuelan:

| En la plantilla | La realidad de RutaVivaMantaro |
|---|---|
| Colores `#1E3A8A` azul, `#059669` verde, `#DC2626` rojo | **Terracota `#a23919`**, verde valle `#27695c`, ocre `#745800`, error `#ba1a1a`. Sistema «Mantaro Moderno». Ver §8.1 |
| Contraste «7.1:1» | **Medido: entre 6,13:1 y 16,32:1** según el par. Ver §8.2 con los 11 pares |
| «Cifrado AES-256 en reposo» | **Falso en el código del proyecto.** Lo que hay es Argon2id para contraseñas y el cifrado en reposo que da Supabase por su cuenta. Ver §8.3 |
| 4 integrantes | **Son 3.** Ver §1 |
| HU-01 a HU-07 de sensores y alertas push | **Son 6 HU** y son de turismo. Ver §6 |
| Arquitectura Hexagonal `/src/domain`, `/src/ports`, `/src/adapters` | **No existe.** Es un monolito por capas. Ver §7.2, que es la sección más importante de este dossier |
| «Cobertura ≥ 80 % del núcleo de dominio» en el DoD | La cobertura real es **96,27 %** del backend, y el umbral que se exige en CI es **95 %**. Ver §5.2 |

---

## 1. Portada

| Campo | Valor |
|---|---|
| Asignatura | Procesos de Software — ASUC01702 |
| NRC / Sección | **30173** |
| Nivel / Ciclo | Noveno ciclo (IX), electivo de especialidad |
| Periodo académico | 2026-20 |
| Proyecto | **RutaVivaMantaro** — Plataforma de turismo inteligente para la Ruta del Valle del Mantaro |
| Institución | Universidad Continental, Huancayo |

### Integrantes (son tres, no cuatro)

| Apellidos y nombres | Código | Rol |
|---|---|---|
| **Reyes Cordero, Ítalo Eduardo** | 75220834 | Ingeniero de Desarrollo y Prototipado |
| **Surichaqui Hurtado, Jackelin** | 70765067 | Ingeniera de Proceso |
| **Huaman Lazaro, Jefferson** | 77812516 | Ingeniero |

> **Atención al apellido: es SURICHAQUI.** Está mal escrito en entregas
> anteriores y en el nombre de algún archivo. Corregirlo aquí.

La plantilla pide cuatro roles (Leader/Architect, Process Analyst & QA Lead,
Backend & Data Engineer, Frontend & Mobile Developer). Con tres integrantes hay
que repartir cuatro sombreros o declarar tres. **Decir que son tres es lo
correcto**; inventar un cuarto integrante es falsificar la autoría.

---

## 2. EJE 1 — Diagnóstico AS-IS / TO-BE

### 2.1 El problema, en una frase

> Planificar un viaje por el Valle del Mantaro obliga hoy al visitante a hacer
> de analista: buscar qué hay en fuentes dispersas, decidir el orden sin saber
> distancias ni costos, y llamar por teléfono a cada proveedor para averiguar
> si puede atenderle. **El proceso existe, pero recae entero sobre él.**

Ámbito: cuatro provincias de Junín — Huancayo, Concepción, Jauja y Chupaca.

### 2.2 Actores y necesidades (Matriz 3.1.1)

| Actor | Necesidad operativa | Decisión que debe tomar |
|---|---|---|
| **Visitante** (con o sin cuenta) | Saber qué hay, qué le conviene y cuánto cuesta moverse, sin llamar a nadie | Qué visitar, en qué orden y qué día |
| **Prestador de servicios** (proveedor) | Que su capacidad y sus horarios sean consultables sin atender llamadas | Aceptar, contraproponer o rechazar una solicitud |
| **Gestor turístico** (municipal / regional) | Retroalimentación agregada por tema y por recurso, no un listado de comentarios | Dónde intervenir primero |
| **Operador de la plataforma** | Visión completa de las solicitudes para desatascarlas | Reasignar o mediar en una coordinación detenida |

### 2.3 Las 7 brechas (Matriz 3.1.2 — AS-IS vs TO-BE)

Esta es la matriz real del proyecto. **La brecha 4 se añadió después** de la
primera entrega de la Guía 1, al chocar el análisis con la implementación del
ruteo: conviene decirlo, porque demuestra proceso iterativo de verdad.

| # | AS-IS (brecha / problema) | Consecuencia | TO-BE (proceso propuesto) | Incremento |
|---|---|---|---|---|
| 1 | No existe una fuente integrada, oficial y actualizada de la oferta de la ruta | El visitante busca en fuentes dispersas y desactualizadas | Catálogo único importado del Inventario Nacional del MINCETUR, con validación automática | 1 |
| 2 | El análisis y la priorización recaen en el visitante, sin criterios explícitos | Decisiones por intuición; el visitante no sabe por qué elige | Recomendador TF-IDF **que explica** qué términos pesaron | 3 |
| 3 | Las preferencias del visitante no se registran ni se usan sistemáticamente | Cada consulta empieza de cero | Asistente de preferencias en 6 pasos, **sin exigir cuenta** | 2 y 3 |
| 4 | El proceso no incorpora la distribución geográfica ni el tiempo y costo de desplazamiento | Itinerarios imposibles de cumplir en un día | Ruteo multimodal sobre red vial real, con desnivel y costo | 4 |
| 5 | La capacidad y condiciones del proveedor no son verificables al decidir | Hay que llamar para saber si atienden a 12 personas un sábado | Endpoint de disponibilidad que responde **antes de enviar nada** y da **todos** los motivos | 5 |
| 6 | No existe punto único de coordinación ni registro de lo acordado | Lo acordado se pierde entre llamadas y WhatsApp | Canal único con estados y tabla `cambio_de_estado` que registra quién y cuándo | 5 |
| 7 | La retroalimentación no retorna estructurada al proceso ni al gestor | El gestor no sabe dónde intervenir | Valoración con análisis de sentimiento y tablero agregado por tema | 6 |

### 2.4 Sistema de indicadores (los seis reales, con su letra pequeña)

**Regla que gobierna este tablero:** *un número sin decir qué NO dice es peor
que no tener número.* Los seis salen de `GET /api/indicadores/tablero`.

| # | Indicador | Valor medido | Lo que NO dice |
|---|---|---|---|
| 1 | Oferta validada y vigente | **79,32 %** (234 de 295) | «Validado» = pasa las comprobaciones automáticas de coordenadas, provincia y vigencia. **No** que alguien lo haya comprobado en el terreno |
| 2 | Preferencias que llegan a itinerario | — | **Sustituye** al «tiempo entre preferencia y confirmación» del plan: sin uso real no hay tiempos que medir |
| 3 | Recomendaciones sin error | **100 %** | Es 100 % **por construcción** (los filtros duros se aplican antes de puntuar). No mide si son las que la persona habría elegido |
| 4 | Itinerarios viables y trazables | **4 de 4 perfiles**; peor caso 6,52 s de 10 s | **Sustituye** al «error medio entre tiempo estimado y real»: nadie ha cronometrado traslados en campo |
| 5 | Canales para confirmar un servicio | **1** (antes 3 o más) | Las «horas medias hasta confirmar» **no significan nada**: los proveedores son de demostración |
| 6 | Experiencias con valoración | **100 %** | No dice que la gente esté contenta, ni que las valoraciones sean representativas, ni que el sentimiento detectado sea correcto (12 de 14 frases) |

> **Aviso sobre volúmenes, que hay que escribir en el informe:** con 5
> valoraciones, 3 itinerarios y 1 solicitud, **casi nada es estadísticamente
> sólido**. Si preguntan si es significativo, la respuesta honesta es **no**.
> El propio tablero lo dice antes de los números.

---

## 3. EJE 2 — Tailoring del ciclo de vida

### 3.1 El modelo elegido

> **Desarrollo iterativo e incremental, gestionado con Scrum, con prácticas
> Agile DevOps, Continuous Discovery y DataOps sobre el catálogo y los
> modelos. MLOps diferido y condicionado.**

### 3.2 Matriz de decisión ponderada (datos reales del proyecto)

| Alternativa | Puntaje (sobre 5) |
|---|---|
| Enfoque tradicional (Cascada) | **1,92** |
| Scrum solo | **3,88** |
| **Compuesta (la elegida)** | **4,96** |

Comparación de 7 modelos (sobre 30): Cascada **7** · Incremental **18** ·
Kanban **19** · Espiral **21** · DataOps/MLOps **22** · DevOps **24** ·
Scrum **26**.

### 3.3 Factores de adaptación (Matriz 3.2.1)

| Factor | Situación real | Nivel | Justificación de la adaptación |
|---|---|---|---|
| Incertidumbre de requisitos | La brecha 4 **apareció a mitad del proyecto**, al implementar el ruteo | Alto | Exige iteraciones cortas; con Cascada esa brecha se habría descubierto al final |
| Complejidad técnica | PostGIS, OR-Tools, OSMnx, rasterio, TF-IDF, un LLM local | Alto | Exige separación por capas y pruebas automáticas desde la fase 1 |
| Frecuencia de cambios | 125 commits en 10 semanas sobre `main` | Medio-alto | Descarta Cascada por coste de retrabajo |
| Criticidad y riesgo | Datos públicos; nadie depende del sistema para operar | **Bajo** | **Por eso NO se hizo MLOps ni microservicios**: habrían sido infraestructura sin motivo |
| Disponibilidad de datos propios | Cero al empezar. Las fuentes son externas y estables | Alto (de restricción) | **Es el argumento que diferencia IA de MLOps.** Ver §3.4 |

### 3.4 El argumento sobre MLOps — es el eje del trabajo y hay que repetirlo igual

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

**Esto no se contradice nunca en ninguna entrega.** Si el informe propone
MLOps desde el sprint 1, rompe la coherencia con los dos documentos ya
entregados.

### 3.5 Las reglas autoimpuestas que el proceso cumplió en cada commit

Son restricciones verificables, no estilo. Dan material directo para el EJE 3
y para CMMI.

| Regla | Qué significa | Cómo se comprueba |
|---|---|---|
| Todo en español | Variables, funciones, archivos, tablas, columnas, endpoints, commits | Leer cualquier archivo |
| **Regla de oro de la IA** | Toda funcionalidad con modelo tiene alternativa por reglas, conmutable por `.env` | `USAR_MODELO_RECOMENDACION`, `USAR_MODELO_AFLUENCIA`, `USAR_MODELO_SENTIMIENTO` |
| El asistente nunca genera datos | Solo llama funciones del backend y redacta con lo que devuelven | Prueba `test_el_modelo_solo_ve_lo_que_devolvio_la_consulta_a_la_base` |
| Honestidad con los datos | Todo dato estimado se marca, con fuente y fecha | Campos `es_estimado`, `fuente`, `fecha_referencia`, `origen_del_calculo` |
| Pruebas desde la fase 1 | Una fase no está hecha si sus pruebas no pasan | CI en rojo si fallan |
| Un commit por tarea | Conventional Commits en español, todo a `main`, sin ramas | `git log` |
| Sin nube de pago | Ollama local, Leaflet + OSM, SonarQube community, Supabase/Render/Vercel en plan gratuito | — |

**Lo que se decidió NO hacer:** no inventar atractivos, tarifas, horarios ni
estadísticas · no usar nube de pago · no MLOps · no realidad aumentada · no
microservicios.

---

## 4. EJE 3 — Categorización normativa, RAE y DoD

### 4.1 Advertencia de honestidad sobre este eje

**El proyecto no tiene una matriz RAE escrita ni un documento de DoD.** Lo que
sí tiene es un conjunto de controles **realmente ejecutados y verificables**
(la integración continua, las reglas de commit, los ADR). Lo correcto es
presentar eso y decir que el DoD se formaliza aquí a partir de lo que ya se
exigía, no afirmar que existía un acta previa.

Con tres integrantes, además, los roles RAE se solapan. Declararlo es más
defendible que inventar una separación que no hubo.

### 4.2 Categorización normativa (Matriz 3.3.1) — con los artefactos reales

| Categoría | Actividad del proyecto | Producto de trabajo real | Responsable |
|---|---|---|---|
| **Principal** | Especificación de HU y brechas | 7 brechas + 6 HU + `docs/referencia/01` y `09` | R: Proceso / A: Equipo |
| **Principal** | Análisis y diseño | **16 ADR** en `docs/adr/` + diagramas C4 en `docs/contratos/datos-c4.md` + `openapi.json` | R: Desarrollo / A: Equipo |
| **Principal** | Implementación | 125 commits; 44 endpoints; 11 migraciones Alembic | R: Desarrollo |
| **Principal** | Integración y pruebas | **786 pruebas backend + 148 frontend + 13 E2E Playwright** | R: Proceso (QA) |
| **Principal** | Despliegue | Supabase + Render + Vercel, plan gratuito | R: Desarrollo |
| **Soporte** | Gestión de configuración (SCM) | Git, `main` sin ramas, tag `v1.0-PMV`, `.gitignore`, `.env.ejemplo` | R: Desarrollo |
| **Soporte** | Aseguramiento de calidad (PQA) | SonarQube community 26.9.0 + Quality Gate propio `RutaVivaMantaro` | R: Proceso |
| **Soporte** | Verificación y validación | CI de GitHub Actions (2 trabajos, 8 comprobaciones) | R: Proceso |
| **Gestión** | Gestión de riesgos | `docs/referencia/16-pendientes-y-limitaciones.md` | R: Equipo |
| **Gestión** | Mejora continua | `docs/referencia/15-historial-de-fallos.md` y `20-registro-de-defectos.md` | R: Equipo |

### 4.3 Definition of Done — el que de verdad se exige (verificable en CI)

Esto no es una aspiración: es lo que el flujo de GitHub Actions comprueba en
cada `push` a `main`, en una máquina Ubuntu limpia. Si algo falla, el commit
queda en rojo.

**Trabajo `backend`** (con servicio `postgis/postgis:16-3.4`):

1. Instalar dependencias en máquina limpia.
2. Crear extensiones `postgis`, `unaccent`, `pg_trgm`.
3. `python -m alembic upgrade head` — las 11 migraciones desde cero.
4. `python -m pytest -q` — **786 pruebas y cobertura ≥ 95 %** (`fail_under = 95`).
5. `python -m ruff check app/ pruebas/ alembic/` — 0 avisos.
6. `python -m black --check app/ pruebas/ alembic/` — formato exacto.

**Trabajo `frontend`** (Node 24):

7. `npx vitest run` — **148 pruebas**.
8. `npx eslint src/` — 0 avisos.
9. `npx tsc --noEmit` — 0 errores de tipos en modo estricto.

> **Dato que vale para CMMI (VER) y para el criterio 1 de la rúbrica:** el
> umbral de cobertura **pasó de 60 % a 95 % el 6 de noviembre de 2026**
> (commit `d7126b9`). Antes el 95 % era un número en un informe; ahora la rama
> se pone en rojo sola. Es la diferencia entre medir y exigir.

**Lo que el DoD NO incluye, y hay que matizarlo con cuidado:** durante los
seis incrementos no hubo revisión por pares ni Pull Requests, porque la regla
del proyecto era trabajar directo sobre `main` sin ramas. **Eso cambió el 8 de
noviembre de 2026**: la migración a arquitectura hexagonal se hizo en la rama
`refactor/arquitectura-hexagonal` y entró por la **solicitud de incorporación
#1**, la primera del proyecto, con la integración continua en verde como
condición de fusión. Es una sola, y hay que decir que es una sola: el DoD de
los seis incrementos no la incluía.** El
sustituto real es la CI más los ADR, que documentan cada decisión antes de
implementarla.

---

## 5. EJE 4 — WBS, priorización y control de desviaciones

### 5.1 WBS real (6 incrementos, 14 sprints)

```
RUTAVIVAMANTARO
├── 1. INCREMENTO 1 — Catálogo único validado        (sprints 1-2, brecha 1)
│   ├── HU-01: Explorar el catálogo de la ruta
│   └── HU-02: Que el dato sea confiable y se diga cuándo no lo es
├── 2. INCREMENTO 2 — Registro de preferencias       (sprints 3-4, brecha 3)
│   └── HU-03: Armar el viaje sin tener que registrarse
├── 3. INCREMENTO 3 — Recomendación y afluencia      (sprints 5-7, brechas 2 y 3)
│   └── HU-04: Recomendaciones que explican por qué
├── 4. INCREMENTO 4 — Ruteo geoespacial multimodal   (sprints 8-10, brecha 4)
│   └── HU-05: El itinerario del día, con horarios y costos
├── 5. INCREMENTO 5 — Canal único de coordinación    (sprints 11-12, brechas 5 y 6)
└── 6. INCREMENTO 6 — Valoración y evidencia         (sprints 13-14, brecha 7)
    └── HU-06: Que la aplicación avise de sus propios límites
```

**Dependencias reales:** el 2 necesita el 1 · el 3 necesita el 1 y el 2 · el 4
necesita que el 1 esté georreferenciado.

**Priorización valor/riesgo:** el orden de los incrementos **es** la
priorización, y sigue la cadena de dependencias de datos, no el valor
percibido. El catálogo va primero porque sin él los otros cinco no tienen
sobre qué operar, aunque el valor visible para el usuario esté en el 4.

### 5.2 Control de desviaciones — las reales, documentadas

Estas son desviaciones verdaderas del proyecto, no las del ejemplo de la
plantilla. Están todas en `docs/referencia/15-historial-de-fallos.md` y
`20-registro-de-defectos.md`.

| Desviación detectada | Causa raíz | Acción correctiva aplicada | Evidencia |
|---|---|---|---|
| **La brecha 4 no existía** en la primera entrega del análisis | El análisis se hizo antes de descubrir que el ruteo geoespacial era indispensable | Se añadió la brecha 4 y se reordenaron los incrementos | `docs/referencia/01` |
| **El indicador 2 del plan era inmedible** (tiempo entre preferencia y confirmación) | Sin uso real no hay tiempos; todos los datos son de prueba | Se sustituyó por «preferencias que llegan a itinerario» y **se declaró la sustitución** | `docs/indicadores/02` |
| **El indicador 4 del plan era inmedible** (error entre tiempo estimado y real) | Exigiría cronometrar traslados en campo | Se sustituyó por «el itinerario no contradice sus propias restricciones» | `docs/indicadores/04` |
| **Guardar un itinerario no era idempotente**: el indicador 6 bajaba solo por visitar una pantalla | `guardar: true` creaba fila nueva en cada entrada a la pantalla de valoración | Idempotencia por (preferencia, fecha) + 3 pruebas de regresión | §10.1 |
| **El plan de varios días repetía el mismo recorrido** en todos los días | Optimizador determinista + entradas idénticas + sin memoria entre días | Exclusión en cascada: las paradas del día 1 se retiran del repertorio del día 2 | ADR-016 |
| **SonarQube informaba 13,4 % de cobertura** siendo 73 % | Rutas absolutas de Windows en `coverage.xml` que no existen en el contenedor Linux | `normalizar_cobertura.py` reescribe **solo rutas**, ningún número → 68,2 % importado | `docs/referencia/18` |
| **El itinerario tardaba ~85 s en el despliegue** y 6 s en local | N+1: 380 consultas de tarifa por itinerario, a 200 ms de ida y vuelta hasta São Paulo | Caché de tarifas por sesión (`WeakKeyDictionary`) | commit `e3eca63` |
| **La API de Supabase exponía las tablas** (hashes de contraseña legibles con la clave pública) | PostgREST expone por omisión el esquema `public` | Revocados permisos a los roles `anon` y `authenticated`; verificado en ambos sentidos | §8.3 |
| **La cobertura se medía pero no se exigía** | `fail_under = 60` mientras el curso pide 95 | Subido a 95; CI en rojo si baja | commit `d7126b9` |

> **Esta tabla es, probablemente, el activo más fuerte del informe.** Son nueve
> desviaciones con causa raíz y corrección verificable. La rúbrica pide
> «control de desviaciones» en el criterio 1 (5 puntos).

---

## 6. EJE 5 — Historias de usuario del PMV

Son **seis**, y el guion del vídeo las recorre en este orden. El texto completo
de cada escena está en `docs/guion-video-historias-de-usuario.md`.

| HU | Enunciado | Criterio de aceptación (Given-When-Then) | Incremento |
|---|---|---|---|
| **HU-01** | Como visitante, quiero explorar el catálogo de la ruta, para saber qué hay sin buscar en fuentes dispersas | **Dado** el catálogo del MINCETUR cargado, **cuando** el visitante filtra por provincia, categoría y accesibilidad, **entonces** la lista y el mapa muestran solo los recursos que cumplen los tres filtros | 1 |
| **HU-02** | Como visitante, quiero que el dato sea confiable y que se me diga cuándo no lo es, para no fiarme de lo que no está comprobado | **Dado** un recurso sin coordenadas o sin validar, **cuando** se muestra su ficha, **entonces** se marca explícitamente en vez de ocultarlo | 1 |
| **HU-03** | Como visitante, quiero armar el viaje sin registrarme, para probar la plataforma sin crear una cuenta | **Dado** un visitante sin sesión, **cuando** completa los 6 pasos de preferencias, **entonces** se guarda la preferencia y se le devuelve su identificador para seguirla | 2 |
| **HU-04** | Como visitante, quiero recomendaciones que expliquen por qué, para poder decidir con criterio | **Dada** una preferencia con intereses y presupuesto, **cuando** se generan recomendaciones, **entonces** cada tarjeta muestra su afinidad y los términos que pesaron, y existe la lista de descartados con su motivo | 3 |
| **HU-05** | Como visitante, quiero el itinerario del día con horarios y costos, para saber si el plan cabe en un día | **Dada** una preferencia y una fecha, **cuando** se arma el itinerario, **entonces** devuelve orden de visita, horas de llegada y salida, distancia, desnivel y rango de costo, y cada traslado declara si salió de la red vial o de línea recta corregida | 4 |
| **HU-06** | Como visitante, quiero que la aplicación avise de sus propios límites, para no confundir una estimación con un dato | **Dado** un itinerario con tramos estimados, altitud alta o presupuesto ajustado, **cuando** se muestra, **entonces** aparecen los avisos correspondientes en el idioma del visitante | 6 |

> **Nota para el redactor:** la plantilla pide que las HU del PMV sean las del
> Incremento 1. Aquí las seis HU recorren los seis incrementos porque así está
> hecho el guion del vídeo. Si el profesor exige que el PMV sean solo las del
> Incremento 1, el PMV son **HU-01 y HU-02**, y el resto se presenta como
> incrementos posteriores.

---

## 7. EJE 6 — GQM, arquitectura y pruebas funcionales

### 7.1 GQM (Goal-Question-Metric)

| Goal | Question | Metric | Valor medido |
|---|---|---|---|
| Que la oferta publicada sea confiable | ¿Qué proporción de la oferta pasa las validaciones automáticas? | % validado y vigente | **79,32 %** (234/295) |
| Que la recomendación no contradiga lo que el visitante pidió | ¿Alguna recomendación viola una restricción declarada? | % de recomendaciones sin error | **100 %** (por construcción) |
| Que el itinerario sea ejecutable en un día | ¿El plan contradice alguna de sus propias restricciones? | Perfiles viables / total, y tiempo del peor caso | **4 de 4**; **6,52 s** de 10 s |
| Que coordinar no exija varios canales | ¿Cuántos canales hacen falta para confirmar un servicio? | N.º de canales | **1** (antes 3 o más) |
| Que la retroalimentación vuelva al proceso | ¿Qué proporción de experiencias deja valoración estructurada? | % de itinerarios con valoración | **100 %** |
| Que el código esté verificado | ¿Qué proporción del backend ejecutan las pruebas? | % de cobertura de líneas | **96,27 %** |
| Que el código no acumule deuda | ¿Cuánta deuda y cuántos defectos declara el análisis estático? | Bugs / vulnerabilidades / deuda | **0 / 0 / 12 h 31 min** (ratio 0,2 %) |

### 7.2 ARQUITECTURA — el núcleo SÍ es hexagonal desde el 8 de noviembre

> **ESTA SECCIÓN SE REESCRIBIÓ POR COMPLETO EL 8 DE NOVIEMBRE DE 2026.**
> La versión anterior decía que la arquitectura no era hexagonal. Era cierto
> entonces y ya no lo es. Si tienes una copia vieja de este dossier, tírala.

**El núcleo de cálculo está migrado a puertos y adaptadores. Las capas de
persistencia y entrada todavía no.** Lo que sigue distingue las dos cosas, y
hay que mantener esa distinción en el informe: afirmar que el sistema entero es
hexagonal sería tan falso como lo contrario.

Fusionado en `main` con el commit **`0a45446`**, por la **solicitud de
incorporación #1** —la primera del proyecto—, etiquetado como **`v2.0`**.

#### Lo que se puede afirmar, y cómo se comprueba

| Afirmación | Cómo se verifica |
|---|---|
| Existen `backend/src/domain/`, `/ports/` y `/adapters/` | Abrir el repositorio en GitHub |
| El dominio son **2 275 líneas en 11 módulos** | `find backend/src/domain -name "*.py"` |
| **El dominio no importa ningún framework** | `pytest pruebas/test_dominio_sin_frameworks.py` |
| Hay un puerto **en uso real**, no decorativo | `ports/elevacion.py` y su uso en `construir_y_guardar` |

**La pieza que vale los puntos es la prueba automática.** El criterio pide
*«demostrando cero acoplamiento de frameworks en el Dominio»*. Esa frase, en un
informe, es algo que nadie puede verificar sin leer 68 archivos.
`backend/pruebas/test_dominio_sin_frameworks.py` lo comprueba en cada envío al
repositorio: **15 pruebas, 0,10 segundos**, y tiene **paso con nombre propio en
la integración continua**.

Tres cosas que hay que saber decir sobre esa prueba si preguntan:

1. **Lee los imports con el módulo `ast`, no con búsqueda de texto.** Un
   comentario que mencione SQLAlchemy no la engaña, y un import escondido
   dentro de una función tampoco se le escapa.
2. **Comprueba que el dominio no está vacío.** Sin eso, borrar la carpeta
   entera dejaría la suite en verde: «cero acoplamiento» se cumpliría por no
   tener nada que acoplar.
3. **Se verificó que falla de verdad.** Se metió un módulo intruso que
   importaba SQLAlchemy dentro de `domain/` y saltaron las dos comprobaciones.
   Una prueba que nunca puede fallar no demuestra nada.

#### El árbol que el docente va a buscar

```
backend/src/
├── domain/              2 275 líneas. CERO frameworks.
│   ├── red_vial.py      caminos sobre la red, pendientes, rodeo
│   ├── tiempo_recorrido.py   función de Tobler
│   ├── afinidad.py      TF-IDF y términos decisivos
│   ├── sentimiento.py   análisis con umbral de confianza
│   ├── avisos.py        avisos como {código, parámetros}
│   ├── temporada.py     meses del viaje
│   └── valores/         los 9 objetos de valor
├── ports/
│   └── elevacion.py     FuenteDeAltitud
└── adapters/outbound/
    ├── elevacion_copernicus.py   teselas GeoTIFF, httpx, rasterio
    └── red_vial_osm.py           descarga de OSM, grafo en disco
```

**Por qué `backend/src/` y no `/src/` en la raíz, que es lo que pide el
criterio al pie de la letra:** en Render el *Root Directory* del servicio es
`backend`. Un `src/` colgando de la raíz quedaría fuera de lo que Render copia
y el API dejaría de arrancar. El `README.md` de la raíz lleva el árbol visible
para compensarlo. **Esto hay que decirlo si lo preguntan**: es una restricción
de despliegue, no un descuido.

#### Por qué OR-Tools y scikit-learn están DENTRO del dominio

Es la pregunta más probable en la defensa, porque a primera vista parece una
violación. No lo es.

Son **librerías de cálculo, no de infraestructura**: no hablan con la red, ni
con el disco, ni con la base de datos. Un puerto delante de OR-Tools no
desacoplaría nada real —nadie va a sustituir el optimizador— y añadiría una
capa de indirección que hay que mantener. La prueba de acoplamiento **no las
prohíbe a propósito**, y el razonamiento está firmado y fechado en el
**ADR-017**.

#### Lo que NO se puede afirmar

| Rol hexagonal | Estado real |
|---|---|
| **Domain Core** | ✅ `src/domain/`, verificado sin frameworks |
| **Adaptadores de salida** (elevación, red vial) | ✅ `src/adapters/outbound/` |
| **Puerto de salida** (fuente de altitud) | ✅ `ports/elevacion.py`, inyectado por parámetro |
| **Adaptadores de entrada** (driving) | ⚠️ `rutas/` funciona como tal, pero no se ha movido a `adapters/inbound/` |
| **Puertos de repositorio** (catálogo, itinerarios, coordinación) | ❌ **No existen** |
| **Inversión de dependencias en la persistencia** | ❌ **No la hay.** 9 módulos importan SQLAlchemy |

Medido el 8 de noviembre: **50 firmas** en todo `backend/src/` reciben
`sesion: Session`, y **9 módulos** de `servicios/` e `ia/` importan SQLAlchemy
o GeoAlchemy2 directamente.

Los dos casos difíciles son `recomendador.py` y `validacion_catalogo.py`:
tienen **PostGIS incrustado dentro de la consulta SQL** (`cast(..., Geometry)`),
así que separar el cálculo geoespacial de la persistencia no es mover código,
es rediseñar la consulta.

#### Qué falta, declarado con su alcance

Está en el ADR-017 y en `docs/plan-migracion-hexagonal.md`:

| Fase | Qué | Tamaño |
|---|---|---|
| 3 | Puertos de repositorio y adaptadores de persistencia | 9 módulos, 50 firmas |
| 4 | Los enrutadores a `adapters/inbound/http/` | 9 + 9 archivos |
| 5 | El cliente de Ollama detrás de un puerto | 1 módulo |
| 6 | Raíz de composición con inyección por `Depends` | 1 archivo |

> **Cómo redactarlo en el informe.** En el marco teórico, explicar Hexagonal
> como el patrón adoptado. En el diseño, presentar el árbol de arriba y **la
> prueba automática como evidencia**, que es lo que el criterio pide
> literalmente. En las conclusiones **no** escribir «se desacoplaron
> **totalmente** las reglas de negocio del Domain Core» —la frase que trae la
> plantilla— porque la persistencia sigue acoplada. Escribir: «se desacopló el
> núcleo de cálculo, verificado por una prueba automática en integración
> continua, y la migración de la capa de persistencia queda planificada en el
> ADR-017 con su alcance».
>
> **Y decir que se hizo por una solicitud de incorporación revisada**: es la
> primera del proyecto y cierra el hallazgo de «cero revisión entre ramas» que
> el propio informe declara como el más grave de calidad.

### 7.3 Estructura real del repositorio (para el ANEXO B y el vídeo)

```
PROYECTO-PROCESOS-DE-SOFTWARE-/
├── backend/
│   ├── src/                     (se llamaba app/ hasta la v2.0)
│   │   ├── main.py              monta los enrutadores
│   │   ├── configuracion.py     .env + interruptores de modelo
│   │   ├── base_datos.py        motor y sesiones
│   │   ├── domain/     (11)     el cálculo y las reglas. CERO frameworks
│   │   ├── ports/       (1)     FuenteDeAltitud
│   │   ├── adapters/    (2)     elevación (Copernicus) y red vial (OSM)
│   │   ├── modelos/     (9)     las tablas
│   │   ├── esquemas/   (11)     entrada y salida de la API
│   │   ├── rutas/      (10)     los 44 endpoints
│   │   ├── servicios/   (9)     lógica aún acoplada a la base (fases 3 a 6)
│   │   ├── ia/          (3)     afluencia, calendario, asistente
│   │   └── utilidades/ (13)     guiones de carga y verificación
│   ├── alembic/versions/ (11)   migraciones
│   ├── pruebas/        (27)     786 pruebas
│   └── pyproject.toml           ruff, black, pytest, cobertura (fail_under 95)
├── frontend/src/
│   ├── paginas/        (12)     una por ruta
│   ├── componentes/    (20)     piezas reutilizables
│   ├── i18n/                    es.json y en.json (598 claves cada uno)
│   └── estilos/index.css        el sistema de diseño «Mantaro Moderno»
├── frontend/e2e/        (4)     13 pruebas Playwright
├── docs/
│   ├── adr/            (17)     decisiones de arquitectura
│   ├── decisiones/     (15)     por qué se hizo cada cosa
│   ├── indicadores/     (6)     una nota por indicador
│   ├── referencia/     (21)     documentación completa
│   └── capturas/       (15)     evidencias de pantalla
├── pruebas/carga/       (6)     guiones de k6
├── .github/workflows/           integración continua
└── sonar-project.properties
```

### 7.4 Pruebas: los números de hoy

| Nivel | Cantidad | Herramienta | Comando |
|---|---|---|---|
| **Unitarias + integración backend** | **786 pasando**, 2 saltadas | pytest 9.1.1 | `python -m pytest -q` |
| **Cobertura backend** | **96,27 %** (146 líneas sin cubrir de 3 918) | pytest-cov 7.1.0 | idem |
| **Unitarias frontend** | **148 pasando** en 14 archivos | vitest 4.1.11 | `npm run probar` |
| **Extremo a extremo** | **13** en 4 archivos | Playwright (Edge del sistema) | `npm run e2e` |
| **Carga** | 3 escenarios, 3 110 peticiones, 0 errores | k6 v2.3.0 en Docker | ver §8.4 |
| **Análisis estático** | 0 bugs, 0 vulnerabilidades | SonarQube community 26.9.0 | ver §8.5 |

**Módulos del backend al 100 % de cobertura:** `servicios/red_vial.py`,
`servicios/costos.py`, `servicios/seguridad.py`, `servicios/usuarios.py`,
`servicios/temporada.py`, `servicios/validacion_catalogo.py`, `ia/asistente.py`,
`ia/tiempo_recorrido.py`, `rutas/coordinacion.py`, `rutas/asistente.py`,
`rutas/autenticacion.py`, `esquemas/coordinacion.py`, `utilidades/dependencias.py`,
`main.py`, `modelos/afluencia.py`.

#### Las dos exclusiones declaradas, que hay que escribir en el informe

**1. Los diez guiones de operación están excluidos de la medición de
cobertura**, nombrados uno por uno en el `omit` de `backend/pyproject.toml`:
cargan el catálogo del MINCETUR, descargan las 295 fichas web, bajan el modelo
de elevación de Copernicus, construyen el grafo de OpenStreetMap y siembran
datos de demostración. Se ejecutan a mano, una vez, desde una terminal y
mirando la salida. Cubrirlos exigiría simular las respuestas del MINCETUR, de
OSM y de Copernicus: esas pruebas comprobarían las imitaciones, no el código.

> **Declarar esta exclusión no es opcional.** Subir un número escondiendo lo
> que lo baja sería lo contrario de lo que este proyecto defiende sobre los
> datos. El propio `pyproject.toml` dice que la exclusión «se declara también
> en el informe académico».

**2. Quedan 2 líneas sin cubrir que son código muerto, no deuda de pruebas:**
`_nombre_del_dia` en `servicios/coordinacion.py` (huérfana desde que el aviso
pasó a mandar el número del día para que lo nombre i18next) y un `raise`
inalcanzable en `_rol_para_el_cambio` (solo se llega con el estado `enviada`, al
que ninguna transición lleva).

### 7.5 Fichas de prueba funcional con evidencia — qué capturas existen

La rúbrica pide (criterio 3, 4 puntos) fichas con capturas para **TODOS** los
RF. Están en `docs/capturas/`, con su índice en `00-INDICE.md`:

| Archivo | Qué muestra | Sirve para |
|---|---|---|
| `01_catalogo.png` | Catálogo con lista y mapa | HU-01 |
| `02_filtros.png` | Filtros aplicados | HU-01 |
| `03_ficha_recurso.png` | Ficha de un recurso | HU-01 / HU-02 |
| `04a_preferencias_paso1.png`, `04b_preferencias_paso2.png` | Asistente de preferencias | HU-03 |
| `05_recomendaciones.png` | Recomendaciones con afinidad y términos | HU-04 |
| `06_itinerario.png`, `07_itinerario_mapa.png` | Itinerario y su mapa | HU-05 |
| `08_avisos.png` | Avisos de límites | HU-06 |
| `09_ingles.png` | La misma pantalla en inglés | Usabilidad / i18n |
| `10_api_docs.png` | Los 44 endpoints en `/docs` | Soportabilidad |
| `11_cobertura_pytest.png`, `11_pytest_consola_real.png` | Cobertura y consola | PQA / VER |
| `12_github_actions.png` | Pipeline en verde | CI/CD |
| `13_sonarqube.png` | Tablero de SonarQube | PQA |

> **FALTA una captura de HU-02** que muestre explícitamente un recurso marcado
> como no validado o sin coordenadas. `03_ficha_recurso.png` sirve a medias.
> Es lo único que impide que las fichas cubran las seis HU al 100 %.

---

## 8. EJE 7 — FURPS+, colores, WCAG y OWASP

### 8.1 Factor U — Psicología de colores (los colores REALES)

Sistema de diseño **«Mantaro Moderno»**, creado en Stitch para este proyecto
(ADR-012). Estética declarada: **andino contemporáneo**. Los tokens viven en
`frontend/src/estilos/index.css`.

| Rol | Tema claro | Justificación declarada en el código |
|---|---|---|
| **Primario** | **`#a23919`** terracota | La tierra y la cerámica local del valle |
| Primario contenedor | `#c3502f` | — |
| **Secundario** | **`#27695c`** verde valle | Los campos del Mantaro |
| **Terciario** | **`#745800`** ocre | El sol y la textilería wanka |
| **Error** | **`#ba1a1a`** | Atención inmediata; es el único rojo del sistema |
| Superficie | `#fff8f5` crema cálida | Fondo cálido, no blanco clínico |
| Texto sobre superficie | `#1e1b18` | — |

Hay **tema oscuro completo** (clase `.oscuro` en `<html>`), con su propia
paleta: primario `#ffb5a0`, secundario `#93d3c3`, superficie `#16110f`. La
elección del usuario manda sobre la preferencia del sistema operativo.

**Argumento defendible, y es un buen argumento:** la paleta **no se eligió por
teoría del color genérica**, se derivó de la materialidad del Valle del
Mantaro. Un azul corporativo habría sido intercambiable con cualquier otro
sistema; la terracota y el verde valle no.

### 8.2 Factor U — Accesibilidad WCAG 2.1 AA (contraste MEDIDO)

Calculado con la fórmula de luminancia relativa de WCAG 2.1 sobre los tokens
reales. **Los 11 pares principales pasan AA (≥ 4,5:1); 6 de 11 pasan AAA
(≥ 7:1).**

| Par | Ratio | AA | AAA |
|---|---|---|---|
| Claro — texto normal sobre superficie | **16,32:1** | ✔ | ✔ |
| Claro — texto secundario sobre superficie | **8,89:1** | ✔ | ✔ |
| Claro — texto sobre botón primario | **6,70:1** | ✔ | — |
| Claro — texto sobre botón de error | **6,46:1** | ✔ | — |
| Claro — color de error sobre superficie | **6,15:1** | ✔ | — |
| Claro — secundario sobre superficie | **6,13:1** | ✔ | — |
| Oscuro — texto normal sobre superficie | **15,15:1** | ✔ | ✔ |
| Oscuro — texto secundario sobre superficie | **11,00:1** | ✔ | ✔ |
| Oscuro — primario sobre superficie | **11,03:1** | ✔ | ✔ |
| Oscuro — error sobre superficie | **11,03:1** | ✔ | ✔ |
| Oscuro — texto sobre contenedor de error | **7,72:1** | ✔ | ✔ |

**El peor par es 6,13:1**, un 36 % por encima del mínimo AA. *(Reproducible con
el guion que calculó esto; la fórmula es la de WCAG 2.1 §1.4.3.)*

Otros elementos de accesibilidad, **contados en el código**:

| Elemento | Cantidad |
|---|---|
| `aria-label` | 44 |
| `aria-hidden` | 26 |
| `role=` | 23 |
| `aria-expanded` | 5 |
| `aria-current` | 3 |
| `aria-labelledby` | 2 |
| `aria-live` | 2 |
| `prefers-reduced-motion` | 1 (respetado por framer-motion) |
| Claves de i18n | **598 en español y 598 en inglés**, simétricas |

> **NO escribir «compatibilidad 100 % con lectores de pantalla».** Nadie ha
> probado la aplicación con NVDA, JAWS ni VoiceOver. Lo que se puede afirmar es
> que **hay 105 atributos ARIA y los contrastes están medidos**. Afirmar
> compatibilidad total sin haberla probado es exactamente el tipo de cosa que
> el resto del informe critica.

### 8.3 Restricciones adicionales (+) — Auditoría OWASP Top 10:2025

| Código | Vulnerabilidad | Estado real | Mecanismo / evidencia |
|---|---|---|---|
| **A01:2025** | Broken Access Control | **Mitigado** | Dependencias `UsuarioOpcional` / `UsuarioRequerido` + `exigir_rol`. Las reglas de visibilidad de solicitudes están probadas desde la API: un visitante no ve ni cancela la de otro (404, no 403, para no confirmar que existe); el operador tiene visión completa. `utilidades/dependencias.py` al **100 % de cobertura** |
| **A02:2025** | Cryptographic Failures | **Mitigado con una salvedad** | **Argon2id** vía `passlib` para contraseñas (ganador del PHC 2015, recomendación OWASP); sal automática por contraseña. JWT firmado HS256. **Salvedad: `clave_secreta` tiene un valor por omisión inseguro en `configuracion.py`** (`clave_insegura_solo_para_desarrollo`); en producción se inyecta por variable de entorno, pero el valor por omisión sigue en el código |
| **A03:2025** | Injection | **Mitigado** | **Todo** el acceso a datos pasa por SQLAlchemy con consultas parametrizadas. **Verificado: cero concatenaciones de cadena para construir SQL en `app/`.** Validación de entrada con Pydantic en los 44 endpoints |
| **A04:2025** | Insecure Design | **Parcial** | Las reglas de estado y permisos viven en la capa de servicio, no repartidas por los endpoints (ADR-009), y el grafo de transiciones es explícito (`TRANSICIONES_VALIDAS`). **Pero no se puede alegar Arquitectura Hexagonal** como mecanismo: ver §7.2 |
| **A05:2025** | Security Misconfiguration | **Mitigado con un pendiente** | `.gitignore` correcto desde el primer commit; `.env.ejemplo` versionado **sin valores reales**; ningún secreto en el historial; CORS desde configuración (`ORIGENES_PERMITIDOS`), no comodín. **Pendiente: `.env.ejemplo` no lista 4 variables que el código sí lee** (`ORIGENES_PERMITIDOS`, `SEGUNDOS_DE_BUSQUEDA`, `MAXIMO_CANDIDATOS`, `TOPE_DE_CANDIDATOS_DEL_VIAJE`) |
| **A06:2025** | Vulnerable Components | **No auditado formalmente** | No se ha corrido `pip-audit` ni `npm audit` como parte del proceso. **Decirlo así** |
| **A07:2025** | Auth Failures | **Mitigado** | Longitud mínima de contraseña 8 (criterio OWASP, elegido en vez de reglas de composición que empujan a «Contrasena1!»); token con expiración (`MINUTOS_EXPIRACION_TOKEN`); token caducado o manipulado se trata como «sin sesión», nunca con error 500. Probado |
| **A08:2025** | Data Integrity Failures | **Parcial** | 11 migraciones Alembic versionan el esquema; restricciones `CHECK` y `UNIQUE` en la base como reglas de negocio (probadas en `test_modelos_afluencia.py`). **`pickle` se usa para el grafo vial**, con la condición documentada de que el archivo lo escribe la propia máquina y nunca se acepta de terceros |
| **A09:2025** | Logging Failures | **Parcial** | La tabla `cambio_de_estado` registra cada movimiento con quién y cuándo (es la brecha 6). Las contraseñas nunca se registran. **No hay registro de seguridad centralizado ni alertas** |
| **A10:2025** | SSRF | **No aplica en caliente** | El sistema solo sale a la red en los guiones de operación (MINCETUR, OSM, Copernicus), con URL fijas en el código, y a Ollama en `localhost`. Ningún endpoint acepta una URL del usuario |

#### El hallazgo de seguridad real del despliegue — vale la pena contarlo

Al desplegar en Supabase se descubrió que **la API PostgREST exponía las tablas
del esquema `public`**: con la clave publicable (que es pública por diseño) se
podían leer filas de `usuario`, **incluidos los hashes de contraseña**. Se
verificó que era explotable, se revocaron los permisos de los roles `anon` y
`authenticated`, y se volvió a verificar en ambos sentidos (que ya no se puede
leer, y que el backend sigue funcionando).

**Es un A01 encontrado y cerrado en un despliegue real.** Es mucho mejor
material que un «mitigado» teórico.

### 8.4 Factor P — Rendimiento (pruebas de carga con k6)

**Leer primero:** estas mediciones se tomaron **en una laptop**, no en un
servidor. El generador de carga, el backend y PostgreSQL compiten por los
mismos núcleos; `uvicorn` corre con **un solo trabajador**; la latencia de red
es **cero** porque todo es `localhost`. Sirven para comparar escenarios entre
sí y localizar el cuello de botella, **no como capacidad de producción**.

Entorno: Windows 11 Home 10.0.26200 · PostgreSQL 16.4 + PostGIS 3.4 en Docker ·
k6 v2.3.0 en Docker · 25 de septiembre de 2026.

| | (a) Catálogo `GET /api/recursos` | (b) Recomendaciones `POST /api/recomendaciones` | (c) Itinerario `POST /api/itinerarios` |
|---|---|---|---|
| Niveles de carga | 5 → 15 → 30 VU | 5 → 10 → 20 VU | 1 → 2 → 4 VU |
| Peticiones | **2 942** | **102** | **66** |
| Throughput | 29,27 RPS\* | **0,93 RPS** | **0,23 RPS** |
| p50 al nivel más bajo | **10,11 ms** | 5,25 s | 5,10 s |
| p95 al nivel más alto | **21,29 ms** | **30,26 s** | **17,10 s** |
| Tasa de error | **0,00 %** | **0,00 %** | **0,00 %** |
| ¿Degrada? | Solo en la cola (p99: 49→73→150 ms) | Sí, lineal, desde <5 usuarios | Saturado desde 1 usuario |

\* marcado por el `sleep(0.5)` del guion, no por el servidor.

**Cuello de botella localizado:** tres órdenes de magnitud separan el catálogo
del itinerario (10 ms contra 5 100 ms). **No es la base de datos: es CPU en el
proceso de Python.** Se ve en que el throughput no sube al añadir usuarios.

**Coste de arranque en frío, medido:** la primera petición de itinerario tras
reiniciar el backend tarda **11,01 s**; la segunda, **5,15 s**. La diferencia
son los 28 MB del grafo vial que se cargan una vez por proceso.

**Total: 3 110 peticiones con 0 fallos** y 6 556 comprobaciones de contenido
correctas. **El sistema se degrada en tiempo, no en corrección**: bajo 20
usuarios tarda 30 segundos, pero no devuelve un error ni deja de declarar lo
que estima.

> **PENDIENTE para el redactor:** existe además un escenario de **500 usuarios**
> (`pruebas/carga/01-catalogo-500.js`, con umbrales `http_req_failed < 1 %` y
> `p(95) < 800 ms`) que se ejecutó en la Semana 10. Encontró el límite del
> `QueuePool` de SQLAlchemy (5 + 10 = 15 conexiones, `pool_timeout` 30 s) con
> cientos de errores `QueuePool limit`, y el backend quedó sin responder al
> terminar. **Los números exactos de esa ejecución no están guardados en el
> repositorio**; están en el historial de la conversación de la Semana 10. Si se
> van a citar, hay que recuperarlos de ahí o volver a ejecutar la prueba. No
> inventarlos.
>
> La causa está identificada en el código: `backend/src/base_datos.py` crea el
> motor **sin `pool_size` ni `max_overflow`**, así que usa los valores por
> omisión. **No está corregido.**

### 8.5 Factor S — Soportabilidad y análisis estático

SonarQube **community 26.9.0** en Docker local, 25 de septiembre de 2026,
duración 11 min 40 s. Escáner `sonarsource/sonar-scanner-cli`.

| Métrica | 1.ª ejecución | Tras correcciones | Calificación |
|---|---|---|---|
| Bugs | 1 | **0** | Fiabilidad **A** |
| Vulnerabilidades | 0 | **0** | Seguridad **A** |
| Puntos calientes de seguridad | 0 | **0** | — |
| Code smells | 178 | **133** | Mantenibilidad **A** |
| CRITICAL | 21 | **16** | — |
| BLOCKER | 0 | **0** | — |
| Deuda técnica | 885 min | **751 min = 12 h 31 min** | Ratio **0,2 %** |
| Duplicación | 0,0 % | **0,0 %** | — |
| Cobertura importada | 68,1 % | **68,2 %** | — |

Tamaño medido: **15 588 líneas de código**, 108 archivos, 694 funciones,
complejidad ciclomática 1 883, cognitiva 1 181.

**Quality Gate propio** `RutaVivaMantaro`, creado porque el perfil «Sonar way»
solo mide código nuevo y en un primer análisis eso se cumple trivialmente:
cobertura total ≥ 60 % (**68,2 %** OK) · duplicación ≤ 3 % (**0,0 %** OK) ·
blockers = 0 (**0** OK).

#### ⚠️ Las «0 vulnerabilidades» valen menos de lo que parecen

El propio tablero de SonarQube lo avisa:

> *Limited security analysis. SonarQube Community Build does not scan for
> critical injection vulnerabilities (SQL injection, XSS, and more).*

**La edición community no busca inyección SQL ni XSS.** El «0
vulnerabilidades» y la **A** de seguridad **no significan que el proyecto esté
libre de inyección**: significan que esta herramienta, en esta edición, no la
buscó.

Lo que sostiene que no hay inyección SQL **no es SonarQube**: es que todo el
acceso a datos pasa por SQLAlchemy parametrizado y no hay concatenación de
cadenas para construir SQL (§8.3, A03). **Eso es lo que hay que decir en la
defensa, no el A de Sonar.**

> **OJO con el DoD de la plantilla:** pide «0 deudas técnicas críticas». Hay
> **16 code smells CRITICAL** y 12 h 31 min de deuda. Son *code smells*, no
> vulnerabilidades, pero no es cero. Escribir la cifra real.

### 8.6 Factor R — Confiabilidad, y F — Funcionalidad

| Factor | Evidencia medida |
|---|---|
| **F** — Funcionalidad | 44 endpoints documentados en `/docs`; 6 HU con criterios Given-When-Then verificados por pruebas; 2 idiomas con 598 claves simétricas |
| **R** — Confiabilidad | 0 errores en 3 110 peticiones de carga; 786 + 148 + 13 pruebas en verde; CI en máquina limpia desde cero (base de datos, migraciones y dependencias incluidas) |
| **P** — Rendimiento | §8.4 |
| **S** — Soportabilidad | §8.5; 16 ADR; 21 documentos de referencia; 15 notas de decisión |
| **+** | §8.3 OWASP; restricciones autoimpuestas de §3.5 |

---

## 9. EJE 8 — CMMI-DEV (representación continua)

### 9.1 Por qué representación continua y no escalonada

CMMI admite dos. La **escalonada** asigna un nivel de madurez global (1–5) a
una **organización**. La **continua** asigna un nivel de capacidad (0–3) a cada
área de práctica por separado.

Esta auditoría usa la **continua**, y justificarlo importa: el sujeto auditado
**no es una organización**, es un equipo de tres estudiantes con un único
proyecto, un único repositorio y un único ciclo de vida. Afirmar que ese equipo
tiene un «nivel de madurez organizacional» sería forzar el modelo. En cambio,
preguntar si la verificación está gestionada **sí** tiene respuesta verificable.

### 9.2 Resultado de la auditoría (del informe de Semana 11, commit `df74496`)

| Área de práctica | Nivel | Justificación |
|---|---|---|
| **VER** — Verificación | **3 · Definido** | Proceso estándar documentado y automatizado: CI en máquina limpia con 8 comprobaciones, umbral de cobertura exigido, y el resultado retroalimenta al estándar |
| **ESTIM** — Estimación | **2 · Gestionado** | Estimación formal por incrementos con reestimación documentada |
| **PLAN** — Planificación | **2 · Gestionado** | WBS de 6 incrementos y 14 sprints, con dependencias explícitas |
| **CM** — Gestión de configuración | **2 · Gestionado** | Git con `main` único, tag `v1.0-PMV`, `.gitignore` correcto desde el primer commit, migraciones versionadas |
| **PQA** — Aseguramiento de calidad | **2 en producto · 1 en proceso** | El producto se audita (SonarQube, Quality Gate propio); el **proceso** no tiene auditorías de cumplimiento planificadas |
| **VAL** — Validación | **1 · Ejecutado** | Ver §9.3 |

### 9.3 Por qué VAL se queda en Nivel 1 — y qué ha cambiado desde la auditoría

Del informe de Semana 11, textual:

> Es tentador puntuar alto aquí, porque hay criterios de aceptación bien
> escritos y pruebas automáticas que los comprueban. Pero eso no es validación
> en el sentido de CMMI: es **verificación** de los criterios de aceptación,
> que ya se contabiliza en VER. La validación pregunta si se construyó el
> producto **correcto**, y esa pregunta solo la contesta el usuario para el que
> se construyó, usándolo en su entorno real.

La auditoría dio dos motivos: **(a)** ningún gestor turístico ni prestador del
Valle del Mantaro ha usado la plataforma, y **(b)** no existía un despliegue
accesible donde pudieran hacerlo.

> **⚠️ ACTUALIZACIÓN IMPORTANTE: el motivo (b) ya no se sostiene.** El sistema
> **está desplegado** desde principios de noviembre (Supabase + Render +
> Vercel, §11). El motivo (a) sigue intacto: no hay usuarios reales, ni plan de
> validación, ni usuarios identificados, ni actas de aceptación.
>
> **VAL sigue en Nivel 1**, pero la justificación cambia: ya no es «no hay
> dónde», es «no se ha hecho». Y la no conformidad de configuración que la
> bloqueaba —«sin artefacto de despliegue no hay entorno donde un usuario pueda
> usar el producto»— **está resuelta**. Eso es una mejora de proceso real que
> el informe integrador puede reclamar como cerrada.

### 9.4 Plan de mejora continua (CAR) — las acciones concretas pendientes

| Brecha de capacidad | Acción propuesta | Estado |
|---|---|---|
| VAL en Nivel 1 | Plan de validación con usuarios identificados del valle y actas de aceptación | **Pendiente** |
| VAL bloqueada por falta de despliegue | Desplegar a un entorno accesible | ✅ **Hecho** (Supabase + Render + Vercel) |
| PQA del proceso en Nivel 1 | Auditorías de cumplimiento del proceso planificadas, no solo del producto | Pendiente |
| Cobertura medida pero no exigida | `fail_under = 95` en CI | ✅ **Hecho** (`d7126b9`, 6-nov-2026) |
| Código muerto sin detectar | Eliminar `_nombre_del_dia` y el `raise` inalcanzable | Identificado, pendiente |
| Componentes sin auditar (A06) | Añadir `pip-audit` y `npm audit` a la CI | Pendiente |
| Pool de conexiones sin dimensionar | Fijar `pool_size` y `max_overflow` en `base_datos.py` | **Identificado y NO corregido** |
| Sin revisión por pares | Era la regla «todo a `main` sin ramas». **Corregido parcialmente el 8-nov-2026**: la migración hexagonal entró por la solicitud de incorporación #1 | **Acción correctiva aplicada una vez** |

---

## 10. Conclusiones y lecciones aprendidas — material real

### 10.1 La lección que el proyecto puede documentar mejor que nadie

**Tres de los defectos más graves se encontraron USANDO la aplicación, no con
pruebas.** Vale la pena decirlo porque es una lección genuina sobre los límites
de la verificación automática:

1. **El indicador 6 bajaba solo por visitar una pantalla.** Guardar un
   itinerario no era idempotente: la pantalla de valoración lo rearmaba al
   entrar y creaba una fila nueva cada vez. El denominador crecía con
   duplicados que nadie iba a valorar. **Ninguna prueba lo detectaba**, porque
   cada prueba por separado era correcta.
2. **El plan de varios días devolvía el mismo recorrido todos los días.** Lo
   notó el usuario, no la suite. Causa: optimizador determinista + entradas
   idénticas + ninguna memoria entre días.
3. **SonarQube informaba 13,4 % de cobertura siendo 73 %.** El número era
   plausible, estaba en un tablero de aspecto serio, y era falso.

> **La lección, formulada:** una configuración que nadie ha ejecutado no está
> «lista», está **sin comprobar**. Y un número que sale de una herramienta no
> es automáticamente cierto.

### 10.2 Lecciones sobre el tailoring

- **Seleccionar el modelo por sus factores, no por moda.** La matriz ponderada
  dio 4,96 a la combinación frente a 3,88 de Scrum solo y 1,92 de Cascada.
- **La brecha 4 apareció a mitad del proyecto.** Con Cascada se habría
  descubierto al final. Es la prueba empírica de que el tailoring acertó.
- **Distinguir IA de MLOps fue la decisión de proceso más importante.**
  Implementar MLOps habría sido infraestructura sin datos que la justifiquen.
- **Un criterio de terminación que ninguna herramienta comprueba se incumple
  sin que nadie se entere.** De ahí `fail_under = 95`.

### 10.3 Lo que NO escribir en las conclusiones

- ❌ «Se desacoplaron **totalmente** las reglas de negocio del Domain Core» —
  es falso (§7.2).
- ❌ «**0 vulnerabilidades** OWASP 2025 confirmadas por SonarQube» — la edición
  community no busca inyección ni XSS (§8.5).
- ❌ «Compatibilidad **100 %** con lectores de pantalla» — nadie lo ha probado
  (§8.2).
- ❌ «Reducción de pérdidas operativas del 22 % al < 3 %» — es del proyecto de
  ejemplo de la plantilla; aquí no hay nada medido de eso.

---

## 11. Anexos

### ANEXO A — Vídeo demostrativo

**PENDIENTE: no está grabado.** El guion técnico, escena por escena, con lo que
hay que mostrar y lo que hay que decir, está en
`docs/guion-video-historias-de-usuario.md` — recorre HU-01 → HU-06 sobre la
aplicación en ejecución (no sobre el código).

**Aviso sobre el guion de la plantilla (ANEXO C):** su minutado describe el
proyecto de ejemplo (login RBAC, paquetes telemáticos, alertas
georreferenciadas, exportación PDF/Excel). **No sirve.** Y su primera escena
(00:00–00:45) manda enseñar `/src/domain/` en GitHub, que **no existe**.
Sustituirla por la estructura real de §7.3.

### ANEXO B — Repositorio

| | |
|---|---|
| **URL** | `https://github.com/75220834-cloud/PROYECTO-PROCESOS-DE-SOFTWARE-` |
| Visibilidad | Público |
| Ramas | `main` + `refactor/arquitectura-hexagonal` (fusionada por la solicitud #1) |
| Commits | **131** |
| Primer commit | `ac079d8` — 28 de agosto de 2026 |
| Último commit | `0a45446` — 8 de noviembre de 2026 (fusión de la solicitud #1) |
| **Tags existentes** | **`v1.0-PMV`** y **`v2.0`** |
| Tags pendientes | ninguno |

> La rúbrica menciona explícitamente «tags de versión (v1.0-PMV, v2.0)» en el
> criterio 2. **Los dos existen y están publicados.** `v2.0` apunta a la fusión
> de la migración hexagonal.

### ANEXO D — Despliegue (no está en la plantilla, pero conviene añadirlo)

| Pieza | Servicio | Plan |
|---|---|---|
| Base de datos | **Supabase** — proyecto `wjeqduwkvbqobidsbwwm`, región `sa-east-1` (São Paulo), PostgreSQL 17.11 + PostGIS 3.3 | Gratuito |
| Backend (API) | **Render** — runtime nativo de Python, Root Directory `backend`. **URL: `https://rutavivamantaro-api.onrender.com`** | Gratuito |
| Frontend | **Vercel** — proyecto `proyecto-procesos-de-software` | Gratuito |
| Integración continua | **GitHub Actions** — 2 trabajos, 8 comprobaciones | Gratuito |

**Cumple la restricción del proyecto de no usar nube de pago.**

**Comprobado el 8 de noviembre de 2026**, después de la migración hexagonal: el
API está **Live** con el commit `0a45446`, arrancando con
`uvicorn src.main:aplicacion`. Verificado de verdad, no solo que el panel
dijera «Live»:

| Petición | Respuesta |
|---|---|
| `GET /api/indicadores/catalogo` | 295 recursos, 234 validados, **79,32 %** |
| `GET /api/recursos?tamano_pagina=1` | devuelve el recurso real con coordenadas |
| `GET /api/salud` | `base_datos: operativo`, PostGIS 3.3 |

> **Sobre `estado_general: "degradado"` en `/api/salud`:** es lo esperado y hay
> que saber explicarlo. Ollama no existe en producción —es un modelo local— así
> que el asistente conversacional reporta `no_disponible`. El sistema lo declara
> en vez de fingir que todo está bien, que es la misma regla de honestidad que
> gobierna las tarifas y los avisos. **No es un fallo del despliegue.**

> **DATO QUE FALTA y solo lo tiene el equipo:** la **URL pública del frontend
> en Vercel**. `frontend/.env` apunta a `http://localhost:8000`, así que no
> está en el repositorio. Hace falta para el ANEXO B/D y para el vídeo.

---

## 12. Los pendientes, en una sola lista

Lo que el informe **no puede afirmar** hasta que se haga:

| # | Pendiente | Impacto en la rúbrica |
|---|---|---|
| 1 | **Grabar el vídeo** demostrativo (5 min) | Criterio 4 — **5 puntos** |
| 2 | **URL públicas** de Render y Vercel | Anexos; criterio 4 |
| 3 | ~~Crear el tag `v2.0`~~ **HECHO el 8-nov-2026** | Criterio 2 — resuelto |
| 4 | **Captura de HU-02** mostrando un recurso no validado | Criterio 3 — es la única HU sin evidencia propia |
| 5 | `ORIGENES_PERMITIDOS` en Render sigue en `https://PENDIENTE.vercel.app` en el archivo local de referencia | Si no se cambió en el panel de Render, el frontend no puede llamar a la API (CORS) |
| 5b | **Volver a sacar la captura de la consola de pytest** | Las cifras cambiaron: ahora son **786 pruebas y 96,27 %**, no 771 y 96,28 % |
| 6 | ~~Render puede no haber redesplegado~~ **RESUELTO el 8-nov-2026**: Render está Live con `0a45446` en `https://rutavivamantaro-api.onrender.com`, verificado contra `/api/indicadores/catalogo` y `/api/recursos` | — |
| 7 | Las 4 variables nuevas no están en `.env.ejemplo` | OWASP A05 |
| 8 | `pip-audit` / `npm audit` nunca ejecutados | OWASP A06 |
| 9 | `pool_size` / `max_overflow` sin fijar en `base_datos.py` | Factor P; es la causa del fallo con 500 usuarios |
| 10 | Números exactos de la prueba de 500 usuarios no guardados en el repo | Factor P |
| 11 | El comentario del paso de CI dice «falla por debajo del 60 %» y ahora es 95 % | Cosmético, pero es documentación desactualizada |
| 12 | Código muerto: `_nombre_del_dia` y el `raise` inalcanzable | CMMI/CAR |

---

## 13. Comandos para reproducir cualquier cifra de este dossier

```bash
cd backend && POSTGRES_USUARIO=rutaviva POSTGRES_CONTRASENA=pruebas_locales POSTGRES_BASE=rutavivamantaro POSTGRES_HOST=localhost POSTGRES_PUERTO=5432 .venv/Scripts/python.exe -m pytest -q
```

```bash
cd frontend && npm run probar
```

```bash
cd frontend && npm run e2e
```

```bash
git -c core.pager=cat log --oneline | wc -l && git -c core.pager=cat tag -l
```

```bash
grep -rhoE '@enrutador\.(get|post|put|patch|delete)' backend/src/rutas/ | wc -l
```

```bash
grep -rnE "\bProtocol\b|\bABC\b|abstractmethod" backend/src/ | wc -l
```

> La suite del backend necesita el contenedor levantado (`docker compose up -d`)
> y las cinco variables `POSTGRES_*` en la propia línea, porque **no existe
> `backend/.env`** y el valor por omisión de la contraseña no coincide con el
> del contenedor.
