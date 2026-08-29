/**
 * Pruebas de la línea de tiempo del itinerario.
 *
 * Lo que más se comprueba aquí no es que pinte bien, sino que **no esconda la
 * incertidumbre**: que un tramo estimado se vea como estimado, que un precio
 * salga siempre como rango con «aprox.», y que reordenar sea posible sin
 * ratón. Las tres son exigencias del proyecto, no detalles de estilo.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import LineaDeTiempo from '@/componentes/LineaDeTiempo';
import i18n from '@/i18n';
import type { ParadaItinerario, TrasladoPublico } from '@/servicios/api';

function traslado(cambios: Partial<TrasladoPublico> = {}): TrasladoPublico {
  return {
    modo: 'combi',
    minutos: 25,
    distancia_km: 8.4,
    desnivel_m: 12,
    precio_min_soles: '2.00',
    precio_max_soles: '3.00',
    es_estimado: true,
    fuente: 'Estimación del equipo por distancia',
    fecha_referencia: '2026-08-29',
    origen_del_calculo: 'red_vial',
    trazado: [],
    ...cambios,
  };
}

function parada(
  orden: number,
  nombre: string,
  cambios: Partial<ParadaItinerario> = {},
): ParadaItinerario {
  return {
    orden,
    recurso_id: 100 + orden,
    nombre,
    distrito: 'HUANCAYO',
    categoria: '2. MANIFESTACIONES CULTURALES',
    latitud: -12.06 - orden / 100,
    longitud: -75.21 - orden / 100,
    altitud_msnm: 3250 + orden,
    // padStart y no `0${...}`: con orden 1 esa plantilla daba «010:00:00».
    hora_llegada: `${String(8 + orden).padStart(2, '0')}:00:00`,
    hora_salida: `${String(9 + orden).padStart(2, '0')}:00:00`,
    duracion_visita_min: 60,
    puntaje_relativo: 90 - orden * 10,
    traslado: orden === 0 ? null : traslado(),
    ...cambios,
  };
}

const PARADAS = [
  parada(0, 'Plaza de la Constitución'),
  parada(1, 'Convento de Santa Rosa de Ocopa'),
  parada(2, 'Laguna de Ñahuinpuquio'),
];

function renderizar(elemento: ReactNode) {
  return render(<MemoryRouter>{elemento}</MemoryRouter>);
}

describe('LineaDeTiempo', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  it('muestra las paradas en el orden recibido y numeradas', () => {
    renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

    const titulos = screen.getAllByRole('heading', { level: 3 });

    expect(titulos.map((h) => h.textContent)).toEqual([
      'Plaza de la Constitución',
      'Convento de Santa Rosa de Ocopa',
      'Laguna de Ñahuinpuquio',
    ]);
  });

  it('numera cada parada en su etiqueta accesible', () => {
    renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

    expect(screen.getByLabelText(/Parada 1 de 3/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Parada 3 de 3/)).toBeInTheDocument();
  });

  it('muestra la hora de llegada y de salida de cada parada', () => {
    renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

    expect(screen.getByText('08:00 – 09:00')).toBeInTheDocument();
    expect(screen.getByText('09:00 – 10:00')).toBeInTheDocument();
  });

  it('no dibuja traslado antes de la primera parada', () => {
    renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

    // Dos traslados para tres paradas: no se llega a la primera desde nada.
    expect(screen.getAllByText('En combi')).toHaveLength(2);
  });

  describe('honestidad con los datos', () => {
    it('muestra el precio siempre como rango y con «aprox.»', () => {
      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

      expect(screen.getAllByText(/aprox\. S\/ 2\.00 – 3\.00/)).toHaveLength(2);
    });

    it('mantiene el «aprox.» aunque el rango sea de un solo valor', () => {
      const paradas = [
        parada(0, 'Origen'),
        parada(1, 'Destino', {
          traslado: traslado({ precio_min_soles: '5.00', precio_max_soles: '5.00' }),
        }),
      ];

      renderizar(<LineaDeTiempo paradas={paradas} alReordenar={vi.fn()} />);

      expect(screen.getByText(/aprox\. S\/ 5\.00/)).toBeInTheDocument();
    });

    it('avisa cuando el tramo se calculó en línea recta', () => {
      const paradas = [
        parada(0, 'Origen'),
        parada(1, 'Destino', {
          traslado: traslado({ origen_del_calculo: 'linea_recta' }),
        }),
      ];

      renderizar(<LineaDeTiempo paradas={paradas} alReordenar={vi.fn()} />);

      expect(screen.getByText(/OpenStreetMap no tiene vías registradas/)).toBeInTheDocument();
    });

    it('no avisa cuando el tramo se calculó sobre la red vial', () => {
      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

      expect(screen.queryByText(/OpenStreetMap no tiene vías registradas/)).toBeNull();
    });

    it('no muestra precio para los tramos a pie, porque caminar no cuesta', () => {
      const paradas = [
        parada(0, 'Origen'),
        parada(1, 'Destino', {
          traslado: traslado({
            modo: 'caminando',
            precio_min_soles: '0.00',
            precio_max_soles: '0.00',
          }),
        }),
      ];

      renderizar(<LineaDeTiempo paradas={paradas} alReordenar={vi.fn()} />);

      expect(screen.getByText('A pie')).toBeInTheDocument();
      expect(screen.queryByText(/aprox\./)).toBeNull();
    });

    it('deja la fuente y la fecha del precio a mano de quien las busque', () => {
      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

      const precio = screen.getAllByText(/aprox\. S\//)[0];

      expect(precio).toHaveAttribute(
        'title',
        expect.stringContaining('Estimación del equipo por distancia'),
      );
      expect(precio).toHaveAttribute('title', expect.stringContaining('2026-08-29'));
    });
  });

  describe('reordenar', () => {
    it('permite subir una parada con Alt y flecha arriba', async () => {
      const alReordenar = vi.fn();
      const usuario = userEvent.setup();

      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={alReordenar} />);

      const tercera = screen.getByLabelText(/Parada 3 de 3/);
      tercera.focus();

      await usuario.keyboard('{Alt>}{ArrowUp}{/Alt}');

      expect(alReordenar).toHaveBeenCalledWith([100, 102, 101]);
    });

    it('permite bajar una parada con Alt y flecha abajo', async () => {
      const alReordenar = vi.fn();
      const usuario = userEvent.setup();

      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={alReordenar} />);

      screen.getByLabelText(/Parada 1 de 3/).focus();

      await usuario.keyboard('{Alt>}{ArrowDown}{/Alt}');

      expect(alReordenar).toHaveBeenCalledWith([101, 100, 102]);
    });

    it('no reordena con las flechas sin pulsar Alt', async () => {
      const alReordenar = vi.fn();
      const usuario = userEvent.setup();

      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={alReordenar} />);

      screen.getByLabelText(/Parada 1 de 3/).focus();

      await usuario.keyboard('{ArrowDown}');

      // Sin el modificador, alguien recorriendo la lista con el teclado
      // reordenaría el viaje sin querer.
      expect(alReordenar).not.toHaveBeenCalled();
    });

    it('no deja subir la primera parada por encima de sí misma', async () => {
      const alReordenar = vi.fn();
      const usuario = userEvent.setup();

      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={alReordenar} />);

      screen.getByLabelText(/Parada 1 de 3/).focus();

      await usuario.keyboard('{Alt>}{ArrowUp}{/Alt}');

      expect(alReordenar).not.toHaveBeenCalled();
    });

    it('no deja bajar la última parada por debajo de sí misma', async () => {
      const alReordenar = vi.fn();
      const usuario = userEvent.setup();

      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={alReordenar} />);

      screen.getByLabelText(/Parada 3 de 3/).focus();

      await usuario.keyboard('{Alt>}{ArrowDown}{/Alt}');

      expect(alReordenar).not.toHaveBeenCalled();
    });

    it('bloquea el arrastre mientras el backend recalcula', () => {
      renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} recalculando />);

      expect(screen.getByLabelText(/Parada 1 de 3/)).toHaveAttribute('draggable', 'false');
    });
  });

  it('avisa cuando no hay ninguna parada, en vez de quedarse en blanco', () => {
    renderizar(<LineaDeTiempo paradas={[]} alReordenar={vi.fn()} />);

    expect(screen.getByText(/No se pudo armar ninguna parada/)).toBeInTheDocument();
  });

  it('enlaza cada parada con la ficha de su recurso', () => {
    renderizar(<LineaDeTiempo paradas={PARADAS} alReordenar={vi.fn()} />);

    const primera = screen.getByLabelText(/Parada 1 de 3/);
    const enlace = within(primera).getByRole('link');

    expect(enlace).toHaveAttribute('href', '/recursos/100');
  });
});
