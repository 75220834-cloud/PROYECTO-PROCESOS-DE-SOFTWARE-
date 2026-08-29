# Indicador 3 — Recomendaciones sin error respecto de las preferencias

**Incremento:** 3 — Recomendación inteligente y predicción de afluencia
**Brechas que mide:** 2 y 3
**Estado:** implementado, con una salvedad que hay que declarar

---

## Qué mide

El porcentaje de recomendaciones que **respetan las restricciones declaradas**
por el visitante.

## La salvedad, dicha desde el principio

El nombre del indicador puede leerse de dos maneras, y solo una es medible hoy:

| Lectura | ¿Medible? | Por qué |
|---|---|---|
| «Ninguna recomendación viola una restricción declarada» | ✅ **Sí** | Las restricciones son objetivas y comprobables |
| «Las recomendaciones son las que el visitante habría elegido» | ❌ **No** | Haría falta un conjunto anotado que nadie ha construido |

**Se mide la primera.** Medir la segunda exigiría que alguien anotara a mano
cuáles de los 234 recursos son «correctos» para cada perfil, y esa anotación
sería una opinión disfrazada de verdad. Inventarla para poder publicar un
número bonito es exactamente lo que este proyecto se comprometió a no hacer.

## Cómo se calcula

```
porcentaje = 100 × recomendaciones_sin_violacion / total_recomendaciones
```

Una recomendación **viola** una restricción si:

1. No tiene coordenadas (no podría entrar en un itinerario).
2. No pasó la validación del catálogo.
3. Está fuera del alcance de la movilidad declarada.
4. No cubre ninguno de los intereses marcados.

Las tres primeras las garantiza la **Capa 0 — filtros duros**, que se aplica
antes de puntuar nada. La cuarta la garantiza el filtro final, que descarta los
recursos con afinidad cero.

## Medición vigente

**100 %**, y por construcción: un recurso que viola cualquiera de las cuatro
condiciones no llega a la lista. Está comprobado en
`backend/pruebas/test_rutas_recomendaciones.py`, clase `TestFiltrosDuros`.

Que salga 100 % no es un logro impresionante: es lo mínimo exigible. Su valor
está en que **el sistema puede demostrar por qué**, recurso a recurso, y eso es
justamente lo que la brecha 2 echaba en falta.

## Lo que sí es informativo: los descartes

Cada recomendación devuelve también lo que se descartó y por qué. Para una
preferencia típica desde Huancayo, en taxi:

| Motivo del descarte | Recursos |
|---|---|
| Sin coordenadas en la fuente oficial | 61 |
| Fuera del alcance de la movilidad | variable según el distrito de origen |

Ese conteo sí dice algo: **la calidad de la fuente oficial es el techo de lo
que el sistema puede recomendar**. Con 61 recursos sin coordenadas, hay un
20,7 % del catálogo que ningún itinerario podrá incluir mientras el MINCETUR no
los georreferencie.

## Dónde vive

| Pieza | Ubicación |
|---|---|
| Capa 0 — filtros duros | `backend/app/servicios/recomendador.py` |
| Capa 1 — afinidad | `backend/app/ia/afinidad.py` |
| Capa 2 — afluencia | `backend/app/ia/afluencia.py` |
| Endpoint | `POST /api/recomendaciones` |
| En la interfaz | `/preferencias/{id}/resultados` |
| Experimentos | `backend/notebooks/01_incremento3_afinidad_y_afluencia.ipynb` |

## Cómo comprobarlo a mano

1. Completa el asistente eligiendo **«caminando»** como movilidad.
2. En la pantalla de resultados, abre «recursos descartados».
3. Comprueba que los descartados por distancia están todos a más de 8 km, que
   es el alcance declarado para ir a pie.
