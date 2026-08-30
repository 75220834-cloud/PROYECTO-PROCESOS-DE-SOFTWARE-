/**
 * Pruebas de la tarjeta de servicio.
 *
 * Comprueban que la tarjeta **haga verificable la capacidad del proveedor**,
 * que es la brecha 5. Hasta el Incremento 5, saber si un taller podía atender
 * a doce personas un sábado exigía llamar; si esta tarjeta no lo dice, la
 * brecha sigue abierta aunque el dato esté en la base.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TarjetaServicio from '@/componentes/TarjetaServicio';
import i18n from '@/i18n';
import type { ServicioPublico } from '@/servicios/api';

function servicio(cambios: Partial<ServicioPublico> = {}): ServicioPublico {
  return {
    id: 3,
    nombre: 'Taller de burilado para principiantes',
    tipo: 'taller',
    descripcion: 'Dos horas de introducción al burilado, con el mate incluido.',
    proveedor: {
      id: 1,
      nombre: 'Taller de mates burilados Cochas (demostración)',
      distrito: 'EL TAMBO',
      telefono: '+51 900 000 101',
      correo: 'taller.cochas@ejemplo.invalid',
      descripcion: null,
      es_demostracion: true,
      // Los de demostración no están en el directorio del Estado: no tienen
      // RUC ni certificado porque no existen.
      ruc: null,
      direccion: null,
      pagina_web: null,
      clase: null,
      categoria: null,
      certificado: null,
      fuente: null,
      fecha_corte: null,
    },
    recurso_id: null,
    capacidad_maxima: 12,
    duracion_min: 120,
    antelacion_minima_horas: 48,
    precio_min_soles: '35.00',
    precio_max_soles: '50.00',
    unidad_precio: 'por_persona',
    fecha_referencia: '2026-08-29',
    idiomas: 'es',
    es_accesible: true,
    // Cierra los lunes: es el caso que hace que la fila de días signifique algo.
    disponibilidad: [1, 2, 3, 4, 5, 6].map((dia) => ({
      dia_semana: dia,
      hora_inicio: '09:00:00',
      hora_fin: '16:00:00',
      cupo: 12,
    })),
    ...cambios,
  };
}

describe('TarjetaServicio', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  describe('lo que hace verificable la capacidad', () => {
    it('dice a cuánta gente atiende', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('Hasta 12 personas')).toBeInTheDocument();
    });

    it('dice con cuánta antelación hay que avisar', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('Avisar con 48 h de antelación')).toBeInTheDocument();
    });

    it('dice cuánto dura', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('2 h')).toBeInTheDocument();
    });

    it('dice qué días atiende, también en palabras', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      // Siete casillas de colores no significan nada sin vista.
      const fila = screen.getByRole('img');

      expect(fila).toHaveAttribute('aria-label', expect.stringContaining('Atiende'));
      // Cierra los lunes, así que la L no debe aparecer en la etiqueta.
      expect(fila.getAttribute('aria-label')).toBe('Atiende: M, X, J, V, S, D');
    });

    it('avisa cuando no hay horarios publicados', () => {
      render(<TarjetaServicio servicio={servicio({ disponibilidad: [] })} />);

      expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Sin horarios publicados');
    });
  });

  describe('honestidad con los datos', () => {
    it('marca al proveedor de demostración', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('Demostración')).toBeInTheDocument();
    });

    it('explica al pasar el ratón que el proveedor no existe', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('Demostración')).toHaveAttribute(
        'title',
        expect.stringContaining('no existen'),
      );
    });

    it('no marca a un proveedor real', () => {
      const real = servicio();
      real.proveedor = { ...real.proveedor, es_demostracion: false };

      render(<TarjetaServicio servicio={real} />);

      expect(screen.queryByText('Demostración')).toBeNull();
    });

    it('muestra el precio como rango, con «aprox.» y con su fecha', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText('aprox. S/ 35.00 – 50.00')).toBeInTheDocument();
      expect(screen.getByText(/2026-08-29/)).toBeInTheDocument();
    });

    it('dice qué incluye el precio', () => {
      render(<TarjetaServicio servicio={servicio()} />);

      expect(screen.getByText(/por persona/)).toBeInTheDocument();
    });
  });

  it('llama a alPedir con el servicio cuando se pulsa', async () => {
    const alPedir = vi.fn();
    const usuario = userEvent.setup();
    const elServicio = servicio();

    render(<TarjetaServicio servicio={elServicio} alPedir={alPedir} />);

    await usuario.click(screen.getByRole('button', { name: 'Solicitar' }));

    expect(alPedir).toHaveBeenCalledWith(elServicio);
  });

  it('no enseña el botón de pedir cuando no hay a quién avisar', () => {
    // Es el caso del panel del proveedor: ve sus servicios, no los pide.
    render(<TarjetaServicio servicio={servicio()} />);

    expect(screen.queryByRole('button', { name: 'Solicitar' })).toBeNull();
  });
});
