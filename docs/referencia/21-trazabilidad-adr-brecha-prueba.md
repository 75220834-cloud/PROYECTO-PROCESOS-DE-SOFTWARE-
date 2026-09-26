# 21 — Trazabilidad: brecha → ADR → prueba → endpoint → indicador

**Qué explica este archivo:** el tramo central de la matriz de trazabilidad
integral que pide la consigna:

> Problema → Proceso TO-BE → Modelo adaptado → Actividad → **DECISIÓN DE
> ARQUITECTURA → CASO DE PRUEBA** → PMV → Indicador de valor

Los dos primeros tramos y el último están en
[09 — Los seis incrementos](09-los-seis-incrementos.md) y
[10 — Los indicadores](10-indicadores.md). Aquí se cierra el hueco del medio.

**Cada eslabón es comprobable en el repositorio.** No hay ninguno deducido: los
archivos de prueba y sus recuentos salen de la
[matriz de registro](19-matriz-de-registro-de-pruebas.md), los endpoints del
contrato OpenAPI, y los indicadores de las funciones que los calculan.

---

## Brecha 1 — No existe una fuente integrada, oficial y actualizada de la oferta

| Eslabón | Qué lo sostiene |
|---|---|
| **ADR** | [ADR-001](../adr/ADR-001-fuente-del-catalogo-inventario-mincetur.md) — el catálogo se construye sobre el Inventario Nacional del MINCETUR<br>[ADR-002](../adr/ADR-002-enriquecer-el-catalogo-con-la-ficha-web.md) — se enriquece leyendo las 295 fichas web |
| **Pruebas** | `test_catalogo.py` (23) · `test_validacion_catalogo.py` (20) · `test_rutas_catalogo.py` (17) · `test_fichas_y_temporada.py` (30) · `TarjetaRecurso.prueba.tsx` (5) · **`e2e-01-catalogo.spec.ts` (5)** |
| **Endpoints** | `GET /api/recursos` · `GET /api/recursos/filtros` · `GET /api/recursos/mapa` · `GET /api/recursos/{id_recurso}` · `GET /api/indicadores/catalogo` |
| **Indicador** | **1 — Oferta validada y vigente**, `rutas/valoraciones.py::_indicador_1_catalogo` → **79,32 %** (234 de 295) |

**El eslabón que más se nota:** ADR-001 decidió detectar el orden de las
coordenadas leyendo los datos en vez de suponerlo, y `test_catalogo.py` lo prueba
**en los dos sentidos**. Si el MINCETUR corrigiera su CSV mañana, el importador
seguiría funcionando y la prueba seguiría pasando.

---

## Brecha 2 — La oferta no se ajusta al perfil del visitante

| Eslabón | Qué lo sostiene |
|---|---|
| **ADR** | [ADR-004](../adr/ADR-004-se-acepta-tfidf-para-la-afinidad.md) — se acepta TF-IDF para ordenar<br>[ADR-005](../adr/ADR-005-se-descarta-lightgbm-para-la-afluencia.md) — se descarta LightGBM y se entregan las reglas |
| **Pruebas** | `test_afinidad_y_afluencia.py` (37) · `test_rutas_recomendaciones.py` (25) · `test_calendario.py` (42) · `TarjetaRecomendacion.prueba.tsx` (9) · **`e2e-03-recomendaciones.spec.ts` (2)** |
| **Endpoints** | `POST /api/recomendaciones` · `GET /api/calendario/dia/{fecha}` · `GET /api/calendario/{anio}` |
| **Indicador** | **3 — Recomendaciones sin error**, `rutas/valoraciones.py::_indicador_3_recomendaciones` → **100 %** |

**El eslabón que más se nota:** lo que cierra esta brecha no es que salga una
lista, sino que cada recomendación **diga por qué**. `TarjetaRecomendacion.prueba.tsx`
lo fija en el componente y `e2e-03` lo comprueba en la pantalla real: si un día
dejara de venir el campo de términos que pesaron, las dos fallan.

---

## Brecha 3 — Las preferencias del visitante no se registran

| Eslabón | Qué lo sostiene |
|---|---|
| **ADR** | [ADR-003](../adr/ADR-003-la-aplicacion-funciona-sin-cuenta.md) — el visitante obtiene su viaje sin registrarse |
| **Pruebas** | `test_rutas_preferencias.py` (28) · `test_rutas_autenticacion.py` (17) · `test_seguridad.py` (15) · `AsistentePreferencias.prueba.tsx` (9) · **`e2e-02-preferencias.spec.ts` (2)** |
| **Endpoints** | `POST /api/preferencias` · `GET /api/preferencias` · `GET /api/preferencias/{id}` · `PUT /api/preferencias/{id}` · `POST /api/preferencias/{id}/reclamar` · `GET /api/preferencias/opciones` · más los 3 de autenticación |
| **Indicador** | **2 — De preferencias a itinerario**, `rutas/valoraciones.py::_indicador_2_preferencias` |

