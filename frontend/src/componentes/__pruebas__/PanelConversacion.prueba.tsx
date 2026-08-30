/**
 * Pruebas del asistente conversacional.
 *
 * Lo que aquí se comprueba no es que el modelo responda bien —eso no es
 * determinista y no se puede fijar con un `expect`—, sino las tres cosas de
 * las que sí responde la interfaz:
 *
 * 1. Que **se vea de dónde salió la respuesta**. Enseñar qué funciones se
 *    ejecutaron es lo que hace la conversación auditable: sin eso, la palabra
 *    del modelo es lo único que sostiene lo que dice.
 * 2. Que **si Ollama no está, se diga y se ofrezca el formulario**. El plan de
 *    trabajo lo exige con esas palabras: no fallar en silencio.
 * 3. Que **la advertencia sobre los datos esté siempre a la vista**, porque el
 *    visitante puede llegar aquí desde cualquier pantalla sin haber leído nada
 *    sobre de dónde salen los precios.
 *
 * Se simula `fetch` para no depender de que el backend ni Ollama estén
 * levantados: estas pruebas tienen que correr en cualquier máquina.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import usuario from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PanelConversacion } from '@/componentes/PanelConversacion';
import i18n from '@/i18n';

/** Lo que el panel envió al backend, para poder comprobarlo. */
let ultimoEnvio: { mensajes: { rol: string; contenido: string }[]; idioma: string } | null = null;

/**
 * Simula la API del asistente.
 *
 * `disponible` decide si Ollama está; `respuesta` es lo que contesta el modelo
 * y qué funciones dice haber ejecutado.
 */
function simularApi(
  disponible: boolean,
  respuesta: { mensaje: string; funciones: { nombre: string; argumentos: object }[] } = {
    mensaje: 'El Convento de Santa Rosa de Ocopa está en Concepción.',
    funciones: [{ nombre: 'buscar_recursos', argumentos: { texto: 'ocopa' } }],
  },
) {
  return vi.fn(async (entrada: RequestInfo | URL, opciones?: RequestInit) => {
    const url = String(entrada);

    if (url.includes('/api/asistente/estado')) {
      return new Response(
        JSON.stringify({
          disponible,
          modelo: 'qwen2.5:7b-instruct',
          motivo: disponible ? null : 'Ollama no responde en http://localhost:11434',
        }),
        { status: 200 },
      );
    }

    if (url.includes('/api/asistente/mensaje')) {
      ultimoEnvio = JSON.parse(String(opciones?.body));
      return new Response(
        JSON.stringify({
          mensaje: respuesta.mensaje,
          funciones_usadas: respuesta.funciones,
          preferencia_id: null,
          esta_disponible: true,
          aviso: null,
        }),
        { status: 200 },
      );
    }

    throw new Error(`La prueba no esperaba una llamada a ${url}`);
  });
}

