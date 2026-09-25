# ADR-009 — Las reglas de estado y de permisos viven en el servicio, no en los endpoints ni en la interfaz

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 5 — canal único de coordinación (brechas 5 y 6) |
| **Atributo de calidad principal** | **Seguridad** (control de acceso efectivo) |
| **Atributos secundarios** | Mantenibilidad (grafo de estados declarado en un solo sitio) |
| **Nota de origen** | [`2026-08-29-donde-viven-las-reglas-de-coordinacion.md`](../decisiones/2026-08-29-donde-viven-las-reglas-de-coordinacion.md) |

---

## Contexto

La brecha 6 dice: *no existe punto único de coordinación **ni registro de lo
acordado***. Son dos cosas, y la segunda no cabe en un campo `estado`.

El plan pide además dos cosas que **suenan a interfaz y no lo son**:

> - Un proveedor solo ve las solicitudes de sus servicios
> - Un visitante no puede acceder al panel administrativo

## Decisión

**Un solo módulo decide qué transiciones son válidas y quién puede provocarlas.**
Ni los endpoints ni la interfaz tienen voz en eso.

### El reparto por capas

| Capa | Qué hace | Qué **NO** hace |
|---|---|---|
| `servicios/coordinacion.py` | Decide qué solicitudes ve cada rol y quién puede mover cada estado | — |
| `rutas/coordinacion.py` | Traduce los errores del servicio a 403 y 409 | Decidir nada |
| `paginas/Panel.tsx` | Oculta las pestañas que no corresponden | **Proteger** nada |

> **Una regla de acceso que solo vive en el frontend no existe.** Quien abra la
> consola del navegador llama al API directamente, y quien escriba `/panel` llega
> igual. El comentario de cabecera de `Panel.tsx` lo dice con esas palabras, para
> que nadie lo lea al revés dentro de seis meses.

### El grafo de transiciones está declarado, no repartido

```python
TRANSICIONES_VALIDAS = {
    ENVIADA:         {EN_REVISION, CONFIRMADA, RECHAZADA, CANCELADA},
    EN_REVISION:     {CONTRAPROPUESTA, CONFIRMADA, RECHAZADA, CANCELADA},
    CONTRAPROPUESTA: {CONFIRMADA, RECHAZADA, CANCELADA},
    CONFIRMADA:      {CANCELADA},   # solo se puede cancelar
    RECHAZADA:       frozenset(),   # final
    CANCELADA:       frozenset(),   # final
}
```

Son seis estados y treinta pares posibles. Si cada endpoint decidiera, tarde o
temprano habría uno que resucita una solicitud rechazada — no por descuido, sino
porque nadie tiene treinta pares en la cabeza al escribir el séptimo endpoint.

### El historial es una tabla, no un campo

`cambio_de_estado` guarda una fila por movimiento. Un campo `estado` dice dónde
está ahora; no responde cuándo se envió, cuándo la vio el proveedor, qué contestó
ni cuánto se tardó en cerrar. Y **sin el historial no se puede calcular el
indicador del incremento**, que mide cuántas interacciones hacen falta para
confirmar.

Se guarda **el rol además del usuario**:

```python
usuario_id: Mapped[int | None]
rol_de_quien_cambio: Mapped[str | None]
```

Parece redundante, pero **el rol de una persona puede cambiar después**. Si un
proveedor pasa a operador, el registro diría que aquel cambio de 2026 lo hizo un
operador, y no fue así. *Un registro que se reescribe solo no es un registro.*

### Tres reglas de negocio derivadas

- **El visitante no puede confirmar su propia solicitud.**
  `ESTADOS_DEL_VISITANTE = {CANCELADA}`. Confirmarse a uno mismo una reserva sería
  volver a no tener acuerdo, que es la brecha que este incremento cierra.
- **Las solicitudes vivas consumen cupo.** Se cuentan confirmadas *y* vivas
  (enviadas, en revisión, con contrapropuesta). Una en revisión todavía puede
  confirmarse: prometer su plaza a otro es literalmente *la capacidad del
  proveedor no es verificable al decidir*, la brecha 5.
- **Se devuelven todos los motivos, no el primero.** Decir «no hay sitio», que lo
  corrija, y entonces «además llegas tarde», es la forma más segura de que
  abandone el formulario.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Un campo `estado` sin tabla de historial** | Cierra la mitad de la brecha 6 (dónde está) y no la otra (qué se acordó y cuándo). Y deja el indicador del incremento sin poder calcularse. |
| **Validar las transiciones en cada endpoint** | Seis estados, treinta pares. Con el grafo declarado, añadir un estado es cambiar una tabla; repartido, es revisar siete endpoints. |
| **Controlar el acceso en el frontend** | No es control: es ocultación. La API queda abierta a quien la llame directamente. |
| **Derivar el rol del usuario al leer el historial** | El rol puede cambiar. El registro quedaría reescrito por un cambio posterior ajeno al hecho registrado. |
| **Contar solo las confirmadas para el cupo** | Permitiría prometer dos veces la misma plaza y que luego ambas se confirmen. |

## Consecuencias

**Positivas**

- El control de acceso es efectivo, no cosmético, y está probado.
- El indicador 5 es calculable: canales pasaron de **tres o más a uno**.
- Añadir un estado nuevo es una línea en una tabla.

**Negativas**

- Más superficie de base de datos: una tabla adicional por cada movimiento.
- Duplicación aparente (`rol_de_quien_cambio`), que hay que explicar a quien lea
  el esquema por primera vez — de ahí este ADR.

### El fallo que estuvo a punto de colarse

Un usuario con rol `proveedor` **pero sin ficha de proveedor asociada**. La
implementación ingenua:

```python
if usuario.rol == PROVEEDOR:
    return todas_las_solicitudes_de(proveedor_del_usuario(usuario))
```

Si `proveedor_del_usuario` devuelve `None`, según cómo se filtre eso puede acabar
devolviendo **todas las solicitudes de todos los proveedores**: la peor fuga
posible del incremento. La implementación real devuelve explícitamente una
consulta vacía, y hay una prueba que lo fija.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_coordinacion.py -v
```

| Prueba | Qué fija |
|---|---|
| `test_una_solicitud_rechazada_no_resucita` | El grafo de estados se cumple |
| `test_una_confirmada_solo_se_puede_cancelar` | Los estados finales lo son |
| `test_un_proveedor_solo_ve_las_solicitudes_de_sus_servicios` | Aislamiento entre proveedores |
| `test_un_proveedor_sin_ficha_asociada_no_ve_nada` | La fuga que estuvo a punto de colarse |
| `test_un_visitante_no_puede_confirmar_su_propia_solicitud` | Que un acuerdo tiene dos partes |
| `test_las_solicitudes_vivas_consumen_cupo` | Que no se prometa dos veces la misma plaza |
| `test_devuelve_todos_los_motivos_y_no_solo_el_primero` | El trato al visitante |

## Relacionado

- [ADR-010 — Los proveedores son de demostración](ADR-010-los-proveedores-son-de-demostracion.md)
- [ADR-003 — La aplicación funciona sin cuenta](ADR-003-la-aplicacion-funciona-sin-cuenta.md)
