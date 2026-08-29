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
