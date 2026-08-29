/**
 * Pruebas del selector de idioma.
 *
 * Comprueban el requisito de la Fase 0: que cambiar el selector cambie de
 * verdad un texto de la interfaz, no solo el valor del desplegable.
 */
import { render, screen } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import { Encabezado } from '@/componentes/Encabezado';
import i18n, { CLAVE_IDIOMA } from '@/i18n';

describe('SelectorIdioma', () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage('es');
  });

  it('cambia el lema de la aplicacion de espanol a ingles', async () => {
    render(<Encabezado />);

    expect(screen.getByText(/Ruta del Valle del Mantaro/i)).toBeInTheDocument();

    await usuario.selectOptions(screen.getByLabelText(/idioma|language/i), 'en');

    expect(screen.getByText(/Mantaro Valley Route/i)).toBeInTheDocument();
  });

  it('recuerda el idioma elegido en el navegador', async () => {
    render(<Encabezado />);

    await usuario.selectOptions(screen.getByLabelText(/idioma|language/i), 'en');

    expect(window.localStorage.getItem(CLAVE_IDIOMA)).toBe('en');
  });
});
