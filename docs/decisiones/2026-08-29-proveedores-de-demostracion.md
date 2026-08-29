# Los proveedores son de demostración, y por qué se dice tres veces

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** Incremento 5 — canal único de coordinación (brechas 5 y 6)

## El problema

El Incremento 5 necesita proveedores con servicios, capacidades, horarios y
precios para poder enseñar cómo funciona la coordinación. El plan de trabajo lo
pide explícitamente:

> «Datos semilla de proveedores y servicios de ejemplo, **claramente marcados
> como datos de demostración**.»

Y el proyecto **no tiene ni un solo proveedor real**. Nadie ha hablado con la
asociación de burileros de Cochas, ni con un restaurante de Ingenio, ni con el
convento de Ocopa. No hay convenios, no hay precios consultados, no hay
teléfonos.

## Lo que se hizo

Cinco proveedores con seis servicios, todos inventados, y **tres marcas
independientes** para que nadie pueda confundirse:

| Marca | Dónde vive | Para quién |
|---|---|---|
| `es_demostracion = True` | Columna de la tabla `proveedor` | Quien consulte la base de datos |
| Sufijo «(demostración)» | En el nombre | Quien lea cualquier listado, informe o exportación |
| Prefijo `+51 900 000 xxx` | En el teléfono | Quien marque sin haber leído nada |

Y una cuarta, en la interfaz: una etiqueta visible en cada tarjeta de servicio y
de solicitud, con el texto completo al pasar el ratón, además de un párrafo
explicativo arriba de la pantalla.

### Por qué tres marcas y no una

Porque cada una falla en un caso distinto:

- La **columna** no la ve quien mira una tabla exportada a Excel sin esa
  columna.
- El **sufijo del nombre** sí viaja con el dato a cualquier sitio, pero se
  puede recortar en una interfaz estrecha.
- El **teléfono falso** es la última red: si alguien llegó hasta el punto de
  marcar, no le va a contestar nadie a quien esté molestando.

El rango `+51 900 000 xxx` se eligió porque no está asignado a ningún operador
peruano. Un número inventado al azar podría ser el de una persona real.

### Y una quinta: el guion se niega a ejecutarse en producción

```python
if configuracion.entorno != "desarrollo":
    print("ERROR: el entorno es '...'. Estos proveedores son inventados y no "
          "deben crearse fuera de desarrollo.", file=sys.stderr)
    return 1
```

Es la misma salvaguarda que lleva el guion de usuarios de demostración.

## Lo que sí es real

**Los tipos de servicio y los lugares.** Salen de lo que el propio inventario
del MINCETUR describe en el valle:

- talleres de mates burilados en Cochas (El Tambo),
- comedores de trucha junto a la piscigranja de Ingenio,
- guiado en el convento de Santa Rosa de Ocopa.

Los sitios existen y están en el catálogo cargado desde la fuente oficial. Lo
inventado son los proveedores concretos, sus precios y sus horarios.

Es la misma distinción que se hizo con las tarifas de transporte: el hecho de
que haya combis entre Huancayo y Jauja es real; el precio que se muestra es una
estimación declarada.

## Qué habría pasado sin las marcas

Un visitante de la exposición, o el jurado, podría:

1. Ver «Truchas del Ingenio» con un teléfono y creer que puede reservar.
2. Concluir que el proyecto tiene acuerdos con proveedores del valle.
3. Citar los precios como si fueran de mercado.

Las tres cosas serían falsas, y ninguna sería culpa de quien las creyó.

## Lo que esto le cuesta al indicador

El [indicador 5](../indicadores/05-canales-e-interacciones-para-confirmar.md)
mide interacciones sobre solicitudes a proveedores inventados. Eso significa
que **las horas medias hasta confirmar no significan nada**: en la medición
salieron cerca de cero porque el ciclo entero se ejecutó en seis segundos.

El número de **canales** sí es válido, porque es estructural: no depende de con
qué proveedor se hable, sino de cuántos sitios distintos hay que usar para
cerrar un acuerdo. Antes tres o más; ahora uno.

## Cómo se sustituirían por proveedores reales

1. Conseguir el permiso de cada proveedor. Publicar sus datos sin él sería un
   problema legal, no solo de honestidad.
2. Crear su ficha con `es_demostracion = False` y sin el sufijo.
3. Asociarle una cuenta con rol `proveedor` para que gestione sus servicios.
4. Borrar los sembrados, o dejarlos: al estar marcados, no estorban.

Nada de esto exige tocar código.

## Cómo verificarlo

```bash
cd backend
.venv/Scripts/python.exe -m app.utilidades.proveedores_semilla
```

Pruebas:

- Backend, en `pruebas/test_coordinacion.py`:
  `test_marca_los_proveedores_de_demostracion`.
- Frontend, en `TarjetaServicio.prueba.tsx`: «marca al proveedor de
  demostración» y «explica al pasar el ratón que el proveedor no existe».
- **«no marca a un proveedor real»** — comprueba que la etiqueta *desaparece*
  cuando el proveedor no es de demostración. Es la que hace que la marca
  signifique algo: una etiqueta que sale siempre no distingue nada.

## Relacionado

- [Cómo se calculan las tarifas de transporte](2026-08-29-como-se-calculan-las-tarifas-de-transporte.md)
- [Fuente del catálogo: MINCETUR](2026-08-29-fuente-del-catalogo-mincetur.md)