function montar() {
  // Sin reintentos: si una consulta falla en una prueba, tiene que fallar ya y
  // no tres veces más tarde, cuando la prueba ya terminó.
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  function Envoltura({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={cliente}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  }

  return render(<PanelConversacion />, { wrapper: Envoltura });
}

describe('PanelConversacion', () => {
  beforeEach(async () => {
    ultimoEnvio = null;
    await i18n.changeLanguage('es');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('abrir y cerrar', () => {
    it('empieza cerrado: es una ayuda, no una interrupción', () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('el botón dice qué hace, aunque solo tenga un icono', () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      // Sin esto, un lector de pantalla anuncia «botón» y ya está.
      expect(screen.getByRole('button', { name: 'Abrir el asistente' })).toBeInTheDocument();
    });

    it('se abre al pulsarlo', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('se cierra con Escape', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.keyboard('{Escape}');

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });
  });

  describe('la conversación', () => {
    it('envía lo que se escribe y enseña la respuesta', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.type(screen.getByLabelText('Escribe tu pregunta…'), 'Busca el Convento');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      expect(await screen.findByText(/Convento de Santa Rosa de Ocopa/)).toBeInTheDocument();
    });

    it('manda la conversación entera, no solo el último mensaje', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      const campo = screen.getByLabelText('Escribe tu pregunta…');

      await usuario.type(campo, 'Hola');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));
      await screen.findByText(/Convento de Santa Rosa de Ocopa/);

      await usuario.type(campo, '¿Y cuánto cuesta?');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      // Tres turnos: la pregunta, la respuesta y la repregunta. Sin el turno
      // del medio, el modelo no sabe a qué se refiere «cuánto cuesta».
      await waitFor(() => expect(ultimoEnvio?.mensajes).toHaveLength(3));
      expect(ultimoEnvio?.mensajes[1].rol).toBe('assistant');
    });

    it('no deja enviar una pregunta vacía', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled();
    });

    it('rellena el campo al pulsar un ejemplo', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.click(screen.getByRole('button', { name: 'Busca el Convento de Ocopa' }));

      expect(screen.getByLabelText('Escribe tu pregunta…')).toHaveValue(
        'Busca el Convento de Ocopa',
      );
    });

    it('avisa si no se pudo contactar con el asistente', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(async (entrada: RequestInfo | URL) => {
          if (String(entrada).includes('/estado')) {
            return new Response(
              JSON.stringify({ disponible: true, modelo: 'qwen2.5:7b-instruct', motivo: null }),
              { status: 200 },
            );
          }
          throw new Error('la red falló');
        }),
      );
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.type(screen.getByLabelText('Escribe tu pregunta…'), 'Hola');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      expect(await screen.findByText(/No se pudo contactar con el asistente/)).toBeInTheDocument();
    });
  });

  describe('la conversación es auditable', () => {
    it('enseña qué funciones se ejecutaron para responder', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.type(screen.getByLabelText('Escribe tu pregunta…'), 'Busca el Convento');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      // Es lo que permite comprobar que la respuesta salió del catálogo y no
      // de la imaginación del modelo.
      expect(await screen.findByText('consultó el catálogo')).toBeInTheDocument();
    });

    it('traduce el nombre técnico a algo que se entienda', async () => {
      vi.stubGlobal(
        'fetch',
        simularApi(true, {
          mensaje: 'Te armé el itinerario.',
          funciones: [
            { nombre: 'crear_preferencia', argumentos: {} },
            { nombre: 'construir_itinerario', argumentos: {} },
          ],
        }),
      );
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.type(screen.getByLabelText('Escribe tu pregunta…'), 'Ármame un día');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      expect(await screen.findByText('guardó tus preferencias')).toBeInTheDocument();
      expect(screen.getByText('armó el itinerario')).toBeInTheDocument();
    });

    it('no enseña nada si el modelo respondió sin consultar', async () => {
      // Es información honesta: significa que esa respuesta no está respaldada
      // por ninguna consulta al catálogo.
      vi.stubGlobal(
        'fetch',
        simularApi(true, { mensaje: 'Puedo buscarte sitios del valle.', funciones: [] }),
      );
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));
      await usuario.type(screen.getByLabelText('Escribe tu pregunta…'), 'Hola');
      await usuario.click(screen.getByRole('button', { name: 'Enviar' }));

      await screen.findByText('Puedo buscarte sitios del valle.');
      expect(screen.queryByText('consultó el catálogo')).not.toBeInTheDocument();
    });
  });

  describe('honestidad con los datos', () => {
    it('avisa siempre de dónde salen los datos y qué son los precios', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      const advertencia = screen.getByText(/Inventario Nacional de Recursos Turísticos/);

      expect(advertencia).toBeInTheDocument();
      expect(advertencia.textContent).toContain('estimaciones');
    });
  });

  describe('cuando Ollama no está', () => {
    it('lo dice en vez de quedarse pensando', async () => {
      vi.stubGlobal('fetch', simularApi(false));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      expect(
        await screen.findByText('El asistente no está disponible ahora mismo.'),
      ).toBeInTheDocument();
    });

    it('explica el motivo técnico, para quien tenga que arreglarlo', async () => {
      vi.stubGlobal('fetch', simularApi(false));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      expect(await screen.findByText(/Ollama no responde/)).toBeInTheDocument();
    });

    it('ofrece el camino por formulario', async () => {
      vi.stubGlobal('fetch', simularApi(false));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      // El asistente es capa de interacción: si se cae, no se pierde ninguna
      // capacidad del sistema, solo una manera cómoda de pedirla.
      const enlace = await screen.findByRole('link', {
        name: 'Planifica tu viaje con el formulario',
      });

      expect(enlace).toHaveAttribute('href', '/preferencias');
    });

    it('no deja escribir, para no dar falsas esperanzas', async () => {
      vi.stubGlobal('fetch', simularApi(false));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Abrir el asistente' }));

      await waitFor(() => expect(screen.getByLabelText('Escribe tu pregunta…')).toBeDisabled());
    });
  });

  describe('en inglés', () => {
    beforeEach(async () => {
      await i18n.changeLanguage('en');
    });

    it('el panel entero está traducido', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Open the assistant' }));

      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
      expect(screen.getByLabelText('Type your question…')).toBeInTheDocument();
    });

    it('le dice al backend en qué idioma responder', async () => {
      vi.stubGlobal('fetch', simularApi(true));
      montar();

      await usuario.click(screen.getByRole('button', { name: 'Open the assistant' }));
      await usuario.type(screen.getByLabelText('Type your question…'), 'What can I visit?');
      await usuario.click(screen.getByRole('button', { name: 'Send' }));

      await waitFor(() => expect(ultimoEnvio?.idioma).toBe('en'));
    });
  });
});
