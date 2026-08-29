/**
 * Pruebas del interruptor de tema claro/oscuro.
 *
 * Lo que se comprueba es el efecto real: que la clase "oscuro" aparezca y
 * desaparezca del elemento <html>, porque esa clase es la que activa todas
 * las variantes  dark:  de Tailwind. Comprobar solo el estado interno del
 * componente no demostraria que el tema cambia de verdad.
 */
import { render, screen } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import { InterruptorTema } from '@/componentes/InterruptorTema';
import { CLAVE_TEMA } from '@/hooks/useTema';
import '@/i18n';

describe('InterruptorTema', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove('oscuro');
  });

  it('anade la clase "oscuro" al documento al pulsarlo', async () => {
    render(<InterruptorTema />);

    expect(document.documentElement).not.toHaveClass('oscuro');

    await usuario.click(screen.getByRole('button'));

    expect(document.documentElement).toHaveClass('oscuro');
  });

  it('vuelve al tema claro al pulsarlo dos veces', async () => {
    render(<InterruptorTema />);
    const boton = screen.getByRole('button');

    await usuario.click(boton);
    await usuario.click(boton);

    expect(document.documentElement).not.toHaveClass('oscuro');
  });

  it('recuerda la eleccion en el navegador para la proxima visita', async () => {
    render(<InterruptorTema />);

    await usuario.click(screen.getByRole('button'));

    expect(window.localStorage.getItem(CLAVE_TEMA)).toBe('oscuro');
  });
});
