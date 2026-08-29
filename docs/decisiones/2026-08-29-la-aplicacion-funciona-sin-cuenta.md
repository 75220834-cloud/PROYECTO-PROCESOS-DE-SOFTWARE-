# La aplicación funciona sin cuenta

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** todo el recorrido del visitante

## Contexto

El Incremento 2 introduce usuarios y autenticación. La forma habitual de
montarlo —y la más fácil— es exigir una cuenta antes de dejar hacer nada: el
visitante entra, se le pide correo y contraseña, y solo entonces empieza.

El proyecto declara la accesibilidad del proceso como objetivo, y la brecha 3
habla de **registrar las preferencias**, no de registrar personas.

## Decisión

**El visitante completa todo el asistente y obtiene su viaje sin registrarse.
La cuenta se ofrece al final, y solo para guardarlo.**

### Cómo funciona por dentro

1. La tabla `preferencia_viaje` admite `usuario_id` **nulo**.
2. Al guardar sin sesión, el backend devuelve el identificador y el frontend
   lo conserva en el navegador (`localStorage`, clave
   `rutaviva.preferencia`). Ese identificador es lo único que permite volver
   a la preferencia, y solo lo tiene esa persona.
3. Si el visitante decide crear una cuenta, el proveedor de sesión llama a
   `POST /api/preferencias/{id}/reclamar`, que asocia la preferencia a la
   cuenta recién creada. **No hay que repetir el asistente.**
4. Una preferencia que ya tiene dueño no se puede reclamar: responde 404, no
   403, para no confirmar que ese identificador existe.

### Consecuencias en la seguridad

Una preferencia sin dueño es accesible para quien tenga su identificador.
Es una decisión consciente, no un descuido:

- No contiene datos personales. Son fechas, un presupuesto, un distrito y una
  lista de intereses.
- Los identificadores son secuenciales, así que alguien podría recorrerlos y
  leer preferencias anónimas ajenas. **Si en el futuro guardaran algo
  sensible, habría que cambiarlos por identificadores aleatorios (UUID).**
  Queda anotado aquí para no descubrirlo tarde.
- En cuanto una preferencia tiene dueño, solo su dueño la ve.

## Alternativas descartadas

| Alternativa | Por qué se descartó |
|---|---|
| Exigir cuenta desde el principio | Es la forma más rápida de perder al visitante: se le pide algo antes de haberle dado nada. |
| Guardar la preferencia **solo** en el navegador | No se podría medir el indicador del incremento, ni recuperar el viaje desde otro dispositivo, ni usarla en la recomendación del servidor. |
| Crear una cuenta «invitada» automática | Genera cuentas basura y obliga a decidir cuándo borrarlas. Un `usuario_id` nulo dice lo mismo sin inventar nada. |

## Cómo comprobarlo

- Backend: `test_se_puede_guardar_sin_haber_iniciado_sesion` y toda la clase
  `TestReclamarPreferencia`, en `backend/pruebas/test_rutas_preferencias.py`.
- Frontend: `recorre los seis pasos sin haber iniciado sesión y guarda la
  preferencia`, en
  `frontend/src/paginas/__pruebas__/AsistentePreferencias.prueba.tsx`.

Si alguna de esas pruebas falla, la aplicación ha empezado a exigir cuenta
para algo que prometió que no la necesita.
