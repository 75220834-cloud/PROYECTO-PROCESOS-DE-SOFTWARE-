# La ficha web traía lo que el CSV no

**Fecha:** 30 de agosto de 2026
**Estado:** implementado

---

## Lo que pasó

Durante seis fases el proyecto declaró dos limitaciones como si fueran de la
fuente:

> «El inventario del MINCETUR no publica horarios.»
> «El inventario del MINCETUR no trae descripciones.»

Las dos están escritas en el README y en la documentación de los incrementos.
Las dos eran **verdad del CSV** y **falsas de la fuente**.

Cada recurso del inventario tiene además una **ficha web** en el propio
sistema del MINCETUR. Su dirección estaba guardada en la columna `url_ficha`
desde la Fase 1, se enseñaba como enlace en la pantalla de detalle, y nadie
—yo incluido— había abierto una para ver qué hay dentro.

Hay dentro: descripción larga, horario de visita, tipo de ingreso, época
propicia y **conteos reales de visitantes** con su fuente y su año.

---

## Lo que cambió, medido

De las 295 fichas leídas, 0 fallidas:

| Dato | Antes | Ahora |
|---|---|---|
| Descripciones | 0 | **295** (100 %) |
| Horarios | 0 | **208** (71 %) |
| Tipo de ingreso | 0 | **210** (71 %) |
| Conteos de visitantes | 0 | **414 filas** en 207 recursos |
| Fiestas con fecha | 0 | **28** de 36 |

El Centro Piscícola El Ingenio recibió **120 889 visitantes locales en 2023**
según el conteo del MINCETUR. Ese número estaba publicado y no lo estábamos
usando: la afluencia se calculaba solo con reglas sobre el calendario.

---

## La lección, que es la que importa

**«La fuente no lo publica» hay que comprobarlo antes de escribirlo.** La frase
sonaba razonable, encajaba con el discurso de honestidad del proyecto y nadie
la puso en duda durante seis fases. Era falsa, y estaba impresa en dos
documentos entregables.

Una limitación declarada es una afirmación como cualquier otra: hay que poder
enseñar en qué se apoya. En este caso se apoyaba en no haber mirado.

---

## Cómo se lee, y por qué así

Son 295 páginas de un servicio público del Estado. El módulo
`utilidades/fichas_mincetur.py`:

- **espera un segundo entre peticiones**, para no degradar el servicio a nadie;
- **guarda cada página en disco**: reejecutar el guion no genera ni una
  petición nueva;
- **se identifica** en el `User-Agent` diciendo qué es y para qué;
- **se puede reanudar** si se corta a la mitad.

Las tablas se buscan **por su cabecera y no por su posición**. Las fichas sin
visitantes no traen esa tabla, y todo lo de abajo se corre un puesto: buscar
«la cuarta tabla» habría dado el horario de otra cosa en la mitad de los
casos.

---

## Los tres fallos que aparecieron construyéndolo

### 1. «Julio» es también un nombre de persona

El «Concurso Regional de Enfrenadura de Caballos Peruanos de Paso» salía
celebrándose en julio porque uno de sus fundadores se llamaba **Julio Camac**.

La regla que lo arregla: si el mes va en mayúscula y detrás viene otra palabra
en mayúscula, es un nombre propio. «11 de Julio en Matahuasi» pasa; «Julio
Camac» no.

### 2. Las fichas cuentan la historia del pueblo, y esa historia lleva meses

La Feria Nacional Ganadera de Cuasimodo salía con **cinco meses** sacados de
una frase sobre arrieros del siglo pasado: «acostumbraban tener dos salidas,
las que empezaban en diciembre y terminaban en marzo».

Ahora cada frase se puntúa: suman los verbos de celebración en presente —«se
celebra», «se realiza cada año»— y restan las marcas de pasado. Si ninguna
frase habla de la fecha, se dice que **la ficha no la precisa**. Son 8 de 36.

El primer intento de arreglarlo fue rechazar toda frase con una marca de
pasado, y dejó **las 36 fiestas sin fecha**: casi toda descripción menciona
algún año. Puntuar en vez de descartar fue lo que funcionó.

### 3. Los patrones se escribieron sin `r"..."`

Python convirtió cada `\b` en un carácter de retroceso literal, y las
expresiones dejaron de reconocer nada sin dar ningún error. Se detectó porque
el extractor devolvía cero en un caso que a mano era evidente.

---

## Lo que no se hizo, y por qué

**No se rellena lo que la ficha no dice.** El 29 % de los recursos sigue sin
horario y 8 fiestas sin fecha. Para esos, el itinerario sigue avisando de que
no puede garantizar que estén abiertos.

**Las fechas de las fiestas se comparan por mes, no por día.** Muchas son
móviles —«el último domingo de enero», «fecha móvil entre marzo y abril»—.
Convertirlas a un día exacto exigiría calcular el calendario litúrgico y
adivinar lo que la ficha no dice. Se guarda la frase literal, que es lo que el
visitante lee, y los meses, que es lo que el sistema compara.

---

## Relacionado

- [Los avisos son datos, no frases](2026-08-30-los-avisos-son-datos-no-frases.md)
- [Fuente del catálogo](2026-08-29-fuente-del-catalogo-mincetur.md)
- [Proveedores de demostración](2026-08-29-proveedores-de-demostracion.md)
