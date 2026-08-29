# El sistema de diseño «Mantaro Moderno» es la fuente única del estilo

**Fecha:** 29 de agosto de 2026
**Estado:** aceptada
**Afecta a:** `frontend/src/estilos/`, todos los componentes de la interfaz

## Contexto

Durante la Fase 0 se construyó la interfaz con una paleta inventada sobre la
marcha (verde valle, tierra, cielo, pizarra), porque todavía no se conocía el
diseño previsto.

Después se comprobó que el equipo ya tenía el diseño completo generado en
**Stitch**, en el proyecto *Proyecto Procesos de Software*: 26 pantallas
(escritorio y móvil) y un sistema de diseño formal llamado **Mantaro
Moderno**, con paleta, tipografías, radios, espaciado y reglas de componente.

Mantener dos paletas distintas habría significado que el código y la
documentación visual del proyecto se contradijeran, justo lo que el proyecto
declara como riesgo.

## Decisión

**El sistema de diseño de Stitch manda.** El código copia sus valores; no los
inventa ni los ajusta por gusto. Cualquier cambio de color, tipografía o radio
se hace primero en Stitch y luego se traslada a
`frontend/src/estilos/index.css`.

### Lo que se adoptó

| Elemento | Valor |
|---|---|
| Primario (terracota) | `#a23919` — la tierra y la cerámica local |
| Secundario (verde valle) | `#27695c` — los campos del Mantaro |
| Terciario (ocre) | `#745800` — el sol y la textilería wanka |
| Superficie | `#fff8f5` — crema cálida, nunca blanco puro |
| Fondo en modo oscuro | `#16110f` — marrón «chullpi», no gris neutro |
| Tipografía de títulos | Manrope |
| Tipografía de cuerpo | Be Vietnam Pro |
| Radios | 0,25 / 0,5 / 1 / 1,5 rem |
| Ancho máximo | 1280 px |

Las sombras llevan un matiz de terracota (`rgba(212, 93, 58, 0.08)`) en lugar
de gris neutro: es lo que conserva la calidez que pide el sistema.

## Decisiones derivadas

### Los tokens se nombran en español

`--color-primario`, `--color-superficie`, `--color-sobre-superficie`. Stitch
los llama `primary`, `surface`, `on-surface` (nomenclatura de Material 3). La
tabla de equivalencias está comentada en la cabecera de
`frontend/src/estilos/index.css` para que quien compare ambos los encuentre.

Se eligió el español porque es la regla de idioma del proyecto y porque las
clases resultantes (`bg-superficie`, `text-primario`) se leen igual de bien.

### Las tipografías se autoalojan, no se cargan de Google Fonts

Se instalaron como paquetes (`@fontsource-variable/manrope`,
`@fontsource/be-vietnam-pro`) y se empaquetan con la aplicación.

El motivo es concreto: el Proyecto 6 declara la **conectividad limitada** como
restricción, y la aplicación se va a exponer en clase. Si el aula no tiene
internet, con Google Fonts la tipografía se degrada a la del sistema y el
diseño se rompe justo durante la defensa. El coste es de unos 200 kB
empaquetados.

### La greca wanka es un acento, nunca un fondo

Se implementó como la utilidad `greca-wanka`: una franja de rombos al 18 % de
opacidad, usada como borde bajo el encabezado y encima del pie. El sistema de
diseño es explícito en que estos patrones deben ser *«acentos arquitectónicos,
nunca decoración abrumadora»*, y que el resultado debe verse **alegre y cálido,
jamás recargado**.

## Lo que todavía no se implementó

Las pantallas de Stitch incluyen ilustraciones planas animadas de fauna del
valle (vizcacha, llama, picaflor, pato y trucha) y secciones con fotografías
de los atractivos y de las cuatro provincias.

No se implementan aún por dos motivos:

1. Las fotografías reales de los atractivos llegan con el catálogo de la
   Fase 1. Poner imágenes de relleno contradiría la regla de honestidad con
   los datos.
2. Las ilustraciones requieren los recursos gráficos, que se exportarán de
   Stitch cuando estén cerrados.

La hoja de estilos ya respeta `prefers-reduced-motion`, de modo que cuando las
animaciones se añadan se detendrán para quien lo haya pedido en su sistema
operativo.
