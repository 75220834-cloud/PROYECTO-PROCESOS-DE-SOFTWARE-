# Los avisos son datos, no frases

**Fecha:** 30 de agosto de 2026
**Fase:** 7
**Estado:** implementado

---

## La decisión

El backend dejó de redactar los avisos que ve el visitante. Ahora manda un
código y sus datos, y la interfaz escribe la frase:

```json
{ "codigo": "altitud", "parametros": { "metros": 3706 } }
```

Son **67 códigos**: los avisos del itinerario, los de las recomendaciones, las
salvedades del tablero, los motivos de afluencia, las razones por las que un
recurso quedó descartado, los motivos por los que un servicio no se puede
pedir, y los mensajes de error.

---

## Por qué se hizo

### El motivo que lo destapó

Recorriendo la aplicación en inglés apareció esto: la interfaz estaba en
inglés y los avisos del backend seguían en español. Un visitante veía

> «Before you set out»

y justo debajo

> «El punto más alto del día está a 3706 m s. n. m.»

Las 581 cadenas de la interfaz estaban traducidas; estas no, porque no eran
cadenas de la interfaz: eran frases que el backend construía y mandaba ya
escritas.

### El motivo que había estado dando la lata todo el proyecto

Los plurales. Cuando el backend redacta, cada frase concuerda a mano, y se
colaban cosas como:

- «Solo hay 1 valoración(es)»
- «1 de los 1 recursos valorados tienen menos de 5 valoraciones»
- «El servicio atiende como máximo a 1 persona(s)»
- «Ese día quedan 1 plaza(s)»

Se arreglaban de una en una, y volvían a aparecer en la siguiente frase que
alguien escribía con prisa. **i18next las resuelve solo**, con sus formas
`_one` y `_other`, y además acierta en inglés sin escribir dos veces la frase.

---

## La consecuencia que no se buscaba, y que es la más útil

**Las pruebas mejoraron.** Antes decían cosas así:

```python
assert any("no traen comentario" in a for a in cuerpo["avisos"])
```

Esa prueba se rompía al cambiar una coma. Peor: fijaba la redacción, así que
arreglar la concordancia de una frase rompía pruebas que no tenían nada que
ver con lo que se estaba tocando. Pasó de verdad: al corregir «no traen» por
«no trae» se cayó una prueba que había estado fijando **la falta de
concordancia**.

Ahora dicen:

```python
assert "valoraciones_sin_comentario" in codigos(cuerpo["avisos"])
```

Y cuando importa el dato y no solo el hecho:

```python
assert parametros_de(avisos, "recursos_poco_fiables")["total"] == 1
```

**Un aviso dejó de ser texto y pasó a ser un dato.** Se puede preguntar a la
base cuántos itinerarios avisaron de altitud sin buscar subcadenas.

---

## Las tres decisiones que hubo que tomar dentro

### 1. Tres códigos para los horarios, no uno con parámetros

Las tres frases no cambian solo de número, cambian de sujeto: «el único»,
«ninguno de los N», «N de los M». Cubrirlas con una sola plantilla
parametrizada da frases forzadas en español y peores en inglés. Son
`sin_horario_el_unico`, `sin_horario_ninguno` y `sin_horario_algunos`.

### 2. El nombre y la salvedad de los indicadores no viajan

El nombre del indicador 1 es siempre «Oferta validada y vigente». Mandarlo en
cada respuesta era mandar una constante en español que después no se podía
traducir. Ahora la tarjeta los busca por el número del incremento, en
`indicadores.1.nombre`, `indicadores.1.brecha` e `indicadores.1.salvedad`.

Lo único que viaja es lo que cambia con los datos: el valor y el detalle.

### 3. Un parámetro numérico no siempre es «la cantidad»

i18next elige el plural mirando un parámetro llamado exactamente `count`. El
backend, en cambio, nombra los suyos por lo que significan: `cuantas`,
`validados`, `libres`. Son mejores nombres y no se querían perder.

La interfaz copia el primer numérico como `count`… pero **no todos valen**. En
«1 de 3 recursos valorados», lo que decide singular o plural es el 1, no el 3.
Por eso hay una lista de parámetros que son referencias y no cantidades:
`total`, `cupo`, `minimo`, `pedidas`, `dia`, `metros`, `subida`.

Sin esa lista salía «1 de los 3 recursos valorados **tienen**», que es
exactamente la falta de concordancia que se venía a arreglar.

---

## Lo que impide que esto se rompa

Una prueba del frontend lee la lista de códigos **del propio archivo de
Python** y comprueba que cada uno tiene su frase en los dos idiomas:

```
frontend/src/utilidades/__pruebas__/avisos.prueba.ts
```

Duplicar la lista ahí habría sido copiar lo que se quiere comprobar, que no
comprueba nada. También falla al revés: una frase sin código que la use es
código muerto en un archivo que ya es largo.

Y en el backend, `aviso()` rechaza cualquier código que no esté declarado en
`CODIGOS_CONOCIDOS`, así que el error salta al construirlo y no en una
respuesta HTTP a medio camino.

---

## El coste

- **Una migración de base de datos.** La columna `itinerario.avisos` pasó de
  `TEXT` con los avisos concatenados por saltos de línea a `JSONB`. Los avisos
  que ya estaban guardados se pierden: de una frase en español no se puede
  deducir qué código la produjo, y adivinarlo metería datos falsos. El coste
  real es nulo, porque al abrir un itinerario guardado los avisos se recalculan.
- **42 pruebas hubo que reescribir.** Todas afirmaban sobre el texto. Ninguna
  perdió cobertura: la mayoría quedó comprobando algo más preciso que antes.
- **Un archivo de idioma más largo.** 581 claves por idioma, frente a 467.

---

## Relacionado

- [El asistente no cierra ninguna brecha](2026-08-29-el-asistente-no-cierra-ninguna-brecha.md)
- [Indicador 6](../indicadores/06-experiencias-con-valoracion.md)
