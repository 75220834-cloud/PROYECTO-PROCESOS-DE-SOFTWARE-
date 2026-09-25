# ADR-005 — Se descarta LightGBM para la afluencia y se entrega la alternativa por reglas

| | |
|---|---|
| **Estado** | Aceptada — modelo **descartado**, devuelto al backlog |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 3 — recomendación personalizada (brechas 2 y 3) |
| **Atributo de calidad principal** | **Fiabilidad** (no presentar como predicción lo que no lo es) |
| **Atributos secundarios** | Mantenibilidad (no se mantiene un modelo sin datos que lo justifiquen) |
| **Interruptor** | `USAR_MODELO_AFLUENCIA` |
| **Nota de origen** | [`2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md`](../decisiones/2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md) |

---

## Contexto

La segunda capa del Incremento 3 estima la **afluencia esperada** en un recurso
para una fecha. El plan preveía un modelo de árboles (LightGBM) entrenado sobre
histórico de visitantes.

Al ir a entrenarlo, la tabla `afluencia_historica` tenía **0 filas**.

El Ministerio de Cultura publica series mensuales de visitantes a sitios
arqueológicos y museos, pero apenas cubren recursos del Valle del Mantaro: la
mayoría de los 295 del catálogo son danzas, fiestas patronales, pueblos
artesanales y sitios naturales **que nadie contabiliza**.

## Decisión

**Se descarta el modelo y se entrega la alternativa por reglas.**

La función `entrenar_modelo_de_afluencia` **existe, funciona y está probada**,
pero **se niega a entrenar con menos de 120 filas** y devuelve el motivo por
escrito. Con menos, un modelo de árboles memoriza los ejemplos: su error de
entrenamiento sale excelente y su predicción real no vale nada.

> Presentar eso como predicción sería mentir con más pasos.

La alternativa por reglas que se entrega en su lugar **no es un placeholder**:
son siete reglas de calendario apoyadas en un dato firme, el calendario festivo,
cuyas fiestas móviles se **calculan** con el algoritmo de la Pascua (Butcher,
1876) en vez de escribirse a mano. Verificado contra 16 fechas oficiales,
incluida la de 2026: Semana Santa del 29 de marzo al 5 de abril.

Y la respuesta **dice con qué vía se calculó**, de modo que el tablero nunca
atribuye al modelo algo que no hizo.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Entrenar con las pocas filas disponibles** | Con menos de 120 filas el modelo memoriza. El error de entrenamiento engaña y la predicción real no sirve. La guarda de 120 filas existe precisamente para impedirlo. |
| **Generar datos sintéticos de afluencia** | Sería inventar una estacionalidad que nadie ha medido, en el proyecto cuyo eje es no inventar. |
| **Repartir los totales anuales entre doce meses** | El mismo problema: la fuente da el total del año, no el mes. Se guardan con `mes = NULL` en vez de inventar la distribución. |
| **No estimar afluencia en absoluto** | El plan la pide y aporta valor real: el visitante quiere saber si va a encontrar una feria llena o un sitio vacío. Las reglas de calendario lo responden razonablemente. |

## Consecuencias

**Positivas**

- No hay ningún modelo entrenado que versionar, servir ni reentrenar: es la otra
  mitad del argumento de **MLOps diferido**.
- El código deja constancia escrita de por qué no hay modelo, con el umbral
  exacto, de modo que la decisión es auditable y reversible.
- La afluencia se explica siempre con su motivo («es domingo y hay fiesta
  patronal»), lo que una predicción de árboles no daría gratis.

**Negativas, y asumidas**

- La estimación **no aprende del comportamiento real**: es una heurística de
  calendario, y se presenta como tal.
- Queda una capacidad a medio construir en el repositorio (la función de
  entrenamiento), que hay que mantener compilando y probada aunque no se use.

## Qué haría falta para activarlo

1. Series de visitantes que cubran recursos del valle. La fuente más
   prometedora son los **registros municipales**, no las series nacionales.
2. Al menos **120 filas**, mejor varios cientos.
3. Volver a ejecutar el cuaderno y comparar el error medio absoluto del modelo
   contra el de las reglas. **Solo si el modelo gana, se activa.**

> **Nota posterior, verificada el 25 de septiembre de 2026.** El ADR-002 (ficha
> web del MINCETUR) aportó **414 filas** de conteos reales en 207 recursos, y la
> tentación es concluir que el umbral de 120 ya se supera. **No se supera.**
> Consultado contra la base: de esas 414 filas, **0 tienen mes**
> (`SELECT count(*) FROM afluencia_historica WHERE mes IS NOT NULL` → 0). Son
> totales anuales, guardados con `mes = NULL` justamente para no inventar la
> estacionalidad.
>
> El entrenador necesita ejemplos de tipo `CaracteristicasDelDia`, que exige un
> mes (`mes=dia.month`). Un total anual no se puede convertir en uno de esos
> ejemplos sin repartirlo entre doce meses, que es precisamente lo que este ADR
> se niega a hacer. **Los ejemplos utilizables siguen siendo 0 y la decisión
> sigue vigente sin cambios.**
>
> Lo que haría falta no es más volumen: es **granularidad mensual**.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_afinidad_y_afluencia.py pruebas/test_calendario.py -v
```

## Relacionado

- [ADR-004 — Se acepta TF-IDF para la afinidad](ADR-004-se-acepta-tfidf-para-la-afinidad.md) — misma regla, resultado contrario
- [ADR-002 — El catálogo se enriquece con la ficha web](ADR-002-enriquecer-el-catalogo-con-la-ficha-web.md)
