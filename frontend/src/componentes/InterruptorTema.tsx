/**
 * Botón que alterna entre tema claro y oscuro.
 *
 * Detalle de accesibilidad: el botón no lleva texto visible, solo un icono,
 * así que necesita aria-label y title para que un lector de pantalla y el
 * texto emergente del ratón digan qué hace. Ese texto pasa por i18n.
 */
import { useTranslation } from 'react-i18next';

import { useTema } from '@/hooks/useTema';

export function InterruptorTema() {
  const { t } = useTranslation();
  const { tema, alternarTema } = useTema();

  const esOscuro = tema === 'oscuro';
  const etiqueta = esOscuro ? t('encabezado.cambiar_a_claro') : t('encabezado.cambiar_a_oscuro');

  return (
    <button
      type="button"
      onClick={alternarTema}
      aria-label={etiqueta}
      title={etiqueta}
      className="rounded-md p-2 text-sobre-superficie-variante transition-colors hover:bg-superficie-contenedor-alto hover:text-primario"
    >
      {/* Iconos dibujados con SVG: no añaden ninguna dependencia y heredan el
          color del texto gracias a stroke="currentColor". */}
      {esOscuro ? (
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
          {/* Sol */}
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
          aria-hidden="true"
        >
          {/* Luna */}
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  );
}
