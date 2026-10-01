# Guion del video: una historia de usuario a la vez

**Para qué es esto:** grabar la demostración de RutaVivaMantaro mostrando **la
aplicación funcionando** en `http://localhost:5173`, historia por historia.
Aquí no hay código: solo **qué abrir, qué señalar con el cursor y qué decir**.

**Duración objetivo:** 9 a 11 minutos en total.
**Orden:** HU-01 → HU-02 → HU-03 → HU-04 → HU-05 → HU-06. Es el mismo orden en
que una persona real usa la aplicación, así que el video se graba **de una sola
pasada**, sin volver atrás.

---

## Antes de pulsar «grabar» (5 minutos de preparación)

### 1. Levanta todo y compruébalo

| Orden | Qué | Cómo comprobar que está bien |
|---|---|---|
| 1 | Docker Desktop abierto | el ícono no dice «starting» |
| 2 | `docker compose up -d` | `docker compose ps` dice `healthy` |
| 3 | `uvicorn` (backend) | abre `http://localhost:8000/docs` y carga |
| 4 | `npm run dev` (frontend) | abre `http://localhost:5173` y carga |
| 5 | Ollama | solo si vas a mostrar el asistente |

### 2. Calienta el itinerario antes de grabar

**Esto es lo más importante de la preparación.** La primera vez que se arma un
itinerario, el sistema descarga y procesa la red vial del valle, y **tarda
bastante**. Si grabas eso en vivo, el video se queda 40 segundos mirando
«Armando tu itinerario…».

Haz el recorrido completo **una vez entero antes de grabar** (asistente →
recomendaciones → itinerario). Después, cuando grabes, el mismo recorrido
responde en pocos segundos porque la red vial ya está en caché.

### 3. Deja el navegador limpio

- Ventana del navegador **maximizada**, zoom al 100 %.
- **Cierra la consola del navegador** (F12). Si queda abierta se ve en el video.
- Ten estas direcciones listas, pero **no las abras todavía**:
  - `http://localhost:5173/`
  - `http://localhost:5173/explorar`
- **Tema claro** (el sol/luna está arriba a la derecha). Se lee mejor al grabar.
- Si vas a mostrar el panel del gestor: `gestor@rutavivamantaro.pe` /
  `RutaViva2026`. Déjalo ya iniciado en **otra pestaña** para no grabar el
  tecleo de la contraseña.

### 4. Tres cosas que NO debes decir en todo el video

Se contradicen con los datos reales y cualquiera puede desmontarlas en la
sustentación:

| No digas | Di esto |
|---|---|
| «los precios son los oficiales» | «son estimaciones nuestras, y la aplicación lo dice con la palabra *aprox.*» |
| «el tiempo de viaje es exacto» | «es una estimación, y cuando el cálculo es menos fiable la aplicación lo avisa» |
| «cada lugar tiene su foto» | no lo menciones. El inventario del MINCETUR **no publica fotos**, y la ficha no muestra ninguna |

---

# HU-01 · Explorar el catálogo de la ruta

> **Criterio que estás demostrando:** el visitante encuentra los recursos
> turísticos del valle, los ve en lista y en mapa, y los puede filtrar.
> **Prueba automatizada que lo respalda:** `e2e-01-catalogo.spec.ts`, 5 casos.

### Minuto estimado: 0:00 – 2:00

### Paso 1 — Arranca en la página de inicio

**En pantalla:** abre `http://localhost:5173/`

**Qué señalas con el cursor:** el título grande **«Descubre el Valle del Mantaro
a tu manera»**, y bajas despacio hasta **«Las cuatro provincias de la ruta»**.

**Qué dices:**

> «Esta es RutaVivaMantaro. Es una plataforma para planificar un recorrido por
> la Ruta del Valle del Mantaro, en Junín, que cubre cuatro provincias:
> Huancayo, Concepción, Jauja y Chupaca.
> Voy a recorrer las historias de usuario en el mismo orden en que las usaría un
> visitante real.»

### Paso 2 — Entra a «Explorar»

