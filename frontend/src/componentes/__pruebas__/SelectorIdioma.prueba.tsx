/**
 * Pruebas del selector de idioma.
 *
 * Comprueban el requisito de la Fase 0: que cambiar el selector cambie de
 * verdad los textos de la interfaz, no solo el valor del desplegable.
 *
 * El encabezado usa NavLink, que necesita un enrutador por encima. En las
 * pruebas se usa MemoryRouter, que guarda la ruta en memoria en vez de tocar
 * la barra de direcciones del navegador.
 */
import { render, screen } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { Encabezado } from '@/componentes/Encabezado';
import { ProveedorTema } from '@/componentes/ProveedorTema';
import i18n, { CLAVE_IDIOMA } from '@/i18n';

function renderizarConEnrutador(elemento: ReactNode) {
  return render(
    <ProveedorTema>
      <MemoryRouter initialEntries={['/']}>{elemento}</MemoryRouter>
    </ProveedorTema>,
  );
}

describe('SelectorIdioma', () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage('es');
  });

  it('traduce la navegación de español a inglés', async () => {
    renderizarConEnrutador(<Encabezado />);

    // En español la navegación dice "Inicio" y el botón "Iniciar sesión".
    expect(screen.getAllByText('Inicio').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Iniciar sesión').length).toBeGreaterThan(0);

    await usuario.selectOptions(screen.getAllByLabelText(/idioma|language/i)[0], 'en');

    // En inglés pasan a "Home" y "Sign in".
    expect(screen.getAllByText('Home').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Sign in').length).toBeGreaterThan(0);
    expect(screen.queryByText('Iniciar sesión')).not.toBeInTheDocument();
  });

  it('recuerda el idioma elegido en el navegador', async () => {
    renderizarConEnrutador(<Encabezado />);

    await usuario.selectOptions(screen.getAllByLabelText(/idioma|language/i)[0], 'en');

    expect(window.localStorage.getItem(CLAVE_IDIOMA)).toBe('en');
  });
});
