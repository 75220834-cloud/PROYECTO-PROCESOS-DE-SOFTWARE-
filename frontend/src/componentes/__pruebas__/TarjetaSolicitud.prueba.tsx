/**
 * Pruebas de la tarjeta de solicitud.
 *
 * Lo que se comprueba es que **la tarjeta pueda demostrar lo acordado**, que es
 * la brecha 6. Un estado suelto no basta: hace falta el historial con sus
 * fechas y quién movió cada cosa.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import TarjetaSolicitud from '@/componentes/TarjetaSolicitud';
import i18n from '@/i18n';
import type { EstadoSolicitud, SolicitudPublica } from '@/servicios/api';

function solicitud(cambios: Partial<SolicitudPublica> = {}): SolicitudPublica {
  return {
    id: 7,
    servicio_id: 3,
    servicio_nombre: 'Taller de burilado para principiantes',
    proveedor_nombre: 'Taller de mates burilados Cochas (demostración)',
    proveedor_telefono: '+51 900 000 101',
    proveedor_es_demostracion: true,
    itinerario_id: null,
    fecha_servicio: '2026-09-18',
    hora_servicio: '10:00:00',
    numero_personas: 4,
    nombre_contacto: 'Persona de prueba',
    telefono_contacto: '+51 900 000 111',
    correo_contacto: null,
    mensaje: 'Vamos con dos niños.',
    estado: 'confirmada',
    precio_acordado_soles: '160.00',
    respuesta_proveedor: 'Confirmado, traigan abrigo',
    precio_min_soles: '35.00',
    precio_max_soles: '50.00',
    creado_en: '2026-08-29T18:52:25Z',
    actualizado_en: '2026-08-29T18:52:31Z',
    interacciones: 3,
    historial: [
      {
        estado_anterior: null,
        estado_nuevo: 'enviada',
        rol_de_quien_cambio: 'visitante',
        nota: null,
        ocurrido_en: '2026-08-29T18:52:25Z',
      },
      {
        estado_anterior: 'enviada',
        estado_nuevo: 'en_revision',
        rol_de_quien_cambio: 'proveedor',
        nota: 'Mirando la agenda',
        ocurrido_en: '2026-08-29T18:52:29Z',
      },
      {
        estado_anterior: 'en_revision',
        estado_nuevo: 'confirmada',
        rol_de_quien_cambio: 'proveedor',
        nota: 'Confirmado, traigan abrigo',
        ocurrido_en: '2026-08-29T18:52:31Z',
      },
    ],
    ...cambios,
  };
}

describe('TarjetaSolicitud', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  it('muestra el estado en el que está la solicitud', () => {
    render(<TarjetaSolicitud solicitud={solicitud()} />);

    expect(screen.getByText('Confirmada')).toBeInTheDocument();
  });

  it('explica qué significa el estado al pasar el ratón', () => {
    render(<TarjetaSolicitud solicitud={solicitud({ estado: 'en_revision' })} />);

    expect(screen.getByText('En revisión')).toHaveAttribute(
      'title',
      'El proveedor la está mirando.',
    );
  });

  it('marca al proveedor de demostración', () => {
    render(<TarjetaSolicitud solicitud={solicitud()} />);

    expect(screen.getByText('Demostración')).toBeInTheDocument();
  });

  it('concuerda el singular con una sola persona', () => {
    render(<TarjetaSolicitud solicitud={solicitud({ numero_personas: 1 })} />);

    expect(screen.getByText(/1 persona/)).toBeInTheDocument();
  });

  describe('el registro de lo acordado', () => {
    it('el historial va plegado, pero anuncia cuántas interacciones hubo', () => {
      render(<TarjetaSolicitud solicitud={solicitud()} />);

      expect(screen.getByRole('button', { name: /3 interacciones/ })).toHaveAttribute(
        'aria-expanded',
        'false',
      );
      expect(screen.queryByText(/Mirando la agenda/)).toBeNull();
    });

    it('al desplegarlo muestra cada cambio con su fecha y quién lo hizo', async () => {
      const usuario = userEvent.setup();
      render(<TarjetaSolicitud solicitud={solicitud()} />);

      await usuario.click(screen.getByRole('button', { name: /interacciones/ }));

      const lista = screen.getByRole('list');

      expect(within(lista).getAllByText(/29\/08\/2026/)).toHaveLength(3);
      expect(within(lista).getByText('Enviada')).toBeInTheDocument();
      expect(within(lista).getAllByText(/por proveedor/)).toHaveLength(2);
      expect(within(lista).getByText(/Mirando la agenda/)).toBeInTheDocument();
    });

    it('el historial cuenta la misma historia que el estado actual', async () => {
      const usuario = userEvent.setup();
      render(<TarjetaSolicitud solicitud={solicitud()} />);

      await usuario.click(screen.getByRole('button', { name: /interacciones/ }));

      // El último cambio del historial tiene que coincidir con el estado.
      const lista = screen.getByRole('list');
      const ultimo = within(lista).getAllByRole('listitem').at(-1);

      expect(ultimo?.textContent).toContain('Confirmada');
    });
  });

  describe('los precios', () => {
    it('muestra el acordado y el publicado, para poder compararlos', () => {
      render(<TarjetaSolicitud solicitud={solicitud()} />);

      expect(screen.getByText('S/ 160.00')).toBeInTheDocument();
      expect(screen.getByText('aprox. S/ 35.00 – 50.00')).toBeInTheDocument();
    });

    it('no inventa un precio acordado cuando todavía no lo hay', () => {
      render(
        <TarjetaSolicitud
          solicitud={solicitud({ estado: 'enviada', precio_acordado_soles: null })}
        />,
      );

      expect(screen.queryByText(/Precio acordado/)).toBeNull();
      expect(screen.getByText('aprox. S/ 35.00 – 50.00')).toBeInTheDocument();
    });
  });

  it('muestra la respuesta del proveedor cuando la hay', () => {
    render(<TarjetaSolicitud solicitud={solicitud()} />);

    expect(screen.getByText('Confirmado, traigan abrigo')).toBeInTheDocument();
  });

  it('solo enseña acciones cuando se le pasan', () => {
    const { rerender } = render(<TarjetaSolicitud solicitud={solicitud()} />);

    expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull();

    rerender(<TarjetaSolicitud solicitud={solicitud()} acciones={<button>Confirmar</button>} />);

    expect(screen.getByRole('button', { name: 'Confirmar' })).toBeInTheDocument();
  });

  const ESTADOS: EstadoSolicitud[] = [
    'enviada',
    'en_revision',
    'contrapropuesta',
    'confirmada',
    'rechazada',
    'cancelada',
  ];

  it.each(ESTADOS)('traduce el estado «%s» sin dejar la clave en crudo', (estado) => {
    render(<TarjetaSolicitud solicitud={solicitud({ estado })} />);

    expect(screen.queryByText(`coordinacion.estado.${estado}`)).toBeNull();
  });
});
