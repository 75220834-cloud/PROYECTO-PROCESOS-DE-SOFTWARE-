# Registros de Decisiones de Arquitectura (ADR)

**Qué es esta carpeta:** las decisiones de arquitectura del proyecto en formato
ADR estándar. Cada una dice qué se decidió, qué alternativas se descartaron y por
qué, qué consecuencias tiene —incluidas las malas— y **qué atributo de calidad
afecta**.

**De dónde salen:** de las 15 notas de `docs/decisiones/`, escritas en el momento
de tomar cada decisión, con las mediciones delante. Los ADR las reexpresan en
formato estándar; **las notas originales se conservan** porque contienen el
detalle de cómo se llegó a cada número.

**Última actualización:** 25 de septiembre de 2026

---

## Tabla resumen

| ADR | Decisión en una línea | Atributo de calidad | Consecuencia principal |
|---|---|---|---|
| [001](ADR-001-fuente-del-catalogo-inventario-mincetur.md) | El catálogo se construye sobre el Inventario Nacional del MINCETUR, y el orden de las coordenadas se detecta leyendo los datos | Fiabilidad | 295 recursos con procedencia citable; 61 sin coordenada quedan fuera del mapa, marcados |
| [002](ADR-002-enriquecer-el-catalogo-con-la-ficha-web.md) | Se enriquece el catálogo leyendo las 295 fichas web del MINCETUR, a 1 petición/s y con caché en disco | Fiabilidad | 295 descripciones, 208 horarios, 414 conteos reales de visitantes que antes no se usaban |
| [003](ADR-003-la-aplicacion-funciona-sin-cuenta.md) | El visitante obtiene su viaje sin registrarse; la cuenta se ofrece al final y solo para guardarlo | Usabilidad | Nada del recorrido exige cuenta; a cambio, los identificadores secuenciales son deuda de seguridad declarada |
| [004](ADR-004-se-acepta-tfidf-para-la-afinidad.md) | Se acepta TF-IDF con similitud coseno para ordenar las recomendaciones | Usabilidad | Ordena de verdad (36–105 valores distintos frente a 2–3) y explica por qué; el valor crudo del coseno no se puede mostrar |
| [005](ADR-005-se-descarta-lightgbm-para-la-afluencia.md) | Se descarta LightGBM para la afluencia y se entrega la alternativa por reglas de calendario | Fiabilidad | Cero modelos entrenados que versionar (MLOps diferido); la afluencia es una heurística y se presenta como tal |
| [006](ADR-006-dos-modos-de-calculo-de-distancia.md) | Dos modos de cálculo de distancia con factor de rodeo medido (1,26), y el sistema dice siempre cuál usó | Fiabilidad | Techo declarado: solo 173 de 295 recursos (58,6 %) se pueden rutear con precisión real |
| [007](ADR-007-se-acepta-or-tools-con-recorrido-abierto.md) | Se acepta OR-Tools con recorrido **abierto** y peso de afinidad calibrado en 3 | Rendimiento | +14,8 % de afinidad sobre la línea base, a costa de +42 km y +80 min, que la interfaz muestra |
| [008](ADR-008-las-tarifas-se-estiman-con-formula-declarada.md) | Las tarifas de transporte se estiman con fórmula declarada, con rango, fecha, fuente y marca de estimado | Fiabilidad | El Incremento 4 conserva su restricción de presupuesto; las tarifas reales siguen sin saberse, y se dice |
| [009](ADR-009-las-reglas-de-estado-y-permisos-viven-en-el-servicio.md) | Un solo módulo decide las transiciones válidas y los permisos; la interfaz oculta, no protege | **Seguridad** | Control de acceso efectivo y probado; una tabla de historial adicional por cada movimiento |
| [010](ADR-010-los-proveedores-son-de-demostracion.md) | Los proveedores de ejemplo son de demostración y se marcan por cinco vías independientes | Fiabilidad | El ciclo de coordinación se puede demostrar; el indicador 5 queda parcialmente inválido y se declara cuál mitad |
| [011](ADR-011-se-acepta-pysentimiento-con-umbral-de-confianza.md) | Se acepta pysentimiento, que también mira las estrellas y solo se impone con confianza > 0,70 | Fiabilidad | 12/14 contra 8/14 de las reglas leyendo solo texto; ~1 s por comentario y 26 s de carga inicial |
| [012](ADR-012-mantaro-moderno-es-la-fuente-unica-del-estilo.md) | «Mantaro Moderno» es la fuente única del estilo y las tipografías se autoalojan | Usabilidad | La aplicación se ve igual sin internet, que es la condición real de la defensa; +200 kB de paquete |
| [013](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md) | Los avisos viajan del backend como `{codigo, parametros}`; la interfaz redacta la frase | **Mantenibilidad** | 69 códigos con traducción garantizada por prueba; costó una migración a JSONB y reescribir 42 pruebas |
| [014](ADR-014-el-asistente-es-capa-de-interaccion.md) | El asistente es capa de interacción: no cierra ninguna brecha y no puede inventar datos por arquitectura | **Disponibilidad** | Si Ollama cae no se pierde ninguna capacidad; tarda 25–40 s y no tiene pruebas automáticas del modelo |
| [015](ADR-015-integracion-continua-y-umbral-de-cobertura.md) | GitHub Actions ejecuta todas las comprobaciones y la cobertura se **exige** con `fail_under = 60` | Mantenibilidad | Verde al primer intento en 3 min 3 s; la CI mide algo menos de cobertura porque no tiene la red vial |

