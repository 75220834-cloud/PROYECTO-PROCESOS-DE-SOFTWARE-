# 15 — Historial de fallos

**Qué explica este archivo:** todos los fallos encontrados durante el
desarrollo, **cómo se encontraron** y cómo se arreglaron.

No es una lista de vergüenzas: es la prueba de que esto se probó de verdad. Un
proyecto sin fallos documentados es un proyecto que no se probó, o que los
escondió.

**Lo más útil de esta lista:** casi la mitad se encontraron **usando la
aplicación**, no ejecutando pruebas. Es el argumento más fuerte a favor de
probar con las manos.

---

## Los tres que más enseñan

### 1. OR-Tools resolvía un problema distinto del que teníamos

**Síntoma:** el optimizador devolvía **1 parada** donde la alternativa por
reglas encontraba 3.

**Causa:** `RoutingIndexManager(n, 1, 0)` declara que el vehículo **vuelve al
punto de partida**. Es lo correcto para un camión de reparto. Un itinerario
turístico **no es un tour cerrado**: no vuelves al primer sitio.

**Arreglo:** un nodo final virtual, para que el recorrido pueda terminar donde
sea.

```python
fin_del_dia = reales
gestor = pywrapcp.RoutingIndexManager(reales + 1, 1, [0], [fin_del_dia])
```

**Cómo se encontró:** comparando las dos vías. Sin la alternativa por reglas
—la regla de oro— nadie habría notado que 1 parada era poco.

**Fijado por:** dos pruebas de regresión en `test_ruteo.py`.

---

### 2. El asistente negaba que Concepción tuviera atractivos

**Síntoma:** a «¿qué puedo visitar en Concepción?» respondía que no había
recursos registrados. **Hay trece.**

**Causa:** el modelo escribe «CONCEPCIÓN» con tilde; el inventario del MINCETUR
la guarda como «CONCEPCION». `ILIKE` es sensible a tildes en PostgreSQL.

**Por qué es el peor fallo posible aquí:** no es inventar. Es **negar algo que
sí existe**, y hacerlo con la misma seguridad con la que habría dicho la
verdad. Un sistema que se equivoca inventando se detecta; uno que se equivoca
negando, no.

**Arreglo:** normalizar los dos lados con `unaccent`.

**Cómo se encontró:** preguntándole cosas normales al asistente.

---

### 3. Dos limitaciones declaradas eran falsas

**Síntoma:** el README decía, y lo repetía la documentación de los incrementos:

> «El inventario del MINCETUR no publica horarios.»
> «El inventario del MINCETUR no trae descripciones.»

**Causa:** era verdad **del CSV**, no de la fuente. Cada recurso tiene además
una **ficha web** cuya dirección estaba guardada en `url_ficha` **desde la Fase
1**. Nadie había abierto una.

**Resultado del arreglo:** 295 descripciones, 208 horarios, 414 conteos reales
de visitantes, 28 fechas de fiestas.

**La lección, que es la más importante de este archivo:**

> **«La fuente no lo publica» hay que comprobarlo antes de escribirlo.** La
> frase sonaba razonable, encajaba con el discurso de honestidad del proyecto,
> y nadie la puso en duda durante seis fases. Se apoyaba en no haber mirado.

---

## Fallos de datos

| Fallo | Cómo se encontró | Arreglo |
|---|---|---|
| **Latitud y longitud intercambiadas** en el CSV del MINCETUR | Los recursos caían en el océano | El cargador las corrige y lo dice |
| **El mismo RUC en dos directorios** — un hotel que también tiene restaurante | Al cargar los prestadores: violación de clave única | Se fusionan las clases: «Hotel · Restaurante» |
| **«Julio» es nombre de persona** | El Concurso de Enfrenadura salía en julio porque su fundador se llamaba Julio Camac | Si el mes va en mayúscula y le sigue otra palabra en mayúscula, es un nombre propio |
| **La historia del pueblo lleva meses** | La Feria de Cuasimodo salía con cinco meses de una frase sobre arrieros del siglo pasado | Se puntúa cada frase; si ninguna habla de la fecha, se dice que la ficha no la precisa |

**Sobre el último:** el primer intento fue **rechazar toda frase con una marca
de pasado**, y dejó **las 36 fiestas sin fecha** — casi toda descripción
menciona algún año. Puntuar en vez de descartar fue lo que funcionó.

---

## Fallos que rompían un indicador

### Guardar un itinerario no era idempotente

La pantalla de valoración rearma el itinerario al entrar, y con `guardar: true`
creaba **una fila nueva cada vez**.

**Efecto:** el denominador del indicador 6 crecía con duplicados que nadie iba
a valorar, así que **el porcentaje bajaba solo por visitar una pantalla**. Y
las valoraciones quedaban colgando de un itinerario distinto del que la
pantalla enseñaba.

