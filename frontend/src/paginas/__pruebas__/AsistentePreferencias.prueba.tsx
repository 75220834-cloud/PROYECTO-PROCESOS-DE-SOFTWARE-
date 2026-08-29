/**
 * Pruebas del asistente de preferencias en seis pasos.
 *
 * La prueba central es `recorre los seis pasos sin haber iniciado sesión`:
 * comprueba la promesa del proyecto de que no hace falta cuenta para armar
 * el viaje.
 *
 * Se simula la API sustituyendo `fetch`, para que las pruebas no dependan de
 * que el backend esté levantado.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ProveedorSesion } from '@/componentes/ProveedorSesion';
import { ProveedorTema } from '@/componentes/ProveedorTema';
import i18n from '@/i18n';
import { AsistentePreferencias } from '@/paginas/AsistentePreferencias';

const OPCIONES = {
  intereses: [
    'naturaleza',
    'arqueologia',
    'iglesias_conventos',
    'artesania',
    'gastronomia',
    'ferias_fiestas',
    'aventura',
    'fotografia',
  ],
  movilidades: ['caminando', 'transporte_publico', 'taxi', 'combinado'],
  ritmos: ['relajado', 'moderado', 'intenso'],
  distritos: ['HUANCAYO', 'CONCEPCION', 'JAUJA', 'SAÑO'],
};

/** Guarda lo que el asistente envió a la API, para poder comprobarlo. */
let ultimoEnvio: unknown = null;

function simularApi() {
  return vi.fn(async (entrada: RequestInfo | URL, opciones?: RequestInit) => {
    const url = String(entrada);

    if (url.includes('/api/preferencias/opciones')) {
      return new Response(JSON.stringify(OPCIONES), { status: 200 });
    }

    if (url.endsWith('/api/preferencias') && opciones?.method === 'POST') {
      ultimoEnvio = JSON.parse(String(opciones.body));
      return new Response(
        JSON.stringify({ id: 77, usuario_id: null, duracion_dias: 3, ...(ultimoEnvio as object) }),
        { status: 201 },
      );
    }

    // Cualquier otra llamada (comprobar la sesión guardada) responde 401.
    return new Response(JSON.stringify({ detail: 'no' }), { status: 401 });
  });
}

/**
 * Pulsa «Siguiente».
 *
 * OJO al usarlo: el asistente monta cada paso dentro de AnimatePresence con
 * mode="wait", así que el paso que sale termina su animación ANTES de que
 * entre el siguiente. El número de paso cambia al instante, pero los campos
 * del paso nuevo tardan en aparecer. Por eso las pruebas los buscan con
 * `findBy*`, que reintenta, y no con `getBy*`, que falla de inmediato.
 */
async function avanzar() {
  await usuario.click(screen.getByRole('button', { name: 'Siguiente' }));
}

function renderizar(elemento: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <ProveedorTema>
      <QueryClientProvider client={cliente}>
        <MemoryRouter initialEntries={['/preferencias']}>
          <ProveedorSesion>{elemento}</ProveedorSesion>
        </MemoryRouter>
      </QueryClientProvider>
    </ProveedorTema>,
  );
}

