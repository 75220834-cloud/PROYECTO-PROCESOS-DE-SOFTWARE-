# Indicador 6 — Experiencias con valoración registrada

**Incremento:** 6 — Valoración de cierre y evidencia
**Brecha que mide:** 7 — *la retroalimentación no retorna estructurada al
proceso ni al gestor*
**Estado:** implementado

---

## Qué mide

El porcentaje de **itinerarios** que tienen al menos una valoración.

```
porcentaje = 100 × itinerarios_con_valoracion / total_itinerarios
```

## Por qué sobre itinerarios y no sobre valoraciones

La pregunta que responde la brecha 7 es *«¿cuántas experiencias volvieron al
proceso?»*, no *«¿cuántas opiniones hay?»*.

Diez valoraciones de un mismo viaje —el día completo y nueve paradas— siguen
siendo **una** experiencia que retornó. Contarlas como diez inflaría el
indicador sin que nada hubiera mejorado.

Hay una prueba que lo fija: `test_cuenta_itinerarios_y_no_valoraciones` crea
tres valoraciones de un solo itinerario y comprueba que la cobertura sale 100 %
con `con_valoracion == 1`.

## El fallo que casi rompe este indicador

Guardar un itinerario **no era idempotente**. La pantalla de valoración rearma
el itinerario al entrar, y con `guardar: true` creaba una fila nueva cada vez.

Efecto sobre el indicador: el denominador crecía con duplicados que nadie iba a
valorar nunca, así que el porcentaje bajaba solo por visitar una pantalla.

Se corrigió haciendo `guardar_itinerario` idempotente por preferencia y fecha:
«el itinerario del día X para la preferencia Y» es una sola cosa. Tres pruebas
de regresión lo fijan.

Se encontró **usando la aplicación**, no con una prueba.

---

## Qué más se mide, y por qué importa

El indicador de cobertura es un número; la brecha pide que la
retroalimentación *retorne estructurada al gestor*. Eso son cuatro agregaciones
más, todas en `GET /api/indicadores/evidencia`:

| Agregación | Qué pregunta responde |
|---|---|
| Distribución de sentimiento | ¿La gente sale contenta? |
| **Temas con su % negativo** | **¿Dónde actuar?** |
| Ranquin de recursos con sus temas | ¿Qué va peor, y por qué? |
| Evolución por mes | ¿Esto mejora o empeora? |

La segunda es la que convierte opiniones en decisiones. Un tema muy mencionado
y mayoritariamente negativo es un problema concreto; uno muy mencionado y
positivo es una fortaleza que conviene no romper.

---

## Medición del 29 de agosto de 2026

Cuatro valoraciones sobre un itinerario de cinco paradas, analizadas con el
modelo:

| Puntuación | Sentimiento | Confianza | Temas |
|---|---|---|---|
| 5 ★ | positivo | 0,99 | limpieza, atención |
| 1 ★ | negativo | 0,99 | limpieza, precio |
| 3 ★ | negativo | 0,76 | acceso, señalización, paisaje |
| 4 ★ | positivo | 0,90 | atención |

| Métrica | Valor |
|---|---|
| Itinerarios valorados | **100,0 %** (1 de 1) |
| Valoraciones | 4 |
| Con comentario | 4 |
| Puntuación media | 3,25 / 5 |
| Analizadas por el modelo | 4 |
| Analizadas por las reglas | 0 |

El tablero avisó por sí solo de que con cuatro valoraciones las medias son
orientativas, y marcó los tres recursos como «pocas valoraciones».

---

## Lo que este indicador NO dice

- **No dice que la gente esté contenta.** Dice cuántas experiencias volvieron
  con opinión. Un 100 % de cobertura con media de 1,5 sería un desastre bien
  medido.
- **No dice que las valoraciones sean representativas.** Quien valora es quien
  quiere valorar, y eso sesga: la gente muy contenta y la muy enfadada escriben
  más que la indiferente. Corregirlo exigiría muestreo, que aquí no aplica.
- **No dice que el sentimiento detectado sea correcto.** Ver
  [por qué se aceptó pysentimiento](../decisiones/2026-08-29-por-que-se-acepto-pysentimiento.md):
  el modelo acierta 12 de 14 frases de prueba, no 14 de 14.
- **Con estos volúmenes, casi nada es estadísticamente sólido.** El propio
  tablero lo dice antes que los números.

---

## Y lo que este incremento habilita

El documento académico sostiene que **MLOps se difiere** hasta que el sistema
genere datos propios:

> «MLOps gobierna el reentrenamiento continuo de modelos que aprenden de datos
> que el propio sistema genera. Eso aparece cuando el Incremento 6 acumule
> valoraciones propias.»

La tabla `valoracion` **es** esos datos propios. Hasta el Incremento 5, todo lo
que sabía el sistema venía de fuentes externas estables: el inventario del
MINCETUR, las series de visitantes, la red vial de OpenStreetMap.

Esto no significa que ahora haya que hacer MLOps: significa que a partir de
aquí empieza a haber un motivo para plantearlo, que es exactamente lo que
sostienen los dos documentos entregados.

---

## Cómo verificarlo

```bash
curl http://localhost:8000/api/indicadores/evidencia
```

O en la interfaz: `/panel`, pestaña **Evidencia** (rol de gestor, operador o
administrador).

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_valoraciones.py -v
```

Las pruebas que sostienen este indicador:

| Prueba | Qué fija |
|---|---|
| `test_cuenta_itinerarios_y_no_valoraciones` | La unidad de medida |
| `test_guardar_dos_veces_devuelve_el_mismo_itinerario` | Que el denominador no se infle |
| `test_marca_los_recursos_con_pocas_valoraciones` | Que se avise de lo frágil |
| `test_agrega_los_temas_con_su_signo` | El número que dice dónde actuar |
| `test_declara_cuantas_analizo_cada_via` | La trazabilidad de la regla de oro |
| `TestElRanquinNoSeSolapa` (clase) | Que un recurso no sea lo mejor y lo peor |

## Dónde se ve

| Qué | Dónde |
|---|---|
| Modelo | `backend/app/modelos/valoracion.py` |
| Agregación | `backend/app/servicios/evidencia.py` |
| Endpoints | `GET /api/indicadores/evidencia`, `GET /api/indicadores/tablero` |
| Interfaz del visitante | `/preferencias/{id}/valorar` |
| Tablero del gestor | `/panel` → pestaña Evidencia |
| Los seis indicadores | `/panel` → pestaña Indicadores |

## Relacionado

- [Por qué se aceptó pysentimiento](../decisiones/2026-08-29-por-que-se-acepto-pysentimiento.md)
- [Indicador 5](05-canales-e-interacciones-para-confirmar.md)
