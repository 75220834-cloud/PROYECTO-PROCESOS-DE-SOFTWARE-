# Indicador 2 — Tiempo entre las preferencias y la confirmación del itinerario

**Incremento:** 2 — Registro de preferencias del visitante
**Brecha que mide:** 3 — las preferencias del visitante no se registran ni se usan sistemáticamente
**Estado:** **medio implementado** — falta el otro extremo de la medición

---

## Qué mide

Cuánto tiempo pasa desde que el visitante declara lo que quiere hasta que
tiene un itinerario confirmado.

Antes del Incremento 2 este tiempo no se podía medir siquiera, porque el
primer extremo no existía: lo que el visitante quería no quedaba registrado en
ninguna parte. Ahora sí.

## Por qué todavía no se puede calcular entero

El indicador necesita **dos marcas de tiempo**:

| Extremo | Estado | Dónde vive |
|---|---|---|
| Cuándo se registran las preferencias | ✅ implementado | `preferencia_viaje.creado_en` |
| Cuándo se confirma el itinerario | ⏳ Fase 4 | `itinerario.creado_en` |

El segundo llega con el Incremento 4, que es el que construye itinerarios. Se
documenta así, a medias y diciéndolo, en vez de inventar un número: publicar
un indicador que no se puede calcular sería exactamente el tipo de afirmación
que este proyecto se comprometió a no hacer.

## Cómo se calculará

```sql
SELECT avg(itinerario.creado_en - preferencia_viaje.creado_en)
FROM itinerario
JOIN preferencia_viaje ON itinerario.preferencia_id = preferencia_viaje.id
WHERE itinerario.estado = 'confirmado';
```

## Lo que sí se puede medir ya

El endpoint interno `GET /api/preferencias/indicadores/resumen` devuelve:

| Dato | Para qué sirve |
|---|---|
| Total de preferencias registradas | Volumen de uso del asistente |
| Cuántas se hicieron **con** cuenta | — |
| Cuántas se hicieron **sin** cuenta | Sostiene la decisión de no exigir registro |

Ese último número es interesante por sí mismo: si la mayoría de las
preferencias se crean sin cuenta, confirma que obligar a registrarse antes de
dar nada habría costado visitantes.

## Dónde vive

| Pieza | Ubicación |
|---|---|
| Tabla | `preferencia_viaje` |
| Endpoints | `backend/app/rutas/preferencias.py` |
| Asistente | `frontend/src/paginas/AsistentePreferencias.tsx` |
| Pruebas | `backend/tests/test_rutas_preferencias.py` |
