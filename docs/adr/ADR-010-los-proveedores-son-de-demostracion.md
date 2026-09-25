# ADR-010 — Los proveedores de ejemplo son de demostración y se marcan por cinco vías independientes

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 5 — canal único de coordinación (brechas 5 y 6) |
| **Atributo de calidad principal** | **Fiabilidad** (que nadie pueda confundir un dato inventado con uno real) |
| **Atributos secundarios** | Seguridad (el guion se niega a ejecutarse fuera de desarrollo) |
| **Nota de origen** | [`2026-08-29-proveedores-de-demostracion.md`](../decisiones/2026-08-29-proveedores-de-demostracion.md) |

---

## Contexto

El Incremento 5 necesita proveedores con servicios, capacidades, horarios y
precios para poder enseñar cómo funciona la coordinación. El plan lo pide:
*«Datos semilla de proveedores y servicios de ejemplo, **claramente marcados como
datos de demostración**»*.

Y el proyecto **no tiene ni un solo proveedor real con convenio**. Nadie ha
hablado con la asociación de burileros de Cochas, ni con un restaurante de
Ingenio, ni con el convento de Ocopa. No hay convenios, ni precios consultados,
ni teléfonos.

## Decisión

Cinco proveedores con seis servicios, inventados, y **cinco marcas
independientes**:

| Marca | Dónde vive | Para quién |
|---|---|---|
| `es_demostracion = True` | Columna de la tabla `proveedor` | Quien consulte la base de datos |
| Sufijo «(demostración)» | En el nombre | Quien lea cualquier listado, informe o exportación |
| Prefijo `+51 900 000 xxx` | En el teléfono | Quien marque sin haber leído nada |
| Etiqueta visible + párrafo | En la interfaz | El visitante y el jurado |
| `ENTORNO != "desarrollo"` → el guion aborta | En `proveedores_semilla.py` | Quien despliegue por error |

### Por qué cinco marcas y no una

Porque **cada una falla en un caso distinto**:

- La **columna** no la ve quien mira una tabla exportada a Excel sin esa columna.
- El **sufijo del nombre** viaja con el dato a cualquier sitio, pero se puede
  recortar en una interfaz estrecha.
- El **teléfono falso** es la última red: si alguien llegó al punto de marcar, no
  va a molestar a nadie. El rango `+51 900 000 xxx` se eligió porque **no está
  asignado a ningún operador peruano**; un número al azar podría ser de una
  persona real.

### Lo que sí es real

**Los tipos de servicio y los lugares**, que salen de lo que el propio inventario
del MINCETUR describe: talleres de mates burilados en Cochas (El Tambo),
comedores de trucha junto a la piscigranja de Ingenio, guiado en el convento de
Santa Rosa de Ocopa. Los sitios existen y están en el catálogo oficial. Lo
inventado son los proveedores concretos, sus precios y sus horarios.

Es la misma distinción de ADR-008: que haya combis entre Huancayo y Jauja es
real; el precio mostrado es una estimación declarada.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **No sembrar ningún proveedor** | Sin proveedores no hay ninguna cuenta que pueda confirmar una solicitud, y el ciclo completo —pedir, responder, confirmar, registrar— dejaría de poderse enseñar. Ese ciclo es lo que cierran las brechas 5 y 6. |
| **Una sola marca** (solo la columna) | No sobrevive a una exportación que omita la columna. Cada marca cubre un fallo de las otras. |
| **Usar proveedores reales sin su permiso** | Publicar sus datos sin autorización sería un problema legal, no solo de honestidad. |
| **Teléfonos aleatorios** | Podrían ser de personas reales, a quienes se molestaría. |
| **Sustituir los demo por los 162 reales del directorio** | Los reales del Directorio Nacional **sí se cargaron** (ADR-001 y su nota), pero no tienen capacidad ni precios publicados, así que no se les puede pedir un servicio. Los dos grupos coexisten, marcados y separados. |

## Consecuencias

**Positivas**

- El ciclo de coordinación se puede demostrar de principio a fin.
- Verificado en base de datos: **167 proveedores, de los cuales 5 son de
  demostración** y 162 son del Directorio Nacional de Prestadores Calificados.
- Nadie puede citar un precio de demostración como precio de mercado sin haber
  ignorado cinco avisos.

**Negativas, y cuantificadas**

- **El indicador 5 queda parcialmente inválido.** Mide interacciones sobre
  solicitudes a proveedores inventados, así que **las horas medias hasta
  confirmar no significan nada**: en la medición salieron cerca de cero porque el
  ciclo entero se ejecutó en seis segundos.
- **El número de canales sí es válido**, porque es estructural: no depende de con
  qué proveedor se hable, sino de cuántos sitios distintos hay que usar para
  cerrar un acuerdo. Antes tres o más; ahora uno.

## Cómo se sustituirían por proveedores reales

1. Conseguir el permiso de cada proveedor.
2. Crear su ficha con `es_demostracion = False` y sin el sufijo.
3. Asociarle una cuenta con rol `proveedor`.
4. Borrar los sembrados, o dejarlos: al estar marcados, no estorban.

**Nada de esto exige tocar código.**

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_coordinacion.py -k demostracion -v
```

La prueba que hace que la marca signifique algo es **«no marca a un proveedor
real»**: comprueba que la etiqueta *desaparece* cuando el proveedor no es de
demostración. Una etiqueta que sale siempre no distingue nada.

## Relacionado

- [ADR-008 — Las tarifas se estiman con fórmula declarada](ADR-008-las-tarifas-se-estiman-con-formula-declarada.md)
- [ADR-009 — Las reglas de estado y permisos viven en el servicio](ADR-009-las-reglas-de-estado-y-permisos-viven-en-el-servicio.md)
