# Cobertura de OpenStreetMap en el Valle del Mantaro

**Fecha:** 29 de agosto de 2026
**Estado:** medición completada; condiciona el diseño del Incremento 4
**Afecta a:** el ruteo geoespacial (brecha 4)

## Por qué se midió antes de programar nada

El plan de trabajo lo exige de forma explícita: *«Antes de comprometer el ruteo,
mide la cobertura real de OpenStreetMap por distrito»*. El motivo es de
honestidad: si un distrito no tiene vías registradas, calcular una «ruta real»
allí es imposible, y presentarla como tal sería inventar precisión.

`CONTEXTO_PROYECTO.md` ya listaba la cobertura de OSM en distritos rurales como
**dato no verificado**. Esto lo verifica.

## Cómo se midió

Se descargó de Overpass la red vial completa (`network_type="all"`, que incluye
caminos de herradura y sendas, no solo carreteras) del rectángulo que envuelve
los 234 recursos georreferenciados, con un margen de 0,05°.

```bash
python -m app.utilidades.medir_cobertura_osm
```

| Dato de la descarga | Valor |
|---|---|
| Área cubierta | −12,526 a −11,246 lat · −75,823 a −75,012 lon (≈ 10 000 km²) |
| Nodos | **40 071** |
| Aristas | **111 704** |
| Tiempo de descarga | 243 s |

La métrica principal es **la distancia de cada recurso al nodo más cercano de
la red**. Es la que responde a la pregunta que importa: si un recurso está a
3 km de la vía registrada más próxima, ninguna ruta calculada sobre esa red
llega hasta él. Se fija el umbral de desconexión en **500 m**, unos siete
minutos caminando por terreno sin vía registrada.

## Resultado

| | |
|---|---|
| Distritos evaluados | 56 |
| Recursos georreferenciados | 234 |
| **Sobre la red vial** (≤ 500 m) | **173 (73,9 %)** |
| **A más de 500 m de una vía** | **61 (26,1 %)** |
| Distritos con cobertura **buena** | 33 |
| Distritos con cobertura **parcial** | 7 |
| Distritos con cobertura **pobre** | 16 |

### El núcleo urbano está muy bien cubierto

| Distrito | Recursos | Nodos cerca | Distancia mediana |
|---|---:|---:|---:|
| El Tambo | 10 | 8 800 | 68 m |
| Huancayo | 9 | 8 000 | 44 m |
| Chilca | 4 | 6 216 | 38 m |
| Pilcomayo | 1 | 4 435 | 84 m |
| Sicaya | 3 | 2 894 | 34 m |
| Chupaca | 4 | 2 323 | 30 m |
| Huancán | 2 | 2 176 | **2 m** |

### Los distritos altos están mal cubiertos

| Distrito | Provincia | Recursos | Nodos | Mediana | Máxima | Desconectados |
|---|---|---:|---:|---:|---:|---:|
| Chongos Alto | Huancayo | 10 | 267 | 1 951 m | **5 316 m** | 7 de 10 |
| Molinos | Jauja | 7 | 18 | 675 m | **5 135 m** | 5 de 7 |
| Canchayllo | Jauja | 10 | 172 | 564 m | 3 404 m | 5 de 10 |
| Yanacancha | Chupaca | 6 | 145 | 801 m | 3 512 m | 4 de 6 |
| San José de Quero | Concepción | 9 | 491 | 608 m | 899 m | 5 de 9 |
| Sincos | Jauja | 4 | 23 | 2 002 m | 2 480 m | 4 de 4 |

Dos distritos no tienen prácticamente red registrada: **Chacapampa** y
**Ricrán**, ambos con 1 nodo y **0 aristas**.

## Dos hallazgos que cambian el diseño para bien

### 1. La red está completamente conectada

Se comprobó la conectividad del grafo: **un solo componente con los 40 071
nodos**. De 400 pares de recursos elegidos al azar entre los conectados,
**los 400 tienen camino**. No hay islas.

Esto importa mucho: significa que el ruteo real funcionará entre cualquier par
de recursos conectados, sin casos imposibles que haya que manejar aparte.

### 2. El factor de corrección está medido, no inventado

El plan hablaba de usar «distancia en línea recta corregida por un factor».
Ese factor se midió sobre los tramos donde la red **sí** existe, comparando
distancia por la red contra distancia en línea recta (índice de rodeo):

| Estadístico | Valor |
|---|---|
| Percentil 25 | 1,12 |
| **Mediana** | **1,26** |
| Media | 1,35 |
| Percentil 75 | 1,47 |
| Percentil 90 | 1,75 |
| Máximo | 4,23 |

**Se adopta 1,26**, la mediana. Se prefiere a la media (1,35) porque esta la
inflan unos pocos pares con rodeos enormes —cruzar el río, bordear un cerro—
que no representan el caso típico.

*Nota sobre el mínimo de 0,71:* una ruta no puede ser más corta que la línea
recta. Ese valor aparece porque la línea recta se mide entre los **recursos**
mientras que la ruta se mide entre sus **nodos más cercanos**, que pueden estar
más juntos. Es una limitación de la medición, no un dato imposible.

## Decisión de diseño

El sistema usa **dos modos de cálculo, y siempre dice cuál usó**:

| Situación | Cómo se calcula | Qué ve el visitante |
|---|---|---|
| Ambos recursos a ≤ 500 m de la red | Ruta real sobre el grafo de OSM | Nada especial |
| Alguno a > 500 m | Línea recta × **1,26** | Aviso visible de que el tramo es estimado |

El aviso en la interfaz es obligatorio, no opcional: *«Este tramo usa distancia
estimada: la zona tiene poca información de vías registrada»*. Sin él, el
visitante creería que un tiempo estimado sobre línea recta es un tiempo
calculado, y en Chongos Alto eso puede significar horas de diferencia.

## Consecuencia para el proyecto

**El 26,1 % de los recursos georreferenciados quedará con tramos estimados.**
Sumado al 20,7 % que no tiene coordenadas, el techo de lo que el sistema puede
rutear con precisión real es de unos **173 de 295 recursos (58,6 %)**.

Ese número no es un fracaso del software: es el estado de los datos públicos
del Valle del Mantaro, medido. Decirlo es justamente lo que el enfoque DataOps
del proyecto aporta frente a una aplicación que dibujara líneas bonitas sobre
un mapa sin saber si se corresponden con algo.

## Cómo reproducirlo

```bash
python -m app.utilidades.medir_cobertura_osm
```

El informe completo, distrito a distrito, queda en
`backend/datos/cobertura_osm.json`. La red descargada se cachea en
`backend/datos/cache_osm/`, así que la segunda ejecución no vuelve a bajarla.
