# ADR-012 — «Mantaro Moderno» es la fuente única del estilo, y las tipografías se autoalojan

| | |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 29 de agosto de 2026 |
| **Alcance** | `frontend/src/estilos/`, todos los componentes de la interfaz |
| **Atributo de calidad principal** | **Usabilidad** (coherencia visual y accesibilidad) |
| **Atributos secundarios** | Disponibilidad (funciona sin internet), mantenibilidad (fuente única) |
| **Nota de origen** | [`2026-08-29-sistema-de-diseno-mantaro-moderno.md`](../decisiones/2026-08-29-sistema-de-diseno-mantaro-moderno.md) |

---

## Contexto

Durante la Fase 0 la interfaz se construyó con una paleta inventada sobre la
marcha (verde valle, tierra, cielo, pizarra), porque el diseño previsto todavía no
se conocía.

Después se comprobó que el equipo **ya tenía el diseño completo** generado en
Stitch: 26 pantallas (escritorio y móvil) y un sistema de diseño formal llamado
**Mantaro Moderno**, con paleta, tipografías, radios, espaciado y reglas de
componente.

Mantener dos paletas distintas habría significado que el código y la
documentación visual del proyecto **se contradijeran** — justo lo que el proyecto
declara como riesgo.

## Decisión

**El sistema de diseño de Stitch manda.** El código copia sus valores; no los
inventa ni los ajusta por gusto. Cualquier cambio de color, tipografía o radio se
hace **primero en Stitch** y luego se traslada a `frontend/src/estilos/index.css`.

### Lo adoptado

| Elemento | Valor |
|---|---|
| Primario (terracota) | `#a23919` — la tierra y la cerámica local |
| Secundario (verde valle) | `#27695c` — los campos del Mantaro |
| Terciario (ocre) | `#745800` — el sol y la textilería wanka |
| Superficie | `#fff8f5` — crema cálida, **nunca blanco puro** |
| Fondo en modo oscuro | `#16110f` — marrón «chullpi», no gris neutro |
| Tipografía de títulos | Manrope |
| Tipografía de cuerpo | Be Vietnam Pro |
| Radios | 0,25 / 0,5 / 1 / 1,5 rem |
| Ancho máximo | 1280 px |

Las sombras llevan un matiz de terracota (`rgba(212, 93, 58, 0.08)`) en lugar de
gris neutro: es lo que conserva la calidez que pide el sistema.

### Tres decisiones derivadas

**1. Los tokens se nombran en español.** `--color-primario`,
`--color-superficie`, `--color-sobre-superficie`. Stitch los llama `primary`,
`surface`, `on-surface` (nomenclatura de Material 3); la tabla de equivalencias
está comentada en la cabecera de `index.css`. Se eligió el español por la regla de
idioma del proyecto y porque las clases resultantes (`bg-superficie`,
`text-primario`) se leen igual de bien.

**2. Las tipografías se autoalojan, no se cargan de Google Fonts.** Se instalan
como paquetes (`@fontsource-variable/manrope`, `@fontsource/be-vietnam-pro`) y se
empaquetan con la aplicación. **El motivo es concreto:** el proyecto declara la
*conectividad limitada* como restricción, y la aplicación se expone en clase. Si
el aula no tiene internet, con Google Fonts la tipografía se degrada a la del
sistema y **el diseño se rompe justo durante la defensa**. Cuesta ~200 kB.

**3. La greca wanka es un acento, nunca un fondo.** Implementada como la utilidad
`greca-wanka`: franja de rombos al **18 % de opacidad**, como borde bajo el
encabezado y encima del pie. El sistema de diseño es explícito en que estos
patrones deben ser *«acentos arquitectónicos, nunca decoración abrumadora»*.

## Alternativas consideradas y por qué se descartaron

| Alternativa | Por qué se descartó |
|---|---|
| **Mantener la paleta inventada de la Fase 0** | El código y el diseño entregado se contradirían. Es riesgo declarado del proyecto. |
| **Cargar las tipografías de Google Fonts** | Es lo más cómodo y lo más frágil: sin internet en el aula, el diseño se rompe en la defensa. |
| **Nombrar los tokens en inglés, como Stitch** | Contradice la regla de idioma. Se resolvió con una tabla de equivalencias comentada, que da lo mejor de las dos. |
| **Usar la greca como fondo de sección** | El propio sistema de diseño lo prohíbe: «acentos, nunca decoración abrumadora». |
| **Un framework de componentes de terceros** (Material UI, shadcn) | Traería su propio sistema de diseño, que habría que doblegar al de Stitch. Tailwind + tokens propios es menos código y más fiel. |

## Consecuencias

**Positivas**

- Una sola fuente de verdad del estilo; cualquier discrepancia es un error
  localizable.
- **La aplicación se ve igual sin internet**, que es la condición real de la
  exposición.
- Modo oscuro con **0 fallos de contraste en 9 rutas**, medido.
- La hoja de estilos respeta `prefers-reduced-motion` desde el principio.

**Negativas, y asumidas**

- ~200 kB extra en el paquete por las tipografías autoalojadas.
- Cambiar un color exige tocar dos sitios (Stitch y el CSS), por diseño: el orden
  importa y evita que el código derive.
- **Quedan partes del diseño sin implementar**, por motivos declarados:
  1. Las **ilustraciones animadas** de fauna del valle (vizcacha, llama,
     picaflor, pato, trucha) requieren los recursos gráficos, que se exportarán de
     Stitch cuando estén cerrados.
  2. Las **secciones con fotografías** de los atractivos: poner imágenes de
     relleno contradiría la regla de honestidad con los datos.

## Relacionado

- [ADR-013 — Los avisos viajan como código y parámetros](ADR-013-los-avisos-viajan-como-codigo-y-parametros.md)