**Arreglo:** idempotente por preferencia y fecha. **Tres pruebas de regresión.**

**Cómo se encontró:** usando la aplicación.

### «Mejor» y «peor valorados» mostraban los mismos recursos

Con pocos recursos, las dos listas se solapaban y el mismo aparecía como lo
mejor y lo peor. **Arreglo:** `_partir_el_ranquin`.

---

## Fallos de honestidad — cuando el sistema decía algo falso

| Fallo | Por qué importaba |
|---|---|
| **Los tramos motorizados nunca se ruteaban** | Se marcaban siempre como línea recta, así que el aviso «no hay red vial registrada cerca» **era literalmente falso** |
| **`sin_horario` se contaba antes de truncar** | Decía «30 de los 20 recursos» |
| **Tramos del mismo nodo marcados como estimados** | Se introdujo `hay_cobertura` para distinguir «no hay red», «mismo nodo» y «red partida» |
| **Comparación de sentimiento amañada** | Las reglas veían la puntuación y el modelo no. Al medirlo bien: reglas 8/14, modelo 11/14 |

El último es el más importante de esta sección: **la primera medición
favorecía a las reglas por un sesgo mío**, no por mérito. Volver a medirlo bien
cambió la decisión.

---

## Fallos de redacción

Los plurales, que volvían una y otra vez:

- «Solo hay 1 valoración(es)»
- «1 de los 1 recursos valorados **tienen**»
- «1 parada(s)», «1 persona(s)», «1 plaza(s)»
- «3 distrito(s) más»

**Se arreglaban de uno en uno y reaparecían** en la siguiente frase que alguien
escribía con prisa. La solución definitiva fue estructural: que el backend
mande código y parámetros, y que i18next resuelva el plural. Ver
[11](11-idiomas-y-avisos.md).

**Un detalle revelador:** al corregir «no traen» por «no trae» se cayó una
prueba que llevaba tiempo **fijando la falta de concordancia**. Una prueba
puede consolidar un error si afirma sobre el texto.

Y textos obsoletos: la portada siguió diciendo **«Fase 0: entorno preparado»**
hasta la Fase 7.

---

## Fallos de interfaz

| Fallo | Cómo se encontró |
|---|---|
| **El botón principal de la portada no hacía nada** — un `<button>` sin `onClick`, desde la Fase 0 | Lo dijo el usuario probando |
| **`<li>` dentro de `<li>`** en la línea de tiempo — HTML inválido | React avisaba por consola; ninguna prueba lo cazaba |
| **Los números del mapa ilegibles en modo oscuro** — Leaflet pinta fondo claro fijo | Midiendo el contraste de las 9 rutas en los dos temas |
| **La ficha ignoraba `descripcion_en`** aunque estuvieras en inglés | Revisando el barrido de idiomas |

---

## Fallos míos, de programación

Estos no cambian el producto, pero son los que más tiempo cuestan:

| Fallo | Efecto |
|---|---|
| **Expresiones regulares sin `r"..."`** | Python convirtió cada `\b` en un carácter de retroceso. **Dejaron de reconocer nada sin dar ningún error.** |
| **Alembic no detecta cambios en `CHECK`** | Al hacer `mes` nulable, la columna cambió pero el `CHECK` seguía exigiendo 1–12 |
| **Un `uvicorn` huérfano** | Sobrevivió a su padre y seguía sirviendo código viejo en el puerto 8000 |
| **La caché de Vite corrupta** | Servía un módulo vacío |
| **Fixtures de prueba equivocadas** | Varias veces la prueba estaba mal y el código bien: Tobler 2,96 (era 3,55), ids 101/103 (eran 100/102), `0${9+1}` dando «010:00» |

El de las expresiones regulares es el más traicionero: **falló en silencio**.
Se detectó porque el extractor devolvía cero en un caso que a mano era evidente.

---

## Lo que este historial demuestra

1. **Probar con las manos encuentra lo que las pruebas no.** El botón muerto,
   el itinerario duplicado, el asistente negando Concepción: ninguno lo cazó
   una prueba.
2. **La alternativa por reglas no es solo un respaldo: es un detector.** El
   fallo de OR-Tools se vio comparando las dos vías.
3. **Una prueba que afirma sobre texto puede consolidar un error.**
4. **Las afirmaciones sobre los datos también hay que verificarlas.** «La
   fuente no lo publica» estuvo seis fases sin comprobarse.

---

## Relacionado

- [12 — Pruebas y calidad](12-pruebas-y-calidad.md)
- [14 — Guion de defensa](14-guion-de-defensa.md)
- `docs/decisiones/` — las 14 notas, cada una con su medición