**El eslabón que más se nota:** ADR-003 promete que **nada del recorrido exige
cuenta**, y esa promesa se comprueba en tres niveles a la vez: en el backend
(`test_se_puede_guardar_sin_haber_iniciado_sesion`), en el componente
(`AsistentePreferencias.prueba.tsx`) y de extremo a extremo (`e2e-02`, que
además verifica que el encabezado sigue ofreciendo *iniciar* sesión al terminar).
Si alguien añadiera un muro de registro, caerían las tres.

---

## Brecha 4 — El proceso no incorpora el tiempo ni el costo de desplazamiento

| Eslabón | Qué lo sostiene |
|---|---|
| **ADR** | [ADR-006](../adr/ADR-006-dos-modos-de-calculo-de-distancia.md) — dos modos de distancia, y se declara cuál se usó<br>[ADR-007](../adr/ADR-007-se-acepta-or-tools-con-recorrido-abierto.md) — OR-Tools con recorrido abierto<br>[ADR-008](../adr/ADR-008-las-tarifas-se-estiman-con-formula-declarada.md) — las tarifas se estiman con fórmula declarada |
| **Pruebas** | `test_ruteo.py` (33) · `test_tiempo_recorrido.py` (30) · `test_costos.py` (24) · `test_rutas_itinerarios.py` (33) · `LineaDeTiempo.prueba.tsx` (18) · `TotalesDelDia.prueba.tsx` (8) · **`e2e-04-itinerario.spec.ts` (3)** |
| **Endpoints** | `POST /api/itinerarios` · `POST /api/itinerarios/reordenar` · `GET /api/itinerarios` · `GET /api/itinerarios/{itinerario_id}` |
| **Indicador** | **4 — Itinerarios viables y trazables**, `rutas/valoraciones.py::_indicador_4_itinerarios` → **4 de 4 perfiles**, peor caso 6,52 s de 10 s |

**El eslabón que más se nota:** ADR-006 decidió que el sistema **declare siempre
si el tramo salió de la red vial o de una línea recta corregida**, y esa decisión
se prueba en cuatro sitios. `e2e-04` lo comprueba sobre la pantalla —recorre las
paradas y exige que cada traslado traiga `origen_del_calculo`—, y
`TotalesDelDia.prueba.tsx` exige que el costo lleve «aprox.».

Esa misma decisión es lo que permite que **la suite pase en la integración
continua, que no tiene la red vial descargada**: las pruebas afirman sobre el
campo en vez de dar por hecho que hay red.

---

## Resumen en una tabla

| Brecha | ADR | Archivos de prueba | Casos | Endpoints | Indicador | Valor |
|---|---|---|---|---|---|---|
| **1** | 001, 002 | 6 | **100** | 5 | 1 | 79,32 % |
| **2** | 004, 005 | 5 | **115** | 3 | 3 | 100 % |
| **3** | 003 | 5 | **71** | 9 | 2 | preferencias → itinerario |
| **4** | 006, 007, 008 | 7 | **149** | 4 | 4 | 4 de 4, peor caso 6,52 s |

---

## Las decisiones transversales, que no pertenecen a una brecha

Tres ADR sostienen las cuatro brechas a la vez y por eso no aparecen arriba:

| ADR | Qué sostiene en las cuatro |
|---|---|
| [ADR-013](../adr/ADR-013-los-avisos-viajan-como-codigo-y-parametros.md) | Todos los avisos y errores de las cuatro brechas viajan como `{codigo, parametros}`. La prueba `avisos.prueba.ts` (19 casos) lee los 69 códigos del archivo de Python y exige traducción en los dos idiomas |
| [ADR-012](../adr/ADR-012-mantaro-moderno-es-la-fuente-unica-del-estilo.md) | La interfaz de las cuatro usa el mismo sistema de diseño, con tipografías autoalojadas para que funcione sin internet |
| [ADR-015](../adr/ADR-015-integracion-continua-y-umbral-de-cobertura.md) | Las pruebas de las cuatro se ejecutan solas en cada push, y la cobertura se exige |

Y dos que sostienen las brechas 5, 6 y 7, fuera del PMV de esta entrega:
[ADR-009](../adr/ADR-009-las-reglas-de-estado-y-permisos-viven-en-el-servicio.md),
[ADR-010](../adr/ADR-010-los-proveedores-son-de-demostracion.md) y
[ADR-011](../adr/ADR-011-se-acepta-pysentimiento-con-umbral-de-confianza.md).

---

## Relacionado

- [00 — Índice de los ADR](../adr/00-INDICE.md)
- [09 — Los seis incrementos](09-los-seis-incrementos.md) — la matriz de arriba
- [10 — Los indicadores](10-indicadores.md) — la matriz de abajo
- [19 — Matriz de registro de pruebas](19-matriz-de-registro-de-pruebas.md)
