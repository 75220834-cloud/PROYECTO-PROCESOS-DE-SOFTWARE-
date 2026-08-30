# Por qué se aceptó pysentimiento, y por qué la primera medición era tramposa

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** Incremento 6 — valoración de cierre y evidencia (brecha 7)

## La decisión que había que tomar

La regla de oro de la IA del proyecto exige que toda funcionalidad con modelo
tenga una alternativa por reglas, y que **si el modelo no supera su línea base,
se entrega la alternativa y el modelo vuelve al backlog**.

- **Modelo:** pysentimiento, RoBERTuito en español, local.
- **Reglas:** puntuación + diccionario de palabras con negaciones.
- **Interruptor:** `USAR_MODELO_SENTIMIENTO` en el `.env`.

## Primera medición: las reglas ganaban

Sobre trece frases de reseña con su clasificación esperada:

| | Aciertos | Tiempo total |
|---|---|---|
| **Reglas** | **13/13** | 5,6 ms |
| Modelo | 11/13 | 11 403 ms |

Las reglas acertaban todo y eran **dos mil veces más rápidas**. Por la regla de
oro, el modelo tocaba descartarlo.

## Y era tramposa, por dos motivos

**El grave: las reglas veían la puntuación y el modelo no.**

Las reglas parten del número de estrellas y usan el texto para corregirlo. El
modelo solo recibía el texto. Eso no compara comprensión del lenguaje: compara
«estrellas + diccionario» contra «solo texto», y la puntuación es el dato más
predictivo que hay en una reseña.

**El otro: las frases las escribió la misma persona que escribió el
diccionario.** Ese sesgo no se puede quitar sin un conjunto anotado por
terceros, que no existe, y se declara.

## Segunda medición, aislando el texto

Se le pasa a las reglas una puntuación de 3 —la que no aporta nada— para que su
veredicto salga solo del diccionario. Catorce frases, la mitad con vocabulario
que **no** está en el diccionario:

| | Aciertos |
|---|---|
| Reglas (solo texto) | 8/14 |
| **Modelo (solo texto)** | **11/14** |

Las reglas fallan donde era previsible que fallaran:

| Frase | Reglas | Modelo |
|---|---|---|
| «La verdad es que superó todas nuestras expectativas.» | neutro ✗ | positivo ✓ |
| «Nos arrepentimos de haber ido hasta allá.» | neutro ✗ | negativo ✓ |
| «Nos hicieron esperar dos horas bajo el sol y nadie se disculpó.» | neutro ✗ | negativo ✓ |
| «Muy bonito todo, lástima que cerraran justo cuando llegamos.» | **positivo ✗** | negativo ✓ |

La última es la peor: el diccionario ve «bonito» y clasifica como positiva una
queja. Un diccionario no puede leer ironía, y las reseñas están llenas de ella.

## Lo que se hizo con esa información

**No** se eligió una vía y se descartó la otra. Se le dio al modelo el dato que
se le estaba ocultando:

```python
# El modelo lee el texto; la puntuación aporta su señal; el modelo solo se
# impone al número cuando está seguro.
CONFIANZA_PARA_IMPONERSE = 0.70
```

El umbral también está medido: los dos fallos del modelo venían con confianza
**0,52 y 0,67**, y sus aciertos con **0,80–0,98**. El 0,70 separa los dos
grupos.

### Medición final

| | Con la puntuación | Solo texto |
|---|---|---|
| Reglas | 13/13 | 8/14 |
| **Modelo** | **13/13** | **12/14** |

Empatan donde el número lo dice casi todo, y el modelo gana claramente donde
hay que leer. **Modelo aceptado.**

## Un caso destapó una inconsistencia

«Estuvo normal, nada del otro mundo.» con 3 estrellas seguía saliendo
*positivo*, porque la primera versión trataba el 3 como «sin señal» y dejaba
pasar cualquier veredicto del modelo.

Un 3 no es la ausencia de opinión: es una opinión tibia. Contradecirla exige la
misma seguridad que contradecir un 1 o un 5. Corregido, y con prueba.

## Tres entradas muertas en mis propios diccionarios

Ruff avisó de un duplicado, y al mirarlo aparecieron dos problemas peores:

| Entrada | Por qué nunca coincidiría |
|---|---|
| `"gustó"` | El texto se normaliza sin tildes antes de comparar |
| `"no recomiendo"` | El texto se trocea en palabras sueltas |
| `"no vale"`, `"no volveria"` | Lo mismo |

Eran **código muerto que aparentaba funcionar**: alguien leyendo el diccionario
habría creído que esas expresiones se detectaban. Se quitaron —las negaciones
ya las cubre el mecanismo de negadores, que invierte «recomiendo» cuando lleva
un «no» delante— y hay pruebas que impiden que vuelvan a colarse:

- `test_ninguna_palabra_tiene_tildes`
- `test_ninguna_palabra_tiene_espacios`
- `test_los_terminos_de_los_temas_no_tienen_tildes`

## Por qué las reglas siguen existiendo

No como formalidad. El modelo pesa cientos de megas, tarda 26 segundos en
cargar la primera vez y **cerca de un segundo por comentario**. En un portátil
de exposición sin GPU, o en una máquina donde la descarga falle, el sistema
tiene que seguir dando valoraciones analizadas.

Y lo hace: si se pide el modelo y no está disponible, se analiza con las reglas
y **se dice** —el campo `analizado_por` queda en `"reglas"`—, así que el
tablero nunca atribuye al modelo algo que no hizo.

Hay una prueba que simula el fallo del modelo y comprueba justo eso.

## Limitación conocida y medida

El modelo necesita contexto. La misma idea en dos longitudes:

| Frase | Veredicto | Confianza |
|---|---|---|
| «Superó todas nuestras expectativas.» | neutro | 0,52 |
| «La verdad es que superó todas nuestras expectativas.» | positivo | 0,85 |

Está escrito en una prueba (`test_el_modelo_tambien_falla_con_frases_muy_cortas`)
que además falla si un día deja de ser cierto, para que la documentación no
envejezca en silencio.

Es también lo que justifica el umbral: con 0,52 el modelo **no** se impone a la
puntuación, que es exactamente lo que debe pasar cuando duda.

## Cómo verificarlo

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_sentimiento.py -v
```

Las pruebas del modelo se saltan solas si `pysentimiento` no está instalado: el
proyecto tiene que poder probarse sin descargar nada.

## Relacionado

- [Por qué se aceptó TF-IDF y se descartó LightGBM](2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md)
  — la misma regla de oro en el Incremento 3, con el resultado contrario
- [Por qué se aceptó OR-Tools y cómo se calibró](2026-08-29-por-que-se-acepto-or-tools-y-como-se-calibro.md)
- [Indicador 6](../indicadores/06-experiencias-con-valoracion.md)
