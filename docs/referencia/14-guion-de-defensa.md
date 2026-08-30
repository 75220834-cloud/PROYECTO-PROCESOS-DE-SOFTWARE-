# 14 — Guion de defensa

**Qué explica este archivo:** qué enseñar y en qué orden, y **las preguntas
incómodas con su respuesta honesta**.

Está escrito para leerse la noche antes.

---

## El argumento central, en una frase

> **Lo que separa este proyecto de una pantalla bonita es que el sistema dice
> cuándo estima, cuándo no sabe y cuándo sus números son frágiles.**

Si solo te acuerdas de una cosa, que sea esa. Casi todas las respuestas de
abajo son un caso particular de ella.

---

## El recorrido, en 10 minutos

### 1. El catálogo (2 min)

`/explorar`. **295 recursos del inventario oficial del MINCETUR.** Filtra por
provincia, abre uno.

**Lo que hay que señalar:** el distintivo de **validado**. 234 de 295 pasaron
la validación. Los otros **se muestran marcados, no se ocultan**.

> «Ocultarlos daría un catálogo que parece completo y no lo está.»

### 2. Preferencias y recomendaciones (3 min)

`/preferencias`. Seis pasos. **Sin registrarte** — dilo en voz alta.

Prueba con: sale de `HUANCAYO`, 1 día, S/ 150, `artesania` y `gastronomia`,
`transporte_publico`, ritmo `moderado`.

**Lo que hay que señalar:** cada recomendación dice **por qué**. «Pesaron:
artesanal, taller, mate». Eso no es decoración: es lo que cierra la brecha 2.

Y la **afluencia con su motivo**. Prueba un domingo y un martes: cambia.

### 3. El itinerario (2 min)

**Armar itinerario.** Mapa, horas, distancias, costo.

**Lo que hay que señalar: los avisos de arriba.** Dicen cosas incómodas a
propósito: que un tramo se estimó en línea recta, que hay una parada a 3 706 m
y conviene aclimatarse, o por qué el día quedó corto.

Y los precios con **«aprox.»** y su fecha.

### 4. Coordinar (1,5 min)

`/coordinar`. Dos secciones, y la diferencia importa:

- Los **5 de demostración**, con servicios que se pueden pedir. Marcados.
- Los **162 reales** del directorio del MINCETUR, con RUC y certificado.
  Certificados por el Estado, **sin convenio con el proyecto**.

Pide un servicio. Entra como `proveedor@rutavivamantaro.pe` y confírmalo:
**cada cambio queda registrado con quién y cuándo**.

### 5. Valorar y el panel (1,5 min)

Valora con un comentario con matices. Luego entra como
`gestor@rutavivamantaro.pe` → `/panel` → **Evidencia**.

**Lo que hay que señalar:** el **% negativo por tema**. Es el número que dice
**dónde actuar**. Y que el tablero **avisa solo** de que con pocas valoraciones
las medias son orientativas.

### 6. El asistente (2 min) — el momento fuerte

Botón redondo abajo a la derecha. **Pídele un lugar que no existe:**

```
Quiero visitar el Palacio de la Cultura de Jauja, ¿cómo llego?
```

Consulta el catálogo, no lo encuentra, **lo dice, y no propone un sustituto
inventado**.

**Señala la etiqueta de debajo:** «consultó el catálogo». Eso hace la
conversación auditable.

> ⚠️ **Tarda 25–40 segundos.** Avisa antes de pulsar, o ten una captura
> preparada.

---

## Las preguntas incómodas

### «¿Los indicadores 2 y 4 no son los que proponía tu plan?»

**No lo son, y está documentado.**

El plan pedía «tiempo entre preferencias y confirmación» y «error medio entre
tiempo estimado y real». Los dos exigen datos que **no existen**: uso real con
tiempos, y traslados cronometrados en campo.

Había tres opciones: no medir nada, inventar números, o **medir algo que sí es
medible y decir que sustituye al original**. Se eligió la tercera, y la
sustitución está escrita en la propia respuesta del API, no escondida.

> «Un indicador que no se puede medir y se presenta como medido es peor que
> uno sustituido y declarado.»

### «¿Con 5 valoraciones esto es estadísticamente significativo?»

**No, y el sistema lo dice antes que yo.**

El tablero avisa por sí solo de que con menos de 5 valoraciones las medias son
orientativas, y marca los recursos con pocas. No hay que preguntármelo: está en
pantalla.

### «¿Los proveedores son reales?»

**Los 162 del directorio, sí.** Del Directorio Nacional de Prestadores
Calificados del MINCETUR, datos abiertos con licencia abierta. Con su RUC y su
número de certificado, para que se pueda comprobar.

**Los 5 de demostración, no**, y llevan la palabra «(demostración)» en el
nombre y teléfonos del rango `+51 900 000`, que no corresponde a ningún número
peruano.

**Ninguno tiene convenio con el proyecto**, y la interfaz lo dice arriba.

### «¿Por qué los reales no se pueden reservar?»

Porque **su capacidad y sus precios no están publicados**. Inventarlos sería
exactamente lo que este proyecto dice no hacer. Se enlaza a su teléfono, su web
y Google Maps para que el visitante los contacte él mismo.

Los de demostración se quedan porque **sin ellos no habría ninguna cuenta que
pudiera confirmar una solicitud**, y el ciclo que cierran las brechas 5 y 6
dejaría de poderse enseñar.

