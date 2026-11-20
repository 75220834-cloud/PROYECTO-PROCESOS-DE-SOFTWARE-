## Descripción del cambio

<!-- Qué cambia y por qué. Si corrige un hallazgo, dilo. -->

Closes #

## Qué se tocó

<!-- Lista de archivos o módulos. -->

## Criterios de terminación

Son los criterios reales de este proyecto, no una lista genérica. Cada uno se
comprueba solo en la integración continua: si falla, el envío sale en rojo.

- [ ] **Compila sin errores.** El backend importa y el frontend construye.
- [ ] **Las pruebas pasan y la cobertura se mantiene.** `pytest` en verde con
      `fail_under = 95` en `backend/pyproject.toml`; `vitest` en verde en el
      frontend.
- [ ] **El estilo pasa.** `ruff check` y `black --check` sobre `src/`,
      `pruebas/` y `alembic/`; `eslint` sobre `frontend/src`.
- [ ] **El dominio sigue limpio.** `pruebas/test_dominio_sin_frameworks.py`
      en verde: ningún módulo de `backend/src/domain/` importa FastAPI,
      SQLAlchemy, GeoAlchemy2, psycopg, Alembic, Pydantic ni un cliente HTTP.
- [ ] **Los tipos pasan.** `tsc --noEmit` en el frontend.
- [ ] **Commits semánticos en español**, con la brecha entre corchetes cuando
      corresponda.
- [ ] **Documentación al día.** Si el cambio contradice algo escrito en
      `docs/`, se corrige en este mismo envío.

## Revisión

<!-- Quién revisa. El autor no puede aprobar su propia propuesta. -->

## Evidencia

<!-- Captura, enlace a la ejecución en verde de Actions, o lo que corresponda. -->
