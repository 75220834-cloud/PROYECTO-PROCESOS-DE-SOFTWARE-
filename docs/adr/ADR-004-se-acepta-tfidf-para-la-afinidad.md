# ADR-004 — Se acepta TF-IDF con similitud coseno para la afinidad

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 3 — recomendación personalizada (brechas 2 y 3) |
| **Atributo de calidad principal** | **Usabilidad** (utilidad y explicabilidad del resultado) |
| **Atributos secundarios** | Rendimiento (se ajusta en memoria por petición) |
| **Interruptor** | `USAR_MODELO_RECOMENDACION` |
| **Nota de origen** | [`2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md`](../decisiones/2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md) |

---

## Contexto

La **regla de oro de IA** del proyecto exige que toda funcionalidad con modelo
tenga una alternativa por reglas explícitas, conmutable por configuración, y que
**si el modelo no supera su línea base se entregue la alternativa y el modelo
vuelva al backlog**.

Este ADR registra la aplicación de esa regla a la capa de afinidad: TF-IDF con
similitud coseno frente a una alternativa por reglas, sobre los 234 recursos
validados y cuatro perfiles de visitante.

## Decisión

**Se acepta el modelo TF-IDF.** La alternativa por reglas se conserva, se
prueba, y sigue siendo utilizable con `USAR_MODELO_RECOMENDACION=false`.

### La medición, y por qué la pregunta obvia estaba mal planteada

La comparación natural sería «¿coinciden las dos vías en el mejor resultado?».
Se midió y **la respuesta fue que no, en ninguno de los cuatro perfiles**. Al
mirar por qué, apareció el motivo real:

| Perfil | Modelo: puntajes distintos | Reglas: puntajes distintos | Reglas: empatados en el 1.º |
|---|---:|---:|---:|
| artesanía + iglesias | 70 | **2** | **38** |
| naturaleza + aventura | 105 | **3** | 16 |
| arqueología | 56 | **2** | 27 |
| gastronomía + ferias | 36 | 3 | 1 |

Las reglas puntúan como *proporción de intereses cubiertos*. Con dos intereses
marcados los únicos puntajes posibles son 0, 0,5 y 1, lo que sobre 234 recursos
deja **38 empatados en primer puesto** y un orden arbitrario entre ellos.
Preguntar «¿cuál es el mejor según las reglas?» no tiene respuesta cuando 38
empatan.

### Los tres motivos de la aceptación

1. **Ordena de verdad.** 36–105 valores distintos frente a 2–3, y un único
   primero frente a decenas empatadas.
2. **Sigue siendo explicable.** Cada recomendación devuelve los términos que más
   pesaron, calculados como el producto de los pesos TF-IDF del recurso y de la
   consulta. No es una aproximación *post hoc*: es la descomposición literal del
   numerador del coseno.
3. **No necesita histórico propio.** Se ajusta con el propio catálogo, en
   memoria, en cada petición. Es lo que sostiene el argumento de **MLOps
   diferido**: no hay modelo entrenado que versionar ni reentrenar.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Solo reglas por intereses** | Se conserva como respaldo, pero **no puede ordenar**: 38 recursos empatados en el primer puesto con dos intereses marcados. |
| **Embeddings de un modelo de lenguaje** | Exigiría descargar y servir un modelo de cientos de MB para una tarea que TF-IDF resuelve sobre 234 documentos, y perdería la explicabilidad por término. |
| **Filtrado colaborativo** | No hay histórico de usuarios: es el mismo problema que hundió el modelo de afluencia (ver ADR-005). |

## Consecuencias

**Positivas**

- Cada recomendación explica **por qué** («pesaron: artesanal, taller, mate»),
  que es lo que cierra la brecha 2.
- Cero infraestructura de modelos: no hay artefacto entrenado en el repositorio.

**Negativas, y gestionadas**

- **El valor del coseno no significa nada para una persona.** Un 0,047 no se
  interpreta. Por eso la interfaz muestra un **puntaje relativo al mejor
  resultado**, con la aclaración explícita de que no es un porcentaje absoluto.
- Lo que las reglas hacen mejor se pierde: su 0,5 se lee literalmente como
  «cubre la mitad de lo que pediste».
- **Dos errores del diccionario de términos salieron probando en el navegador,
  no con pruebas unitarias**, porque las pruebas partían del propio diccionario:
  «museo de sitio» clasificado como iglesia, y `"rio"` coincidiendo dentro de
  `"santuaRIO"` por comparar subcadenas. Corregido con límites de palabra
  (`\b`) y fijado con pruebas de regresión.

> **Lección registrada:** las pruebas unitarias comprueban que el código hace lo
> que su autor cree; probar con datos reales comprueba si lo que su autor cree es
> cierto. Hacen falta las dos.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_afinidad_y_afluencia.py pruebas/test_rutas_recomendaciones.py -v
```

Experimento: `backend/notebooks/01_incremento3_afinidad_y_afluencia.ipynb`,
ejecutado y con salidas guardadas.

## Relacionado

- [ADR-005 — Se descarta LightGBM para la afluencia](ADR-005-se-descarta-lightgbm-para-la-afluencia.md)
- [ADR-007 — Se acepta OR-Tools](ADR-007-se-acepta-or-tools-con-recorrido-abierto.md)
- [ADR-011 — Se acepta pysentimiento](ADR-011-se-acepta-pysentimiento-con-umbral-de-confianza.md)
