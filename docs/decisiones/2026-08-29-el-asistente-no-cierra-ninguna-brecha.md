# El asistente conversacional no cierra ninguna brecha

**Fecha:** 29 de agosto de 2026
**Fase:** 7
**Estado:** implementado

---

## La decisión

El asistente conversacional se presenta como **capa de interacción**, no como
funcionalidad nueva. No se le asigna ninguna brecha ni ningún indicador.

Es una forma alternativa de llegar a lo que ya construyeron los Incrementos 2,
3 y 4. Todo lo que permite pedir hablando se puede pedir también por
formulario.

## Por qué importa decirlo así

Porque es lo que mantiene la coherencia con los dos documentos académicos
entregados, y porque es verdad.

Un asistente con un modelo de lenguaje detrás es la parte más vistosa del
proyecto y la más fácil de vender como «la innovación». Presentarlo así sería
exagerar: si mañana se apaga Ollama, **no se pierde ninguna capacidad del
sistema**. Se pierde una manera cómoda de pedir las cosas.

La comprobación es sencilla: la interfaz enseña un enlace al formulario
justamente cuando el asistente no está disponible. Si el asistente cerrara una
brecha, ese enlace no podría existir.

---

## Cómo se garantiza que no inventa datos

Es la promesa que hay que poder defender, y no descansa en la buena voluntad
del modelo.

### La arquitectura, primero

El modelo **no sabe nada** del Valle del Mantaro. Su papel es:

1. Leer lo que pide el visitante.
2. Elegir qué función del backend responde a eso.
3. Redactar con **lo que devolvió esa función**.

Las cinco funciones —`buscar_recursos`, `crear_preferencia`,
`generar_recomendaciones`, `construir_itinerario`, `consultar_afluencia`—
consultan la base de datos. El modelo solo ve su resultado en formato JSON.

Si alguien pregunta por un lugar que no está en el catálogo, la búsqueda
devuelve cero resultados y en el mismo JSON viaja un aviso escrito en palabras:

> «No hay ningún recurso con esos criterios en el Inventario Nacional de
> Recursos Turísticos del MINCETUR. NO inventes uno y NO propongas ningún otro
> lugar de memoria.»

### Las instrucciones, después

El mensaje de sistema fija seis reglas. Las dos primeras son las que sostienen
todo lo demás: no inventar y **no afirmar que algo no está en el catálogo sin
haberlo consultado**.

La segunda no estaba al principio, y hubo que añadirla. Ver más abajo.

---

## Lo que se descubrió usando el asistente de verdad

Ninguno de los tres fallos siguientes lo encontró una prueba. Los tres
aparecieron preguntándole cosas normales.

### Fallo 1 — acertar por casualidad

La primerísima prueba fue pedirle el «Palacio de la Cultura de Jauja», que no
existe. Respondió que no lo encontraba en el catálogo oficial.

Parecía perfecto. No lo era: **la lista de funciones ejecutadas venía vacía**.
El modelo no había consultado nada. Dijo la verdad por casualidad, y con la
misma seguridad habría podido decir lo contrario.

Se añadió la regla 2, que obliga a consultar antes de afirmar. Con ella, la
misma pregunta ejecuta `buscar_recursos` y responde con el resultado real.

### Fallo 2 — negar lo que sí existe

A la pregunta «¿qué puedo visitar en Concepción?» respondió que no había
recursos registrados. Hay trece.

La causa: el modelo escribe «CONCEPCIÓN» con tilde y el inventario del MINCETUR
la guarda como «CONCEPCION» sin ella. La comparación fallaba.

Es el peor tipo de fallo posible para este proyecto. No es inventar: es
**negar**, y hacerlo con aplomo.

Se corrigió normalizando los dos lados con `unaccent`, la extensión de
PostgreSQL que ya estaba instalada.

### Fallo 3 — el vacío empuja a inventar

A «busca el Convento de Ocopa» respondió que no estaba en el catálogo, y a
continuación se ofreció a recomendar «el Convento de San Francisco en
Huancayo», que se sacó de la memoria.

Hubo dos causas encadenadas:

- Se buscaba la frase literal. El inventario lo llama «Convento De Santa Rosa
  De Ocopa», así que «Convento de Ocopa» no casaba como subcadena.
- El modelo mandó `categoria="iglesias_conventos"`, que es un código de
  *interés*, no una categoría del MINCETUR. Se aplicaba el filtro a ciegas y la
  consulta salía vacía.

**La lección que se llevó al código:** una búsqueda vacía por un filtro mal
escrito no es un resultado neutro. Es el escenario que empuja al modelo a
rellenar el hueco. Por eso ahora un filtro desconocido **se ignora** en vez de
aplicarse: devolver de más es un problema menor que devolver nada.

Y por eso el aviso de «sin resultados» prohíbe explícitamente proponer
alternativas que no salgan de una nueva búsqueda.

---

## La verificación, cruzada contra la base de datos

Tres preguntas, y cada dato de las respuestas comprobado uno a uno:

| Pregunta | Funciones ejecutadas | Resultado |
|---|---|---|
| Palacio de la Cultura de Jauja | `buscar_recursos(distrito=JAUJA, texto=Palacio de la Cultura)` | 0 resultados, lo rechaza, no propone alternativa |
| ¿Qué visitar en Concepción? | `buscar_recursos(distrito=CONCEPCIÓN)` | 8 lugares, **los 8 existen** en la base y están validados |
| Busca el Convento de Ocopa | `buscar_recursos(texto=Convento de Ocopa, categoria=iglesias_conventos)` | Lo encuentra; distrito, provincia y altitud (3384 msnm) coinciden con la fila |

En el catálogo no hay ninguna fila cuyo nombre contenga «Palacio» y «Cultura».

---

## Lo que sigue sin resolver

- **Tarda entre 25 y 40 segundos por respuesta** en un portátil sin GPU
  dedicada. Es el coste de correr un modelo de 7 000 millones de parámetros en
  la CPU. No hay forma de arreglarlo sin cambiar de máquina o de modelo.
- **El modelo puede equivocarse eligiendo la función.** Que no invente datos no
  significa que siempre elija bien: puede buscar por distrito cuando debía
  buscar por texto. Devuelve datos reales que no responden a la pregunta. La
  lista de funciones ejecutadas que se enseña en la interfaz existe justamente
  para que eso se pueda ver.
- **No hay pruebas automáticas del modelo.** Lo que se prueba —33 pruebas— son
  las funciones del backend, que son la frontera entre el modelo y los datos.
  Fijar con un `assert` lo que responde un modelo de lenguaje no es posible sin
  fijar también su semilla y su versión, y aun así sería frágil.

---

## Relacionado

- [Por qué se aceptó OR-Tools](2026-08-29-por-que-se-acepto-or-tools-y-como-se-calibro.md)
- [Cómo se calculan las tarifas](2026-08-29-como-se-calculan-las-tarifas-de-transporte.md)
- [Proveedores de demostración](2026-08-29-proveedores-de-demostracion.md)
