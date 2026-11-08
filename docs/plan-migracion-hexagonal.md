# Plan de migración a arquitectura hexagonal

Medido contra el código el **8 de noviembre de 2026**, sobre el commit `d7126b9`.
Ninguna cifra de este documento está estimada: cada una sale de un comando que
se puede repetir. Los comandos están al final.

Estado de partida verificado: **771 pruebas pasan, 2 se saltan, 96,28 % de
cobertura**, `fail_under = 95`, la suite tarda 3 min 33 s.

---

## 1. Diagnóstico

### 1.1 Lo que ya está bien, y es más de lo que parece

**Cero importaciones de FastAPI en la capa de lógica.** Ni en `servicios/` ni en
`ia/`. Los enrutadores viven en `rutas/` y no se han filtrado hacia abajo.

**Cero Pydantic y cero Alembic en la capa de lógica.** Los esquemas de
`esquemas/` solo los usan los enrutadores.

Esto significa que la separación «entrada ↔ dominio» ya existe de hecho. La
migración no tiene que inventarla, solo nombrarla y moverla de carpeta.

### 1.2 El acoplamiento real

**Nueve módulos de lógica importan SQLAlchemy y los modelos ORM:**

| Módulo | Líneas |
|---|---|
| `servicios/catalogo.py` | 29, 30, 32 |
| `servicios/coordinacion.py` | 25, 26, 28, 37 |
| `servicios/costos.py` | 48, 49, 51, 52 |
| `servicios/evidencia.py` | 34, 35, 37, 38, 39 |
| `servicios/recomendador.py` | 24, 25, 26, 30, 31 |
| `servicios/ruteo.py` | 54, 55, 62, 63, 69 |
| `servicios/usuarios.py` | 5, 6, 8 |
| `servicios/validacion_catalogo.py` | 29, 30, 31, 33 |
| `ia/asistente.py` | 51, 52, 54 |

`recomendador.py` y `validacion_catalogo.py` además importan **GeoAlchemy2** y
hacen `cast(..., Geometry)`: el cálculo geoespacial está *dentro* de la consulta
SQL, no encima de ella. Son los dos casos difíciles.

**Cuarenta y siete firmas** de función reciben `sesion: Session`. Ese es el
tamaño real de la superficie a invertir.

**Dos módulos hablan HTTP:** `servicios/elevacion.py:38` y `ia/asistente.py:50`,
los dos con `httpx`.

### 1.3 Tres módulos están a un paso de ser dominio puro

`servicios/red_vial.py`, `ia/afinidad.py` e `ia/sentimiento.py` **no importan
SQLAlchemy**. Su única atadura son enumeraciones y constantes que viven en
`modelos/`. Eso no es acoplamiento de framework: es un `StrEnum` guardado en la
carpeta equivocada.

### 1.4 Nueve objetos de valor atrapados en la infraestructura

Estos `StrEnum` son dominio puro y hoy viven en archivos de SQLAlchemy:

| Enumeración | Archivo actual |
|---|---|
| `TipoServicio`, `EstadoSolicitud` | `modelos/coordinacion.py` |
| `EstadoItinerario`, `OrigenDelCalculo` | `modelos/itinerario.py` |
| `Ritmo`, `Movilidad`, `Interes` | `modelos/preferencias.py` |
| `ModoTransporte` | `modelos/transporte.py` |
| `Sentimiento`, `TemaValoracion` | `modelos/valoracion.py` |

Moverlos a `src/domain/` y que el ORM los importe desde allí hace que la
dependencia apunte hacia adentro, que es justamente la regla hexagonal.

### 1.5 Las librerías de cálculo

| Librería | Dónde |
|---|---|
| OR-Tools | `servicios/ruteo.py` |
| scikit-learn, NumPy | `ia/afinidad.py`, `ia/afluencia.py` |
| OSMnx, NetworkX | `servicios/red_vial.py` (y un guion de operación) |
| rasterio | `servicios/elevacion.py` |
| pysentimiento | `ia/sentimiento.py` |

### 1.6 Tamaño del movimiento

- **68 archivos** `.py` en `backend/app/`, **27** en `backend/pruebas/`.
- **246 sentencias de importación** que empiezan por `from app.` (156 en el
  paquete, 90 en las pruebas). Todas hay que reescribirlas.

---

## 2. Dónde va `src/`, y por qué

**Decisión: `backend/src/{domain,ports,adapters}/`.**

El criterio del docente escribe `/src/domain/`, lo que sugiere la raíz del
repositorio. **No se puede**, y la razón es de despliegue: en Render el *Root
Directory* del servicio es `backend`. Un `src/` colgando de la raíz quedaría
fuera de lo que Render copia y el API dejaría de arrancar.

