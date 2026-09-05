# Documentación de referencia de RutaVivaMantaro

Esto es el **mapa completo del proyecto**. Está escrito para que nadie —ni una
persona nueva, ni yo en una sesión futura— tenga que volver a auditar 24 000
líneas de código para saber qué hay, cómo funciona y por qué se hizo así.

**Última actualización:** 4 de septiembre de 2026
**Estado del proyecto:** terminado (las 8 fases del plan, 0–7)

---

## Cómo usar esto según lo que necesites

### Si vas a redactar un documento académico

Lee en este orden: **01 → 09 → 10 → 06**. Ahí está el lenguaje del curso
—brechas, incrementos, indicadores— con los números reales y sus salvedades.
Para justificar una decisión técnica, salta a la nota correspondiente en
`docs/decisiones/`.

### Si eres yo retomando el proyecto

Lee **00 (este) → 02 → 03 → 16**. Con esos cuatro sabes dónde está todo, qué
decisiones ya están tomadas y qué queda pendiente. No hace falta leer código
para responder la mayoría de preguntas.

### Si te vas a defender oralmente

**14** es el guion, con las preguntas incómodas y su respuesta. **15** es el
historial de fallos, que es lo que demuestra que el proyecto se probó de
verdad. **10** son los indicadores con lo que cada uno NO dice.

### Si vas a tocar el código

**02 → 03 → 04 → 05 → 12**. Y antes de añadir nada, mira **16** por si ya está
decidido que no se hace. **17** dice qué comprueba la integración continua en
cada push, que es lo que se va a poner en rojo si algo se rompe.

---

## Los archivos

| # | Archivo | Qué explica |
|---|---|---|
| 00 | [00-INDICE.md](00-INDICE.md) | Este mapa. Qué hay en cada archivo y en qué orden leerlos según para qué. |
| 01 | [01-vision-y-contexto.md](01-vision-y-contexto.md) | Qué es el proyecto, para qué curso, qué problema resuelve, las 7 brechas del análisis y los 6 incrementos que las cierran. El **porqué** de todo lo demás. |
| 02 | [02-arquitectura.md](02-arquitectura.md) | Cómo está montado: capas, diagrama, qué tecnología se usó en cada una y por qué se eligió esa. Incluye lo que se descartó. |
| 03 | [03-modelo-de-datos.md](03-modelo-de-datos.md) | Las 17 tablas, su diagrama entidad-relación, qué guarda cada una y las decisiones de diseño que no son obvias. |
| 04 | [04-api.md](04-api.md) | Los 43 endpoints agrupados por área, cómo se autentica, qué forma tienen los errores y cómo viajan los avisos. |
| 05 | [05-frontend.md](05-frontend.md) | Las 12 pantallas, los 20 componentes, cómo se maneja el estado, el sistema de diseño y los dos idiomas. |
| 06 | [06-fuentes-de-datos.md](06-fuentes-de-datos.md) | De dónde sale **cada dato**: qué publica cada fuente, qué no, y qué se hace cuando falta. Es la base del argumento de honestidad. |
| 07 | [07-inteligencia-artificial.md](07-inteligencia-artificial.md) | Los cuatro usos de IA, sus alternativas por reglas, y las **mediciones** con las que se aceptó o rechazó cada modelo. |
| 08 | [08-asistente-conversacional.md](08-asistente-conversacional.md) | Cómo funciona el asistente con Ollama, por qué arquitectónicamente no puede inventar datos, y cómo demostrarlo. |
| 09 | [09-los-seis-incrementos.md](09-los-seis-incrementos.md) | Brecha por brecha: qué se construyó, dónde está el código, qué lo prueba y qué indicador lo mide. La **matriz de trazabilidad**. |
| 10 | [10-indicadores.md](10-indicadores.md) | Los 6 indicadores con su fórmula, su valor actual, cómo se calcula y **lo que cada uno no dice**. |
| 11 | [11-idiomas-y-avisos.md](11-idiomas-y-avisos.md) | Cómo se consiguió que la aplicación entera funcione en dos idiomas, incluidos los avisos que genera el backend. |
| 12 | [12-pruebas-y-calidad.md](12-pruebas-y-calidad.md) | Las 697 pruebas: qué cubre cada archivo, qué filosofía siguen y qué herramientas de calidad se ejecutan. |
| 13 | [13-instalacion-y-operacion.md](13-instalacion-y-operacion.md) | Cómo levantar todo desde cero, las cuentas de prueba, y qué hacer cuando algo falla. |
| 14 | [14-guion-de-defensa.md](14-guion-de-defensa.md) | Qué enseñar y en qué orden, y las preguntas incómodas con su respuesta honesta. |
| 15 | [15-historial-de-fallos.md](15-historial-de-fallos.md) | Todos los fallos encontrados, cómo se encontraron y cómo se arreglaron. Es lo que demuestra que esto se probó de verdad. |
| 16 | [16-pendientes-y-limitaciones.md](16-pendientes-y-limitaciones.md) | Lo que no está hecho, lo que no se puede hacer con los datos que hay, y las ideas descartadas con su motivo. |
| 17 | [17-integracion-y-despliegue.md](17-integracion-y-despliegue.md) | Cómo se comprueba el proyecto a mano y de forma automática, los dos procedimientos comparados, y qué haría falta para desplegarlo de verdad. |

---

## Qué hay fuera de esta carpeta, y por qué

Esta documentación cuenta **qué hay y cómo funciona**. El **porqué** de cada
decisión concreta vive donde se tomó, y se enlaza desde aquí:

| Carpeta | Qué contiene |
|---|---|
| `docs/decisiones/` | **15 notas**, una por decisión de proceso. Se escribieron en el momento de tomar cada una, con las mediciones delante. Reescribirlas ahora perdería matices. |
| `docs/indicadores/` | **6 notas**, una por indicador, con su medición del día y las pruebas que lo sostienen. |
| `README.md` | Cómo montar el proyecto desde cero. Es la puerta de entrada del repositorio, y no se duplica aquí: el archivo 13 lo resume y enlaza. |

Los propios archivos de código llevan la explicación de sus decisiones internas
en el docstring del módulo. Cuando esta documentación diga «ver
`servicios/ruteo.py`», es porque ahí está el detalle que no cabe aquí.

---

## Cómo mantener esto

Cuando algo cambie:

1. **Toca el archivo de esta carpeta que corresponda**, no crees uno nuevo.
2. Si la decisión es discutible, añade una nota en `docs/decisiones/` con la
   fecha y **la medición** que la sostiene. Una decisión sin número detrás no
   se puede defender.
3. Actualiza la fecha de arriba en este índice.

Los números de este documento —697 pruebas, 43 endpoints, 295 recursos— son de
la fecha de arriba. Si han pasado meses, compruébalos antes de citarlos en un
documento entregable:

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
```
