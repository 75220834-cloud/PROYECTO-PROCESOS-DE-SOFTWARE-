/**
 * Componente raíz: define el esqueleto común (encabezado y pie) y las rutas.
 *
 * Rutas existentes: inicio, catálogo, detalle de recurso, asistente de
 * preferencias, resultados, itinerario, valoración, acceso, «Mis viajes»,
 * coordinación y panel del gestor.
 *
 * El asistente conversacional cuelga fuera del enrutador porque está
 * disponible en todas las pantallas.
 */
import { useTranslation } from 'react-i18next';
import { Route, Routes } from 'react-router-dom';

import { Encabezado } from '@/componentes/Encabezado';
import { PanelConversacion } from '@/componentes/PanelConversacion';
import { Acceso } from '@/paginas/Acceso';
import { AsistentePreferencias } from '@/paginas/AsistentePreferencias';
import { Catalogo } from '@/paginas/Catalogo';
import { Coordinacion } from '@/paginas/Coordinacion';
import { DetalleRecurso } from '@/paginas/DetalleRecurso';
import { Inicio } from '@/paginas/Inicio';
import { Itinerario } from '@/paginas/Itinerario';
import { MisViajes } from '@/paginas/MisViajes';
import { Panel } from '@/paginas/Panel';
import { PreferenciaGuardada } from '@/paginas/PreferenciaGuardada';
import { Resultados } from '@/paginas/Resultados';
import { Valorar } from '@/paginas/Valorar';

function Pie() {
  const { t } = useTranslation();

  const enlaces = ['pie.privacidad', 'pie.terminos', 'pie.soporte', 'pie.cultura'] as const;

  return (
    <footer className="mt-auto bg-superficie-contenedor-maximo">
      {/* Greca wanka como borde superior del pie: el sistema de diseño la
          propone justamente como divisor de sección. */}
      <div className="greca-wanka h-1.5 w-full" aria-hidden="true" />

      <div className="mx-auto flex max-w-contenido flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <img
              src="/logo_rutavivamantaro.png"
              alt=""
              aria-hidden="true"
              className="h-8 w-8 rounded-md object-contain"
            />
            <span className="font-titulo font-extrabold text-secundario">
              {t('aplicacion.nombre')}
            </span>
          </div>

          <p className="mt-3 max-w-xs text-sm text-sobre-superficie-variante">
            {t('pie.derechos')}
          </p>

          <p className="mt-1 text-xs text-sobre-superficie-variante">{t('pie.curso')}</p>
        </div>

        <ul className="flex flex-wrap gap-x-6 gap-y-2">
          {enlaces.map((clave) => (
            <li key={clave}>
              <span className="text-sm text-sobre-superficie-variante">{t(clave)}</span>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}

export function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Encabezado />

      <div className="flex-1">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/explorar" element={<Catalogo />} />
          <Route path="/recursos/:id" element={<DetalleRecurso />} />
          <Route path="/preferencias" element={<AsistentePreferencias />} />
          <Route path="/preferencias/:id" element={<PreferenciaGuardada />} />
          <Route path="/preferencias/:id/resultados" element={<Resultados />} />
          <Route path="/preferencias/:id/itinerario" element={<Itinerario />} />
          <Route path="/preferencias/:id/valorar" element={<Valorar />} />
          <Route path="/acceso" element={<Acceso />} />
          <Route path="/mis-viajes" element={<MisViajes />} />
          <Route path="/coordinar" element={<Coordinacion />} />
          <Route path="/panel" element={<Panel />} />
        </Routes>
      </div>

      <Pie />

      {/* Fuera del enrutador a propósito: el asistente acompaña al visitante
          en cualquier pantalla. Es capa de interacción sobre lo que ya hacen
          los Incrementos 2, 3 y 4, no una pantalla más. */}
      <PanelConversacion />
    </div>
  );
}
