/**
 * Componente raiz: define el esqueleto comun (encabezado y pie) y las rutas.
 *
 * En la Fase 0 solo existe la pagina de inicio. El enrutador ya esta montado
 * para que anadir /catalogo, /preferencias o /itinerario en las siguientes
 * fases sea agregar una linea, no reestructurar la aplicacion.
 */
import { Route, Routes } from 'react-router-dom';

import { Encabezado } from '@/componentes/Encabezado';
import { Inicio } from '@/paginas/Inicio';

export function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Encabezado />

      <div className="flex-1">
        <Routes>
          <Route path="/" element={<Inicio />} />
        </Routes>
      </div>

      <footer className="border-t border-pizarra-100 px-4 py-6 text-center text-xs text-pizarra-500 dark:border-pizarra-800 dark:text-pizarra-300">
        RutaVivaMantaro · Universidad Continental · Procesos de Software
      </footer>
    </div>
  );
}
