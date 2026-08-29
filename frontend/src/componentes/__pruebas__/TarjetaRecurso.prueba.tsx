/**
 * Pruebas de la tarjeta de recurso del catálogo.
 *
 * Lo que se comprueba es la regla de honestidad con los datos: la tarjeta
 * debe DECIR cuándo falta información, no disimularlo.
 */
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { TarjetaRecurso } from '@/componentes/TarjetaRecurso';
import i18n from '@/i18n';
import type { RecursoResumen } from '@/servicios/api';

const RECURSO_VALIDADO: RecursoResumen = {
  id: 1,
  codigo_mincetur: '793',
  nombre: 'Convento de Santa Rosa de Ocopa',
  provincia: 'CONCEPCION',
  distrito: 'SANTA ROSA DE OCOPA',
  categoria: '2. MANIFESTACIONES CULTURALES',
  tipo: 'Museos',
  latitud: -11.9169,
  longitud: -75.3103,
  esta_validado: true,
  esta_vigente: true,
  fecha_corte: '2026-08-27',
  foto_url: null,
};

const RECURSO_SIN_COORDENADAS: RecursoResumen = {
  ...RECURSO_VALIDADO,
  id: 2,
  nombre: 'Recurso sin ubicación registrada',
  latitud: null,
  longitud: null,
  esta_validado: false,
};

function renderizar(elemento: ReactNode) {
  return render(<MemoryRouter>{elemento}</MemoryRouter>);
}

describe('TarjetaRecurso', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  it('muestra el nombre, el distrito y la provincia con formato legible', () => {
    renderizar(<TarjetaRecurso recurso={RECURSO_VALIDADO} />);

    expect(screen.getByText(RECURSO_VALIDADO.nombre)).toBeInTheDocument();
    // El dato viene en mayúsculas de la base; se muestra ablandado.
    expect(screen.getByText(/Santa Rosa de Ocopa · Concepcion/)).toBeInTheDocument();
  });

  it('quita el número de la categoría del MINCETUR', () => {
    renderizar(<TarjetaRecurso recurso={RECURSO_VALIDADO} />);

    expect(screen.getByText('Manifestaciones culturales')).toBeInTheDocument();
    expect(screen.queryByText(/^2\./)).not.toBeInTheDocument();
  });

  it('marca como validado el recurso que pasó la validación', () => {
    renderizar(<TarjetaRecurso recurso={RECURSO_VALIDADO} />);

    expect(screen.getByText('Validado')).toBeInTheDocument();
    expect(screen.getByText(/Inventario MINCETUR/)).toBeInTheDocument();
  });

  it('avisa cuando la fuente oficial no trae coordenada', () => {
    // Regla de honestidad: no se oculta el dato que falta ni se inventa una
    // ubicación aproximada. El visitante tiene que poder saberlo.
    renderizar(<TarjetaRecurso recurso={RECURSO_SIN_COORDENADAS} />);

    expect(screen.getByText(/Sin coordenada en la fuente oficial/)).toBeInTheDocument();
    expect(screen.getByText('Incompleto')).toBeInTheDocument();
  });

  it('enlaza al detalle del recurso', () => {
    renderizar(<TarjetaRecurso recurso={RECURSO_VALIDADO} />);

    const enlace = screen.getByRole('link', { name: RECURSO_VALIDADO.nombre });
    expect(enlace).toHaveAttribute('href', '/recursos/1');
  });
});
