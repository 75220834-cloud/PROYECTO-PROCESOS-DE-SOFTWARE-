# ADR-007 — Se acepta OR-Tools para el ruteo, con recorrido abierto y peso de afinidad calibrado

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 4 — ruteo geoespacial multimodal (brecha 4) |
| **Atributo de calidad principal** | **Rendimiento** (calidad de la solución dentro de un tiempo acotado) |
| **Atributos secundarios** | Usabilidad (el canje se muestra, no se esconde) |
| **Interruptor** | `USAR_MODELO_RECOMENDACION` |
| **Nota de origen** | [`2026-08-29-por-que-se-acepto-or-tools-y-como-se-calibro.md`](../decisiones/2026-08-29-por-que-se-acepto-or-tools-y-como-se-calibro.md) |

---

## Contexto

Aplicación de la regla de oro de IA al ruteo:

- **Modelo:** OR-Tools, ruteo con ventanas de tiempo (VRPTW) en su variante de
  recolección de premios (*prize-collecting*).
- **Alternativa por reglas:** vecino más cercano con verificación de horarios.
- **Pregunta a responder con datos:** ¿el optimizador supera al vecino más
  cercano?

## Decisión

**Se acepta OR-Tools**, con dos decisiones de modelado que son la sustancia de
este ADR.

### 1. El recorrido es abierto: un día de turismo no es un circuito cerrado

La primera medición dijo que el optimizador **perdía**: devolvía **1 parada**
donde el vecino más cercano encontraba **3** con el mismo presupuesto.

La causa era un error de modelado, no del algoritmo:

```python
gestor = pywrapcp.RoutingIndexManager(tamano, 1, 0)   # empieza Y TERMINA en el nodo 0
```

Eso declara que el vehículo vuelve al punto de partida. Es correcto para un
camión de reparto y **falso para un visitante**, que termina donde termina y se
va a dormir. Estaba cobrando el regreso en tiempo y en presupuesto.

Corregido con un **nodo ficticio de fin de día**, al que se llega gratis desde
cualquier sitio:

```python
gestor = pywrapcp.RoutingIndexManager(reales + 1, 1, [0], [fin_del_dia])
```

Con el recorrido abierto, la segunda medición (Huancayo, arqueología +
naturaleza + gastronomía, ritmo moderado, S/ 450 a tres días):

| Camino | Paradas | Afinidad acumulada | km | min de viaje |
|---|---|---|---|---|
| Vecino más cercano | 5 | 263 | 14,8 | 71 |
| **OR-Tools** | **5** | **302** | **57,1** | **151** |

**+39 puntos de afinidad (+14,8 %)**, que es el objetivo que fija el plan:
*maximizar el puntaje de afinidad acumulado dentro del tiempo disponible*.

### 2. El peso de la penalización está calibrado, no elegido

«Maximizar afinidad» se traduce haciendo opcional cada visita con
`AddDisjunction` y penalizando saltársela en proporción a su afinidad. Ese peso
decide el canje entre *visitar un sitio que encaja mejor* y *pasar la mañana en
una combi*. Se midió:

| Peso | Paradas | Afinidad | km | min |
|---|---|---|---|---|
| 1 | 5 | 263 | 14,8 | 71 |
| 2 | 5 | 288 | 38,9 | 107 |
| **3** | **5** | **302** | **57,1** | **151** |
| 5 · 10 · 20 | 5 | 302 | 57,1 | 151 |

A partir de 3 la afinidad **se satura**. Se toma **el peso más bajo que alcanza
el óptimo**, para que el tiempo de viaje siga desempatando entre soluciones de
igual afinidad.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Vecino más cercano (la alternativa por reglas)** | Se conserva y se prueba, pero cae en la trampa clásica: se lleva el recurso más próximo al inicio aunque sea el de menor afinidad. Hay una prueba que construye ese escenario y comprueba que las reglas caen y el optimizador no. |
| **Descartar OR-Tools tras la primera medición** | Era lo que mandaba la regla de oro, y estuvo a punto de hacerse. Antes de descartarlo se buscó la causa, y la causa era mío, no del algoritmo. **Descartarlo habría sido descartar la herramienta correcta por un error de modelado propio.** |
| **Peso de penalización 10 o 20** | No mejoran la afinidad (saturada en 3) y solo añadirían kilómetros si el problema cambiara. |
| **Circuito cerrado (volver al inicio)** | Modela un reparto, no un día de turismo. Es el error que causó el falso negativo. |

## Consecuencias

**Positivas**

- +14,8 % de afinidad acumulada sobre la línea base, medido.
- Tiempo de resolución acotado: en la verificación de los 4 perfiles, entre
  **2,51 s y 6,75 s** por itinerario, con tope declarado de 10 s.
- La alternativa por reglas sigue viva y **sirvió como detector**: sin ella, el
  fallo del circuito cerrado no se habría visto.

**Negativas, y mostradas al visitante en lugar de esconderlas**

- Los 39 puntos de afinidad se pagan con **+42 km y +80 minutos** de transporte.
  El objetivo que fija el plan es maximizar afinidad y se respeta, pero la
  interfaz muestra tiempo y costo de cada traslado para que la decisión no quede
  oculta.
- **El fallo lo encontró usar la aplicación en el navegador, no la suite de 33
  pruebas**, que pasaba entera con el error dentro porque ninguna comparaba las
  dos vías bajo un presupuesto que apretara. Se añadieron dos pruebas de
  regresión que sí lo cazan.

### La restricción que está implementada y no tiene datos

| Restricción | Estado |
|---|---|
| Hora de inicio y fin del día | Activa (8:00–18:00 por omisión) |
| Duración de la visita | Activa, con duración por categoría **supuesta** |
| Presupuesto de traslado | Activa |
| **Horario de atención** | **Implementada y probada, con datos parciales** |

Cuando se tomó esta decisión la tabla `horario_atencion` estaba **vacía** y se
decidió no inventar horarios. El ADR-002 aportó después **208 horarios** leídos
de la ficha web, así que la restricción ya muerde en el 71 % de los recursos. En
el 29 % restante el itinerario **avisa** de que no puede garantizar que estén
abiertos.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_ruteo.py pruebas/test_rutas_itinerarios.py -v
```

```bash
cd backend && .venv/Scripts/python.exe -m app.utilidades.verificar_fase4
```

## Relacionado

- [ADR-006 — Dos modos de cálculo de distancia](ADR-006-dos-modos-de-calculo-de-distancia.md)
- [ADR-004 — Se acepta TF-IDF](ADR-004-se-acepta-tfidf-para-la-afinidad.md)
