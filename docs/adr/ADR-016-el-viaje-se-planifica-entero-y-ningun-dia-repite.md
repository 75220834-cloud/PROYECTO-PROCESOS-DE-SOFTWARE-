# ADR-016 — El viaje se planifica entero, y ningún día repite los lugares de otro

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 30 de septiembre de 2026 |
| **Incremento** | 4 — ruteo geoespacial multimodal (brecha 4) |
| **Atributo de calidad principal** | **Corrección funcional** (el resultado es el que el visitante espera) |
| **Atributos secundarios** | Rendimiento (una llamada en vez de una por día), Usabilidad (cambiar de día es instantáneo) |
| **Interruptor** | Ninguno. No es una decisión de modelo: es la corrección de un defecto |
| **Defecto que la origina** | [D-29](../referencia/20-registro-de-defectos.md) |

---

## Contexto

Un viaje de tres días devolvía **tres veces el mismo día**: los mismos lugares,
en el mismo orden, con las mismas horas, los mismos costos y los mismos avisos.
Lo único que cambiaba entre las pestañas Día 1, Día 2 y Día 3 era la fecha.

No era un fallo del optimizador ni del recomendador. Los dos hacían exactamente
lo que se les pedía. El fallo estaba **en cómo se les preguntaba**:

1. La pantalla pedía un día por pestaña: `POST /api/itinerarios` con una fecha.
2. Ese endpoint llamaba a `recomendar(sesion, preferencia, …)`, que **no recibe
   la fecha**: solo la preferencia. Para la misma preferencia devolvía siempre
   la misma lista de recursos, en el mismo orden.
3. El optimizador recibía los mismos 20 candidatos, el mismo presupuesto por
   día, el mismo horario y el mismo ritmo. **Y es determinista.**

Entradas idénticas, salida idéntica. La fecha solo intervenía en un sitio —qué
día de la semana es, para consultar el horario de atención— y, cuando los
horarios no distinguen entre jueves, viernes y sábado, no cambiaba nada.

**Y en ningún punto del backend existía la idea de «esto ya está en otro día».**
No es que estuviera roto: nunca se construyó. `recomendar()` ni siquiera tiene
un parámetro para excluir recursos.

## Decisión

**El viaje se planifica entero, en una sola operación, y los días se reparten en
cascada.**

### 1. Un endpoint para el viaje, no uno por día

Se añade `POST /api/itinerarios/viaje`, que devuelve un itinerario por cada
fecha de la preferencia. El endpoint de un día, `POST /api/itinerarios`, **se
mantiene sin cambios**: lo usa el recálculo al reordenar paradas, que trabaja
sobre un día concreto y no debe reoptimizar nada.

La razón de fondo es que **pedir los días por separado no puede resolver el
problema**. Cada petición es independiente por definición; para repartir hace
falta ver los días juntos, y para verlos juntos hay que pedirlos juntos.

### 2. El reparto es en cascada, que es lo que hace una persona

```
Día 1  →  se arma con todo el repertorio        → es el mejor día posible
          sus lugares salen del repertorio
Día 2  →  se arma con lo que queda               → el mejor de lo que sobra
          sus lugares salen del repertorio
Día 3  →  se arma con lo que queda               → y así hasta el último
```

Cada día conserva todo lo que ya tenía: su propio orden, sus horarios con el
horario de atención del día de la semana que le toca, sus totales y sus avisos.
Lo único que cambia es que ninguno puede proponer lo que otro ya propuso.

### 3. El repertorio crece con los días, pero con tope

Un día suelto se resolvía con 20 candidatos como máximo
(`MAXIMO_CANDIDATOS`), un número medido: 380 traslados en la matriz, menos de un
segundo. Para un viaje eso no basta: con ritmo intenso, tres días consumen 24
lugares y el día 3 se quedaría sin nada **teniendo el catálogo recursos de
sobra**.

Se pide `paradas por día × días + margen`, con un tope de
`TOPE_DE_CANDIDATOS_DEL_VIAJE = 45`. El tope no es estético: **la matriz crece
con el cuadrado**. 45 candidatos son 1 980 traslados; 60 serían 3 540, y la
documentación del proyecto ya tenía medido que ahí la espera se empieza a notar.

Un viaje de un solo día sigue pidiendo exactamente 20, para no cambiar por la
puerta de atrás un número que está medido.

### 4. Cuando se acaban los lugares, se dice. No se repite para rellenar

Un viaje largo puede agotar el repertorio. Cuando pasa, el día sale con las
paradas que haya —o sin ninguna— y lleva su aviso:

| Código | Cuándo |
|---|---|
| `lugares_limitados` | El día tiene menos paradas de las que permite el ritmo porque se está agotando el repertorio |
| `sin_lugares_sin_repetir` | Al día no le quedó ningún lugar nuevo |

