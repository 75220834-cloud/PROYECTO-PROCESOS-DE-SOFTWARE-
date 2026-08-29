/**
 * Pruebas del formateo de fechas y del medidor de fuerza de contraseña.
 */
import { describe, expect, it } from 'vitest';

import { formatearFecha, medirFuerza } from '@/utilidades/formato';

describe('formatearFecha', () => {
  it('no adelanta ni atrasa el día por la zona horaria', () => {
    /**
     * Caso borde real y fácil de romper.
     *
     * `new Date('2026-09-05')` interpreta el texto como medianoche UTC. En el
     * Perú, que va cinco horas por detrás, eso son las 19:00 del día 4, así
     * que la fecha se mostraría como el día anterior. Por eso la función
     * construye la fecha a partir de sus tres números.
     */
    expect(formatearFecha('2026-09-05', 'es')).toContain('5');
    expect(formatearFecha('2026-01-01', 'es')).toContain('1');
    expect(formatearFecha('2026-01-01', 'es')).toContain('2026');
  });

  it('usa el formato del idioma activo', () => {
    const enEspanol = formatearFecha('2026-09-05', 'es');
    const enIngles = formatearFecha('2026-09-05', 'en');

    // Ambos llevan el día y el año; el nombre del mes cambia de idioma.
    expect(enEspanol).toContain('2026');
    expect(enIngles).toContain('2026');
    expect(enEspanol).not.toBe(enIngles);
  });
});

describe('medirFuerza', () => {
  it('da cero a una contraseña vacía', () => {
    expect(medirFuerza('')).toBe(0);
  });

  it('puntúa poco una contraseña corta', () => {
    expect(medirFuerza('abc')).toBeLessThanOrEqual(1);
  });

  it('premia la longitud por encima de los símbolos', () => {
    // Una frase larga y fácil de recordar debe puntuar al menos tanto como
    // una corta llena de símbolos: es lo que recomienda la práctica actual.
    const fraseLarga = medirFuerza('caballocorrectobateriagrapa');
    const cortaConSimbolos = medirFuerza('Ab1!');

    expect(fraseLarga).toBeGreaterThan(cortaConSimbolos);
  });

  it('nunca pasa de cuatro', () => {
    expect(medirFuerza('UnaContrasenaMuyLarga123!@#')).toBeLessThanOrEqual(4);
  });

  it('sube al añadir variedad de caracteres', () => {
    expect(medirFuerza('contrasena')).toBeLessThan(medirFuerza('Contrasena1'));
  });
});