**En pantalla:** clic en **«Explorar»** en el menú de arriba.

**Qué señalas:** las **cuatro tarjetas de indicadores** que están arriba del
listado, una por una, de izquierda a derecha:
`Recursos en el catálogo` · `Validados` · `Con coordenadas` · `Vigentes`.

**Qué dices:**

> «La primera historia de usuario es: *como visitante quiero explorar la oferta
> turística del valle*.
> Esto que ven aquí no es una lista inventada por nosotros: son los recursos del
> **Inventario Nacional de Recursos Turísticos del MINCETUR**, de las cuatro
> provincias de la ruta. Son **295 recursos**.
> Y arriba, antes de la lista, la aplicación declara el estado de su propio
> catálogo: cuántos están validados, cuántos tienen coordenada y cuántos están
> vigentes. Volveré a estos números en la historia dos.»

### Paso 3 — Muestra la lista y el mapa juntos

**Qué señalas:** mueve el cursor del listado de tarjetas al mapa que está al
lado, y haz **un solo scroll suave** para que se vea que los dos están en la
misma pantalla.

**Qué dices:**

> «Cada recurso se ve en dos formas a la vez: como tarjeta en la lista, con su
> provincia, su distrito y su categoría; y como marcador en el mapa. Los
> marcadores se agrupan cuando hay muchos cerca, para que el mapa siga siendo
> legible.»

### Paso 4 — Filtra. Esto es el corazón de la HU-01

**En pantalla, en este orden exacto:**

1. En **Provincia**, elige **Jauja**.
2. Espera a que la lista y el mapa se actualicen (es casi inmediato).

**Qué señalas:** primero el contador **«… recursos encontrados»**, y después el
mapa, que ahora tiene menos marcadores y está centrado en otra zona.

**Qué dices:**

> «Ahora filtro por provincia. Elijo Jauja.
> Fíjense en dos cosas: el contador de resultados cambia, y **el mapa se filtra
> también**. No es una lista que se filtra y un mapa que se queda quieto: las
> dos vistas responden al mismo filtro.»

**Luego:**

3. Escribe **`laguna`** en el buscador.

**Qué dices:**

> «Y el buscador por nombre. Escribo *laguna*.
> Una cosa que vale la pena mencionar: la búsqueda **ignora las tildes en los
> dos sentidos**. Si escribo *concepcion* sin tilde, encuentra *Concepción* con
> tilde. Eso está así porque la fuente oficial no es consistente con los
> acentos, y obligar al visitante a adivinar cómo está escrito el nombre sería
> hacerle pagar un problema que no es suyo.»

**Después:** borra el texto del buscador y pon la provincia en **«Todas»** otra
vez, para dejar la pantalla limpia.

### Paso 5 — Cierra la historia 1

**Qué dices:**

> «Con esto queda cubierta la primera historia: el visitante encuentra la oferta
> del valle, la ve en lista y en mapa, y la filtra por provincia, distrito,
> categoría y nombre. Esto está respaldado por cinco pruebas automatizadas de
> extremo a extremo que hacen exactamente lo que acabo de hacer a mano.»

---

# HU-02 · Que el dato sea confiable, y que se diga cuándo no lo es

> **Criterio que estás demostrando:** cada recurso declara si su información
> está validada y vigente, y cuando falta un dato la aplicación lo dice en vez
> de disimularlo.
> **Prueba que lo respalda:** la validación del catálogo en el backend
> (`test_validacion_catalogo.py`, 20 casos) y el caso E2E del sello.

### Minuto estimado: 2:00 – 3:40

### Paso 1 — Señala los sellos de las tarjetas

**En pantalla:** sigues en `/explorar`, sin filtros.

**Qué señalas:** la **etiqueta de color** que tiene cada tarjeta: unas dicen
**«Validado»** en verde, otras dicen **«Incompleto»** en ocre. Pasa el cursor
**encima de un sello verde y quédate ahí dos segundos** para que salga la
ayuda: *«Tiene nombre, distrito reconocido y coordenada dentro del Valle del
Mantaro»*.