describe('AsistentePreferencias', () => {
  beforeEach(async () => {
    window.localStorage.clear();
    ultimoEnvio = null;
    vi.stubGlobal('fetch', simularApi());
    await i18n.changeLanguage('es');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('empieza en el paso 1 de 6', () => {
    renderizar(<AsistentePreferencias />);

    expect(screen.getByText('Paso 1 de 6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /¿Cuándo viajas\?/ })).toBeInTheDocument();
  });

  it('la barra de progreso refleja el paso actual', async () => {
    renderizar(<AsistentePreferencias />);

    const barra = screen.getByRole('progressbar');
    expect(barra).toHaveAttribute('aria-valuenow', '1');
    expect(barra).toHaveAttribute('aria-valuemax', '6');

    await avanzar();

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
  });

  it('se puede volver atrás sin perder lo respondido', async () => {
    renderizar(<AsistentePreferencias />);

    const valorOriginal = (screen.getByLabelText('Fecha de fin') as HTMLInputElement).value;

    await avanzar();
    await usuario.click(await screen.findByRole('button', { name: 'Atrás' }));

    expect(screen.getByText('Paso 1 de 6')).toBeInTheDocument();
    const fechaFin = (await screen.findByLabelText('Fecha de fin')) as HTMLInputElement;
    expect(fechaFin.value).toBe(valorOriginal);
  });

  it('bloquea el paso 2 hasta elegir un distrito', async () => {
    renderizar(<AsistentePreferencias />);

    await avanzar();

    // Sin distrito elegido, el botón de seguir se deshabilita y se explica
    // por qué. Ambas cosas están fuera de la sección animada, así que se
    // pueden comprobar de inmediato.
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(/Elige el distrito/);
  });

  it('bloquea el paso 4 hasta marcar al menos un interés', async () => {
    renderizar(<AsistentePreferencias />);

    await avanzar();
    await usuario.selectOptions(await screen.findByLabelText(/Distrito de origen/), 'HUANCAYO');
    await avanzar();
    await screen.findByLabelText(/Presupuesto en soles/);
    await avanzar();

    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(/al menos un interés/);
  });

  it('detecta las fechas invertidas', async () => {
    renderizar(<AsistentePreferencias />);

    const inicio = screen.getByLabelText('Fecha de inicio');
    await usuario.clear(inicio);
    await usuario.type(inicio, '2027-01-01');

    expect(screen.getByRole('alert')).toHaveTextContent(/no puede ser anterior/);
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
  });

  it('recorre los seis pasos sin haber iniciado sesión y guarda la preferencia', async () => {
    /**
     * LA prueba del Incremento 2. Si falla, la aplicación está exigiendo
     * cuenta para algo que el proyecto prometió que no la necesita.
     */
    renderizar(<AsistentePreferencias />);

    // Paso 1: las fechas vienen rellenas por omisión.
    await avanzar();

    // Paso 2: distrito de origen.
    await usuario.selectOptions(await screen.findByLabelText(/Distrito de origen/), 'CONCEPCION');
    await avanzar();

    // Paso 3: el presupuesto ya trae un valor por omisión.
    await screen.findByLabelText(/Presupuesto en soles/);
    await avanzar();

    // Paso 4: intereses.
    await usuario.click(await screen.findByRole('button', { name: 'Artesanía' }));
    await usuario.click(screen.getByRole('button', { name: 'Gastronomía' }));
    await avanzar();

    // Paso 5: movilidad.
    await usuario.click(await screen.findByRole('button', { name: /Taxi/ }));
    await avanzar();

    // Paso 6: ritmo, y a guardar.
    expect(screen.getByText('Paso 6 de 6')).toBeInTheDocument();
    await usuario.click(await screen.findByRole('button', { name: /Intenso/ }));
    await usuario.click(screen.getByRole('button', { name: 'Guardar mis preferencias' }));

    await waitFor(() => expect(ultimoEnvio).not.toBeNull());

    const enviado = ultimoEnvio as Record<string, unknown>;
    expect(enviado.distrito_origen).toBe('CONCEPCION');
    expect(enviado.intereses).toEqual(['artesania', 'gastronomia']);
    expect(enviado.movilidad).toBe('taxi');
    expect(enviado.ritmo).toBe('intenso');
  });

  it('guarda en el navegador la preferencia creada sin cuenta', async () => {
    /**
     * Es lo único que permite recuperarla después y reclamarla al
     * registrarse. Sin esto, el visitante perdería su viaje al recargar.
     */
    renderizar(<AsistentePreferencias />);

    await avanzar();
    await usuario.selectOptions(await screen.findByLabelText(/Distrito de origen/), 'HUANCAYO');
    await avanzar();
    await screen.findByLabelText(/Presupuesto en soles/);
    await avanzar();
    await usuario.click(await screen.findByRole('button', { name: 'Naturaleza' }));
    await avanzar();
    await screen.findByRole('button', { name: /Taxi/ });
    await avanzar();
    await usuario.click(await screen.findByRole('button', { name: 'Guardar mis preferencias' }));

    await waitFor(() => expect(window.localStorage.getItem('rutaviva.preferencia')).toBe('77'));
  });

  it('permite marcar y desmarcar un interés', async () => {
    renderizar(<AsistentePreferencias />);

    await avanzar();
    await usuario.selectOptions(await screen.findByLabelText(/Distrito de origen/), 'JAUJA');
    await avanzar();
    await screen.findByLabelText(/Presupuesto en soles/);
    await avanzar();

    const aventura = await screen.findByRole('button', { name: 'Aventura' });

    await usuario.click(aventura);
    expect(aventura).toHaveAttribute('aria-pressed', 'true');

    await usuario.click(aventura);
    expect(aventura).toHaveAttribute('aria-pressed', 'false');
  });
});
