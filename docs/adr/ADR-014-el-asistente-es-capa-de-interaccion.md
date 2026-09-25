# ADR-014 — El asistente conversacional es capa de interacción, y no puede inventar datos por arquitectura

| | |
|---|---|
| **Estado** | Aceptada e implementada |
| **Fecha** | 29 de agosto de 2026 (Fase 7) |
| **Alcance** | `app/ia/asistente.py`, `app/rutas/asistente.py`, `PanelConversacion.tsx` |
| **Atributo de calidad principal** | **Disponibilidad** (si el asistente cae, no se pierde ninguna capacidad) |
| **Atributos secundarios** | Fiabilidad (no inventa), rendimiento (25–40 s por respuesta) |
| **Nota de origen** | [`2026-08-29-el-asistente-no-cierra-ninguna-brecha.md`](../decisiones/2026-08-29-el-asistente-no-cierra-ninguna-brecha.md) |

---

## Contexto

Un asistente con un modelo de lenguaje detrás es la parte más vistosa del
proyecto y la más fácil de vender como «la innovación». El proyecto ya tiene dos
documentos académicos entregados que describen seis incrementos y siete brechas,
y ninguno menciona un asistente.

## Decisión

**El asistente se presenta como capa de interacción, no como funcionalidad
nueva. No se le asigna ninguna brecha ni ningún indicador.**

Es una forma alternativa de llegar a lo que ya construyeron los Incrementos 2, 3
y 4. Todo lo que permite pedir hablando **se puede pedir también por formulario**.

La comprobación es estructural: la interfaz muestra un enlace al formulario
justamente cuando el asistente no está disponible. **Si el asistente cerrara una
brecha, ese enlace no podría existir.**

### Cómo se garantiza que no inventa datos

No descansa en la buena voluntad del modelo.

**La arquitectura, primero.** El modelo **no sabe nada** del Valle del Mantaro. Su
papel es: leer lo que pide el visitante, elegir qué función del backend responde, y
redactar con **lo que devolvió esa función**. Las cinco funciones
—`buscar_recursos`, `crear_preferencia`, `generar_recomendaciones`,
`construir_itinerario`, `consultar_afluencia`— consultan la base de datos, y el
modelo solo ve su resultado en JSON.

Si se pregunta por un lugar que no está, la búsqueda devuelve cero y en el mismo
JSON viaja un aviso escrito en palabras:

> «No hay ningún recurso con esos criterios en el Inventario Nacional de Recursos
> Turísticos del MINCETUR. NO inventes uno y NO propongas ningún otro lugar de
> memoria.»

**Las instrucciones, después.** Seis reglas en el mensaje de sistema. Las dos
primeras: no inventar, y **no afirmar que algo no está en el catálogo sin haberlo
consultado**.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Presentarlo como la innovación del proyecto** | Sería exagerar: si se apaga Ollama **no se pierde ninguna capacidad**, solo una manera cómoda de pedir las cosas. Y contradiría los dos documentos entregados. |
| **Asignarle una brecha propia** | Ninguna de las siete brechas del análisis habla de interacción conversacional. Inventar una octava para justificarlo sería al revés de como se hace. |
| **Dejar que el modelo responda con su conocimiento** (sin llamada a funciones) | Es exactamente el escenario en que inventa atractivos que no existen. La llamada a funciones es lo que lo hace imposible. |
| **Un modelo en la nube** (más rápido y mejor) | Servicios de nube de pago están prohibidos por el plan de trabajo, y los datos saldrían de la máquina. |
| **Aplicar el filtro de categoría aunque sea desconocido** | Se probó y fue peor: la consulta salía vacía y **el vacío empuja al modelo a rellenar el hueco**. Ahora un filtro desconocido **se ignora**: devolver de más es un problema menor que devolver nada. |

## Consecuencias

**Positivas**

- El sistema es honesto sobre qué aporta el asistente.
- **La interfaz enseña qué funciones se ejecutaron**, lo que hace la conversación
  auditable: se puede comprobar que consultó el catálogo antes de afirmar.
- Puede quedar desactivado en producción sin perder funcionalidad — que es
  exactamente lo que ocurriría en un despliegue real, porque el modelo pesa 4,4 GB.

**Negativas, declaradas y no resueltas**

- **Tarda 25–40 s por respuesta** en un portátil sin GPU. Es el coste de correr un
  modelo de 7 000 millones de parámetros en CPU. No se arregla sin cambiar de
  máquina o de modelo.
- **El modelo puede equivocarse eligiendo la función.** Que no invente datos no
  significa que elija bien: puede buscar por distrito cuando debía buscar por
  texto, y devolver datos reales que no responden a la pregunta. La lista de
  funciones ejecutadas existe para que eso se vea.
- **No hay pruebas automáticas del modelo.** Las 33 pruebas cubren las funciones
  del backend, que son la frontera entre el modelo y los datos. Fijar con un
  `assert` lo que responde un modelo de lenguaje exigiría fijar semilla y versión,
  y aun así sería frágil.

### Los tres fallos que encontró usarlo, y que ninguna prueba cazó

**1. Acertar por casualidad.** A la primera pregunta —el «Palacio de la Cultura de
Jauja», que no existe— respondió que no lo encontraba. Parecía perfecto: **la lista
de funciones ejecutadas venía vacía**. No había consultado nada. Dijo la verdad por
casualidad, y con la misma seguridad habría podido decir lo contrario. Se añadió la
regla 2.

**2. Negar lo que sí existe.** A «¿qué puedo visitar en Concepción?» respondió que
no había recursos. **Hay trece.** El modelo escribe «CONCEPCIÓN» con tilde y el
inventario la guarda sin ella. **Es el peor fallo posible aquí: no es inventar, es
negar, y con aplomo.** Corregido normalizando con `unaccent`.

**3. El vacío empuja a inventar.** A «busca el Convento de Ocopa» dijo que no
estaba y se ofreció a recomendar «el Convento de San Francisco en Huancayo», que se
sacó de la memoria. Dos causas: se buscaba la frase literal («Convento De Santa
Rosa De Ocopa» no casa como subcadena) y el modelo mandó un código de *interés* como
categoría del MINCETUR.

### Verificación cruzada contra la base de datos

| Pregunta | Funciones ejecutadas | Resultado |
|---|---|---|
| Palacio de la Cultura de Jauja | `buscar_recursos(distrito=JAUJA, texto=Palacio de la Cultura)` | 0 resultados, lo rechaza, **no propone alternativa** |
| ¿Qué visitar en Concepción? | `buscar_recursos(distrito=CONCEPCIÓN)` | 8 lugares, **los 8 existen** y están validados |
| Busca el Convento de Ocopa | `buscar_recursos(texto=Convento de Ocopa, ...)` | Lo encuentra; distrito, provincia y altitud (3384 msnm) coinciden con la fila |

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_asistente.py -v
```

## Relacionado

- [ADR-013 — Los avisos viajan como código y parámetros](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md)
- [ADR-015 — Integración continua](ADR-015-integracion-continua-y-umbral-de-cobertura.md)
