---
name: Solicitud de Cambio (RFC)
about: Registra formalmente un cambio antes de tocar el código, con su impacto y su riesgo
title: "[RFC] "
labels: ["change-request", "pendiente-evaluacion"]
assignees: ''
---

## 1. Descripción del cambio

**Módulo afectado:**
<!-- backend/src/domain, backend/src/adapters, frontend/src, docs/, .github/… -->

**Tipo de cambio:**
<!-- Marca una -->
- [ ] Correctivo — arregla algo que está mal
- [ ] Evolutivo — añade capacidad nueva
- [ ] Adaptativo — responde a un cambio del entorno
- [ ] Perfectivo — mejora algo que ya funciona

**Justificación:**
<!-- Por qué hace falta. Si viene de un hallazgo de revisión, cítalo. -->

## 2. Análisis de impacto

**Archivos que toca:**
<!-- Lista concreta, no «varios». -->

**Esfuerzo estimado:**
<!-- En horas o en puntos de historia. -->

**Riesgo:**
<!-- Marca uno y explica por qué -->
- [ ] Bajo — no toca código que se ejecute en producción
- [ ] Medio — toca código cubierto por pruebas
- [ ] Alto — toca el despliegue, la base de datos o código sin cobertura

**Qué se rompe si sale mal:**
<!-- Sé concreto. «Nada» solo vale si puedes justificarlo. -->

## 3. Criterios de aceptación

<!-- En Dado-Cuando-Entonces cuando aplique. El cambio no está hecho
     hasta que estos criterios se puedan comprobar. -->

- [ ]
- [ ]

## 4. Evidencia esperada

<!-- Qué habrá que poder enseñar: una captura, una ejecución en verde,
     un archivo nuevo en el repositorio. -->
