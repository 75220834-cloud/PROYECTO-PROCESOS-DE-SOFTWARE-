/**
 * Pruebas de la tarjeta de recomendación.
 *
 * Lo que se comprueba es que la tarjeta **explique**, no solo que muestre un
 * número. La brecha 2 del análisis habla de que al visitante le falta
 * criterios explícitos: un «92 %» sin justificación no los aporta.
 */
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { TarjetaRecomendacion } from '@/componentes/TarjetaRecomendacion';
import i18n from '@/i18n';
import type { RecomendacionPublica } from '@/servicios/api';

const RECOMENDACION: RecomendacionPublica = {
  recurso_id: 42,
  nombre: 'Pueblo Artesanal de Cochas Grande',
  provincia: 'HUANCAYO',
  distrito: 'EL TAMBO',
  categoria: '2. MANIFESTACIONES CULTURALES',
  latitud: -12.0021,
  longitud: -75.1997,
  distancia_km: 7,
  puntaje_afinidad: 0.0952,
  puntaje_relativo: 82,
  terminos_decisivos: ['artesanal', 'pueblo artesanal'],
  intereses_cubiertos: ['artesania'],
  afluencia: {
    nivel: 'alto',
    motivo: { codigo: 'afluencia_feria_dominical', parametros: {} },
    festividades: [],
    calculado_por: 'reglas',
  },
  generado_por: 'modelo',
};

function renderizar(elemento: ReactNode) {
  return render(<MemoryRouter>{elemento}</MemoryRouter>);
}

describe('TarjetaRecomendacion', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  it('muestra el puntaje relativo, no la similitud en bruto', () => {
    /**
     * El 0,0952 del coseno no significa nada para el visitante. Mostrarlo
     * sería peor que no mostrar nada.
     */
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText('82 %')).toBeInTheDocument();
    expect(screen.queryByText(/0\.0952/)).not.toBeInTheDocument();
  });

  it('explica por qué se recomienda', () => {
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText(/Porque te interesa artesanía/i)).toBeInTheDocument();
  });

  it('muestra los términos que pesaron en el cálculo', () => {
    /** Es lo que hace auditable la recomendación. */
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText(/artesanal, pueblo artesanal/)).toBeInTheDocument();
  });

  it('muestra la afluencia con su motivo, no solo el nivel', () => {
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText('Mucha gente ese día')).toBeInTheDocument();
    expect(screen.getByText('Hoy hay Feria Dominical en Huancayo')).toBeInTheDocument();
  });

  it('aclara qué significa el porcentaje', () => {
    /** Sin la aclaración, «82 %» se leería como una probabilidad. */
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText('82 %')).toHaveAttribute(
      'title',
      expect.stringContaining('No es un porcentaje absoluto') as unknown as string,
    );
  });

  it('quita el número de la categoría del MINCETUR', () => {
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByText('Manifestaciones culturales')).toBeInTheDocument();
  });

  it('enlaza al detalle del recurso', () => {
    renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);

    expect(screen.getByRole('link', { name: RECOMENDACION.nombre })).toHaveAttribute(
      'href',
      '/recursos/42',
    );
  });

  it('funciona sin distancia calculada', () => {
    /** Caso borde: sin origen georreferenciado no hay distancia. */
    renderizar(<TarjetaRecomendacion recomendacion={{ ...RECOMENDACION, distancia_km: null }} />);

    expect(screen.queryByText(/km/)).not.toBeInTheDocument();
  });

  it('cambia el color de la etiqueta según la afluencia', () => {
    const { rerender } = renderizar(<TarjetaRecomendacion recomendacion={RECOMENDACION} />);
    const conMuchaGente = screen.getByText('Mucha gente ese día').className;

    rerender(
      <MemoryRouter>
        <TarjetaRecomendacion
          recomendacion={{
            ...RECOMENDACION,
            afluencia: { ...RECOMENDACION.afluencia, nivel: 'bajo' },
          }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText('Poca gente').className).not.toBe(conMuchaGente);
  });
});