**Qué dices:**

> «Segunda historia de usuario: *como visitante quiero saber si puedo confiar en
> el dato que estoy viendo*.
> Cada recurso lleva un sello. Verde si pasó la validación, ocre si no.
> Y la validación no es una opinión: son reglas concretas. Tiene que tener
> nombre, un distrito que exista de verdad en el valle, y una coordenada que
> caiga dentro del Valle del Mantaro. Si le falta cualquiera de esas, queda
> marcado como incompleto.»

### Paso 2 — Muestra un recurso que NO pasa, y lo que dice de sí mismo

**En pantalla:** busca en la lista una tarjeta que diga **«Incompleto»** y que
además tenga el texto **«Sin coordenada en la fuente oficial»**. Señálalo.

**Qué dices:**

> «Y aquí está la decisión de la que más orgulloso estoy del proyecto.
> Este recurso **no tiene coordenada en el inventario del MINCETUR**. Nosotros
> podríamos haberlo puesto en el centro de su distrito y el mapa se vería más
> completo y más bonito.
> **No lo hicimos.** Eso sería inventar un dato. Lo que hace la aplicación es
> decirlo: *sin coordenada en la fuente oficial*. Aparece en la lista, pero no
> en el mapa, y dice por qué.»

### Paso 3 — Vuelve a los indicadores de arriba

**En pantalla:** sube al tope de la página.

**Qué señalas:** la tarjeta de **«Validados»** y su porcentaje.

**Qué dices:**

> «Y por eso estos números de arriba son honestos. El indicador del primer
> incremento del proyecto es *porcentaje de oferta con información validada y
> vigente*, y su valor está a la vista del visitante, no escondido en un informe
> nuestro. Si mañana el catálogo empeora, este número baja aquí mismo.»

### Paso 4 — Abre la ficha de un recurso

**En pantalla:** clic en **«Ver detalle»** de un recurso que esté **validado**.

**Qué señalas:** la **descripción** y, abajo, la referencia a la fuente.

**Qué dices:**

> «Y en la ficha de cada recurso está su descripción, que no la escribimos
> nosotros: se leyó de la ficha oficial del MINCETUR de ese recurso, de los 295,
> uno por uno. La aplicación dice de dónde salió y con qué fecha de corte.»

**Después:** vuelve atrás en el navegador.

> **Si alguien te pregunta por las fotos:** di la verdad, que es la respuesta
> fuerte: «el inventario del MINCETUR no publica fotografías de los recursos.
> Poner imágenes de relleno contradiría la regla de honestidad del proyecto, así
> que la ficha no muestra ninguna. Está declarado como decisión de arquitectura
> y como limitación conocida.»

---

# HU-03 · Armar el viaje sin tener que registrarse

> **Criterio que estás demostrando:** el visitante completa el asistente de
> preferencias y obtiene su viaje **sin crear cuenta**, y el asistente no lo
> deja avanzar con datos incompletos.
> **Prueba que lo respalda:** `e2e-02-preferencias.spec.ts`, 2 casos.

### Minuto estimado: 3:40 – 5:40

### Paso 1 — Entra al asistente y di la promesa en voz alta

**En pantalla:** clic en **«Planificar»** del menú (o en «Planificar mi viaje»
desde el inicio).

**Qué señalas:** la **barra de progreso** de arriba y el texto **«Paso 1 de 6»**.
Después señala el aviso que dice **«No necesitas crear una cuenta…»**.

**Qué dices:**

> «Tercera historia: *como visitante quiero que la aplicación me proponga un
> viaje según lo que me gusta, sin obligarme a registrarme primero*.
> Y esto es una promesa del proyecto, no una comodidad: **todo el recorrido
> funciona sin cuenta**. Fíjense arriba a la derecha: dice **Iniciar sesión**.
> Yo no he iniciado sesión. Y voy a armar el viaje completo así.
> Son seis pasos.»

### Paso 2 — Recorre los seis pasos, diciendo para qué sirve cada uno

