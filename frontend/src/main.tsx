/**
 * Punto de entrada del frontend.
 *
 * Aqui se montan los tres proveedores que necesita toda la aplicacion:
 * - BrowserRouter: navegacion entre paginas sin recargar el navegador.
 * - QueryClientProvider: memoria temporal de las respuestas de la API.
 * - la configuracion de i18next, que se activa con solo importarla.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from '@/App';
import '@/estilos/index.css';
import '@/i18n';

// staleTime: durante un minuto se reutiliza la respuesta guardada en vez de
// volver a preguntar a la API. Evita peticiones repetidas al cambiar de pagina.
const clienteDeConsultas = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 60_000, refetchOnWindowFocus: false },
  },
});

const contenedor = document.getElementById('raiz');

if (!contenedor) {
  throw new Error('No se encontro el elemento #raiz en index.html');
}

createRoot(contenedor).render(
  <StrictMode>
    <QueryClientProvider client={clienteDeConsultas}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
