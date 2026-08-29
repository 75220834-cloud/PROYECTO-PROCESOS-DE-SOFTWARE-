# Dónde viven las reglas de estado y de permisos

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** Incremento 5 — canal único de coordinación (brechas 5 y 6)

## La decisión, en una frase

**Un solo módulo decide qué transiciones son válidas y quién puede
provocarlas.** Ni los endpoints ni la interfaz tienen voz en eso.

## Por qué el historial es una tabla y no un campo

La brecha 6 dice: *no existe punto único de coordinación **ni registro de lo
acordado***. Son dos cosas.

Un campo `estado` en la solicitud cierra la primera mitad: dice dónde está
ahora. No cierra la segunda. Con solo ese campo no se puede responder a:

- ¿Cuándo se envió?
- ¿Cuándo la vio el proveedor?
- ¿Qué contestó, y cuándo?
- ¿Cuánto se tardó en cerrar?

Nada de eso cabe en un campo. Por eso hay una tabla `cambio_de_estado` con una
fila por movimiento.

Y hay un efecto colateral que no es menor: **sin el historial no se puede
calcular el indicador del incremento**, que mide justamente cuántas
interacciones hacen falta para confirmar.

### Se guarda el rol además del usuario

```python
usuario_id: Mapped[int | None]
rol_de_quien_cambio: Mapped[str | None]
```

Parece redundante: el rol se puede sacar del usuario. Pero **el rol de una
persona puede cambiar después**. Si alguien que era proveedor pasa a ser
operador, el registro diría que aquel cambio de 2026 lo hizo un operador, y no
fue así. Un registro que se reescribe solo no es un registro.

## Por qué las transiciones están declaradas y no repartidas

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

Si cada endpoint decidiera, tarde o temprano habría uno que resucita una
solicitud rechazada, u otro que confirma una cancelada. No porque alguien sea
descuidado, sino porque son seis estados y treinta pares posibles, y nadie lo
tiene entero en la cabeza al escribir el séptimo endpoint.

Con el grafo declarado, añadir un estado es cambiar una tabla, y las reglas
siguen siendo consistentes por construcción.

## Por qué los permisos están en el servicio y no en la interfaz

El plan de trabajo pide dos cosas que suenan a interfaz y no lo son:

> - Un proveedor solo ve las solicitudes de sus servicios
> - Un visitante no puede acceder al panel administrativo

**Una regla de acceso que solo vive en el frontend no existe.** Quien abra la
consola del navegador puede llamar a la API directamente, y quien escriba la
dirección `/panel` llega igual.

Así que el reparto es:

| Capa | Qué hace | Qué NO hace |
|---|---|---|
| `servicios/coordinacion.py` | Decide qué solicitudes ve cada rol y quién puede mover cada estado | — |
| `rutas/coordinacion.py` | Traduce los errores del servicio a 403 y 409 | Decidir nada |
| `paginas/Panel.tsx` | Oculta las pestañas que no corresponden | **Proteger** nada |

El comentario de cabecera de `Panel.tsx` lo dice con esas palabras, para que
nadie lo lea al revés dentro de seis meses.

### El fallo que estuvo a punto de colarse

Un usuario con rol `proveedor` **pero sin ficha de proveedor asociada**. La
implementación ingenua es:

```python
if usuario.rol == PROVEEDOR:
    return todas_las_solicitudes_de(proveedor_del_usuario(usuario))
```

Si `proveedor_del_usuario` devuelve `None`, según cómo se filtre, eso puede
acabar devolviendo **todas las solicitudes de todos los proveedores**. Sería la
peor fuga posible del incremento.

La implementación real devuelve explícitamente una consulta vacía:

```python
if proveedor is None:
    # Un usuario con rol de proveedor pero sin ficha asociada no ve nada.
    # Devolver todo «porque es proveedor» sería el fallo grave.
    return base.where(SolicitudCoordinacion.id.is_(None))
```

Y hay una prueba que lo fija: `test_un_proveedor_sin_ficha_asociada_no_ve_nada`.

## Por qué el visitante no puede confirmar su propia solicitud

```python
ESTADOS_DEL_PROVEEDOR = {EN_REVISION, CONTRAPROPUESTA, CONFIRMADA, RECHAZADA}
ESTADOS_DEL_VISITANTE = {CANCELADA}
```

Confirmarse a uno mismo una reserva sería volver a no tener acuerdo, que es
exactamente la brecha que este incremento cierra. Lo único que puede hacer
quien pidió es echarse atrás.

## Por qué las solicitudes vivas consumen cupo

Al comprobar si hay sitio, se cuentan las solicitudes **confirmadas y las que
siguen vivas** (enviadas, en revisión, con contrapropuesta).

Una solicitud en revisión todavía puede confirmarse. Prometer su plaza a otro y
que después las dos se confirmen es, literalmente, *la capacidad del proveedor
no es verificable al decidir*: la brecha 5.

## Por qué se devuelven todos los motivos y no el primero

```python
def revisar_disponibilidad(...) -> list[str]:
    """Devuelve los motivos por los que este servicio NO se puede pedir así."""
```

Decirle a alguien «no hay sitio», que lo corrija, y entonces decirle «además
llegas tarde», y luego «además ese día cierra», es la forma más segura de que
abandone el formulario. Se le dan los tres a la vez.

## Cómo verificarlo

```bash
cd backend
.venv/Scripts/python.exe -m pytest pruebas/test_coordinacion.py -v
```

Las pruebas que sostienen esta decisión:

| Prueba | Qué fija |
|---|---|
| `test_una_solicitud_rechazada_no_resucita` | El grafo de estados se cumple |
| `test_una_confirmada_solo_se_puede_cancelar` | Los estados finales lo son |
| `test_un_proveedor_solo_ve_las_solicitudes_de_sus_servicios` | El aislamiento entre proveedores |
| `test_un_proveedor_no_puede_mover_la_solicitud_de_otro` | Y que no puede tocarlas |
| `test_un_proveedor_sin_ficha_asociada_no_ve_nada` | La fuga que estuvo a punto de colarse |
| `test_un_visitante_no_puede_confirmar_su_propia_solicitud` | Que un acuerdo tiene dos partes |
| `test_un_visitante_no_puede_publicar_servicios` | El panel no es para visitantes |
| `test_las_solicitudes_vivas_consumen_cupo` | Que no se prometa dos veces la misma plaza |
| `test_devuelve_todos_los_motivos_y_no_solo_el_primero` | El trato al visitante |

## Relacionado

- [Los proveedores son de demostración](2026-08-29-proveedores-de-demostracion.md)
- [Indicador 5](../indicadores/05-canales-e-interacciones-para-confirmar.md)
- [La aplicación funciona sin cuenta](2026-08-29-la-aplicacion-funciona-sin-cuenta.md)
  — por qué también se puede coordinar sin registrarse
