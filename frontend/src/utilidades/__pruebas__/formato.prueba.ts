/**
 * Pruebas de las funciones de formato de texto.
 *
 * Son lógica pura, así que se prueban sin renderizar nada. Cubren los casos
 * reales que aparecen en el inventario del MINCETUR.
 */
import { describe, expect, it } from 'vitest';

import { formatearCategoria, formatearNombrePropio } from '@/utilidades/formato';

describe('formatearCategoria', () => {
  it('quita el número de clasificación y ablanda las mayúsculas', () => {
    expect(formatearCategoria('2. MANIFESTACIONES CULTURALES')).toBe('Manifestaciones culturales');
    expect(formatearCategoria('1. SITIOS NATURALES')).toBe('Sitios naturales');
  });

  it('conserva las tildes de la fuente oficial', () => {
    // Caso real: la categoría 4 del inventario lleva tres palabras con tilde.
    expect(formatearCategoria('4. REALIZACIONES TÉCNICAS, CIENTÍFICAS Y ARTÍSTICAS')).toBe(
      'Realizaciones técnicas, científicas y artísticas',
    );
  });

  it('devuelve cadena vacía si no hay categoría', () => {
    expect(formatearCategoria(null)).toBe('');
    expect(formatearCategoria(undefined)).toBe('');
    expect(formatearCategoria('')).toBe('');
  });

  it('no se rompe si la categoría no lleva número', () => {
    expect(formatearCategoria('FOLCLORE')).toBe('Folclore');
  });
});

describe('formatearNombrePropio', () => {
  it('convierte un distrito en mayúsculas a nombre propio', () => {
    expect(formatearNombrePropio('SANTA ROSA DE OCOPA')).toBe('Santa Rosa de Ocopa');
    expect(formatearNombrePropio('HUANCAYO')).toBe('Huancayo');
  });

  it('deja en minúscula las preposiciones y artículos intermedios', () => {
    expect(formatearNombrePropio('SAN JUAN DE JARPA')).toBe('San Juan de Jarpa');
  });

  it('pone en mayúscula la primera palabra aunque sea preposición', () => {
    // Caso borde: "DE LA MERCED" no debe quedar "de la Merced".
    expect(formatearNombrePropio('DE LA MERCED')).toBe('De la Merced');
  });

  it('conserva la Ñ del distrito SAÑO', () => {
    // La Ñ es una letra propia del español. Si el backend la hubiera
    // convertido en N, este distrito de Huancayo se mostraría mal escrito.
    expect(formatearNombrePropio('SAÑO')).toBe('Saño');
  });

  it('devuelve cadena vacía si no hay texto', () => {
    expect(formatearNombrePropio(null)).toBe('');
    expect(formatearNombrePropio('')).toBe('');
  });
});