Ve paso por paso. **Una frase por paso, no más**, o se hace largo:

| Paso | Qué pones | Qué dices mientras lo pones |
|---|---|---|
| **1 · ¿Cuándo viajas?** | las fechas ya vienen puestas; déjalas o pon un fin de semana | «Las fechas. Con esto el sistema sabe cuántos días tengo, y puede avisarme si cae alguna fiesta del valle esos días.» |
| **2 · ¿Desde dónde sales?** | elige **Huancayo** | «De dónde salgo cada día. Y esta lista no está escrita a mano: son los distritos donde **de verdad hay recursos registrados** en el inventario.» |
| **3 · ¿Cuál es tu presupuesto?** | **200** | «Mi presupuesto para entradas y traslados. Y aquí ya aparece el aviso: es orientativo, los precios de transporte en el valle cambian.» |
| **4 · ¿Qué te interesa?** | marca **2 o 3** intereses | «Qué me interesa. Puedo marcar varios: naturaleza, cultura, gastronomía…» |
| **5 · ¿Cómo prefieres moverte?** | elige un modo | «Cómo me muevo. Esto decide qué traslados me va a proponer entre un lugar y otro. Y fíjense en esta casilla: **necesito accesibilidad para movilidad reducida**. Si la marco, se descartan los tramos con pendiente fuerte.» |
| **6 · ¿A qué ritmo?** | elige **Moderado** | «Y a qué ritmo quiero viajar, que determina cuántos lugares caben en un día.» |

### Paso 3 — Demuestra la validación (hazlo de verdad, en vivo)

**Esto hay que mostrarlo, no contarlo.** Hazlo en el **paso 2**:

1. Llega al paso 2 (**¿Desde dónde sales?**).
2. **No elijas distrito.**
3. Pulsa **«Siguiente»**.
4. Aparece en rojo: **«Elige el distrito desde el que sales.»**

**Qué dices:**

> «Y el asistente no me deja avanzar con el paso incompleto. Si intento pasar sin
> elegir el distrito de origen, me lo dice y se queda donde está. No me deja
> llegar al final con un viaje imposible de calcular.»

Luego elige el distrito y continúa.

### Paso 4 — Guarda, y muestra que sigue sin cuenta

**En pantalla:** en el paso 6, pulsa **«Guardar mis preferencias»**.

**Qué señalas:** el título **«Ya sabemos qué buscas»**, el bloque **«Lo que nos
contaste»** con el resumen, y después **el menú de arriba a la derecha, que
TODAVÍA dice «Iniciar sesión»**.

**Qué dices:**

> «Guardado. Aquí está el resumen de lo que le dije.
> Y lo importante: **mira arriba a la derecha. Sigue diciendo "Iniciar sesión".**
> Nunca me registré. El viaje quedó guardado y su identificador vive en mi
> navegador.»

**Luego señala el bloque «¿Quieres guardar este viaje?»:**

> «Y la aplicación me ofrece crear una cuenta **ahora, al final**, para
> conservarlo. Si lo hago, el viaje que ya armé se asocia automáticamente a mi
> cuenta nueva: **no tengo que volver a responder las seis preguntas.** Esa es la
> diferencia entre pedir el registro al principio y pedirlo cuando ya tiene
> sentido pedirlo.»

---

# HU-04 · Recomendaciones que explican por qué

> **Criterio que estás demostrando:** el sistema propone recursos ordenados
> según el perfil, **cada uno dice por qué fue elegido**, y también se puede ver
> qué quedó fuera y por qué.
> **Prueba que lo respalda:** `e2e-03-recomendaciones.spec.ts`, 2 casos.

### Minuto estimado: 5:40 – 7:20

### Paso 1 — Entra a las recomendaciones

**En pantalla:** clic en **«Ver lo que te proponemos»**.

**Qué señalas:** el título **«Lo que te proponemos»** y el subtítulo con el
total de recursos ordenados.

**Qué dices:**

> «Cuarta historia: *como visitante quiero que me recomienden qué visitar, y
> quiero entender por qué me lo recomiendan*.
> Aquí está lo que el sistema me propone, ordenado.»

