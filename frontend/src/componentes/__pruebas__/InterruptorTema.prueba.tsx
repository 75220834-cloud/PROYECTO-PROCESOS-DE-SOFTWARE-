/**
 * Pruebas del interruptor de tema claro/oscuro.
 *
 * Lo que se comprueba es el efecto real: que la clase "oscuro" aparezca y
 * desaparezca del elemento <html>, porque esa clase es la que activa todas
 * las variantes  dark:  de Tailwind. Comprobar solo el estado interno del
 * componente no demostraría que el tema cambia de verdad.
 */
import { render, screen } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it } from 'vitest';

import { InterruptorTema } from '@/componentes/InterruptorTema';
import { ProveedorTema } from '@/componentes/ProveedorTema';
import { CLAVE_TEMA } from '@/hooks/useTema';
import '@/i18n';

function renderizarConProveedor(elemento: ReactNode) {
  return render(<ProveedorTema>{elemento}</ProveedorTema>);
}

describe('InterruptorTema', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove('oscuro');
  });

  it('añade la clase "oscuro" al documento al pulsarlo', async () => {
    renderizarConProveedor(<InterruptorTema />);

    expect(document.documentElement).not.toHaveClass('oscuro');

    await usuario.click(screen.getByRole('button'));

    expect(document.documentElement).toHaveClass('oscuro');
  });

  it('vuelve al tema claro al pulsarlo dos veces', async () => {
    renderizarConProveedor(<InterruptorTema />);
    const boton = screen.getByRole('button');

    await usuario.click(boton);
    await usuario.click(boton);

    expect(document.documentElement).not.toHaveClass('oscuro');
  });

  it('recuerda la elección en el navegador para la próxima visita', async () => {
    renderizarConProveedor(<InterruptorTema />);

    await usuario.click(screen.getByRole('button'));

    expect(window.localStorage.getItem(CLAVE_TEMA)).toBe('oscuro');
  });

  it('mantiene sincronizados dos interruptores a la vez', async () => {
    // Caso borde real: el encabezado muestra un interruptor en escritorio y
    // otro dentro del menú desplegable en móvil. Si cada uno guardara su
    // propio estado, mostrarían iconos contradictorios. Esta prueba fija que
    // el estado vive en un único lugar, el proveedor.
    renderizarConProveedor(
      <>
        <InterruptorTema />
        <InterruptorTema />
      </>,
    );

    const [primero, segundo] = screen.getAllByRole('button');

    // No se compara contra un texto concreto: eso ataría la prueba al idioma
    // activo. Lo que importa es que ambos digan LO MISMO, antes y después.
    const etiquetaInicial = primero.getAttribute('aria-label');
    expect(segundo).toHaveAttribute('aria-label', etiquetaInicial);

    await usuario.click(primero);

    // Al pulsar uno, el OTRO también debe reflejar el cambio.
    expect(document.documentElement).toHaveClass('oscuro');
    expect(primero.getAttribute('aria-label')).not.toBe(etiquetaInicial);
    expect(segundo).toHaveAttribute('aria-label', primero.getAttribute('aria-label'));
  });
});
