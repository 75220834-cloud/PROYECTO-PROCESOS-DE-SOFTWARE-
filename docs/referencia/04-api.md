# 04 — La API

**Qué explica este archivo:** los 43 endpoints agrupados por área, cómo se
autentica, qué permisos hay, qué forma tienen los errores y cómo viajan los
avisos.

La documentación viva está en **`http://localhost:8000/docs`**, que FastAPI
genera sola desde el código. Este archivo cuenta lo que ahí no se ve: las
decisiones de diseño.

---

## Los 43 endpoints

### Salud (2)

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/` | Mensaje de bienvenida |
| `GET` | `/api/salud` | Estado de la API, la base de datos y Ollama |

`/api/salud` es lo primero que hay que mirar cuando algo no va: dice cuál de
los tres componentes está caído.

### Autenticación (3)

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/api/autenticacion/registro` | Crea una cuenta |
| `POST` | `/api/autenticacion/sesion` | Inicia sesión y devuelve el token |
| `GET` | `/api/autenticacion/yo` | Datos de la sesión actual |

**Detalle de seguridad:** el acceso con correo inexistente y el acceso con
contraseña incorrecta devuelven **exactamente el mismo error**. Distinguirlos
permitiría averiguar qué correos están registrados.

### Catálogo (5) — Incremento 1

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/recursos` | Lista con filtros y paginación |
| `GET` | `/api/recursos/filtros` | Valores para los desplegables |
| `GET` | `/api/recursos/mapa` | GeoJSON para pintar el mapa |
| `GET` | `/api/recursos/{id}` | Ficha completa |
| `GET` | `/api/indicadores/catalogo` | **Indicador 1** |

`/mapa` devuelve GeoJSON y no la misma lista: el mapa solo necesita
coordenadas y cuatro campos, y mandar la ficha entera de 234 recursos sería
mover diez veces más datos de los que se pintan.

### Preferencias (6) — Incremento 2

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/preferencias/opciones` | Valores válidos para el asistente |
| `POST` | `/api/preferencias` | Guarda una preferencia |
| `GET` | `/api/preferencias` | Las mías |
| `GET` | `/api/preferencias/{id}` | Consulta una |
| `PUT` | `/api/preferencias/{id}` | Actualiza |
| `POST` | `/api/preferencias/{id}/reclamar` | La asocia a tu cuenta |

**`/reclamar` es la pieza que hace posible la promesa** de que no hace falta
cuenta: armas el viaje sin registrarte y, si luego te registras, te lo llevas.

### Recomendaciones y calendario (3) — Incremento 3

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/api/recomendaciones` | Recomienda recursos para una preferencia |
| `GET` | `/api/calendario/{anio}` | Festividades del valle en un año |
| `GET` | `/api/calendario/dia/{fecha}` | Qué ocurre un día concreto |

Es `POST` y no `GET` porque el cuerpo lleva la preferencia y el límite, y
porque el cálculo no es trivial: no es una consulta cacheable.

### Itinerarios (4) — Incremento 4

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/api/itinerarios` | Arma el itinerario de un día |
| `POST` | `/api/itinerarios/reordenar` | Recalcula con el orden que eligió el visitante |
| `GET` | `/api/itinerarios` | Los míos guardados |
| `GET` | `/api/itinerarios/{id}` | Recupera uno |

**`/reordenar` no bloquea al visitante.** En el camino automático el
presupuesto es una restricción dura; aquí manda la persona, así que si su orden
se pasa de presupuesto **se le avisa, no se le impide**. Bloquear un orden que
alguien ha pedido a propósito sería tratarle como si no supiera lo que hace.

### Coordinación (14) — Incrementos 5 y 6

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/proveedores` | **Directorio de los 162 prestadores reales** |
| `GET` | `/api/proveedores/mio` | Mi ficha de proveedor |
| `GET` | `/api/proveedores/mio/servicios` | Mis servicios |
| `GET` | `/api/servicios` | Servicios ofrecidos |
| `POST` | `/api/servicios` | Publica uno (solo proveedores) |
| `GET` | `/api/servicios/{id}` | Ficha de un servicio |
| `POST` | `/api/servicios/{id}/disponibilidad` | **¿Se puede pedir así?** |
| `GET` | `/api/servicios/{id}/plazas` | Plazas libres en una fecha |
| `POST` | `/api/servicios/{id}/tramos` | Publica un tramo horario |
| `POST` | `/api/solicitudes` | Pide un servicio |
| `GET` | `/api/solicitudes` | Las que puedes ver |
| `GET` | `/api/solicitudes/{id}` | Una con su historial completo |
| `POST` | `/api/solicitudes/{id}/estado` | Mueve el estado |
| `GET` | `/api/indicadores/coordinacion` | **Indicador 5** |

**`/disponibilidad` es lo que cierra la brecha 5.** Devuelve **todos** los
motivos por los que no se puede pedir, no el primero: decirle a alguien «no hay
sitio» y, cuando lo arregla, «además llegas tarde», es la clase de trato que
hace abandonar un formulario.

### Valoraciones (4) — Incremento 6

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/api/valoraciones` | Valora una experiencia |
| `GET` | `/api/valoraciones` | Las de un itinerario |
| `GET` | `/api/indicadores/evidencia` | **Tablero del gestor** |
| `GET` | `/api/indicadores/tablero` | **Los seis indicadores juntos** |

