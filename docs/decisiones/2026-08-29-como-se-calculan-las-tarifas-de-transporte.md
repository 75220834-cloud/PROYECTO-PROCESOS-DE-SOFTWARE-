# Cómo se calculan las tarifas de transporte, y por qué no son un dato

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** Incremento 4 — ruteo geoespacial multimodal (brecha 4)

## El problema

El plan de trabajo del Incremento 4 pide:

> Entre distritos: combi, colectivo o taxi, con `tarifa_transporte`. Carga las
> tarifas conocidas de `CONTEXTO_PROYECTO.md`, cada una con su
> `fecha_referencia` y su `fuente`. Las que no tienen fuente, márcalas como
> estimadas.

Al ir a buscar esas tarifas apareció el problema: **`CONTEXTO_PROYECTO.md` no
publica ni un solo valor numérico de tarifa.** Lo que publica es esto:

> «Multimodal con costos: caminando dentro del distrito; combi, colectivo o
> taxi entre distritos, con precio aproximado y `fecha_de_referencia` — **las
> tarifas de Huancayo cambian y no hay tarifa oficial única**.»
> — sección 7

Y, en la lista de datos que **no** están verificados:

> «tarifas Huancayo–Jauja y Huancayo–Chupaca · taxi a Ocopa y a Huaytapallana»
> — sección 9, «Datos NO verificados — no usar sin confirmar»

Así que las «tarifas conocidas» que había que cargar son exactamente cero.

## Las tres salidas posibles

**1. Poner números de memoria y presentarlos como tarifas.**
Prohibido por la regla del proyecto de no inventar tarifas. Y sería lo peor que
podría hacer este módulo: un visitante que ve «Huancayo → Jauja: S/ 8» se lo
cree, porque no tiene forma de saber que ese número no salió de ningún sitio.

**2. No calcular costos.**
Deja el Incremento 4 sin la restricción de presupuesto, que es una de las
cuatro que el plan exige y una parte central de la brecha que hay que cerrar:
*el proceso no incorporaba el tiempo y costo de desplazamiento*.

**3. Calcular con una fórmula explícita, marcarlo todo como estimado, y
guardar la fórmula como «fuente».** ← **la elegida**

## Lo que se hizo

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
soles. El precio de un trayecto es `base + por_km × distancia`, redondeado
hacia arriba al medio sol.

Y con ello viajan tres cosas que no se pueden quitar:

| Campo | Qué garantiza |
|---|---|
| `precio_min` y `precio_max` | Nunca hay un precio único: el rango dice que no se sabe el valor exacto |
| `fecha_referencia` | Un precio sin fecha caduca en silencio |
| `fuente` | Un precio sin fuente es un rumor |
| `es_estimado` | Distingue lo que alguien comprobó de lo que el equipo dedujo |

El texto que se guarda como fuente es deliberadamente incómodo de leer:

> «Estimación del equipo por distancia (tarifa base + soles por kilómetro). No
> procede de una fuente oficial: CONTEXTO_PROYECTO.md declara que no hay tarifa
> oficial única en el valle y lista estas tarifas como no verificadas.»

Quien mire la base de datos tiene que ver de un vistazo que ahí no hay una
consulta a nadie, sino una fórmula.

## Por qué la opción 3 no es lo mismo que la opción 1

Es la distinción que hay que poder defender, así que conviene decirla despacio:

- Un **número inventado** se presenta como un hecho. No tiene fórmula, no tiene
  rango, no se puede discutir y no se sabe cuándo dejó de ser cierto.
- Una **estimación con fórmula visible** se puede revisar, criticar y
  **sustituir**. Los parámetros están en una constante con nombre, en un archivo
  con su explicación al lado, y llegan al visitante con la palabra «aprox.», la
  fecha y una marca de estimado.

Y, sobre todo: **en cuanto alguien consulte una tarifa real y la inserte en la
tabla `tarifa_transporte`, este módulo la prefiere automáticamente sobre su
propia estimación.** No hay que tocar código. La estimación es un respaldo, no
la respuesta.

## Lo que sigue sin saberse

- Las tarifas reales. Nadie del equipo ha ido a preguntar en un paradero.
- Si los parámetros elegidos son del orden correcto. Son un supuesto del
  equipo sobre el orden de magnitud del transporte público e interdistrital
  peruano, no una medición.
- Si el reparto del presupuesto (el 35 % del presupuesto diario destinado a
  traslados, en `PROPORCION_DE_TRASLADO`) se parece a como gasta la gente.

Las tres son preguntas abiertas, están declaradas en el código, y ninguna
impide que el sistema funcione hoy.

## Cómo verificarlo

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_costos.py -v
```

Las pruebas que sostienen esta decisión:

- `test_el_precio_siempre_es_un_rango_y_nunca_un_numero_solo`
- `test_los_parametros_de_estimacion_declaran_rangos_no_valores_unicos`
- `test_todos_los_modos_tienen_parametros_de_estimacion` — si alguien añade un
  modo de transporte y olvida sus parámetros, la prueba falla
- `test_cada_traslado_lleva_precio_en_rango_fuente_y_fecha` (en
  `pruebas/test_rutas_itinerarios.py`) — comprueba lo mismo en la respuesta de
  la API, que es por donde el dato llega de verdad al visitante

## Relacionado

- [Cobertura de OpenStreetMap en el valle](2026-08-29-cobertura-de-openstreetmap-en-el-valle.md)
- [Fuente del catálogo: MINCETUR](2026-08-29-fuente-del-catalogo-mincetur.md)
