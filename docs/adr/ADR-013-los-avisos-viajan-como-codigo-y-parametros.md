# ADR-013 — Los avisos viajan del backend como código y parámetros, no como frases

| | |
|---|---|
| **Estado** | Aceptada e implementada |
| **Fecha** | 30 de agosto de 2026 (Fase 7) |
| **Alcance** | Todo el API y toda la interfaz |
| **Atributo de calidad principal** | **Mantenibilidad** (un solo sitio por frase, y falla si falta) |
| **Atributos secundarios** | Portabilidad (añadir idiomas), usabilidad (plurales correctos) |
| **Nota de origen** | [`2026-08-30-los-avisos-son-datos-no-frases.md`](../decisiones/2026-08-30-los-avisos-son-datos-no-frases.md) |

---

## Contexto

Dos problemas convergieron.

**El que lo destapó.** Recorriendo la aplicación en inglés, la interfaz estaba en
inglés y los avisos del backend seguían en español. El visitante veía

> «Before you set out»

y justo debajo

> «El punto más alto del día está a 3706 m s. n. m.»

Las claves de la interfaz estaban traducidas; estas no, **porque no eran cadenas
de la interfaz**: eran frases que el backend construía y enviaba ya escritas.

**El que había estado dando la lata todo el proyecto.** Los plurales. Cuando el
backend redacta, cada frase concuerda a mano, y se colaban cosas como «Solo hay 1
valoración(es)», «1 de los 1 recursos valorados **tienen**», «1 parada(s)», «3
distrito(s) más». Se arreglaban de una en una y **volvían a aparecer** en la
siguiente frase escrita con prisa.

## Decisión

El backend **deja de redactar**. Manda un código y sus datos; la interfaz escribe
la frase:

```json
{ "codigo": "altitud", "parametros": { "metros": 3706 } }
```

Son **69 códigos** declarados en `app/servicios/avisos.py` (verificado
importando `CODIGOS_CONOCIDOS`), que cubren avisos del itinerario, de las
recomendaciones, salvedades del tablero, motivos de afluencia, razones de
descarte de un recurso, motivos por los que un servicio no se puede pedir, y
mensajes de error.

### Tres decisiones tomadas dentro

**1. Tres códigos para los horarios, no uno parametrizado.** Las tres frases no
cambian solo de número, cambian de sujeto: «el único», «ninguno de los N», «N de
los M». Una sola plantilla da frases forzadas en español y peores en inglés. Son
`sin_horario_el_unico`, `sin_horario_ninguno` y `sin_horario_algunos`.

**2. El nombre y la salvedad de los indicadores no viajan.** El nombre del
indicador 1 es siempre «Oferta validada y vigente»: mandarlo en cada respuesta era
mandar una constante en español que después no se podía traducir. La tarjeta los
busca por el número del incremento. **Lo único que viaja es lo que cambia con los
datos.**

**3. Un parámetro numérico no siempre es «la cantidad».** i18next elige el plural
mirando un parámetro llamado exactamente `count`; el backend nombra los suyos por
lo que significan (`cuantas`, `validados`, `libres`). La interfaz copia el primer
numérico como `count`, pero **no todos valen**: en «1 de 3 recursos valorados» lo
que decide singular o plural es el 1, no el 3. De ahí la lista de parámetros que
son referencias y no cantidades: `total`, `cupo`, `minimo`, `pedidas`, `dia`,
`metros`, `subida`. Sin esa lista salía «1 de los 3 recursos valorados **tienen**».

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Traducir las frases en el backend** (i18n del servidor) | Duplica el sistema de traducción: habría dos catálogos que mantener sincronizados, y el backend tendría que saber el idioma del visitante en cada petición. |
| **Mandar la frase en los dos idiomas** | Dobla el tamaño de cada respuesta y no escala a un tercer idioma. Y el plural seguiría resolviéndose a mano. |
| **Dejarlo en español y documentarlo como limitación** | Era la situación de partida, y es la que un visitante detecta en cinco segundos. |
| **Una sola plantilla parametrizada para los horarios** | Frases forzadas en español y peores en inglés: cambian de sujeto, no solo de número. |
| **Copiar siempre el primer parámetro numérico como `count`** | Produce «1 de los 3 recursos valorados tienen», que es exactamente el error que se venía a arreglar. |

## Consecuencias

**Positivas**

- **Las pruebas mejoraron.** Antes decían
  `assert any("no traen comentario" in a for a in cuerpo["avisos"])`, que se rompía
  al cambiar una coma y **fijaba la redacción**. Ahora dicen
  `assert "valoraciones_sin_comentario" in codigos(cuerpo["avisos"])`.
- **Un aviso dejó de ser texto y pasó a ser un dato.** Se puede preguntar a la
  base cuántos itinerarios avisaron de altitud sin buscar subcadenas.
- **Lo que impide que se rompa:** una prueba del frontend lee la lista de códigos
  **del propio archivo de Python** y comprueba que cada uno tiene su frase en los
  dos idiomas. Falla también al revés: una frase sin código que la use es código
  muerto. Y en el backend, `aviso()` rechaza cualquier código que no esté en
  `CODIGOS_CONOCIDOS`, así que el error salta al construirlo y no en una respuesta
  HTTP a medio camino.

**Negativas, y pagadas**

- **Una migración de base de datos.** `itinerario.avisos` pasó de `TEXT` con las
  frases concatenadas a `JSONB`. Los avisos ya guardados **se pierden**: de una
  frase en español no se puede deducir qué código la produjo. El coste real es
  nulo porque al abrir un itinerario guardado los avisos se recalculan.
- **42 pruebas hubo que reescribir.** Todas afirmaban sobre el texto.
- **Los archivos de idioma son más largos:** 595 claves por idioma frente a 467.
- **Acoplamiento cruzado declarado:** la prueba del frontend lee un archivo del
  backend, así que el trabajo de frontend en la integración continua **no puede
  usar una descarga parcial del repositorio**. Está anotado en ADR-015.
- **Dejó un fallo latente que tardó en aparecer:** `verificar_fase4.py` seguía
  haciendo `a.lower()` sobre los avisos y reventaba con `AttributeError`. No se
  detectó porque ese archivo tiene **0 % de cobertura**. Corregido el 20 de
  septiembre de 2026.

## Cómo verificarlo

```bash
cd frontend && npx vitest run src/utilidades/__pruebas__/avisos.prueba.ts
```

## Relacionado

- [ADR-012 — Mantaro Moderno](ADR-012-mantaro-moderno-es-la-fuente-unica-del-estilo.md)
- [ADR-015 — Integración continua](ADR-015-integracion-continua-y-umbral-de-cobertura.md)
