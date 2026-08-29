/**
 * Funciones de formato de texto para la interfaz.
 *
 * El inventario del MINCETUR guarda los nombres en mayúsculas y las
 * categorías numeradas ("2. MANIFESTACIONES CULTURALES"). Eso está bien para
 * una base de datos, pero gritado en una tarjeta se lee mal. Aquí se ablanda
 * para mostrarlo, sin tocar el dato original.
 *
 * Viven en su propio archivo y no junto a los componentes porque son lógica
 * pura: así se pueden probar sin renderizar nada y no rompen la recarga en
 * caliente de React.
 */

/** Palabras que en español van en minúscula dentro de un nombre propio. */
const PALABRAS_EN_MINUSCULA = new Set(['de', 'del', 'la', 'las', 'los', 'y', 'en', 'el']);

/**
 * Convierte "2. MANIFESTACIONES CULTURALES" en "Manifestaciones culturales".
 *
 * El número inicial es del sistema de clasificación del MINCETUR y no aporta
 * nada al visitante.
 */
export function formatearCategoria(categoria: string | null | undefined): string {
  if (!categoria) return '';

  const sinNumero = categoria.replace(/^\d+\.\s*/, '').toLowerCase();
  return sinNumero.charAt(0).toUpperCase() + sinNumero.slice(1);
}

/**
 * Pasa "SANTA ROSA DE OCOPA" a "Santa Rosa de Ocopa".
 *
 * La primera palabra siempre va en mayúscula, aunque sea una preposición:
 * "DE LA MERCED" debe quedar "De la Merced", no "de la Merced".
 */
export function formatearNombrePropio(texto: string | null | undefined): string {
  if (!texto) return '';

  return texto
    .toLowerCase()
    .split(' ')
    .map((palabra, indice) =>
      indice > 0 && PALABRAS_EN_MINUSCULA.has(palabra)
        ? palabra
        : palabra.charAt(0).toUpperCase() + palabra.slice(1),
    )
    .join(' ');
}

/**
 * Convierte "2026-09-05" en "5 set 2026", según el idioma activo.
 *
 * Se construye la fecha a partir de sus tres números en vez de pasarle el
 * texto a `new Date()`: esa forma interpreta "2026-09-05" como UTC, y en el
 * Perú (UTC−5) mostraría el día anterior.
 */
export function formatearFecha(fecha: string, idioma: string): string {
  const [anio, mes, dia] = fecha.split('-').map(Number);
  const objeto = new Date(anio, mes - 1, dia);

  return objeto.toLocaleDateString(idioma === 'en' ? 'en-GB' : 'es-PE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Mide la fuerza de una contraseña, de 0 a 4.
 *
 * Es un indicador orientativo para el visitante, NO una regla de seguridad:
 * quien decide si la contraseña se acepta es el backend, que exige ocho
 * caracteres. Se premia la longitud antes que exigir «una mayúscula y un
 * símbolo», porque esas reglas empujan a contraseñas predecibles del tipo
 * «Contrasena1!».
 */
export function medirFuerza(contrasena: string): number {
  if (contrasena.length === 0) return 0;

  let puntos = 0;

  // La longitud vale hasta tres puntos y la variedad de caracteres solo uno.
  // Es deliberado: una frase larga y fácil de recordar resiste muchísimo
  // mejor un ataque por fuerza bruta que una contraseña corta llena de
  // símbolos, aunque la segunda "parezca" más segura.
  if (contrasena.length >= 8) puntos += 1;
  if (contrasena.length >= 12) puntos += 1;
  if (contrasena.length >= 16) puntos += 1;

  const mezclaMayusculas = /[a-z]/.test(contrasena) && /[A-Z]/.test(contrasena);
  const tieneDigitoOSimbolo = /\d/.test(contrasena) || /[^\w\s]/.test(contrasena);
  if (mezclaMayusculas || tieneDigitoOSimbolo) puntos += 1;

  return Math.min(puntos, 4);
}
