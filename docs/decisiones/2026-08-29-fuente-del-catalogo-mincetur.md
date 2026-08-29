# El catálogo se construye sobre el inventario del MINCETUR

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Cierra:** brecha 1 — *no existe una fuente integrada, oficial y actualizada de la oferta de la ruta*

## Contexto

El Incremento 1 necesita una fuente de la oferta turística del Valle del
Mantaro que sea **oficial** (para que el catálogo se pueda defender),
**georreferenciada** (porque el Incremento 4 calcula rutas sobre el terreno) y
**fechada** (porque el indicador del incremento mide vigencia).

## Alternativas consideradas

| Fuente | Por qué se descartó |
|---|---|
| **DIRCETUR Junín** | Es la autoridad regional y sería la fuente natural, pero no publica su inventario en formato de datos abiertos. Solo hay documentos en PDF, sin coordenadas ni fecha de corte por recurso. |
| **OpenStreetMap** | Cobertura excelente en Huancayo, pobre en los distritos rurales. Y no es una fuente *oficial*: cualquiera edita. Sirve para la red vial (Incremento 4), no como catálogo de la oferta. |
| **Google Places** | De pago, en la nube y con condiciones de uso que impiden almacenar los datos. El proyecto exige que todo corra local y sin coste. |
| **Recopilación manual del equipo** | Tres personas no pueden inventariar cuatro provincias, y el resultado no sería oficial ni auditable. Es justamente la brecha que se quiere cerrar. |

## Decisión

Se usa el **Inventario Nacional de Recursos Turísticos** del MINCETUR,
publicado por la Dirección General de Estrategia Turística:

```
https://www.mincetur.gob.pe/Datos_abiertos/DGET/Inventario_recursos_turisticos.csv
```

Es la única fuente que cumple los tres requisitos a la vez: es oficial del
Estado peruano, trae latitud y longitud por recurso, y trae la columna
`FECHA_DE_CORTE` que sostiene el indicador de vigencia.

Se filtra `REGIÓN = JUNÍN` y las provincias **Huancayo, Concepción, Jauja y
Chupaca**, que son las cuatro que componen la Ruta del Valle del Mantaro.

## Lo que se encontró en la fuente, y qué se hizo

Al importar el archivo aparecieron tres problemas reales. Esto no es un
inconveniente: es exactamente lo que el enfoque **DataOps** del proyecto
existe para detectar, y la evidencia de que la brecha 1 era real.

### 1. Las columnas de latitud y longitud vienen intercambiadas

La columna rotulada `LATITUD` contiene la longitud, y la rotulada `LONGITUD`
contiene la latitud. **No es un error de algunas filas: afecta al archivo
entero.**

Se comprobó sobre las 6 155 filas del archivo nacional:

| Interpretación | Filas coherentes |
|---|---|
| Tal como vienen los rótulos | **0** |
| Invirtiendo las dos columnas | **4 910** |

Es concluyente porque en el Perú continental los rangos no se solapan: la
latitud va de −18,4 a −0,03 y la longitud de −81,4 a −68,6.

**Qué se hizo:** el importador **no** da por hecho que hay que invertirlas. La
función `detectar_orden_de_coordenadas` lo decide leyendo los datos y
resolviendo por mayoría. Si el MINCETUR corrige el archivo, el importador
seguirá funcionando sin tocar una línea. Está cubierto por pruebas en los dos
sentidos.

### 2. Sesenta y un recursos no traen coordenadas

De los 295 recursos de la ruta, **61 no tienen coordenada** en la fuente
oficial. Son sobre todo danzas, fiestas patronales y platos típicos: bienes de
folclore que el inventario registra sin ubicación puntual.

**Qué se hizo:** se guardan con la ubicación nula y la validación los marca
con el motivo `sin coordenadas`. **No se les asigna la coordenada del centro
del distrito ni ninguna aproximación.** Aparecen en el listado con un aviso
visible y quedan fuera del mapa, porque un marcador inventado sería una
mentira dibujada.

### 3. El archivo viene en codificación cp1252, no UTF-8

Leerlo como UTF-8 rompe todos los nombres con tilde. El importador prueba las
codificaciones en orden y usa la primera que funciona, en vez de suponerla.

## Consecuencias medibles

| Dato | Valor |
|---|---|
| Filas en el archivo nacional | 6 155 |
| Filas de la región Junín | 463 |
| Recursos de las cuatro provincias de la ruta | **295** |
| Con coordenadas válidas | 234 |
| Sin coordenadas en la fuente | 61 |
| **Porcentaje validado (indicador del Incremento 1)** | **79,32 %** |

Reparto por provincia: Huancayo 111 · Jauja 104 · Concepción 51 · Chupaca 29.

## Nota sobre el área de validación

El plan de trabajo proponía validar las coordenadas contra el rectángulo
«aproximadamente latitud −12,5 a −11,5, longitud −75,5 a −74,9». Medido contra
los datos reales, ese rectángulo está desplazado al este y recortado por el
norte: dejaba fuera **52 recursos correctos** de distritos reales de la ruta
—San José de Quero en Concepción, Canchayllo y Apata en Jauja, Yanacancha en
Chupaca—, todos en la zona alta occidental.

Usarlo habría hecho que el indicador declarara inválidos datos oficiales que
son válidos. Se corrigió a **latitud −12,60 a −11,20, longitud −75,90 a
−74,90**, medido sobre la extensión real de los 234 recursos georreferenciados
más un margen. El rectángulo sigue cumpliendo su función: detectar errores
gruesos, incluido el caso de las columnas intercambiadas.
