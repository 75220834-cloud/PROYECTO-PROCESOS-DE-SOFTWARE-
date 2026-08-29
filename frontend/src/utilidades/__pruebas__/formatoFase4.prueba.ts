/**
 * Pruebas de los formateadores que añadió el Incremento 4.
 *
 * El de precio es el que más importa: es el que garantiza que **ningún importe
 * salga a pantalla sin la palabra «aprox.»**. El contexto del proyecto dice que
 * en el valle no hay tarifa oficial única, así que un «S/ 3,00» a secas
 * afirmaría una precisión que no existe.
 */
import { describe, expect, it } from 'vitest';

import { formatearDuracion, formatearPrecio } from '@/utilidades/formato';

describe('formatearDuracion', () => {
  it('deja los minutos sueltos cuando no llega a una hora', () => {
    expect(formatearDuracion(45)).toBe('45 min');
    expect(formatearDuracion(59)).toBe('59 min');
  });

  it('pasa a horas justo al llegar a sesenta', () => {
    expect(formatearDuracion(60)).toBe('1 h');
  });

  it('no dice «0 min» cuando la hora es exacta', () => {
    expect(formatearDuracion(120)).toBe('2 h');
    expect(formatearDuracion(180)).toBe('3 h');
  });

  it('junta horas y minutos cuando hay resto', () => {
    expect(formatearDuracion(95)).toBe('1 h 35 min');
    expect(formatearDuracion(215)).toBe('3 h 35 min');
  });

  it('devuelve cero minutos y no una cadena vacía', () => {
    expect(formatearDuracion(0)).toBe('0 min');
  });
});

describe('formatearPrecio', () => {
  it('muestra el rango completo cuando hay incertidumbre', () => {
    expect(formatearPrecio('2.00', '3.50')).toBe('aprox. S/ 2.00 – 3.50');
  });

  it('mantiene el «aprox.» aunque el rango sea de un solo valor', () => {
    // Que el mínimo y el máximo coincidan no significa que el precio esté
    // confirmado: significa que la estimación dio lo mismo por los dos lados.
    expect(formatearPrecio('5.00', '5.00')).toBe('aprox. S/ 5.00');
  });

  it('no dice «aprox.» cuando el precio es cero, porque caminar es gratis', () => {
    // Aquí no hay incertidumbre ninguna: caminar no cuesta dinero, y eso no es
    // una estimación sino un hecho.
    expect(formatearPrecio('0.00', '0.00')).toBe('S/ 0');
  });

  it('siempre muestra dos decimales', () => {
    expect(formatearPrecio('2', '3')).toBe('aprox. S/ 2.00 – 3.00');
  });

  it('nunca devuelve un importe sin la palabra aprox., salvo el cero', () => {
    const casos: [string, string][] = [
      ['1.50', '2.00'],
      ['0.50', '0.50'],
      ['12.00', '19.50'],
      ['100.00', '250.00'],
    ];

    for (const [minimo, maximo] of casos) {
      expect(formatearPrecio(minimo, maximo)).toMatch(/^aprox\. S\//);
    }
  });
});