### «¿De dónde salen los precios de transporte?»

**De una fórmula documentada, porque no existe ninguna fuente publicada de
tarifas del valle.** Ni el MINCETUR ni el gobierno regional ni las
municipalidades las publican.

Todo costo lleva un **rango**, una **fecha de referencia**, la **fuente** —que
es la fórmula— y la palabra **«aprox.»**.

> «Un número inventado no se puede discutir. Una fórmula publicada sí:
> cualquiera puede mirar los parámetros y decir que está mal calibrada.»

### «¿Usaste IA de verdad o son reglas disfrazadas?»

**Cuatro usos, cada uno medido:**

| Uso | Decisión | El número |
|---|---|---|
| Recomendación | TF-IDF **aceptado** | Encuentra relaciones que las palabras clave no ven |
| Afluencia | LightGBM **rechazado** | No había filas suficientes; el código lo dice |
| Sentimiento | pysentimiento **aceptado** | 11/14 vs 8/14 de las reglas, solo con texto |
| Ruteo | OR-Tools **aceptado** | 302 de afinidad vs 263 del vecino más cercano |

Y **cada uno tiene su alternativa por reglas**, conmutable con el `.env`. Lo
puedo demostrar en vivo.

### «¿Por qué rechazaste un modelo?»

Porque medí y no valía. LightGBM necesitaba histórico que no hay: el Ministerio
de Cultura publica series de visitantes, pero apenas cubren el Valle del
Mantaro.

> «Entrenar un modelo con cuatro datos y presentarlo como si valiera es
> exactamente lo que este proyecto dice no hacer.»

### «¿Por qué no hiciste MLOps?»

**Incorporar modelos de IA no es lo mismo que incorporar MLOps.**

Los modelos se entrenan **una vez** con fuentes externas estables. MLOps
gobierna el **reentrenamiento continuo** de modelos que aprenden de datos que
el propio sistema genera. Eso aparece cuando el Incremento 6 acumule
valoraciones propias.

Antes de eso, MLOps sería **infraestructura sin datos que la justifiquen**.

La tabla `valoracion` **es** esos datos propios. Que ahora existan no significa
que haya que hacer MLOps: significa que empieza a haber un motivo para
plantearlo.

### «¿El asistente puede inventarse un lugar?»

**No, y no por buena voluntad: por arquitectura.**

El modelo no sabe nada del valle. Solo elige qué función del backend responde y
redacta con lo que esa función devuelve. Si pregunta por algo que no está, la
búsqueda devuelve cero y el modelo no tiene de dónde sacarlo.

Te lo demuestro: [ejecutar la prueba del Palacio de la Cultura].

### «¿Qué falló durante el desarrollo?»

**Mucho, y está todo documentado.** Ver [15](15-historial-de-fallos.md).

Los tres que más enseñan:

1. **OR-Tools devolvía 1 parada donde las reglas encontraban 3.** Forzaba
   volver al inicio: un itinerario turístico no es un tour cerrado.
2. **El asistente negaba que Concepción tuviera atractivos.** Tiene trece. Una
   tilde. Es el peor fallo posible aquí: no inventar, sino **negar con aplomo**.
3. **Declaré dos limitaciones que eran falsas.** El README decía que el
   MINCETUR no publica horarios. Era verdad del CSV; la ficha web sí los trae,
   y su dirección estaba guardada desde la Fase 1.

El tercero es el más instructivo: **«la fuente no lo publica» hay que
comprobarlo antes de escribirlo.**

### «¿Por qué un monolito y no microservicios?»

Un equipo, un despliegue. Los microservicios habrían añadido latencia entre
servicios, despliegue distribuido y depuración repartida, **sin resolver ningún
problema que este proyecto tenga**.

Y está prohibido explícitamente en el plan de trabajo.

### «¿Esto funciona en inglés?»

Entero. **581 claves**, incluidos los avisos que genera el backend, que viajan
como código y parámetros. Cámbialo con el selector y recorre lo que quieras.

Lo que no se traduce, a propósito: los nombres del catálogo del MINCETUR, la
atribución de OpenStreetMap y lo que escriben los proveedores.

---

## Lo que NO hay que decir

| No digas | Di |
|---|---|
| «El sistema predice la afluencia» | «La estima con reglas de calendario, y dice cuál usó» |
| «Tenemos los precios» | «Los estimamos con una fórmula documentada, y se marca» |
| «El asistente es la innovación» | «Es capa de interacción: no cierra ninguna brecha» |
| «Los indicadores demuestran que funciona» | «Miden lo que se puede medir hoy, y cada uno dice qué no dice» |
| «Trabajamos con proveedores del valle» | «Cargamos el directorio oficial. No hay convenios» |

---

## Los números que conviene tener a mano

| | |
|---|---|
| Recursos del catálogo | **295**, 79,32 % validados |
| Con descripción y horario | 295 / 208 |
| Conteos reales de visitantes | **414 filas** |
| Prestadores reales | **162** |
| Festividades | 69 (2026–2028) |
| Endpoints | **43** |
| Pruebas | **549 backend** (73 %) + **148 frontend** |
| Idiomas | 2, con 581 claves simétricas |
| Commits | 98, todos en `main` |

---

## Relacionado

- [10 — Los indicadores](10-indicadores.md)
- [15 — Historial de fallos](15-historial-de-fallos.md)
- [16 — Pendientes y limitaciones](16-pendientes-y-limitaciones.md)