Valorar **funciona sin cuenta**. Obligar a registrarse al final del viaje
perdería justo la valoración que se quiere recoger.

### Asistente (2) — Fase 7

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/asistente/estado` | ¿Está Ollama disponible? |
| `POST` | `/api/asistente/mensaje` | Una vuelta de conversación |

**Si Ollama no está, `/mensaje` devuelve 200**, no un error, con
`esta_disponible: false` y el motivo. No es un fallo del servidor: es una
capacidad opcional que falta, y la interfaz tiene que poder ofrecer el
formulario sin alarmar.

---

## Autenticación y permisos

**JWT (HS256)** en la cabecera `Authorization: Bearer <token>`. La clave sale
de `CLAVE_SECRETA` del `.env`; el token dura lo que diga
`MINUTOS_EXPIRACION_TOKEN` (por defecto 1 440, un día).

Tres formas de dependencia, según lo que exija el endpoint:

| Dependencia | Comportamiento |
|---|---|
| `UsuarioRequerido` | Sin token válido, 401. |
| `UsuarioOpcional` | Funciona con y sin sesión. **Es la que hace posible usar la app sin cuenta.** |
| — | Endpoints públicos: catálogo, calendario, salud. |

### La regla de acceso a lo que tiene dueño

Una preferencia o un itinerario **sin dueño** los ve cualquiera que tenga su
identificador. Con dueño, solo su dueño.

**Y se responde 404, no 403.** Un 403 confirmaría que ese identificador existe;
un 404 no dice nada. Es deliberado y está en el código con ese comentario.

### Roles

| Rol | Qué puede |
|---|---|
| `visitante` | Guardar viajes, pedir servicios, valorar |
| `proveedor` | Además: publicar servicios y responder solicitudes |
| `operador` | Ver todas las solicitudes |
| `gestor` | El panel: evidencia e indicadores |
| `administrador` | Todo |

---

## La forma de los errores

Todos los errores propios viajan como un **código**, no como una frase:

```json
{ "detail": { "codigo": "credenciales_incorrectas" } }
```

La interfaz lo traduce. Antes eran frases en español, y por eso la aplicación
en inglés mostraba errores en español. Ver [11](11-idiomas-y-avisos.md).

El 409 de coordinación lleva además todos los motivos:

```json
{
  "detail": {
    "codigo": "servicio_no_disponible",
    "motivos": [
      { "codigo": "falta_antelacion", "parametros": { "horas": 48 } },
      { "codigo": "sin_plazas_suficientes",
        "parametros": { "libres": 2, "cupo": 12, "pedidas": 6 } }
    ]
  }
}
```

Los errores de **Pydantic** siguen viniendo redactados por la biblioteca; la
interfaz los deja pasar tal cual porque no hay clave que buscar.

| Código HTTP | Cuándo |
|---|---|
| 200 / 201 | Bien |
| 401 | Sin token o inválido |
| 403 | Rol insuficiente |
| 404 | No existe, **o existe pero no es tuyo** |
| 409 | Conflicto: ya valoraste, servicio no disponible |
| 422 | Validación de Pydantic |

---

## Los avisos

Cualquier endpoint que quiera decirle algo al visitante devuelve

```json
{ "codigo": "altitud", "parametros": { "metros": 3706 } }
```

Son **67 códigos** declarados en `app/servicios/avisos.py`. La interfaz los
convierte en frase con i18next, lo que además resuelve los plurales.

Aparecen en: `avisos` (itinerario, recomendaciones, evidencia), `motivo`
(afluencia, descarte), `motivos` (disponibilidad), `detalle` y
`sin_dato_porque` (indicadores).

---

## Cómo probar la API a mano

```bash
curl http://localhost:8000/api/salud
```

```bash
curl -X POST http://localhost:8000/api/autenticacion/sesion -H "Content-Type: application/json" -d "{\"correo\":\"gestor@rutavivamantaro.pe\",\"contrasena\":\"RutaViva2026\"}"
```

O más cómodo: abre `http://localhost:8000/docs`, que permite ejecutar cada
endpoint desde el navegador con el token puesto.

---

## Relacionado

- [05 — Frontend](05-frontend.md)
- [11 — Idiomas y avisos](11-idiomas-y-avisos.md)
- [13 — Instalación y operación](13-instalacion-y-operacion.md)
