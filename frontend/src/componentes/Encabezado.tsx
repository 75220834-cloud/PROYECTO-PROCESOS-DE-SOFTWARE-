/**
 * Barra superior de la aplicación.
 *
 * Sigue la estructura del diseño «Mantaro Moderno» de Stitch: logotipo a la
 * izquierda, navegación al centro y, a la derecha, selector de idioma,
 * interruptor de tema y el botón de iniciar sesión.
 *
 * En pantallas pequeñas la navegación central se oculta y aparece un menú
 * desplegable, para que los controles no se amontonen.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';

import { InterruptorTema } from '@/componentes/InterruptorTema';
import { SelectorIdioma } from '@/componentes/SelectorIdioma';

/** Enlaces de la navegación principal. La clave es la que traduce i18n. */
const ENLACES = [
  { ruta: '/', clave: 'navegacion.inicio' },
  { ruta: '/explorar', clave: 'navegacion.explorar' },
  { ruta: '/mis-viajes', clave: 'navegacion.mis_viajes' },
] as const;

function clasesDelEnlace({ isActive }: { isActive: boolean }): string {
  const base = 'rounded-md px-3 py-2 text-sm font-semibold transition-colors';
  // El enlace activo se marca en terracota; los demás en el gris cálido del
  // texto secundario.
  return isActive
    ? `${base} text-primario`
    : `${base} text-sobre-superficie-variante hover:text-primario`;
}

export function Encabezado() {
  const { t } = useTranslation();
  const [menuAbierto, establecerMenuAbierto] = useState(false);

  return (
    <header className="sticky top-0 z-20 border-b border-contorno-variante bg-superficie/90 backdrop-blur">
      <div className="mx-auto flex max-w-contenido items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* Logotipo */}
        <NavLink to="/" className="flex shrink-0 items-center gap-2.5">
          <img
            src="/logo_rutavivamantaro.png"
            alt={t('aplicacion.logotipo_alternativo')}
            className="h-9 w-9 rounded-md object-contain"
          />
          <span className="font-titulo text-lg font-extrabold text-secundario">
            {t('aplicacion.nombre')}
          </span>
        </NavLink>

        {/* Navegación central: solo en pantallas medianas hacia arriba. */}
        <nav className="hidden items-center gap-1 md:flex">
          {ENLACES.map((enlace) => (
            <NavLink key={enlace.ruta} to={enlace.ruta} className={clasesDelEnlace} end>
              {t(enlace.clave)}
            </NavLink>
          ))}
        </nav>

        {/* Controles de la derecha */}
        <div className="flex items-center gap-1 sm:gap-2">
          <div className="hidden sm:block">
            <SelectorIdioma />
          </div>

          <InterruptorTema />

          <button
            type="button"
            className="hidden rounded-md bg-primario px-4 py-2 text-sm font-semibold text-sobre-primario shadow-suave transition-transform hover:-translate-y-0.5 sm:block"
          >
            {t('navegacion.iniciar_sesion')}
          </button>

          {/* Botón de menú: solo en pantallas pequeñas. */}
          <button
            type="button"
            onClick={() => establecerMenuAbierto((abierto) => !abierto)}
            aria-expanded={menuAbierto}
            aria-label={menuAbierto ? t('navegacion.cerrar_menu') : t('navegacion.abrir_menu')}
            className="rounded-md p-2 text-sobre-superficie-variante transition-colors hover:bg-superficie-contenedor-alto md:hidden"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-5 w-5"
              aria-hidden="true"
            >
              {menuAbierto ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Menú desplegable de pantallas pequeñas */}
      {menuAbierto && (
        <nav className="border-t border-contorno-variante bg-superficie-contenedor-bajo px-4 py-3 md:hidden">
          <ul className="flex flex-col gap-1">
            {ENLACES.map((enlace) => (
              <li key={enlace.ruta}>
                <NavLink
                  to={enlace.ruta}
                  className={clasesDelEnlace}
                  onClick={() => establecerMenuAbierto(false)}
                  end
                >
                  {t(enlace.clave)}
                </NavLink>
              </li>
            ))}
          </ul>

          <div className="mt-3 flex items-center justify-between border-t border-contorno-variante pt-3 sm:hidden">
            <SelectorIdioma />
            <button
              type="button"
              className="rounded-md bg-primario px-4 py-2 text-sm font-semibold text-sobre-primario"
            >
              {t('navegacion.iniciar_sesion')}
            </button>
          </div>
        </nav>
      )}

      {/* Greca wanka: una franja fina bajo el encabezado, como acento
          arquitectónico. El sistema de diseño la pide como detalle, nunca
          como fondo. */}
      <div className="greca-wanka h-1.5 w-full" aria-hidden="true" />
    </header>
  );
}
