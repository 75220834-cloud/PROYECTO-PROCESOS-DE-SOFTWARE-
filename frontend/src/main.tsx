/**
 * Punto de entrada del frontend.
 *
 * Aqui se montan los tres proveedores que necesita toda la aplicacion:
 * - ProveedorTema: unica fuente de verdad del tema claro/oscuro.
 * - BrowserRouter: navegacion entre paginas sin recargar el navegador.
 * - QueryClientProvider: memoria temporal de las respuestas de la API.
 * - la configuracion de i18next, que se activa con solo importarla.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'framer-motion';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from '@/App';
import { ProveedorSesion } from '@/componentes/ProveedorSesion';
import { ProveedorTema } from '@/componentes/ProveedorTema';
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
    {/* reducedMotion="user" hace que framer-motion respete la preferencia de
        movimiento reducido del sistema operativo. La regla equivalente que hay
        en el CSS solo afecta a las animaciones CSS; estas son de JavaScript y
        hay que configurarlas aparte. */}
    <MotionConfig reducedMotion="user">
      <ProveedorTema>
        <QueryClientProvider client={clienteDeConsultas}>
          <BrowserRouter>
            <ProveedorSesion>
              <App />
            </ProveedorSesion>
          </BrowserRouter>
        </QueryClientProvider>
      </ProveedorTema>
    </MotionConfig>
  </StrictMode>,
);
