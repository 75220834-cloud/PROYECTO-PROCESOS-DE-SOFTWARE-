# ADR-011 — Se acepta pysentimiento, con umbral de confianza 0,70 y degradación a reglas

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 6 — valoración de cierre y evidencia (brecha 7) |
| **Atributo de calidad principal** | **Fiabilidad** (exactitud de la clasificación) |
| **Atributos secundarios** | Disponibilidad (cae a reglas y lo dice), rendimiento (~1 s por comentario) |
| **Interruptor** | `USAR_MODELO_SENTIMIENTO` |
| **Nota de origen** | [`2026-08-29-por-que-se-acepto-pysentimiento.md`](../decisiones/2026-08-29-por-que-se-acepto-pysentimiento.md) |

---

## Contexto

Aplicación de la regla de oro al análisis de sentimiento de las valoraciones:

- **Modelo:** pysentimiento (RoBERTuito), en español, local.
- **Reglas:** puntuación en estrellas + diccionario de palabras con negaciones.

## Decisión

**Se acepta el modelo**, con dos matices que son la sustancia de este ADR: el
modelo **también mira las estrellas**, y **solo se impone a la puntuación cuando
su confianza supera 0,70**.

### La primera medición era tramposa, y es lo más instructivo de este ADR

| | Aciertos | Tiempo total |
|---|---|---|
| **Reglas** | **13/13** | 5,6 ms |
| Modelo | 11/13 | 11 403 ms |

Las reglas acertaban todo y eran **dos mil veces más rápidas**. Por la regla de
oro tocaba descartar el modelo. Pero la comparación estaba viciada por dos
motivos:

1. **El grave: las reglas veían la puntuación y el modelo no.** Las reglas parten
   del número de estrellas y usan el texto para corregirlo; el modelo solo recibía
   el texto. Eso no compara comprensión del lenguaje: compara «estrellas +
   diccionario» contra «solo texto», y la puntuación es el dato más predictivo que
   hay en una reseña.
2. **Las frases las escribió la misma persona que escribió el diccionario.** Ese
   sesgo no se puede quitar sin un conjunto anotado por terceros, que no existe, y
   **se declara**.

### Segunda medición, aislando el texto

Se le pasa a las reglas una puntuación de 3 —la que no aporta nada— para que su
veredicto salga solo del diccionario. Catorce frases, la mitad con vocabulario
que **no** está en el diccionario:

| | Aciertos |
|---|---|
| Reglas (solo texto) | 8/14 |
| **Modelo (solo texto)** | **11/14** |

Las reglas fallan donde era previsible:

| Frase | Reglas | Modelo |
|---|---|---|
| «La verdad es que superó todas nuestras expectativas.» | neutro ✗ | positivo ✓ |
| «Nos arrepentimos de haber ido hasta allá.» | neutro ✗ | negativo ✓ |
| «Muy bonito todo, lástima que cerraran justo cuando llegamos.» | **positivo ✗** | negativo ✓ |

La última es la peor: el diccionario ve «bonito» y clasifica como positiva una
queja. **Un diccionario no puede leer ironía, y las reseñas están llenas de ella.**

### Medición final, tras darle al modelo el dato que se le ocultaba

| | Con la puntuación | Solo texto |
|---|---|---|
| Reglas | 13/13 | 8/14 |
| **Modelo** | **13/13** | **12/14** |

Empatan donde el número lo dice casi todo, y el modelo gana claramente donde hay
que leer. **Modelo aceptado.**

### El umbral 0,70 también está medido

Los dos fallos del modelo venían con confianza **0,52 y 0,67**; sus aciertos, con
**0,80–0,98**. El 0,70 separa los dos grupos.

```python
CONFIANZA_PARA_IMPONERSE = 0.70
```

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Descartar el modelo tras la primera medición** | Era lo que mandaba la regla de oro sobre una medición **sesgada por mí**. Volver a medirlo bien cambió la decisión. Es el caso que justifica auditar la propia medición antes que el resultado. |
| **Solo reglas** | Se conservan como respaldo, pero no leen ironía ni vocabulario fuera del diccionario: 8/14 contra 12/14. |
| **Dejar que el modelo decida solo con el texto** | Tira la señal más predictiva de una reseña, que es la puntuación. |
| **Sin umbral de confianza** | «Estuvo normal, nada del otro mundo» con 3 estrellas salía *positivo*, porque la primera versión trataba el 3 como «sin señal». **Un 3 no es ausencia de opinión: es una opinión tibia**, y contradecirla exige la misma seguridad que contradecir un 1 o un 5. |
| **Un modelo más grande** | Pesa cientos de MB y tarda ~1 s por comentario ya así. No hay presupuesto de cómputo. |

## Consecuencias

**Positivas**

- El tablero clasifica comentarios con vocabulario que nadie escribió a mano.
- **El campo `analizado_por` dice siempre qué vía se usó**, así que el tablero
  nunca atribuye al modelo algo que hicieron las reglas. Hay una prueba que simula
  el fallo del modelo y comprueba justo eso.
- **Las reglas siguen existiendo por un motivo operativo, no por formalidad:** el
  modelo tarda 26 s en cargar la primera vez y ~1 s por comentario. En un portátil
  de exposición sin GPU, o si la descarga falla, el sistema sigue dando
  valoraciones analizadas.

**Negativas, medidas y declaradas**

- **El modelo necesita contexto.** La misma idea en dos longitudes:

  | Frase | Veredicto | Confianza |
  |---|---|---|
  | «Superó todas nuestras expectativas.» | neutro | 0,52 |
  | «La verdad es que superó todas nuestras expectativas.» | positivo | 0,85 |

  Está fijado en `test_el_modelo_tambien_falla_con_frases_muy_cortas`, que además
  **falla si un día deja de ser cierto**, para que la documentación no envejezca
  en silencio.
- El conjunto de evaluación lo escribió el mismo autor del diccionario. Sesgo
  declarado, no resuelto.
- **En la integración continua el modelo no se instala** (PyTorch, ~2,5 GB, y
  descarga por red): se salta **1** prueba y el módulo queda en **96 %** de
  cobertura. Ver ADR-015.

### Tres entradas muertas que aparentaban funcionar

Ruff avisó de un duplicado y al mirarlo aparecieron entradas que **nunca podrían
coincidir**: `"gustó"` (el texto se normaliza sin tildes), `"no recomiendo"` y
`"no vale"` (el texto se trocea en palabras sueltas). Era código muerto que
aparentaba funcionar: quien leyera el diccionario habría creído que esas
expresiones se detectaban. Se quitaron, y hay tres pruebas que impiden que
vuelvan.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_sentimiento.py -v
```

## Relacionado

- [ADR-004 — Se acepta TF-IDF](ADR-004-se-acepta-tfidf-para-la-afinidad.md)
- [ADR-005 — Se descarta LightGBM](ADR-005-se-descarta-lightgbm-para-la-afluencia.md)
- [ADR-015 — Integración continua](ADR-015-integracion-continua-y-umbral-de-cobertura.md)
