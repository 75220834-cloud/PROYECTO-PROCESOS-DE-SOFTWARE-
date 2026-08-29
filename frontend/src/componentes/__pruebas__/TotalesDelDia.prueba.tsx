/**
 * Pruebas del panel de totales del día.
 *
 * Se comprueba sobre todo que el panel **diga cómo se generó el itinerario** y
 * que la barra de esfuerzo tenga una alternativa en texto. Lo primero es la
 * trazabilidad que exige la regla de oro de la IA del proyecto; lo segundo es
 * que una barra vacía no significa nada para un lector de pantalla.
 */
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import TotalesDelDia from '@/componentes/TotalesDelDia';
import i18n from '@/i18n';
import type { RespuestaItinerario } from '@/servicios/api';

function itinerario(cambios: Partial<RespuestaItinerario> = {}): RespuestaItinerario {
  return {
    itinerario_id: null,
    preferencia_id: 7,
    fecha: '2026-09-12',
    titulo: 'Un día en Concepción',
    generado_por: 'modelo',
    paradas: [],
    tiempo_total_min: 215,
    costo_min_soles: '12.00',
    costo_max_soles: '19.50',
    distancia_total_km: 24.7,
    subida_total_m: 420,
    esfuerzo: 'moderado',
    hay_tramos_estimados: false,
    avisos: [],
    ...cambios,
  };
}

describe('TotalesDelDia', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('es');
  });

  it('muestra la duración en horas y minutos, no en minutos sueltos', () => {
    render(<TotalesDelDia itinerario={itinerario()} />);

    expect(screen.getByText('3 h 35 min')).toBeInTheDocument();
  });

  it('muestra el costo como rango y con «aprox.»', () => {
    render(<TotalesDelDia itinerario={itinerario()} />);

    expect(screen.getByText('aprox. S/ 12.00 – 19.50')).toBeInTheDocument();
  });

  it('aclara que el costo es solo del transporte', () => {
    render(<TotalesDelDia itinerario={itinerario()} />);

    expect(screen.getByText(/sin entradas ni comida/)).toBeInTheDocument();
  });

  it('muestra la subida acumulada y no el desnivel neto', () => {
    render(<TotalesDelDia itinerario={itinerario()} />);

    expect(screen.getByText('420 m de subida acumulada')).toBeInTheDocument();
  });

  it('declara que el itinerario lo calculó el optimizador', () => {
    render(<TotalesDelDia itinerario={itinerario({ generado_por: 'modelo' })} />);

    expect(screen.getByText(/optimizador de rutas \(OR-Tools\)/)).toBeInTheDocument();
  });

  it('declara cuando el itinerario salió de la alternativa por reglas', () => {
    render(<TotalesDelDia itinerario={itinerario({ generado_por: 'reglas' })} />);

    expect(screen.getByText(/alternativa por reglas \(vecino más cercano\)/)).toBeInTheDocument();
  });

  it('da la barra de esfuerzo también en palabras', () => {
    render(<TotalesDelDia itinerario={itinerario()} />);

    expect(
      screen.getByLabelText('Esfuerzo Moderado: 420 metros de subida acumulada'),
    ).toBeInTheDocument();
  });

  it('concuerda el singular cuando solo hay una parada', () => {
    const uno = itinerario({
      paradas: [
        {
          orden: 0,
          recurso_id: 1,
          nombre: 'Convento',
          distrito: 'SANTA ROSA DE OCOPA',
          categoria: null,
          latitud: -11.87,
          longitud: -75.29,
          altitud_msnm: 3384,
          hora_llegada: '08:00:00',
          hora_salida: '09:00:00',
          duracion_visita_min: 60,
          puntaje_relativo: 100,
          traslado: null,
        },
      ],
    });

    render(<TotalesDelDia itinerario={uno} />);

    expect(screen.getByText('1 parada')).toBeInTheDocument();
  });
});