### Paso 2 — Esto es lo más importante del video entero. Tómate tu tiempo

**En pantalla:** acércate a **la primera tarjeta** de la lista.

**Qué señalas, en este orden exacto, y despacio:**

1. El **puntaje de afinidad**.
2. La línea **«Porque te interesa …»**.
3. La línea **«Pesaron: …»** con las palabras.
4. La distancia **«a … km»**.

**Qué dices:**

> «Y aquí está la parte que de verdad cierra esta historia de usuario. **No es
> que salga una lista ordenada. Es que cada recomendación dice por qué está
> ahí.**
> Esta primera tarjeta tiene su puntaje de afinidad. Dice *porque te interesa*, y
> nombra el interés que marqué. Y después dice **"Pesaron"**, y nombra las
> palabras concretas de la descripción de ese recurso que más empujaron para que
> suba en la lista.
> Eso no es una frase de relleno: **son los términos reales que el cálculo
> encontró.** Si yo hubiera marcado otros intereses, estas palabras serían otras.»

### Paso 3 — Señala el pie de la lista: qué calculó esto

**En pantalla:** baja hasta el final de la lista de recomendaciones.

**Qué señalas:** la línea que dice **«Calculado con el modelo de afinidad
(TF-IDF y similitud coseno)»**.

**Qué dices:**

> «Y la aplicación dice **con qué** lo calculó: con el modelo de afinidad, que
> usa TF-IDF y similitud coseno sobre las descripciones oficiales.
> Y esto tiene una contraparte que es una regla del proyecto: **todo lo que usa
> un modelo tiene que tener una alternativa por reglas**, que se activa por
> configuración. Si el modelo se cae o se desactiva, esta misma pantalla sigue
> funcionando y **dice que está calculando con las reglas explícitas, sin
> modelo.** El visitante siempre sabe qué lo decidió.»

### Paso 4 — Abre los descartados

**En pantalla:** busca el bloque que dice **«… recursos descartados»** y pulsa
**«Ver»**.

**Qué señalas:** los motivos que aparecen, por ejemplo *«sin coordenadas: no
puede entrar en un itinerario»* o *«no pasó la validación del catálogo»*.

**Qué dices:**

> «Y lo contrario también está a la vista: **qué quedó fuera, y por qué.**
> La mayoría de los sistemas de recomendación te dan una lista y lo demás
> desaparece sin explicación. Aquí cada descarte trae su motivo: este quedó fuera
> porque no tiene coordenadas y entonces no puede entrar en un itinerario; este
> otro porque no pasó la validación del catálogo.
> Se descartan **antes** de puntuar nada, y la aplicación lo declara.»

---

# HU-05 · El itinerario del día, con horarios y costos

> **Criterio que estás demostrando:** las recomendaciones se convierten en un
> plan de día real, con paradas en orden, horas y totales de tiempo, distancia
> y costo.
> **Prueba que lo respalda:** `e2e-04-itinerario.spec.ts`, 3 casos.

### Minuto estimado: 7:20 – 9:10

### Paso 1 — Arma el itinerario

**En pantalla:** pulsa **«Armar mi itinerario»**.

**Qué dices mientras carga** (recuerda: ya lo calentaste antes de grabar, así
que no debería tardar mucho):

> «Quinta historia: *como visitante quiero que esas recomendaciones se conviertan
> en un plan de un día de verdad, con horarios*.
> Mientras calcula: lo que está haciendo es resolver las rutas **sobre la red
> vial real del valle**, con los datos de OpenStreetMap, y calculando el desnivel
> de cada tramo.»

### Paso 2 — Los totales del día

**En pantalla:** señala el bloque **«Totales del día»**.

**Qué señalas, uno por uno:** `Duración` · `Traslados` · `Recorrido` ·
`Esfuerzo`.

**Qué dices:**

