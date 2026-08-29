# Por qué se aceptó OR-Tools, cómo se calibró, y el fallo que casi lo tumba

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** Incremento 4 — ruteo geoespacial multimodal (brecha 4)

## La decisión que había que tomar

La regla de oro de la IA del proyecto dice que **toda funcionalidad con modelo
mantiene una alternativa por reglas explícitas**, y que si el modelo no supera
su línea base, se entrega la alternativa y el modelo vuelve al backlog.

Aquí:

- **Modelo:** OR-Tools, problema de ruteo con ventanas de tiempo (VRPTW) en su
  variante de recolección de premios.
- **Alternativa por reglas:** vecino más cercano con verificación de horarios.
- **Interruptor:** `USAR_MODELO_RECOMENDACION` en el `.env`.

Y la pregunta a responder con datos, no con opiniones: **¿el optimizador supera
al vecino más cercano?**

## Primera medición: el optimizador perdía

La primera respuesta fue que **no**. Con la preferencia de prueba en taxi,
OR-Tools devolvía **una parada** mientras el vecino más cercano encontraba
**tres** con el mismo presupuesto.

Un optimizador que queda por debajo de su propia línea base no es un
optimizador: es un rodeo caro para llegar a un resultado peor. Por la regla de
oro, tocaba descartarlo.

Antes de descartarlo se buscó la causa, y la causa era un error de modelado, no
del algoritmo.

### El error: un día de turismo no es un circuito cerrado

```python
gestor = pywrapcp.RoutingIndexManager(tamano, 1, 0)
```

Esa línea declara que el vehículo empieza **y termina** en el nodo 0. OR-Tools
está pensado para vehículos de reparto, que vuelven al almacén. Estaba cobrando
el regreso a la primera parada en tiempo y en dinero del presupuesto.

Pero un visitante no vuelve al primer museo al final del día: termina donde
termina y se va a dormir. El regreso no existe.

La corrección estándar es añadir un **nodo ficticio de fin de día** al que se
llega gratis desde cualquier sitio:

```python
gestor = pywrapcp.RoutingIndexManager(reales + 1, 1, [0], [fin_del_dia])
```

Así el recorrido queda abierto.

### Cómo se encontró

**Usando la aplicación en el navegador, no con una prueba.** La suite de 33
pruebas del optimizador pasaba entera con el fallo dentro, porque ninguna
comparaba los dos caminos bajo una restricción de presupuesto que apretara.

Se añadieron dos pruebas de regresión que sí lo cazan:

- `test_el_dia_no_obliga_a_volver_a_la_primera_parada` — el presupuesto da
  exactamente para dos traslados de ida; si se cobrara la vuelta, solo cabría
  uno.
- `test_el_optimizador_nunca_entrega_menos_paradas_que_las_reglas_con_el_mismo_dinero`

## Segunda medición: el optimizador gana

Con el recorrido abierto, sobre la preferencia de prueba (Huancayo, arqueología
+ naturaleza + gastronomía, ritmo moderado, S/ 450 a tres días):

| Camino | Paradas | Afinidad acumulada | km | min de viaje |
|---|---|---|---|---|
| Vecino más cercano | 5 | 263 | 14,8 | 71 |
| **OR-Tools** | **5** | **302** | **57,1** | **151** |

**+39 puntos de afinidad (+14,8 %)**, que es el objetivo que fija el plan de
trabajo: *maximizar el puntaje de afinidad acumulado dentro del tiempo
disponible*.

Hay además una prueba que construye la trampa clásica del vecino más cercano
—el recurso más próximo al inicio es el de menor afinidad— y comprueba que las
reglas caen en ella y el optimizador no:

```python
assert 1 in con_reglas      # el vecino más cercano se lleva el de afinidad 5
assert 1 not in con_modelo  # el optimizador lo evita
```

**Veredicto: OR-Tools aceptado.**

## Cómo se calibró el peso de la afinidad

OR-Tools minimiza. «Maximizar afinidad» se traduce haciendo opcional cada
visita con `AddDisjunction` y penalizando el saltársela en proporción a su
afinidad. El peso de esa penalización decide el canje entre *visitar un sitio
que encaja mejor* y *pasar la mañana en una combi*.

No hay un valor obviamente correcto, así que **se midió**:

| Peso | Paradas | Afinidad | km | min de viaje |
|---|---|---|---|---|
| 1 | 5 | 263 | 14,8 | 71 |
| 2 | 5 | 288 | 38,9 | 107 |
| **3** | **5** | **302** | **57,1** | **151** |
| 5 | 5 | 302 | 57,1 | 151 |
| 10 | 5 | 302 | 57,1 | 151 |
| 20 | 5 | 302 | 57,1 | 151 |

A partir de 3 la afinidad **se satura**: subir más el peso no mejora el
objetivo y solo añadiría kilómetros si el problema fuera otro. Se toma **el
peso más bajo que alcanza el óptimo**, para que el tiempo de viaje siga
desempatando entre soluciones de igual afinidad.

La tabla también deja ver, sin maquillarlo, **el precio que paga el visitante**
por esos 39 puntos: +42 km y +80 minutos de transporte. El objetivo que fija el
plan es maximizar afinidad y se respeta, pero la interfaz muestra el tiempo y
el costo de cada traslado para que esa decisión no quede escondida.

## Las cuatro restricciones, y cuál no tiene datos

| Restricción | Estado |
|---|---|
| Hora de inicio y fin del día | Activa (8:00–18:00 por omisión) |
| Duración de la visita | Activa, con duración por categoría **supuesta** |
| Presupuesto de traslado | Activa |
| **Horario de atención** | **Implementada y probada, pero sin datos** |

La tabla `horario_atencion` está **vacía**: el Inventario Nacional de Recursos
Turísticos del MINCETUR no publica horarios de apertura. Se decidió no
inventarlos.

Lo que sí se hizo:

1. La restricción está implementada y **actúa en cuanto haya datos**.
2. Hay cuatro pruebas que insertan horarios a mano y comprueban que muerde: un
   recurso que abre media hora no entra; ninguna visita termina después del
   cierre; ninguna empieza antes de la apertura; el horario de un martes no
   afecta a un sábado.
3. El itinerario **avisa al visitante** de que esos horarios no se conocen y de
   que confirme antes de ir.

Es la única postura honesta: la alternativa era suponer «abre de 9 a 17» para
295 recursos y presentar como restricción cumplida algo que no se ha
comprobado.

## Cómo verificarlo

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_ruteo.py pruebas/test_rutas_itinerarios.py -v
```

## Relacionado

- [Cómo se calculan las tarifas de transporte](2026-08-29-como-se-calculan-las-tarifas-de-transporte.md)
- [Cobertura de OpenStreetMap en el valle](2026-08-29-cobertura-de-openstreetmap-en-el-valle.md)
- [Por qué se aceptó TF-IDF y se descartó LightGBM](2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md)
  — la misma regla de oro aplicada en el Incremento 3
