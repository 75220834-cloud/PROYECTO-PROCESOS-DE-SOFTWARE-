# ADR-006 — Dos modos de cálculo de distancia, con factor de rodeo medido, y el sistema dice siempre cuál usó

| | |
|---|---|
| **Estado** | Aceptada (origen: medición previa a programar) |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 4 — ruteo geoespacial multimodal (brecha 4) |
| **Atributo de calidad principal** | **Fiabilidad** (no presentar una estimación como un cálculo) |
| **Atributos secundarios** | Usabilidad (el aviso al visitante) |
| **Nota de origen** | [`2026-08-29-cobertura-de-openstreetmap-en-el-valle.md`](../decisiones/2026-08-29-cobertura-de-openstreetmap-en-el-valle.md) |

---

## Contexto

El plan de trabajo exige medir la cobertura real de OpenStreetMap por distrito
**antes de comprometer el ruteo**. El motivo es de honestidad: si un distrito no
tiene vías registradas, calcular una «ruta real» allí es imposible, y presentarla
como tal sería inventar precisión.

`CONTEXTO_PROYECTO.md` listaba la cobertura de OSM en distritos rurales como
**dato no verificado**. Esta decisión nace de verificarlo.

### Lo medido

Se descargó de Overpass la red vial completa (`network_type="all"`, incluidos
caminos de herradura y sendas) del rectángulo que envuelve los 234 recursos
georreferenciados, con margen de 0,05°: **40 071 nodos y 111 704 aristas**,
≈10 000 km², 243 s de descarga.

La métrica principal es la **distancia de cada recurso al nodo más cercano de la
red**, con umbral de desconexión en **500 m** (≈7 minutos caminando por terreno
sin vía registrada).

| | |
|---|---|
| Distritos evaluados | 56 |
| **Sobre la red vial** (≤ 500 m) | **173 de 234 (73,9 %)** |
| **A más de 500 m** | **61 (26,1 %)** |
| Distritos con cobertura buena / parcial / pobre | 33 / 7 / 16 |

El núcleo urbano está muy bien cubierto (Huancán mediana **2 m**, Chupaca 30 m,
Huancayo 44 m). Los distritos altos, mal: Chongos Alto mediana **1 951 m** y
máxima **5 316 m**, con 7 de sus 10 recursos desconectados. **Chacapampa** y
**Ricrán** tienen 1 nodo y **0 aristas**.

## Decisión

El sistema usa **dos modos de cálculo y siempre declara cuál usó**, mediante el
campo `origen_del_calculo`:

| Situación | Cómo se calcula | Qué ve el visitante |
|---|---|---|
| Ambos recursos a ≤ 500 m de la red | Ruta real sobre el grafo de OSM | Nada especial |
| Alguno a > 500 m | Línea recta × **1,26** | **Aviso visible** de tramo estimado |

El aviso es **obligatorio, no opcional**. Sin él, el visitante creería que un
tiempo estimado sobre línea recta es un tiempo calculado, y en Chongos Alto eso
puede significar horas de diferencia.

### El factor 1,26 está medido, no elegido

Índice de rodeo medido sobre los tramos donde la red **sí** existe:

| Estadístico | Valor |
|---|---|
| Percentil 25 | 1,12 |
| **Mediana (adoptada)** | **1,26** |
| Media | 1,35 |
| Percentil 75 | 1,47 |
| Percentil 90 | 1,75 |
| Máximo | 4,23 |

Se prefiere la **mediana** a la media porque a esta la inflan unos pocos pares
con rodeos enormes —cruzar el río, bordear un cerro— que no representan el caso
típico.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Rutear siempre sobre la red, sin comprobar cercanía** | En 61 recursos la «ruta real» saldría desde un nodo a kilómetros del sitio. Sería precisión inventada. |
| **Usar solo línea recta para todo** | Desperdicia la red donde sí existe y es muy buena: en el núcleo urbano la mediana de distancia al nodo es de decenas de metros. |
| **Un factor de corrección tomado de la literatura** | Habría sido un número sin relación con este valle. El plan hablaba de «un factor»; medirlo costó una ejecución del guion. |
| **La media (1,35) en vez de la mediana** | La inflan los rodeos extremos. Se descarta por representatividad, y la tabla completa queda publicada para que la elección se pueda discutir. |
| **Ocultar el aviso de tramo estimado** | Es la decisión que convertiría este ADR en lo contrario de lo que es. |

## Consecuencias

**Positivas**

- **La red está completamente conectada**: un solo componente con los 40 071
  nodos, y de 400 pares de recursos elegidos al azar entre los conectados, **los
  400 tienen camino**. No hay islas que haya que tratar aparte.
- El sistema degrada de forma declarada en vez de fallar o de mentir.
- **Consecuencia inesperada y valiosa**: como las pruebas afirman sobre
  `origen_del_calculo` en vez de dar por hecho que hay red, **la suite pasa en
  una máquina que no tiene la red vial descargada**. Es lo que permite que la
  integración continua funcione sin los 28 MB del grafo (ver ADR-015).

**Negativas, y declaradas**

- **El 26,1 % de los recursos georreferenciados queda con tramos estimados.**
  Sumado al 20,7 % sin coordenadas, el techo de lo que el sistema puede rutear
  con precisión real es de **173 de 295 recursos (58,6 %)**.
- Ese número no es un fallo del software: es el estado de los datos públicos del
  valle, medido y publicado.

*Limitación de la medición, declarada:* el índice de rodeo mínimo observado fue
0,71, y una ruta no puede ser más corta que la línea recta. Aparece porque la
línea recta se mide entre **recursos** y la ruta entre sus **nodos más
cercanos**, que pueden estar más juntos.

## Cómo reproducirlo

```bash
cd backend && .venv/Scripts/python.exe -m app.utilidades.medir_cobertura_osm
```

Informe distrito a distrito en `backend/datos/cobertura_osm.json`.

## Relacionado

- [ADR-007 — Se acepta OR-Tools](ADR-007-se-acepta-or-tools-con-recorrido-abierto.md)
- [ADR-008 — Las tarifas se estiman con fórmula declarada](ADR-008-las-tarifas-se-estiman-con-formula-declarada.md)
