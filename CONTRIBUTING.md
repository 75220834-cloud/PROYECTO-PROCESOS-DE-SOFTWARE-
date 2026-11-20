# Cómo se contribuye a RutaVivaMantaro

Este documento describe cómo entra un cambio en el repositorio. Rige desde el
**19 de noviembre de 2026** y **sustituye a la regla anterior**, que mandaba
todo a `main` sin ramas.

Esa regla anterior no fue un descuido: era deliberada, y está declarada en el
informe académico integrador como el **hallazgo principal de aseguramiento de
calidad**, con su causa raíz —un solo desarrollador y un calendario comprimido—
y su acción correctiva, que es justamente este documento.

---

## 1. Estrategia de ramas (GitFlow)

```
feature/*  ──propuesta──▶  develop  ──release/*──▶  main  ──▶  etiqueta + Release
```

| Rama | Para qué | Quién puede escribir en ella |
|---|---|---|
| `main` | Lo que está en producción. Cada fusión se etiqueta. | Nadie directamente: solo por propuesta desde `release/*` |
| `develop` | Integración de lo que irá en la próxima versión | Nadie directamente: solo por propuesta desde `feature/*` |
| `feature/*` | Un cambio concreto, normalmente una solicitud de cambio | Quien lo desarrolla |
| `release/*` | Preparación de una versión: ajustes finales y número de versión | Quien libera |
| `hotfix/*` | Corrección urgente sobre producción. Sale de `main` y vuelve a `main` **y** a `develop` | Quien corrige |

**Nombres de rama:** `feature/rfc-3-ci-sobre-develop`. Minúsculas, guiones, y
el número de la solicitud de cambio si existe.

### El ciclo completo

1. Se abre una **Solicitud de Cambio (RFC)** como Issue, con la plantilla de
   `.github/ISSUE_TEMPLATE/change_request.md`. Antes de tocar código.
2. Se crea la rama `feature/*` **desde `develop`**.
3. Se trabaja con commits semánticos.
4. Se abre una **propuesta de cambio** hacia `develop`, con `Closes #N`.
5. La integración continua tiene que pasar en verde.
6. **Otra persona** revisa y aprueba. El autor no aprueba su propia propuesta,
   y GitHub tampoco lo permite.
7. Se fusiona con **merge commit**, no con squash, para que el historial
   conserve la forma de la rama en el gráfico de red.

---

## 2. Convención de commits

Conventional Commits **en español**, que es lo que el repositorio ya usaba en
sus primeros 132 commits.

```
tipo(ámbito): qué hace, en imperativo y en minúscula [brecha-N]
```

| Tipo | Cuándo |
|---|---|
| `feat` | Capacidad nueva |
| `fix` | Corrección de un defecto |
| `refactor` | Cambia la forma, no el comportamiento |
| `test` | Solo pruebas |
| `docs` | Solo documentación |
| `chore` | Herramientas, dependencias, configuración |
| `ci` | Integración continua |
| `perf` | Rendimiento |

La marca `[brecha-N]` enlaza el commit con la brecha del análisis AS-IS que
cierra. Es lo que permite recorrer la trazabilidad de brecha a prueba.

**El cuerpo del commit explica el porqué, no el qué.** El qué ya se lee en el
diff.

---

## 3. Política de versiones

Se sigue **SemVer** (`MAYOR.MENOR.PARCHE`) con una salvedad histórica.

| Etiqueta | Qué marca |
|---|---|
| `v1.0-PMV` | Producto Mínimo Viable |
| `v2.0-Inc2` | Incremento 2 — preferencias y recomendación |
| `v3.0-Inc3` | Incremento 3 — ruteo e itinerario |
| `v4.0-Inc4` | Incremento 4 — coordinación y valoraciones |
| `v2.0` | **No es el Incremento 2.** Marca la migración a arquitectura hexagonal del 8 de noviembre de 2026 |

> **Sobre `v2.0`:** la etiqueta se publicó antes de adoptar este esquema de
> versiones y se conserva porque **no se borra ni se mueve nada ya publicado**.
> Coincide en número con `v2.0-Inc2` pero no tiene relación con él: es
> posterior en el tiempo y marca un cambio de arquitectura, no un incremento
> funcional. Las notas de su Release lo dicen de forma explícita.

Cada etiqueta es **anotada** (`git tag -a`) y tiene un Release en GitHub con
sus notas de entrega.

---

## 4. Criterios de terminación

Un cambio no está hecho hasta que **la máquina** lo confirma. Todo lo de esta
lista se comprueba solo en la integración continua:

- Compila sin errores.
- `pytest` en verde con cobertura **≥ 95 %** (`fail_under` en
  `backend/pyproject.toml`).
- `pruebas/test_dominio_sin_frameworks.py` en verde: ningún módulo de
  `backend/src/domain/` importa un marco de trabajo.
- `ruff` y `black` limpios sobre `src/`, `pruebas/` y `alembic/`.
- `eslint` y `tsc --noEmit` limpios en el frontend.
- `vitest` en verde.

Si el cambio contradice algo escrito en `docs/`, se corrige en el mismo envío.
La documentación desactualizada es un defecto, no una tarea pendiente.

---

## 5. Lo que no se hace

- **No se reescribe el historial publicado.** Nada de `push --force` sobre
  `main` ni sobre `develop`.
- **No se borran ni se mueven etiquetas publicadas.**
- **No se fusiona con la integración continua en rojo**, ni aunque el fallo
  «no tenga que ver». Si el fallo no tiene que ver, se arregla igualmente.
- **No se aprueba la propia propuesta.**