Los dos viajan como `{codigo, parametros}` según el [ADR-013](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md)
y están traducidos en los dos idiomas.

**Es la misma regla de honestidad que el resto del proyecto.** Rellenar el día 3
con los lugares del día 1 sería más cómodo y se vería más completo, que es
exactamente lo que estaba pasando antes sin que nadie lo decidiera.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Exclusión secuencial en el endpoint de un día** | Para servir el día 3 habría que resolver antes el 1 y el 2, en cada clic de pestaña. Medido: el viaje de tres días tarda 18,9 s en total; con esta vía el día 3 costaría eso **cada vez que se pulsa la pestaña**, y un viaje largo sería inaceptable. Además el repertorio ampliado encarece cada resolución, así que multiplica justo lo que ya es caro. |
| **Leer de la base de datos los días anteriores** | No hay nada que leer: la pantalla pide los días con `guardar: false`, porque calcular sin guardar es lo que permite probar combinaciones sin llenar la tabla de borradores. Habría que empezar a guardar cada día que alguien mire, que es una decisión peor por un motivo ajeno. |
| **Repartir el repertorio por bloques de ranking** | El día 1 se lleva los puestos 1–6, el día 2 los 7–12, y así. Es barato y no repite, pero el reparto es arbitrario: el día 2 podría quedar con seis lugares en seis distritos distintos mientras el día 1 se queda con seis vecinos. La cascada deja que el optimizador decida con la geografía delante. |
| **Declararlo como limitación conocida** | Era una opción honesta y se puso sobre la mesa. Se descartó porque es un defecto visible en treinta segundos de uso, no una limitación de los datos. |
| **Repetir lugares cuando se agote el repertorio** | Es lo que hacía el defecto. Rellenar con lo mismo y no decirlo contradice la regla de honestidad del proyecto. |

## Consecuencias

**Positivas**

- Los días del viaje son distintos y **ningún lugar se propone dos veces**.
  Verificado contra el sistema levantado con el caso que se reportó: tres días,
  5 + 4 + 4 paradas, **0 repetidos**.
- **Cambiar de pestaña es instantáneo**: los días ya están en la respuesta, así
  que no hay ninguna petición al pulsar Día 2.
- Una sola llamada en vez de una por día.
- Las fechas de las pestañas salen de la propia respuesta, así que la interfaz y
  el reparto no pueden discrepar. Antes el navegador las calculaba por su cuenta
  sumando días en UTC.

**Negativas, declaradas**

- **La primera carga tarda más**, porque arma todos los días y no uno. Medido:
  18,9 s para tres días, frente a entre 5 y 17 s para uno. El costo es lineal
  con los días, así que un viaje de siete días tardaría alrededor de 45 s. El
  texto de la pantalla de espera lo dice: *«cuantos más días, más tarda»*.
- **Un viaje más largo que el tope de repertorio tendrá días con menos
  paradas.** Es una consecuencia real y la aplicación la declara con su aviso.
  La alternativa sería repetir, y eso es el defecto otra vez.

## Lo que esto dice del proceso de pruebas

El defecto convivía con **697 pruebas en verde**, incluidas 33 del ruteo y 33 de
los endpoints del itinerario. Ninguna lo veía porque **todas miraban un día en
aislamiento**, y un día en aislamiento era correcto. Entre ellas había una
llamada `test_ningun_recurso_se_repite`… que comprobaba que no se repitiera
*dentro* del mismo día.

El agujero no estaba en la cantidad de pruebas sino en su alcance: no había
ninguna que mirara **dos días a la vez**. Se añadieron:

- `test_ningun_lugar_aparece_en_dos_dias` y
  `test_ningun_lugar_se_repite_entre_los_tres_dias` (API);
- `test_los_dias_no_son_el_mismo_itinerario`, que compara los planes completos
  porque así es como se vio el defecto;
- `cada día del viaje trae un plan distinto, sin repetir lugares` (E2E, sobre la
  pantalla real).

**Las tres se comprobaron desactivando a propósito el reparto**: con el código
roto fallan las tres, y vuelven a pasar al restaurarlo. Una prueba de regresión
que también pasa con el defecto dentro no prueba nada.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_ruteo.py pruebas/test_rutas_itinerarios.py -v
```

```bash
cd frontend && npx playwright test e2e-04-itinerario.spec.ts
```

## Relacionado

- [ADR-007 — Se acepta OR-Tools con recorrido abierto](ADR-007-se-acepta-or-tools-con-recorrido-abierto.md)
- [ADR-013 — Los avisos viajan como código y parámetros](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md)
- [20 — Registro de defectos](../referencia/20-registro-de-defectos.md), D-29
