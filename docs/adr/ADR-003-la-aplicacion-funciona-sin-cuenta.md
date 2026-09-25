# ADR-003 — La aplicación funciona sin cuenta

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Incremento** | 2 — usuarios y preferencias (brecha 3) |
| **Atributo de calidad principal** | **Usabilidad** (accesibilidad del proceso) |
| **Atributos secundarios** | Seguridad (con una consecuencia negativa declarada) |
| **Nota de origen** | [`2026-08-29-la-aplicacion-funciona-sin-cuenta.md`](../decisiones/2026-08-29-la-aplicacion-funciona-sin-cuenta.md) |

---

## Contexto

El Incremento 2 introduce usuarios y autenticación. La forma habitual de
montarlo —y la más fácil— es exigir cuenta antes de dejar hacer nada.

Pero el proyecto declara la **accesibilidad del proceso** como objetivo, y la
brecha 3 habla de **registrar las preferencias**, no de registrar personas.

## Decisión

**El visitante completa el asistente de seis pasos y obtiene su viaje sin
registrarse. La cuenta se ofrece al final, y solo para guardarlo.**

Mecánica interna:

1. La tabla `preferencia_viaje` admite `usuario_id` **nulo**.
2. Al guardar sin sesión, el backend devuelve el identificador y el frontend lo
   conserva en `localStorage` bajo la clave `rutaviva.preferencia`. Ese
   identificador es lo único que permite volver a la preferencia.
3. Si el visitante crea cuenta, `POST /api/preferencias/{id}/reclamar` asocia la
   preferencia a la cuenta nueva. **No hay que repetir el asistente.**
4. Una preferencia que ya tiene dueño **responde 404, no 403**, para no
   confirmar que ese identificador existe.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Exigir cuenta desde el principio** | Es la forma más rápida de perder al visitante: se le pide algo antes de haberle dado nada. |
| **Guardar la preferencia solo en el navegador** | No se podría medir el indicador del incremento, ni recuperar el viaje desde otro dispositivo, ni usarla en la recomendación del servidor. |
| **Crear una cuenta «invitada» automática** | Genera cuentas basura y obliga a decidir cuándo borrarlas. Un `usuario_id` nulo dice lo mismo sin inventar una entidad. |

## Consecuencias

**Positivas**

- Armar un viaje, ver recomendaciones, construir el itinerario y valorar **no
  requieren cuenta**. Es una promesa comprobable del proyecto.
- El indicador del incremento sigue siendo medible, porque la preferencia vive
  en el servidor.

**Negativas, conscientes y declaradas**

- **Una preferencia sin dueño es accesible para quien tenga su identificador.**
  Se acepta porque no contiene datos personales: fechas, presupuesto, distrito
  e intereses.
- **Los identificadores son secuenciales**, así que alguien podría recorrerlos
  y leer preferencias anónimas ajenas. Queda anotado: **si en el futuro
  guardaran algo sensible, habría que pasar a identificadores aleatorios
  (UUID)**. Es deuda de seguridad conocida, no un descubrimiento pendiente.
- En cuanto una preferencia tiene dueño, solo su dueño la ve.

## Cómo verificarlo

```bash
cd backend && .venv/Scripts/python.exe -m pytest pruebas/test_rutas_preferencias.py -v
```

- Backend: `test_se_puede_guardar_sin_haber_iniciado_sesion` y la clase
  `TestReclamarPreferencia`.
- Frontend: «recorre los seis pasos sin haber iniciado sesión y guarda la
  preferencia», en `AsistentePreferencias.prueba.tsx`.

Si alguna de esas pruebas falla, la aplicación ha empezado a exigir cuenta para
algo que prometió que no la necesita.

## Relacionado

- [ADR-009 — Las reglas de estado y permisos viven en el servicio](ADR-009-las-reglas-de-estado-y-permisos-viven-en-el-servicio.md)
