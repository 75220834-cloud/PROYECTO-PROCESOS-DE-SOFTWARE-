# Indicador 4 — Itinerarios viables y trazables

**Incremento:** 4 — Ruteo geoespacial multimodal
**Brecha que mide:** 4 — *el proceso no incorporaba la distribución geográfica
ni el tiempo y costo de desplazamiento*
**Estado:** implementado, **sustituyendo al indicador propuesto**

---

## Antes que nada: este no es el indicador que decía el plan

`CONTEXTO_PROYECTO.md` propone para el Incremento 4:

> «Error medio entre tiempo de traslado estimado y real»

**Ese indicador no se puede medir hoy, y decir que sí sería mentir.** Calcularlo
exige tiempos de traslado **reales observados**: alguien que haga los trayectos
con un cronómetro, o una fuente que los publique. No existe ninguna de las dos
cosas.

Lo que se podría hacer para «cumplir» sin tener el dato:

| Atajo | Por qué no se hizo |
|---|---|
| Comparar la estimación con otra estimación (Google Maps, OSRM) | Mediría el acuerdo entre dos modelos, no el error frente a la realidad. Y el nombre del indicador diría «real» |
| Usar las cinco distancias verificadas de `CONTEXTO_PROYECTO.md` | Son **distancias**, no tiempos, y son cinco. Un «error medio» sobre cinco pares no es una media de nada |
| Inventar un porcentaje creíble | Es exactamente lo que este proyecto se comprometió a no hacer |

Sí se hizo el contraste que **sí** era posible, y está registrado: la ruta
Ocopa → Concepción sobre la red vial da 6,50 km frente a los 5,50 km publicados
(+18 %). Es un punto de comparación, no un indicador.

Así que se mide otra cosa, se dice que es otra cosa, y se explica cuál. El
indicador propuesto queda **pendiente** hasta que el Incremento 6 acumule
experiencias reales: cuando un visitante confirme que hizo un itinerario, sus
tiempos serán la primera verdad de campo que tenga el proyecto.

Es la misma clase de decisión que se tomó con MLOps y con el indicador 3:
**medir lo que se puede sostener, y declarar lo que no.**

---

## Qué mide

El porcentaje de itinerarios generados que son **viables** —que se pueden
seguir de verdad— y **trazables** —que dicen de dónde sale cada número—.

Un itinerario cuenta como viable y trazable si cumple las seis condiciones:

| # | Condición | Por qué |
|---|---|---|
| 1 | Se calcula en menos de 10 segundos | Un planificador que tarda medio minuto no se usa |
| 2 | Ninguna parada empieza antes de que acabe la anterior | Un horario que se solapa no es un horario |
| 3 | Ninguna parada se sale de la jornada ni del horario del recurso | Llegar a un museo cerrado es peor que no ir |
| 4 | El costo máximo no supera el presupuesto de traslado del día | La restricción de presupuesto es una de las cuatro del plan |
| 5 | Ningún recurso aparece dos veces | |
| 6 | Cada traslado lleva su fuente, su fecha y su rango de precio | Sin eso, el número es un rumor |

Y, además, **se avisa cuando algún tramo se estimó** por falta de cobertura de
OpenStreetMap.

## Por qué se mide esto y no «la calidad del itinerario»

Porque «calidad» no es medible hoy sin inventarse la vara de medir. Haría falta
que alguien recorriera los itinerarios y dijera si estuvieron bien, y esa
anotación no existe.

Lo que sí se puede afirmar sin inventar nada es que el itinerario **no
contradice ninguna de las restricciones que el propio sistema declara**. Es un
listón más bajo, pero es un listón real.

Es la misma decisión que se tomó en el [indicador 3](03-recomendaciones-sin-error.md),
y por el mismo motivo.

## Cómo se calcula

```bash
cd backend
.venv/Scripts/python.exe -m app.utilidades.verificar_fase4
```

El script arma un itinerario para cuatro perfiles deliberadamente distintos
—distinto distrito de origen, distinta movilidad, distinto ritmo— sobre el
catálogo real de 295 recursos, y comprueba las seis condiciones en cada uno.

## Medición del 29 de agosto de 2026

| Perfil | Paradas | Tiempo | Costo máx. | Presupuesto | Tramos reales / estimados |
|---|---|---|---|---|---|
| Huancayo, cultura, transporte público | 5 | 5,05 s | S/ 14,50 | S/ 58,33 | 4 / 0 |
| Huancayo, naturaleza, taxi | 1 | 2,53 s | S/ 0,00 | S/ 70,00 | 0 / 0 |
| Chupaca, artesanía, caminando | 1 | 0,03 s | S/ 0,00 | S/ 35,00 | 0 / 0 |
| Jauja, todo, ritmo intenso | 7 | 3,35 s | S/ 18,50 | S/ 93,33 | 4 / 2 |

**Resultado: 4 de 4 (100 %).**
Tiempo máximo **5,05 s** frente al tope de 10 s. Tiempo medio 2,74 s.

Los tiempos varían unas décimas entre ejecuciones: el optimizador agota su
límite de búsqueda de 2 segundos y el resto depende de cuántos tramos haya que
refinar sobre el grafo. La medición que importa es que el peor caso queda a la
mitad del tope.

### Sobre los dos itinerarios de una sola parada

No son fallos, y el sistema **explica cada uno**:

- **Taxi desde Huancayo:** el trayecto más barato hacia el siguiente recurso
  cuesta hasta S/ 81 y el presupuesto de traslado del día es de S/ 70. El
  itinerario lo dice con las dos cifras y sugiere combi o colectivo.
- **Caminando desde Chupaca:** con un alcance de 8 km y esos intereses solo hay
  un recurso alcanzable. El itinerario lo dice y sugiere ampliar los intereses
  o usar transporte.

Que un indicador salga «bien» con dos itinerarios de una parada sería un
indicador malo si el sistema los entregara en silencio. La condición que
salva esto es la 6, y sobre todo el aviso: **el visitante sabe siempre por qué
el día quedó corto.**

## Lo que este indicador NO dice

- **No dice que los tiempos sean correctos.** Dice que se calcularon sobre la
  red vial real donde la hay, y que se avisó donde no.
- **No dice que los precios sean correctos.** No hay tarifas verificadas en el
  valle; los precios son estimaciones declaradas. Ver
  [Cómo se calculan las tarifas de transporte](../decisiones/2026-08-29-como-se-calculan-las-tarifas-de-transporte.md).
- **No dice que se respeten los horarios de apertura reales.** La restricción
  está implementada y probada, pero la tabla `horario_atencion` está vacía
  porque el MINCETUR no publica horarios. El itinerario avisa de ello.

## Dónde se ve

| Qué | Dónde |
|---|---|
| Script de medición | `backend/app/utilidades/verificar_fase4.py` |
| Servicio | `backend/app/servicios/ruteo.py` |
| Endpoint | `POST /api/itinerarios` |
| Interfaz | `/preferencias/{id}/itinerario` |
| Pruebas | `backend/pruebas/test_ruteo.py`, `backend/pruebas/test_rutas_itinerarios.py` |

## Relacionado

- [Por qué se aceptó OR-Tools y cómo se calibró](../decisiones/2026-08-29-por-que-se-acepto-or-tools-y-como-se-calibro.md)
- [Cobertura de OpenStreetMap en el valle](../decisiones/2026-08-29-cobertura-de-openstreetmap-en-el-valle.md)
