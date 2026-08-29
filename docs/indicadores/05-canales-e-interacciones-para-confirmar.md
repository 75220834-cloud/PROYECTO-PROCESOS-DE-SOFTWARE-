# Indicador 5 — Canales e interacciones para confirmar un servicio

**Incremento:** 5 — Canal único de coordinación
**Brechas que mide:** 5 y 6
**Estado:** implementado, con la salvedad de que **mide un proceso de
demostración**

---

## Antes que nada: qué mide y qué no

Los dos documentos del proyecto lo nombran distinto, y las dos lecturas se
miden:

| Fuente | Nombre del indicador | ¿Se mide? |
|---|---|---|
| `CONTEXTO_PROYECTO.md` | «N.º de canales para confirmar un servicio» | Sí |
| `PROMPT_MAESTRO.md` | «Número de interacciones necesarias para confirmar un servicio» | Sí |

**La salvedad importante:** las solicitudes que se miden son contra proveedores
**inventados**. No hay convenios con nadie del valle. El número de interacciones
que sale mide cómo se comporta *el software*, no cómo se comporta un proveedor
real que tarda dos días en contestar el WhatsApp.

Lo que sí se puede afirmar sin datos de campo es lo de los canales, y es lo que
de verdad cierra la brecha 6.

---

## Los canales: de tres a uno

Es una cuenta estructural, no una medición estadística.

| | **Antes (AS-IS)** | **Ahora (TO-BE)** |
|---|---|---|
| Encontrar al proveedor | Buscar en Facebook o preguntar | Catálogo de servicios |
| Ver si tiene sitio | Llamar y esperar | Escrito en la ficha |
| Pedir | WhatsApp o teléfono | Una solicitud |
| Confirmar | Mensaje de vuelta, si llega | Cambio de estado |
| **Registro de lo acordado** | **Ninguno** | **Historial con fechas** |
| **Canales distintos** | **3 o más** | **1** |

La fila que importa es la penúltima. Un WhatsApp se borra, un teléfono no deja
rastro, y cuando el día llega nadie recuerda si se había dicho «a las diez» o
«a las once». El historial de `cambio_de_estado` guarda cada movimiento con su
estado anterior, su estado nuevo, quién lo hizo, con qué rol y cuándo.

**Eso es lo que dice la brecha 6:** *no existe punto único de coordinación ni
registro de lo acordado*. El punto único es la plataforma; el registro es esa
tabla.

---

## Las interacciones: cómo se cuentan

Cada movimiento de una solicitud queda registrado, y el indicador es la media
de movimientos de las solicitudes que llegaron a confirmarse.

```
interacciones = número de filas en cambio_de_estado para esa solicitud
```

Los dos caminos posibles:

| Camino | Interacciones |
|---|---|
| enviada → confirmada | 2 |
| enviada → en revisión → confirmada | 3 |
| enviada → en revisión → contrapropuesta → confirmada | 4 |

Se cuenta sobre el historial y **no sobre un contador**, por dos razones: un
contador se puede desincronizar, y el historial hace falta igual para saber
cuánto se tardó.

### Por qué las medias van a `null` y no a cero

Si todavía no se ha confirmado ninguna solicitud, el endpoint devuelve `null`
en las medias, y la interfaz escribe «Sin dato todavía».

Devolver cero sería afirmar que confirmar cuesta cero interacciones, que es
justo lo contrario de la verdad. **Una media de cero casos no es cero: es que
no hay dato.**

---

## Medición del 29 de agosto de 2026

Ciclo completo ejecutado contra la API en marcha, con el proveedor de
demostración:

```
crear      -> 201 | estado enviada     | interacciones 1
en revisión -> 200 | estado en_revision
confirmar  -> 200 | estado confirmada  | S/ 160.00 | interacciones 3

HISTORIAL REGISTRADO
  2026-08-29T18:52:25   (inicio)     -> enviada       por visitante
  2026-08-29T18:52:29   enviada      -> en_revision   por proveedor
  2026-08-29T18:52:31   en_revision  -> confirmada    por proveedor
```

| Métrica | Valor |
|---|---|
| Solicitudes | 1 |
| Confirmadas | 1 |
| Interacciones medias hasta confirmar | 3,0 |
| Canales para confirmar | **1** |

Las tres interacciones son el camino con revisión intermedia, que es el
realista: un proveedor mira la agenda antes de comprometerse.

---

## Lo que este indicador NO dice

- **No dice cuánto tarda un proveedor real.** Las horas medias salen cerca de
  cero porque la prueba se hizo en seis segundos. Con proveedores de verdad ese
  número sería el interesante, y hoy no significa nada.
- **No dice que la coordinación funcione en el valle.** Dice que el software la
  soporta y la registra.
- **No compara con el proceso actual medido.** Los «3 o más canales» del AS-IS
  salen del análisis de la Guía 1, no de una observación de campo con
  cronómetro.

---

## Cómo verificarlo

```bash
curl http://localhost:8000/api/indicadores/coordinacion
```

O en la interfaz: `/panel`, pestaña **Indicador** (hace falta rol de proveedor,
operador, gestor o administrador).

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_coordinacion.py -v
```

Las pruebas que sostienen este indicador:

- `test_cuenta_las_interacciones`
- `test_sin_confirmadas_las_medias_van_a_nulo_y_no_a_cero`
- `test_queda_registrada_con_fechas`
- `test_declara_que_el_canal_es_uno`

## Dónde se ve

| Qué | Dónde |
|---|---|
| Modelo del registro | `backend/app/modelos/coordinacion.py`, clase `CambioDeEstado` |
| Cálculo | `backend/app/rutas/coordinacion.py`, `indicador_de_coordinacion` |
| Endpoint | `GET /api/indicadores/coordinacion` |
| Interfaz | `/panel` → pestaña Indicador |
| Historial visible | Cualquier tarjeta de solicitud, botón «Ver el historial» |

## Relacionado

- [Los proveedores son de demostración, y por qué se dice tres veces](../decisiones/2026-08-29-proveedores-de-demostracion.md)
- [Indicador 4 — Itinerarios viables y trazables](04-itinerarios-viables-y-trazables.md)
