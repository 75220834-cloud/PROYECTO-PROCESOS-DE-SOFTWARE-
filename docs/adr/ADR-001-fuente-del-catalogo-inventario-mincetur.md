# ADR-001 — El catálogo se construye sobre el Inventario Nacional del MINCETUR

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 1 — catálogo integrado (cierra la brecha 1) |
| **Atributo de calidad principal** | **Fiabilidad** (exactitud y credibilidad de los datos) |
| **Atributos secundarios** | Mantenibilidad (adaptabilidad del importador) |
| **Nota de origen** | [`2026-08-29-fuente-del-catalogo-mincetur.md`](../decisiones/2026-08-29-fuente-del-catalogo-mincetur.md) |

---

## Contexto

La brecha 1 del análisis es que **no existe una fuente integrada, oficial y
actualizada** de la oferta turística de la Ruta del Valle del Mantaro. El
Incremento 1 necesita una fuente que cumpla tres requisitos simultáneos:

- **oficial**, para que el catálogo se pueda defender ante un jurado;
- **georreferenciada**, porque el Incremento 4 calcula rutas sobre el terreno;
- **fechada**, porque el indicador del incremento mide vigencia del dato.

## Decisión

Se adopta el **Inventario Nacional de Recursos Turísticos** del MINCETUR
(Dirección General de Estrategia Turística), publicado como dato abierto en
CSV, filtrando `REGIÓN = JUNÍN` y las cuatro provincias de la ruta: Huancayo,
Concepción, Jauja y Chupaca.

Es la única fuente evaluada que cumple los tres requisitos a la vez: es del
Estado peruano, trae latitud y longitud por recurso, y trae la columna
`FECHA_DE_CORTE` sobre la que se calcula el indicador de vigencia.

Tres decisiones derivadas, tomadas al encontrar defectos reales en la fuente:

1. **El orden de las coordenadas se detecta leyendo los datos, no se supone.**
   Las columnas rotuladas `LATITUD` y `LONGITUD` vienen **intercambiadas en el
   archivo entero**: de 6 155 filas nacionales, 0 son coherentes con los
   rótulos y 4 910 lo son al invertirlas. `detectar_orden_de_coordenadas`
   resuelve por mayoría, de modo que si el MINCETUR corrige el archivo el
   importador sigue funcionando sin tocar una línea.
2. **Los 61 recursos sin coordenada se guardan con ubicación nula.** No se les
   asigna el centroide del distrito ni ninguna aproximación: aparecen marcados
   con el motivo `sin coordenadas` y quedan fuera del mapa.
3. **La codificación se prueba en orden, no se supone.** El archivo viene en
   cp1252; leerlo como UTF-8 rompe todos los nombres con tilde.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **DIRCETUR Junín** | Es la autoridad regional y la fuente natural, pero no publica su inventario como dato abierto: solo PDF, sin coordenadas ni fecha de corte por recurso. |
| **OpenStreetMap** | Cobertura excelente en Huancayo y pobre en los distritos rurales, y **no es oficial**: cualquiera edita. Se reserva para la red vial del Incremento 4. |
| **Google Places** | De pago, en la nube, y con condiciones de uso que prohíben almacenar los datos. El proyecto exige ejecución local y sin coste. |
| **Recopilación manual del equipo** | Tres personas no pueden inventariar cuatro provincias, y el resultado no sería oficial ni auditable: es exactamente la brecha que se quiere cerrar. |

## Consecuencias

**Positivas**

- 295 recursos cargados, con procedencia citable fila por fila.
- El indicador del Incremento 1 es medible: **79,32 % validado** (234 de 295).
- El importador es idempotente por código MINCETUR y resiste que la fuente
  corrija sus propios defectos.

**Negativas, y asumidas**

- **61 recursos (20,7 %) no tienen coordenada** y quedan fuera del mapa y del
  ruteo. Son danzas, fiestas patronales y platos típicos que el inventario
  registra sin ubicación puntual.
- El catálogo hereda la calidad de la fuente: si el MINCETUR no actualiza, el
  proyecto tampoco.
- Hubo que **corregir el rectángulo de validación** que proponía el plan de
  trabajo: el original dejaba fuera 52 recursos correctos de distritos reales
  de la zona alta occidental. Se midió sobre la extensión real de los 234
  georreferenciados y quedó en latitud −12,60 a −11,20, longitud −75,90 a
  −74,90.

## Reparto verificado

| Provincia | Recursos |
|---|---|
| Huancayo | 111 |
| Jauja | 104 |
| Concepción | 51 |
| Chupaca | 29 |
| **Total** | **295** |

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_catalogo.py pruebas/test_validacion_catalogo.py -v
```

## Relacionado

- [ADR-002 — El catálogo se enriquece con la ficha web](ADR-002-enriquecer-el-catalogo-con-la-ficha-web.md)
- [ADR-006 — Dos modos de cálculo de distancia](ADR-006-dos-modos-de-calculo-de-distancia.md)