`backend/src/domain/` se ve igual de claro al abrir el repositorio en GitHub, y
el propio encargo contempla esta opción. Se compensa con un árbol visible en el
`README.md` de la raíz, sin tener que navegar.

`src` será **un paquete** (`src/__init__.py`), así que los imports quedan
`from src.domain.ruteo import ...`. Esto permite que la fase 1 sea un único
reemplazo `from app.` → `from src.` sobre 246 líneas, en vez de 246 decisiones.

---

## 3. El árbol objetivo

```
backend/
  src/
    domain/                      reglas y cálculo. Cero frameworks.
      valores/                   los 9 StrEnum + objetos de valor
      ruteo.py                   OR-Tools
      afinidad.py                scikit-learn
      sentimiento.py             pysentimiento
      red_vial.py                OSMnx + NetworkX
      costos.py  avisos.py  temporada.py  evidencia.py
      catalogo.py  coordinacion.py  recomendador.py  validacion_catalogo.py
    ports/                       interfaces que el dominio declara
      repositorios.py            uno por agregado
      servicios_externos.py      elevación, modelo conversacional
    adapters/
      inbound/
        http/                    los 9 enrutadores de FastAPI + esquemas Pydantic
      outbound/
        persistencia/
          modelos/               SQLAlchemy
          repositorios/          implementan ports/repositorios.py
        elevacion_http.py        httpx + rasterio
        ollama.py                httpx
    composicion.py               raíz de composición: el único cableado
    main.py  configuracion.py  base_datos.py
  pruebas/
    test_dominio_sin_frameworks.py   la prueba que lo demuestra
```

---

## 4. Fases

Cada fase termina con la suite en verde y un commit propio. Si una fase rompe
pruebas, se arregla **dentro de esa fase**; no se acumula deuda.

### Fase 1 · Renombrar el paquete `app` → `src`

Mecánica pura, sin hexagonal todavía. Deja la ruta final correcta antes de
empezar a mover responsabilidades.

- 68 archivos cambian de ruta, 246 imports reescritos con un solo reemplazo.
- Configuración a tocar, verificada una por una:

| Archivo | Qué |
|---|---|
| `backend/pyproject.toml` | `[tool.coverage.run] source`, `[tool.setuptools.packages.find] include` |
| `backend/alembic/env.py` | líneas 23, 24, 28 |
| `.github/workflows/integracion-continua.yml` | `ruff check app/…`, `black --check app/…` |
| `.claude/launch.json` | `app.main:aplicacion` |
| `README.md` | líneas 148 y 462 |
| `normalizar_cobertura.py` | líneas 13, 49, 59 (rutas de SonarQube) |
| Panel de Render | comando de arranque `uvicorn app.main:…` |

**Riesgo: bajo pero ancho.** Mecánico y las pruebas lo atrapan todo… salvo el
comando de Render, que no tiene prueba. Hay que cambiarlo en el panel **antes**
de fusionar, o el API se cae al desplegar.

### Fase 2 · Dominio puro y la prueba que lo demuestra

Lo más valioso por lo que cuesta.

- Mover los **9 `StrEnum`** a `src/domain/valores/`; el ORM los importa de allí.
- Mover `red_vial.py`, `afinidad.py`, `sentimiento.py` a `src/domain/`.
- Mover `avisos.py` y `temporada.py` (ya son puros).
- Escribir `pruebas/test_dominio_sin_frameworks.py` (sección 5).
- Añadir esa prueba a la integración continua.

Unos 14 archivos. **Al terminar esta fase el criterio del docente ya está
satisfecho de forma honesta**: las tres carpetas existen, `domain/` tiene
contenido real, y una máquina comprueba que no hay frameworks dentro.

### Fase 3 · Puertos de repositorio y adaptadores de persistencia

La fase grande. Por cada módulo: declarar el puerto, implementarlo contra
SQLAlchemy, quitar `Session` del servicio.

- **3a — los fáciles:** `usuarios.py`, `catalogo.py`, `validacion_catalogo.py`.
- **3b — los medianos:** `costos.py`, `evidencia.py`, `recomendador.py`.
- **3c — los difíciles:** `ruteo.py` (1 552 líneas), `coordinacion.py`,
  `asistente.py`. Aquí están las consultas con PostGIS.

47 firmas que invertir. Es la fase que de verdad cuesta días.

### Fase 4 · Adaptadores de entrada

`rutas/` → `src/adapters/inbound/http/`, `esquemas/` al lado. 9 + 9 archivos,
movimiento mecánico.

### Fase 5 · Adaptadores de salida no persistentes

`elevacion.py` y el cliente de Ollama detrás de puertos. 2 módulos.

### Fase 6 · Raíz de composición

Un solo `composicion.py` que decide qué implementación recibe cada puerto,
inyectado con `Depends`. El dominio no sabe qué le llegó.

