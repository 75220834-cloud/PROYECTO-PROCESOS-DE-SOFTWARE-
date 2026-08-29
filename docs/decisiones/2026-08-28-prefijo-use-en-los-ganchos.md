# Los ganchos de React llevan el prefijo `use`, en inglés

**Fecha:** 28 de agosto de 2026
**Estado:** aceptada
**Afecta a:** `frontend/src/hooks/`

## Contexto

La regla de idioma del proyecto exige que todo se nombre en español: variables,
funciones, archivos, carpetas, tablas y endpoints. La única excepción declarada
son «los nombres de bibliotecas de terceros y las palabras reservadas del
lenguaje».

Al escribir el gancho que gestiona el tema claro/oscuro se le llamó `usarTema`,
respetando la regla. ESLint lo rechazó con tres errores de la regla
`react-hooks/rules-of-hooks`:

> React Hook "useState" is called in function "usarTema" that is neither a
> React function component nor a custom React Hook function.

## Problema

El prefijo `use` no es una convención de estilo: es el mecanismo por el que
React, el revisor `eslint-plugin-react-hooks` y el compilador de React
reconocen qué funciones pueden llamar a `useState`, `useEffect` y demás. Una
función que empieza por `usar` es, para esas herramientas, una función normal,
y llamar a un gancho dentro de ella es un error real que puede provocar fallos
sutiles de estado.

No existe forma de configurar el revisor para aceptar el prefijo `usar`: la
comprobación está en el propio algoritmo de la regla, no en una lista de
nombres.

## Decisión

Los ganchos personalizados se nombran `use` + sustantivo en español:
`useTema`, y en el futuro `usePreferencia`, `useItinerario`.

El prefijo `use` se trata como **palabra reservada de la biblioteca**, que es
la excepción que la propia regla de idioma ya contempla. Todo lo demás del
nombre sigue en español.

## Alternativas descartadas

| Alternativa | Por qué se descartó |
|---|---|
| Mantener `usarTema` y desactivar la regla `rules-of-hooks` | Desactiva la comprobación que más errores previene en React. Se perdería calidad real a cambio de coherencia nominal. |
| Mantener `usarTema` y no usar ganchos dentro | Obligaría a escribir la lógica de estado en cada componente, duplicándola. |
| Traducir a `useTheme` | Innecesario: solo el prefijo es técnico, el sustantivo puede y debe ir en español. |

## Consecuencia

Los archivos de `frontend/src/hooks/` son los únicos del proyecto con un
prefijo en inglés. Cada uno lleva un comentario en su cabecera explicando el
motivo y remitiendo a esta nota.