> «Totales del día. Cuánto dura, cuánto cuestan los traslados, cuántos
> kilómetros recorro y cuánto esfuerzo implica, en metros de subida acumulada.
> Y fíjense en el costo: dice **"aprox."**. Eso está en toda la aplicación y es
> deliberado. **Nosotros no tenemos tarifas oficiales de transporte del valle.**
> Lo que hay es una estimación nuestra, con una fórmula declarada y su fecha de
> referencia. Decir una cifra exacta sería mentir con cara de precisión.
> Y también dice **"solo el transporte, sin entradas ni comida"**, para que nadie
> crea que ese es el costo del día completo.»

### Paso 3 — La línea de tiempo, parada por parada

**En pantalla:** señala el bloque **«El plan del día»**.

**Qué señalas:** la **primera parada** con su hora, el **bloque de traslado** que
va entre dos paradas (con su ícono de modo, su duración y su precio), y la
**segunda parada**.

**Qué dices:**

> «Y este es el plan. No es una lista de lugares: es un día.
> Cada parada tiene su hora de llegada y su hora de salida. Y **entre dos paradas
> está el traslado**: cómo me muevo, cuánto tarda y cuánto cuesta aproximadamente.
> Y el orden no lo elegí yo ni es el orden de la lista de recomendaciones.»

**Baja al pie del itinerario y señala el texto que empieza «Este orden lo calculó
el optimizador de rutas…»:**

> «Lo calculó un optimizador de rutas, que busca la combinación con **mayor
> afinidad que cabe en el día y en mi presupuesto**. No es el más corto: es el que
> más me gusta de lo que sí me alcanza el tiempo y el dinero.
> Y otra vez, igual que en las recomendaciones: si se desactiva el optimizador,
> hay una alternativa por reglas y **la pantalla dice cuál de las dos se usó**.»

### Paso 4 — El mapa del itinerario

**En pantalla:** señala el mapa del itinerario.

**Qué dices:**

> «Y el mismo itinerario dibujado sobre el mapa, en el orden de las paradas.»

### Paso 5 — Reordena una parada en vivo (esto impresiona)

**En pantalla:** **arrastra una parada** a otra posición y suéltala.

**Qué señalas:** el texto **«Recalculando…»**, y después las **horas y los
costos que cambiaron**.

**Qué dices:**

> «Y puedo cambiar el orden. Arrastro una parada… y fíjense: dice
> **"Recalculando"**, y los horarios y los costos **se vuelven a calcular solos**
> con el orden nuevo. No es una lista que se reordena visualmente: se recalcula el
> día entero.
> Y se puede hacer también con el teclado, con Alt y las flechas, para quien no
> pueda usar el ratón.»

---

# HU-06 · Que la aplicación avise de sus propios límites

> **Criterio que estás demostrando:** cuando un cálculo es menos fiable o hay
> algo que el visitante debe saber antes de salir, la aplicación **lo dice**, de
> forma visible y arriba.
> **Prueba que lo respalda:** `e2e-04-itinerario.spec.ts` (el caso que exige que
> haya al menos un aviso visible marcando algo como estimado o no garantizado).

### Minuto estimado: 9:10 – 10:30

### Paso 1 — Sube al bloque de avisos

**En pantalla:** sigues en el itinerario. **Sube al tope**, al bloque que dice
**«Antes de salir, ten en cuenta»**.

**Qué dices:**

> «Y la sexta historia es la que, para mí, define el proyecto: *como visitante
> quiero que la aplicación me avise de lo que no sabe o de lo que puede fallar*.
> Fíjense **dónde** está este bloque: **arriba, antes del plan**. No al final en
> letra chica. Un aviso de que un tramo es una estimación, o de que voy a estar a
> casi cuatro mil metros de altura, **no es un detalle de letra pequeña: es algo
> que cambia cómo preparo el viaje.**»

### Paso 2 — Lee uno o dos avisos reales, los que te hayan salido

Lee en voz alta el aviso que te aparezca y explícalo. Los más probables:

**Si sale el aviso de altitud:**

> «Este dice que el punto más alto del día está a tantos metros sobre el nivel
> del mar, y que si vengo de la costa debería dedicar el primer día a
> aclimatarme. Eso no sale de ninguna fuente turística: sale de la altitud real
> de los recursos del itinerario.»

