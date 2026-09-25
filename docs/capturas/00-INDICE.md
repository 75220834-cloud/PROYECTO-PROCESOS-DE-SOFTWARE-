# Capturas de pantalla del software en ejecución

**Fecha:** 25 de septiembre de 2026
**Resolución:** 3200 px de ancho (viewport 1600×1000 con `deviceScaleFactor: 2`)
**Cómo se tomaron:** Playwright con el Microsoft Edge del sistema, en modo sin
cabeza, contra el sistema realmente levantado: backend en `:8000`, frontend en
`:5173`, PostgreSQL 16.4 + PostGIS 3.4 y Ollama.

Se regeneran con:

```bash
cd frontend && node capturar-pantallas.mjs
```

```bash
cd frontend && SONAR_CONTRASENA=la_del_contenedor node capturar-cobertura.mjs
```

La contraseña de SonarQube se pasa por entorno y **no está escrita en el
guion**: es un contenedor local y efímero, pero la regla 1.9 del proyecto
—«nada de secretos en el código»— no admite excepciones por comodidad.

---

## Las capturas

| Archivo | Qué muestra | Px |
|---|---|---|
| `01_catalogo.png` | Catálogo con los **295 recursos**, 234 validados (79,32 %) y el mapa con agrupamiento de marcadores | 3200×2000 |
| `02_filtros.png` | El mismo catálogo **filtrado** por provincia Concepción y «solo validados» | 3200×2000 |
| `03_ficha_recurso.png` | Ficha de un recurso con su **descripción del MINCETUR** | 3200×3274 |
| `04a_preferencias_paso1.png` | Asistente de preferencias, primer paso | 3200×2000 |
| `04b_preferencias_paso2.png` | Asistente de preferencias, paso siguiente | 3200×2000 |
| `05_recomendaciones.png` | Recomendaciones **con el porqué de cada una** | 3200×6414 |
| `06_itinerario.png` | Itinerario completo: línea de tiempo, traslados y totales del día | 3200×3530 |
| `07_itinerario_mapa.png` | El itinerario **dibujado sobre el mapa** | 3200×2000 |
| `08_avisos.png` | **Un aviso visible**: altitud 3733 m s. n. m., más los totales con «aprox.» | 3200×2000 |
| `09_ingles.png` | La misma aplicación **en inglés** | 3200×2000 |
| `10_api_docs.png` | Swagger UI en `/docs` con las 43 operaciones | 3200×13666 |
| `11_cobertura_pytest.png` | Informe HTML de `coverage.py` con el **73 %** *(ver la nota de abajo)* | 3200×4428 |
| `11_pytest_consola.txt` | La **salida literal** de pytest, en texto | — |
| `12_github_actions.png` | La ejecución de integración continua **en verde**, 3m 3s | 3200×2000 |
| `13_sonarqube.png` | El tablero de SonarQube tras el análisis | 3200×2000 |

---

## Dos cosas que hay que decir, y no maquillar

### La captura 11 no es una consola

El entregable pedía «el resultado de **pytest en consola** con el porcentaje de
cobertura». **Una captura de una terminal no se puede tomar desde el entorno en
el que se generaron estas imágenes**, y montar una página web que imitara una
consola habría sido fabricar algo con aspecto de evidencia que no lo es.

Lo que hay en su lugar son dos cosas reales:

- `11_cobertura_pytest.png` — el informe HTML que genera **`coverage.py`** con
  los datos de esa misma ejecución de pytest;
- `11_pytest_consola.txt` — **la salida literal de la consola**, en texto, con
  la línea `549 passed, 1 skipped … Total coverage: 73.42%`, lista para pegarse
  en el informe o para que alguien la capture desde su propia terminal.

### La captura 3 no tiene foto

El entregable pedía «ficha de un recurso **con foto** y descripción». La
descripción está —los 295 recursos la tienen, leída de la ficha web del
MINCETUR—, **pero la foto no existe**:

- `SELECT count(*) FROM recurso_turistico WHERE foto_url IS NOT NULL` → **0**;
- la pantalla de detalle **no renderiza ninguna imagen**: no hay ni un `<img>` en
  `DetalleRecurso.tsx`.

No es un descuido de la captura: es una decisión declarada en
[ADR-012](../adr/ADR-012-mantaro-moderno-es-la-fuente-unica-del-estilo.md).
Poner imágenes de relleno contradiría la regla de honestidad con los datos, y las
fotografías reales de los atractivos no están en la fuente oficial.

**Si la foto es imprescindible para el entregable, hay que conseguir las
imágenes primero.** No se puede resolver con una captura.
