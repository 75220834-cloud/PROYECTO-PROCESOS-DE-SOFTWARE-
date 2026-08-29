# Indicador 1 — Oferta con información validada y vigente

**Incremento:** 1 — Catálogo único validado
**Brecha que mide:** 1 — no existe una fuente integrada, oficial y actualizada de la oferta de la ruta
**Estado:** implementado y medible

---

## Qué mide

El porcentaje de recursos turísticos del catálogo cuya información supera las
cuatro reglas de validación del proyecto.

Antes del Incremento 1 este número no existía: la oferta estaba dispersa entre
documentos del MINCETUR, páginas municipales y conocimiento no escrito, y
nadie podía decir qué proporción de ella estaba en condiciones de usarse.

## Cómo se calcula

```
porcentaje_validado = 100 × recursos_validados / total_de_recursos
```

Un recurso cuenta como **validado** si cumple las cuatro reglas:

| # | Regla | Por qué |
|---|---|---|
| 1 | Tiene nombre | Sin nombre no se puede mostrar ni buscar |
| 2 | Su provincia es una de las cuatro de la ruta | Protege contra que el filtro de importación cuele recursos de fuera del valle |
| 3 | Tiene coordenadas dentro del área del Valle del Mantaro | Sin coordenada no puede entrar en un itinerario (Incremento 4); fuera del área significa coordenada errónea |
| 4 | Tiene fecha de corte y no es demasiado antigua | Distingue *validado* de *vigente* |

**Validado y vigente se cuentan por separado a propósito.** Un recurso puede
estar bien descrito y bien ubicado y aun así tener el dato caducado.
Mezclarlos ocultaría que la fuente oficial lleva tiempo sin actualizarse.

El plazo de vigencia adoptado es de **730 días (dos años)**. Es una decisión
del equipo, no un estándar oficial: el MINCETUR publica el inventario de forma
irregular, y exigir menos dejaría el catálogo vacío en la práctica. Está en
`DIAS_DE_VIGENCIA`, en un solo sitio, para poder discutirlo y cambiarlo.

## Dónde vive

| Pieza | Ubicación |
|---|---|
| Reglas | `backend/app/servicios/validacion_catalogo.py` |
| Tabla que lo guarda | `registro_validacion` |
| Endpoint | `GET /api/indicadores/catalogo` |
| En la interfaz | Cabecera de la página `/explorar` |
| Pruebas | `backend/pruebas/test_validacion_catalogo.py` |

## Cómo se genera una medición nueva

```bash
python -m app.utilidades.cargar_catalogo
```

Cada ejecución **añade una fila** a `registro_validacion`, nunca sobrescribe la
anterior. El histórico es lo que permite demostrar que la calidad del catálogo
mejora con el tiempo, que es justo lo que el documento académico afirma del
enfoque DataOps.

## Medición vigente

Tomada el 29 de agosto de 2026, sobre el inventario del MINCETUR con fecha de
corte 2026-08-27:

| Dato | Valor |
|---|---|
| Total de recursos | 295 |
| Validados | 234 |
| **Porcentaje validado** | **79,32 %** |
| Con coordenadas | 234 (79,32 %) |
| Vigentes | 295 (100 %) |

**El 20,68 % restante son 61 recursos sin coordenada en la fuente oficial.**
Son mayoritariamente danzas, fiestas patronales y platos típicos: bienes de
folclore que el inventario registra sin ubicación puntual.

No se les inventa una coordenada para subir el porcentaje. Ese 79,32 % es el
estado real de la fuente oficial, y decirlo es precisamente el valor del
indicador.

## Cómo mejorar el número, honestamente

1. Georreferenciar a mano los 61 recursos sin coordenada, con fuente
   documentada por cada uno. Requiere trabajo de campo o de archivo.
2. Complementar con OpenStreetMap **marcando el origen de cada coordenada**,
   para no mezclar dato oficial con dato colaborativo sin distinguirlos.
3. Reportar los errores al MINCETUR — empezando por las columnas de latitud y
   longitud intercambiadas, que afectan a todo el archivo nacional y no solo a
   Junín.

Lo que **no** vale: bajar el listón de las reglas, borrar los recursos que no
pasan, o rellenar coordenadas con el centro del distrito.