**Si sale el aviso de tramos estimados:**

> «Y este es el más importante. Dice que uno de los traslados **es una
> estimación**, porque OpenStreetMap no tiene vías registradas cerca de ese
> punto, así que la distancia se calculó en línea recta corregida, y que **el
> tiempo real puede ser bastante mayor**.
> Podríamos no haber dicho nada. El número se vería igual de limpio y nadie se
> daría cuenta. Pero entonces el visitante planificaría su día con un dato que
> nosotros sabemos que es más débil que los otros, y no se lo dijimos.»

**Si sale el aviso de horarios no publicados:**

> «Y este dice que algunos de los recursos **no tienen horario de atención
> publicado en el inventario del MINCETUR**, así que para esos el itinerario solo
> garantiza que la visita cabe en el día, y que conviene confirmar antes de ir.
> No nos inventamos un horario de nueve a cinco para que el plan se vea completo.»

### Paso 3 — Muestra la marca de tramo estimado en la línea de tiempo

**En pantalla:** baja a la línea de tiempo y busca un traslado que tenga la marca
de **«Tramo estimado»**. Señálala.

**Qué dices:**

> «Y el aviso no vive solo arriba: **el tramo concreto también está marcado aquí,
> donde está el número**. Para que no haya forma de leer el tiempo de ese traslado
> sin ver que es una estimación.»

### Paso 4 — Cierra el video con esto

**Qué dices:**

> «Y eso es lo que resume el proyecto. Hay tres sitios donde habríamos podido
> hacer que la aplicación se viera mejor inventando un dato: poner los recursos
> sin coordenada en el centro de su distrito, dar una tarifa exacta de transporte,
> y callarnos que algunos tramos son estimaciones.
> **En los tres decidimos decirlo.** Una aplicación de turismo que dice lo que no
> sabe es más útil que una que se ve completa y te deja tirado en el camino.
> Y todo lo que acabo de mostrar está respaldado por pruebas automatizadas que
> hacen este mismo recorrido: doce pruebas de extremo a extremo sobre la pantalla
> real, además de las de la interfaz y las de la API.»

---

## Extras, solo si te sobra tiempo

Son **opcionales**. No los metas si el video ya pasa de 11 minutos.

| Extra | Dónde | Qué decir en una frase |
|---|---|---|
| **Los dos idiomas** | selector de idioma, arriba | «La aplicación entera está en español y en inglés, **incluidos los avisos que genera el servidor**, que viajan como código y se traducen en el navegador.» |
| **El panel del gestor** | `/panel` con `gestor@rutavivamantaro.pe` | «Y desde el rol de gestor están los seis indicadores del proyecto medidos sobre los datos reales, no escritos a mano.» |
| **Mis viajes** | `/mis-viajes` con sesión iniciada | «Y si decidí registrarme, aquí quedan los viajes que conservé.» |
| **El asistente conversacional** | panel de conversación | «Y hay un asistente que responde preguntas, pero **no genera datos**: solo consulta la base de datos del proyecto. Por diseño no puede inventarse un atractivo que no exista.» |

---

## Chuleta de una sola página (imprímela o tenla al lado)

| HU | Pantalla | El momento que NO puedes olvidar |
|---|---|---|
| **01** | `/explorar` | filtrar por provincia y señalar que **el mapa también se filtra** |
| **02** | `/explorar` | el recurso que dice **«sin coordenada en la fuente oficial»** |
| **03** | `/preferencias` | que arriba **sigue diciendo «Iniciar sesión»** al terminar |
| **04** | `/preferencias/:id/resultados` | la línea **«Pesaron: …»** y la lista de **descartados con su motivo** |
| **05** | `/preferencias/:id/itinerario` | **arrastrar una parada** y que se recalculen horas y costos |
| **06** | el mismo itinerario, arriba | el bloque **«Antes de salir, ten en cuenta»** y el **«Tramo estimado»** |
