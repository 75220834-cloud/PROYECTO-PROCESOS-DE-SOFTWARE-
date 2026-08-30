# 10 — Los indicadores

**Qué explica este archivo:** los seis indicadores con su fórmula, su valor
actual, dónde se calculan y —lo más importante— **lo que cada uno no dice**.

Los seis salen juntos en `GET /api/indicadores/tablero` y se ven en `/panel`,
pestaña **Indicadores**.

---

## La regla que gobierna este tablero

> **Un número sin decir qué NO dice es peor que no tener número.**

Cuatro de los seis miden algo distinto de lo que su nombre sugiere a primera
vista, porque el dato que haría falta para medir lo prometido **no existe**.
Enseñar seis cifras sin esa letra pequeña sería exactamente el problema que
este proyecto dice combatir: presentar como hecho algo que es una aproximación.

Por eso la salvedad **no es una nota al pie**: viaja con el indicador y la
interfaz la pinta siempre.

---

## Indicador 1 — Oferta validada y vigente

| | |
|---|---|
| **Brecha** | 1 — no existe una fuente integrada, oficial y actualizada |
| **Fórmula** | `100 × validados / total` |
| **Valor** | **79,32 %** (234 de 295) |
| **Dónde** | `rutas/valoraciones.py::_indicador_1_catalogo` |

**Lo que NO dice:** «validado» significa que pasa las comprobaciones
automáticas de coordenadas, provincia y vigencia. **No significa que alguien
haya ido a comprobarlo sobre el terreno.**

---

## Indicador 2 — Preferencias que llegan a itinerario

| | |
|---|---|
| **Brecha** | 3 — las preferencias no se registran ni se usan |
| **Fórmula** | `100 × preferencias_con_itinerario / total` |
| **Dónde** | `rutas/valoraciones.py::_indicador_2_preferencias` |

**⚠️ Este indicador SUSTITUYE al que proponía el plan.**

El plan pedía «**tiempo** entre preferencias y confirmación del itinerario».
Sin uso real no hay tiempos que medir: todas las preferencias de la base se
crearon en pruebas, y el tiempo entre una y su itinerario sería el tiempo que
tardé yo en pulsar un botón.

Se mide **cuántas preferencias llegan a convertirse en un plan**, que es
medible hoy y responde a la misma pregunta: ¿sirve de algo registrarlas?

**Prepárate para que te pregunten por esta sustitución.** La respuesta está en
[14](14-guion-de-defensa.md).

---

## Indicador 3 — Recomendaciones sin error

| | |
|---|---|
| **Brecha** | 2 y 3 — el análisis recae en el visitante |
| **Valor** | **100 %** |
| **Dónde** | `rutas/valoraciones.py::_indicador_3_recomendaciones` |

**Qué mide exactamente:** que **ninguna recomendación contradice una
restricción declarada** por el visitante — alcance según su movilidad,
presupuesto, intereses, validación del recurso.

**Lo que NO dice:** no mide si son las que la persona habría elegido. Eso
exigiría un conjunto anotado por personas reales que nadie ha construido.

Es un 100 % **por construcción**: los filtros duros se aplican antes de
puntuar. Y decirlo así es más honesto que presentarlo como un logro del modelo.

---

## Indicador 4 — Itinerarios viables y trazables

| | |
|---|---|
| **Brecha** | 4 — sin geografía ni costo |
| **Valor** | **4 de 4 perfiles**, peor caso medido **5,05 s de 10 s** |
| **Dónde** | `rutas/valoraciones.py::_indicador_4_itinerarios` |

**⚠️ También sustituye al del plan.**

El plan pedía «**error medio entre tiempo de traslado estimado y real**». No es
medible sin cronometrar traslados en campo, y nadie los ha cronometrado.

Se mide que **el itinerario no contradiga ninguna de sus propias
restricciones**: cabe en el día, respeta el presupuesto de traslado, no repite
paradas, y las horas encajan con los horarios conocidos. Sobre 4 perfiles de
visitante distintos, y con el tiempo de cálculo del peor caso.

**Los tres atajos que NO se tomaron**, y que conviene saber nombrar:

1. No se compara el tiempo estimado con otro tiempo estimado.
2. No se inventan tiempos «reales» de referencia.
3. No se declara medido lo que solo está calculado.

Ver `docs/indicadores/04-itinerarios-viables-y-trazables.md`.

---

## Indicador 5 — Canales para confirmar un servicio

| | |
|---|---|
| **Brecha** | 5 y 6 — capacidad no verificable, sin punto único |
| **Valor** | **1 canal** (antes 3 o más) |
| **Dónde** | `rutas/valoraciones.py::_indicador_5_coordinacion` |

**La parte válida:** el número de canales es **estructural**. Antes había que
buscar el contacto, llamar, y confirmar por otro medio. Ahora es uno. Eso es
cierto y no depende del volumen de datos.

**Lo que NO dice, y es importante:** las **horas medias hasta confirmar no
significan nada**. Los proveedores son de demostración y el ciclo se ejecuta en
segundos porque lo ejecuto yo desde dos pestañas.

---

## Indicador 6 — Experiencias con valoración

| | |
|---|---|
| **Brecha** | 7 — la retroalimentación no retorna estructurada |
| **Fórmula** | `100 × itinerarios_con_valoracion / total_itinerarios` |
| **Valor** | **100 %** |
| **Dónde** | `servicios/evidencia.py::calcular_cobertura` |

**Por qué sobre itinerarios y no sobre valoraciones:** la brecha pregunta
«¿cuántas experiencias volvieron al proceso?», no «¿cuántas opiniones hay?».
Diez valoraciones de un mismo viaje siguen siendo **una** experiencia.

Hay una prueba que lo fija: `test_cuenta_itinerarios_y_no_valoraciones`.

**Lo que NO dice:**

- **No dice que la gente esté contenta.** Un 100 % de cobertura con media de
  1,5 sería un desastre bien medido.
- **No dice que las valoraciones sean representativas.** Quien valora es quien
  quiere valorar, y eso sesga.
- **No dice que el sentimiento detectado sea correcto.** El modelo acierta 12
  de 14 frases de prueba, no 14 de 14.

---

## El fallo que casi rompe el indicador 6

Guardar un itinerario **no era idempotente**. La pantalla de valoración rearma
el itinerario al entrar, y con `guardar: true` creaba una fila nueva cada vez.

Efecto: el denominador crecía con duplicados que nadie iba a valorar nunca, así
que **el porcentaje bajaba solo por visitar una pantalla**.

Se encontró **usando la aplicación**, no con una prueba. Se corrigió haciendo
`guardar_itinerario` idempotente por preferencia y fecha, y hay tres pruebas de
regresión.

---

## Cómo consultarlos

```bash
curl http://localhost:8000/api/indicadores/tablero
```

O entra como `gestor@rutavivamantaro.pe` y abre `/panel` → **Indicadores**.

**Aviso sobre los volúmenes:** con 5 valoraciones, 3 itinerarios y 1 solicitud,
**casi nada es estadísticamente sólido**. El propio tablero lo dice antes que
los números, que es lo correcto. Si preguntan «¿esto es significativo?», la
respuesta honesta es **no**.

---

## Relacionado

- [09 — Los seis incrementos](09-los-seis-incrementos.md)
- [14 — Guion de defensa](14-guion-de-defensa.md)
- `docs/indicadores/` — una nota por indicador, con su medición del día
