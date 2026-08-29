/**
 * Componente raíz: define el esqueleto común (encabezado y pie) y las rutas.
 *
 * Rutas existentes: inicio, catálogo, detalle de recurso, asistente de
 * preferencias, acceso y «Mis viajes». El itinerario llega en la Fase 4.
 */
import { useTranslation } from 'react-i18next';
import { Route, Routes } from 'react-router-dom';

import { Encabezado } from '@/componentes/Encabezado';
import { Acceso } from '@/paginas/Acceso';
import { AsistentePreferencias } from '@/paginas/AsistentePreferencias';
import { Catalogo } from '@/paginas/Catalogo';
import { DetalleRecurso } from '@/paginas/DetalleRecurso';
import { Inicio } from '@/paginas/Inicio';
import { MisViajes } from '@/paginas/MisViajes';
import { PreferenciaGuardada } from '@/paginas/PreferenciaGuardada';

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
          <Route path="/acceso" element={<Acceso />} />
          <Route path="/mis-viajes" element={<MisViajes />} />
        </Routes>
      </div>

      <Pie />
    </div>
  );
}
