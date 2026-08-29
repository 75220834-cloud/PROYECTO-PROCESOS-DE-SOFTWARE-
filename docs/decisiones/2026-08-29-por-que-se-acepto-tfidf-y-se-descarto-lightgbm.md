# Por qué se aceptó el modelo de afinidad y se descartó el de afluencia

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Cierra:** brechas 2 y 3 (Incremento 3)

## Contexto

La regla de oro del proyecto exige que toda funcionalidad con modelo tenga una
alternativa por reglas explícitas, conmutable con una variable de
configuración, y que **si el modelo no supera su línea base se entregue la
alternativa y el modelo vuelva al backlog**.

Este documento registra las dos decisiones que salieron de aplicar esa regla.
Los experimentos están en
`backend/notebooks/01_incremento3_afinidad_y_afluencia.ipynb`, ejecutado y con
sus salidas guardadas.

---

## Capa 1 — Afinidad: **modelo ACEPTADO**

### Lo que se comparó

TF-IDF con similitud coseno frente a la alternativa por reglas, sobre los 234
recursos validados del catálogo y con cuatro perfiles de visitante.

### Lo que se midió, y por qué no fue lo que se esperaba

La comparación obvia sería «¿coinciden las dos vías en el mejor resultado?».
**Se midió y la respuesta fue que no**, en ninguno de los cuatro perfiles. Pero
al mirar por qué, resultó que la pregunta estaba mal planteada:

| Perfil | Modelo: puntajes distintos | Reglas: puntajes distintos | Reglas: empatados en el 1.º |
|---|---:|---:|---:|
| artesanía + iglesias | 70 | **2** | **38** |
| naturaleza + aventura | 105 | **3** | 16 |
| arqueología | 56 | **2** | 27 |
| gastronomía + ferias | 36 | 3 | 1 |

Las reglas puntúan como *proporción de intereses cubiertos*. Con dos intereses
marcados, los únicos puntajes posibles son 0, 0,5 y 1. Sobre 234 recursos eso
deja **38 empatados en el primer puesto**, y el orden que ve el visitante entre
ellos es arbitrario. Preguntar «¿cuál es el mejor según las reglas?» no tiene
respuesta cuando 38 empatan.

### Decisión y motivos

**Se acepta el modelo TF-IDF.**

1. **Ordena de verdad.** 36–105 valores distintos frente a 2–3, y un único
   primero frente a decenas empatados.
2. **Sigue siendo explicable.** Cada recomendación devuelve los términos que
   más pesaron, calculados como el producto de los pesos TF-IDF del recurso y
   de la consulta. No es una aproximación *post hoc*: es la descomposición
   literal del numerador del coseno.
3. **No necesita histórico propio.** Se ajusta con el propio catálogo, en
   memoria, en cada petición. Esto es lo que sostiene el argumento de MLOps
   diferido del documento académico.

**La alternativa por reglas se conserva y se prueba.** Con
`USAR_MODELO_RECOMENDACION=false` el sistema entero sigue funcionando: devuelve
recursos que cubren los intereses declarados, solo que sin orden fino entre
ellos. Es peor, pero es utilizable, y esa es su función.

### Lo que las reglas hacen mejor

Su puntaje se lee solo: un 0,5 significa literalmente «cubre la mitad de lo que
pediste». El 0,047 de una similitud coseno no significa nada por sí mismo, y
por eso la interfaz muestra un **puntaje relativo al mejor resultado** en vez
del valor crudo, con una aclaración de que no es un porcentaje absoluto.

---

## Capa 2 — Afluencia: **modelo DESCARTADO por ahora**

### Lo que pasó

No hay datos históricos. La tabla `afluencia_historica` tiene **0 filas**.

El Ministerio de Cultura publica series mensuales de visitantes a sitios
arqueológicos y museos, pero apenas cubren recursos del Valle del Mantaro: la
mayoría de los 295 del catálogo son danzas, fiestas patronales, pueblos
artesanales y sitios naturales que nadie contabiliza.

### Decisión

**Se descarta el modelo y se entrega la alternativa por reglas.**

La función `entrenar_modelo_de_afluencia` existe, funciona y está probada, pero
**se niega a entrenar con menos de 120 filas** y devuelve el motivo. Con menos,
un modelo de árboles memoriza los ejemplos: su error de entrenamiento sale
excelente y su predicción real no vale nada. Presentar eso como predicción
sería mentir con más pasos.

### Qué haría falta para activarlo

1. Series de visitantes que cubran recursos del valle. La fuente más
   prometedora son los registros municipales, no las series nacionales.
2. Al menos 120 filas, mejor varios cientos.
3. Volver a ejecutar el cuaderno y comparar el error medio absoluto del modelo
   contra el de las reglas. **Solo si el modelo gana, se activa.**

### La alternativa por reglas se apoya en un dato firme

El calendario festivo, cuyas fiestas móviles se **calculan** con el algoritmo
de la Pascua (Butcher, 1876) en vez de escribirse a mano. Verificado contra 16
fechas oficiales, incluida la de 2026: Semana Santa del 29 de marzo al 5 de
abril.

---

## Dos errores encontrados al probar en el navegador

Ninguno lo detectaron las pruebas unitarias, porque ambas partían de mi propio
diccionario de términos. Salieron al mirar recomendaciones reales.

### 1. Un museo de sitio no es una iglesia

«Museo de Sitio Wariwillka» encabezaba las búsquedas de quien pedía «iglesias
y conventos», porque `"museo de sitio"` estaba clasificado bajo ese interés. Un
museo de sitio es el museo de una zona arqueológica. Corregido: pasa a
arqueología, junto con `"santuario"`, que en este inventario aparece casi
siempre en «Santuario Arqueológico».

### 2. «río» coincidía dentro de «santuario»

La comparación de términos usaba subcadenas (`termino in texto`), así que
`"rio"` coincidía dentro de `"santuaRIO"` y un santuario arqueológico se
clasificaba también como naturaleza. Lo mismo habría pasado con `"inca"` dentro
de `"incapaz"` o `"arte"` dentro de `"martes"`.

Corregido con límites de palabra (`\b`) en la función `contiene_termino`, y
fijado con pruebas de regresión que comprueban los tres casos.

**Lección para el resto del proyecto:** las pruebas unitarias comprueban que el
código hace lo que su autor cree; probar con datos reales comprueba si lo que
su autor cree es cierto. Hacen falta las dos.
