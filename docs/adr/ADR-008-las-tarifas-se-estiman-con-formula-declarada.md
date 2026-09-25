# ADR-008 — Las tarifas de transporte se estiman con una fórmula declarada, nunca con un número inventado

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 4 — ruteo geoespacial multimodal (brecha 4) |
| **Atributo de calidad principal** | **Fiabilidad** (trazabilidad del dato mostrado) |
| **Atributos secundarios** | Mantenibilidad (la estimación es sustituible sin tocar código) |
| **Nota de origen** | [`2026-08-29-como-se-calculan-las-tarifas-de-transporte.md`](../decisiones/2026-08-29-como-se-calculan-las-tarifas-de-transporte.md) |

---

## Contexto

El plan del Incremento 4 pide cargar «las tarifas conocidas de
`CONTEXTO_PROYECTO.md`, cada una con su `fecha_referencia` y su `fuente`».

Al ir a buscarlas apareció el problema: **`CONTEXTO_PROYECTO.md` no publica ni un
solo valor numérico de tarifa.** Lo que publica es que *«las tarifas de Huancayo
cambian y no hay tarifa oficial única»*, y lista las tarifas Huancayo–Jauja,
Huancayo–Chupaca, taxi a Ocopa y a Huaytapallana en la sección **«Datos NO
verificados — no usar sin confirmar»**.

Las «tarifas conocidas» que había que cargar eran exactamente **cero**. Y no
existe ninguna fuente publicada de tarifas del valle: ni el MINCETUR, ni el
gobierno regional, ni las municipalidades.

## Decisión

Se calcula el costo con una **fórmula explícita**, se marca todo como estimado, y
**se guarda la fórmula como «fuente»**.

En `app/servicios/costos.py`:

```python
PARAMETROS_DE_ESTIMACION = {
    ModoTransporte.COMBI:      ("1.00", "1.50", "0.10", "0.15"),
    ModoTransporte.COLECTIVO:  ("2.00", "3.00", "0.15", "0.25"),
    ModoTransporte.TAXI:       ("5.00", "8.00", "1.50", "2.50"),
    ModoTransporte.CAMINANDO:  ("0.00", "0.00", "0.00", "0.00"),
}
```

Cada tupla es `(base_mínima, base_máxima, por_km_mínimo, por_km_máximo)` en
soles. El precio es `base + por_km × distancia`, redondeado hacia arriba al medio
sol.

Y con cada precio viajan cuatro campos que no se pueden quitar:

| Campo | Qué garantiza |
|---|---|
| `precio_min` y `precio_max` | Nunca hay un precio único: el rango dice que no se sabe el valor exacto |
| `fecha_referencia` | Un precio sin fecha caduca en silencio |
| `fuente` | Un precio sin fuente es un rumor |
| `es_estimado` | Distingue lo que alguien comprobó de lo que el equipo dedujo |

El texto de la fuente es deliberadamente incómodo de leer:

> «Estimación del equipo por distancia (tarifa base + soles por kilómetro). No
> procede de una fuente oficial: CONTEXTO_PROYECTO.md declara que no hay tarifa
> oficial única en el valle y lista estas tarifas como no verificadas.»

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **1. Poner números de memoria y presentarlos como tarifas** | Prohibido por la regla del proyecto. Y sería lo peor que podría hacer este módulo: quien ve «Huancayo → Jauja: S/ 8» se lo cree, porque no tiene forma de saber que ese número no salió de ningún sitio. |
| **2. No calcular costos** | Deja el Incremento 4 sin la restricción de presupuesto, que es una de las cuatro que el plan exige y parte central de la brecha: *el proceso no incorporaba el tiempo y costo de desplazamiento*. |
| **3. Fórmula explícita, todo marcado como estimado, fórmula como fuente** | ← **la elegida** |

### Por qué la opción 3 no es lo mismo que la opción 1

- Un **número inventado** se presenta como un hecho: no tiene fórmula, no tiene
  rango, no se puede discutir, y no se sabe cuándo dejó de ser cierto.
- Una **estimación con fórmula visible** se puede revisar, criticar y
  **sustituir**. Los parámetros están en una constante con nombre y llegan al
  visitante con la palabra «aprox.», la fecha y la marca de estimado.

Y sobre todo: **en cuanto alguien inserte una tarifa real en `tarifa_transporte`,
el módulo la prefiere automáticamente sobre su propia estimación.** No hay que
tocar código. La estimación es un respaldo, no la respuesta.

## Consecuencias

**Positivas**

- El Incremento 4 conserva su restricción de presupuesto.
- Todo costo mostrado es auditable: fórmula, rango, fecha y fuente.
- La vía de sustitución por datos reales está abierta y no requiere desarrollo.

**Negativas, declaradas en el propio código**

- **Las tarifas reales siguen sin saberse.** Nadie del equipo ha ido a preguntar
  en un paradero.
- **No se sabe si los parámetros son del orden correcto.** Son un supuesto del
  equipo sobre la magnitud del transporte peruano, no una medición.
- **No se sabe si el reparto del presupuesto se parece a cómo gasta la gente**
  (el 35 % del presupuesto diario destinado a traslados, en
  `PROPORCION_DE_TRASLADO`).

Las tres son preguntas abiertas, están escritas en el código, y ninguna impide
que el sistema funcione hoy.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_costos.py -v
```

Pruebas que sostienen la decisión:

- `test_el_precio_siempre_es_un_rango_y_nunca_un_numero_solo`
- `test_los_parametros_de_estimacion_declaran_rangos_no_valores_unicos`
- `test_todos_los_modos_tienen_parametros_de_estimacion` — si alguien añade un
  modo y olvida sus parámetros, la prueba falla
- `test_cada_traslado_lleva_precio_en_rango_fuente_y_fecha` — lo mismo en la
  respuesta del API, que es por donde el dato llega de verdad al visitante

## Relacionado

- [ADR-006 — Dos modos de cálculo de distancia](ADR-006-dos-modos-de-calculo-de-distancia.md)
- [ADR-010 — Los proveedores son de demostración](ADR-010-los-proveedores-son-de-demostracion.md)