---

## Reparto por atributo de calidad

| Atributo | ADR que lo tienen como principal |
|---|---|
| **Fiabilidad** | 001, 002, 005, 006, 008, 010, 011 |
| **Usabilidad** | 003, 004, 012 |
| **Mantenibilidad** | 013, 015 |
| **Seguridad** | 009 |
| **Disponibilidad** | 014 |
| **Rendimiento** | 007 |
| **Portabilidad** | — (aparece como atributo secundario en 015) |

> **Nota honesta sobre la clasificación.** El enunciado propone seis atributos
> (rendimiento, mantenibilidad, disponibilidad, portabilidad, seguridad,
> usabilidad). Siete de los quince ADR tienen como atributo principal la
> **fiabilidad**, que es un atributo de ISO/IEC 25010 pero **no está en esa lista
> de seis**. Forzarlos a encajar en los seis habría falseado la clasificación: lo
> que esas siete decisiones protegen es la exactitud y la credibilidad del dato
> que se muestra, que es el eje del proyecto. Se declara en vez de maquillarse.
>
> Ningún ADR tiene la **portabilidad** como atributo principal, y también se dice.

---

## La nota que NO se convirtió en ADR

| Nota | Por qué se descartó |
|---|---|
| [`2026-08-28-prefijo-use-en-los-ganchos.md`](../decisiones/2026-08-28-prefijo-use-en-los-ganchos.md) | Es una **convención de nomenclatura**, no una decisión de arquitectura. Resuelve un choque entre la regla de idioma del proyecto (todo en español) y el mecanismo por el que React y `eslint-plugin-react-hooks` reconocen un gancho, que exige el prefijo `use`. No condiciona la estructura del sistema, ni la elección de ninguna tecnología, ni ningún atributo de calidad más allá de la coherencia del propio nombre. Se conserva como nota de decisión, que es lo que es. |

**Criterio aplicado para decidirlo:** un ADR registra una decisión que condiciona
la **estructura** del sistema, una **elección tecnológica** o el canje de un
**atributo de calidad**. Lo que solo fija cómo se escribe un nombre es una
convención de código.

---

## Sobre el número de ADR frente al número de notas

15 notas → **15 ADR**, pero no es una correspondencia uno a uno:

- Una nota se **descartó** (la del prefijo `use`).
- Una nota se **partió en dos**:
  [`por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md`](../decisiones/2026-08-29-por-que-se-acepto-tfidf-y-se-descarto-lightgbm.md)
  documenta **dos decisiones** —aceptar TF-IDF y descartar LightGBM— con la misma
  regla de oro aplicada y resultados contrarios. Se separaron en ADR-004 y
  ADR-005 porque un ADR registra **una** decisión.

## Numeración

Las notas están fechadas casi todas el mismo día (11 de las 15 son del 29 de
agosto de 2026), así que ordenarlas por fecha no aporta nada. **Se numeran por
incremento**, que es el orden en que se leen mejor:

Incremento 1 → 001, 002 · Incremento 2 → 003 · Incremento 3 → 004, 005 ·
Incremento 4 → 006, 007, 008 · Incremento 5 → 009, 010 · Incremento 6 → 011 ·
Transversales → 012, 013, 014, 015