### Fase 7 · Documentación, revisión y etiqueta

- `docs/adr/ADR-017-migracion-a-arquitectura-hexagonal.md` (hay 16, sigue la 17).
- `docs/referencia/02-arquitectura.md` con el árbol nuevo.
- `README.md` de la raíz con el árbol visible.
- Solicitud de incorporación, revisión de Jefferson Huaman, fusión, etiqueta `v2.0`.

---

## 5. La prueba de acoplamiento

`backend/pruebas/test_dominio_sin_frameworks.py`. Lee los imports con `ast`, no
con búsqueda de texto, así que no la engaña un comentario ni una cadena.

```python
PROHIBIDOS = {
    "fastapi", "sqlalchemy", "geoalchemy2", "psycopg",
    "alembic", "httpx", "requests", "pydantic",
}

def test_ningun_modulo_del_dominio_importa_un_framework():
    for archivo in (RAIZ / "src" / "domain").rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            # ast.Import e ast.ImportFrom, quedándose con la raíz del
            # paquete: "sqlalchemy.orm" cuenta como "sqlalchemy".
            ...
```

Es la pieza más importante del encargo: convierte «cero acoplamiento de
frameworks en el Dominio» de una afirmación en un hecho comprobado en cada
envío. Va también al flujo de integración continua.

---

## 6. Sobre OR-Tools y scikit-learn

El encargo pregunta si esconderlas detrás de un puerto.

**Recomiendo que no.** Son librerías de cálculo, no de infraestructura: no
hablan con la red, ni con el disco, ni con la base. Un puerto delante de
OR-Tools no desacopla nada real, añade una capa que hay que mantener, y es
justo el tipo de ceremonia que convierte lo hexagonal en burocracia.

Lo que sí recomiendo es dejarlo **escrito en el ADR-017**, con el argumento,
para que se lea como una decisión tomada y no como un olvido. Si en la defensa
preguntan por qué `sklearn` aparece dentro de `domain/`, la respuesta está
firmada y fechada.

Nota: la prueba de la sección 5 no las prohíbe, justamente por esto.

---

## 7. Dos caminos, y cuál recomiendo

**El mínimo honesto — fases 1, 2 y 7.** Unos 14 archivos movidos más el
renombrado. Deja las tres carpetas con contenido real, el dominio demostrablemente
limpio, el ADR, la revisión por pares y la etiqueta `v2.0`. **Satisface el
criterio tal como está redactado.** Es realista para esta semana.

**El completo — las siete fases.** Hace que todo el sistema sea hexagonal de
verdad. Las fases 3 a 6 son varios días de trabajo sobre 47 firmas y dos
módulos con PostGIS incrustado. No es realista antes de la entrega.

Mi recomendación: **1, 2 y 7 ahora; 3 a 6 declaradas en el ADR-017 como plan
de continuación con su alcance.** Eso es defendible delante del docente —
«migramos el núcleo y dejamos escrito el resto» es una respuesta de ingeniería.
Lo que no es defendible es crear las tres carpetas vacías para que se vean en
GitHub.

---

## 8. Lo que necesito de ti antes de empezar

1. **Visto bueno al plan**, y cuál de los dos caminos.
2. **El usuario de GitHub de Jefferson Huaman**, para pedirle la revisión.
3. **Confirmación de que puedo tocar la configuración de despliegue**, y quién
   cambia el comando de arranque en el panel de Render: eso no lo puedo hacer yo.
4. **Si quieres que la rama se llame** `refactor/arquitectura-hexagonal`.

## 9. Lista aparte: cosas que no se tocan en esta migración

Si aparece un error de camino, se anota aquí y **no** se arregla en el mismo
commit. Pendientes ya conocidos de antes:

- `src/adapters/outbound/persistencia` deberá heredar el `pool_size` /
  `max_overflow` sin configurar de `base_datos.py`.
- Código muerto en `coordinacion.py`: `_nombre_del_dia` y un `raise` inalcanzable.

---

## 10. Comandos para repetir cada medición

```bash
# archivos e imports
find backend/app -name "*.py" | wc -l
grep -rn "^from app\.\|^import app\." backend/app --include=*.py | wc -l
grep -rn "^from app\.\|^import app\." backend/pruebas --include=*.py | wc -l

# acoplamiento de la capa de logica
grep -rn "^from sqlalchemy\|^from geoalchemy2\|^from app.modelos" backend/app/servicios backend/app/ia
grep -rn "^from fastapi\|^from pydantic" backend/app/servicios backend/app/ia
grep -rn "sesion: Session" backend/app/servicios backend/app/ia | wc -l

# linea base de las pruebas (desde backend/, con el entorno del proyecto)
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing
```
