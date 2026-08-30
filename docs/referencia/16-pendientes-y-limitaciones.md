# 16 — Pendientes y limitaciones

**Qué explica este archivo:** lo que no está hecho, lo que **no se puede hacer**
con los datos que existen, y las ideas descartadas con su motivo.

Si vas a añadir algo al proyecto, **mira aquí antes**: puede que ya esté
decidido que no se hace, y por qué.

---

## Lo que NO se puede hacer, y no es culpa del código

Estas cuatro no se arreglan programando. Son límites de la realidad.

### 1. No existe ninguna fuente de tarifas de transporte

Ni el MINCETUR, ni el gobierno regional, ni las municipalidades publican
precios de combi, colectivo o taxi del valle.

**Qué se hace:** estimar con una fórmula documentada, con rango, fecha y la
palabra «aprox.» siempre visible.

**Qué haría falta para arreglarlo:** trabajo de campo. Alguien recorriendo
rutas y anotando precios.

### 2. El 29 % de los recursos no tiene horario

Ni en el CSV ni en su ficha web. **Qué se hace:** el recurso se queda sin
horario y el itinerario avisa de que no puede garantizar que esté abierto.

### 3. Ocho de las 36 fiestas no precisan su fecha

Su ficha cuenta qué es la fiesta pero no cuándo. Cuatro son **carnavales**, que
son móviles y se atan a la Pascua.

**Qué se hace:** se dice que la ficha no la precisa y se enlaza a ella.

> **Nota para el futuro:** la tabla `festividad` sí calcula los Carnavales con
> el algoritmo de la Pascua. Cruzar esos cuatro con el calendario cerraría el
> hueco, pero mezcla dos fuentes y habría que decidir cuál manda cuando
> discrepen. La ficha de la Tunantada dice «18, 19 y 20 de enero» y nuestra
> tabla dice «20 al 30». **No coinciden.**

### 4. La capacidad de los prestadores reales no está publicada

El directorio del MINCETUR da RUC, categoría y contacto, pero no cuántas plazas
tiene un hotel un sábado. **Qué se hace:** no se les inventa. Se enlaza a su
teléfono para que el visitante pregunte.

---

## Limitaciones de volumen

Con los datos de demostración: **5 valoraciones, 3 itinerarios, 1 solicitud**.

Los indicadores funcionan, pero **casi nada es estadísticamente sólido**. El
tablero lo avisa antes que los números.

**Esto no se arregla generando datos falsos.** Se arregla con uso real.

---

## Lo que no está implementado

### Ideas del plan que quedaron fuera

Del plan de trabajo, sección «Ideas opcionales». **Ninguna está hecha.**

#### Backend

| Idea | Por qué valdría la pena |
|---|---|
| **Exportar a PDF y `.ics`** | El visitante se lleva el itinerario. Probablemente lo más útil de esta lista |
| **Modo sin conexión** | La conectividad limitada es una restricción declarada del proyecto |
| **Notificar al proveedor por correo** | Hoy tiene que entrar a mirar si hay solicitudes |
| **Registro de auditoría del catálogo** | Quién validó qué y cuándo. Refuerza el argumento DataOps |
| **Instantáneas por `fecha_corte`** | Comparar versiones del inventario en el tiempo |
| **Métricas anónimas de uso** | Alimentaría los indicadores con datos reales en vez de estimados |
| **Limitación de peticiones** | Que una demostración pública no tumbe el servidor |
| **Caché de rutas calculadas** | *(Parcialmente hecho: la red vial se cachea en disco)* |

#### Frontend

| Idea | Por qué valdría la pena |
|---|---|
| **Comparar dos itinerarios lado a lado** | Ayuda a decidir y se ve muy bien en la exposición |
| **Compartir por WhatsApp** | Es como se comparten planes en Perú |
| **Modo «tengo poco tiempo»** | Un botón, un día, sin preguntar nada |
| **Recorrido guiado de bienvenida** | Tres pasos con las mascotas animadas |

### Ideas del plan que SÍ se hicieron

Aviso de altitud · esfuerzo físico del día · etiqueta «hoy hay fiesta» ·
agrupamiento de marcadores · cargadores esqueleto · compartir por enlace ·
filtro de accesibilidad · caché de rutas.

---

## Deuda técnica conocida

| Deuda | Impacto | Coste de arreglarlo |
|---|---|---|
| **`descripcion_en` está vacía** en los 295 | En inglés se cae a la española | Traducir 295 textos, o conectar un traductor |
| **Los servicios tienen una sola `descripcion`** | Las de los proveedores no se traducen | Una columna más y un campo en el formulario. Es decisión de producto |
| **`registro_de_evidencia` sin usar** | No hay histórico del tablero | Un guion programado que guarde una instantánea |
| **El asistente tarda 25–40 s** | Malo en una demostración en vivo | Una GPU, o un modelo más pequeño con menos calidad |
| **`tarifa_transporte` vacía** | Los costos se estiman siempre | Ver limitación 1 |

---

## Lo prohibido — no lo hagas

Del plan de trabajo. **No son sugerencias.**

| Prohibido | Por qué |
|---|---|
| **Inventar** atractivos, tarifas, horarios o estadísticas | Es el eje del proyecto |
| **Servicios de nube de pago** | Restricción del proyecto |
| **Implementar MLOps** | Ver [01](01-vision-y-contexto.md). Rompería la coherencia de los dos documentos entregados |
| **Realidad aumentada** | Fuera de alcance |
| **Microservicios** | Ver [02](02-arquitectura.md) |
| **Crear ramas de git** | Todo va a `main` |
| **Avanzar de fase sin autorización** | Regla de trabajo |

Y una que no está en el plan pero se ganó a pulso:

| Prohibido | Por qué |
|---|---|
| **Escribir «la fuente no publica X» sin comprobarlo** | Estuvo seis fases siendo falso. Ver [15](15-historial-de-fallos.md) |

---

## Si vas a añadir algo

1. **Mira si está en «lo prohibido».**
2. **Mira si ya hay una nota** en `docs/decisiones/` que lo descarte.
3. Si toca IA, **necesita alternativa por reglas** e interruptor.
4. Si toca datos, **la fuente tiene que citarse** en la propia fila.
5. Si emite un aviso, **código y parámetros**, nunca una frase.
6. Añade pruebas. Una fase no está hecha si no pasan.
7. **Actualiza el archivo de `docs/referencia/` que corresponda.**

---

## El estado, para no tener que buscarlo

| | |
|---|---|
| Fases | **8 de 8** completadas |
| Commits | 98, todos en `main`, 0 por empujar |
| Pruebas | 549 backend (73 %) + 148 frontend |
| Calidad | ruff, black, eslint, prettier, tsc — **limpios** |
| Endpoints | 43, ninguno sin resumen |
| Idiomas | 2, 581 claves simétricas |
| Modo oscuro | 0 fallos de contraste en 9 rutas |
| SonarQube | Preparado, **NO ejecutado** |

---

## Relacionado

- [01 — Visión y contexto](01-vision-y-contexto.md)
- [06 — Fuentes de datos](06-fuentes-de-datos.md)
- [15 — Historial de fallos](15-historial-de-fallos.md)
