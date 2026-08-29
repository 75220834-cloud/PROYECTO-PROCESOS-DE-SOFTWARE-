/**
 * Selector de idioma (español / inglés).
 *
 * Al cambiar, i18next recarga todos los textos de la interfaz al vuelo y
 * guarda la elección en el navegador, de modo que la próxima visita ya abra
 * en el idioma elegido.
 */
import { useTranslation } from 'react-i18next';

import { IDIOMAS_DISPONIBLES, type Idioma } from '@/i18n';

export function SelectorIdioma() {
  const { t, i18n } = useTranslation();

  // i18next puede devolver 'es-PE' o 'en-US'; nos quedamos con las dos
  // primeras letras para que coincida con nuestras opciones.
  const idiomaActual = (i18n.resolvedLanguage ?? 'es').slice(0, 2) as Idioma;

  const nombreDelIdioma: Record<Idioma, string> = {
    es: t('encabezado.espanol'),
    en: t('encabezado.ingles'),
  };

  return (
    <label className="flex items-center gap-1.5 text-sm text-sobre-superficie-variante">
      {/* Icono de globo terráqueo, como en el diseño de Stitch. */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="h-4 w-4 shrink-0"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18z" />
      </svg>

      <span className="sr-only">{t('encabezado.idioma')}</span>

      <select
        value={idiomaActual}
        onChange={(evento) => void i18n.changeLanguage(evento.target.value)}
        aria-label={t('encabezado.idioma')}
        className="cursor-pointer rounded-md bg-transparent py-1 pr-1 font-medium transition-colors hover:text-primario focus:outline-2 focus:outline-offset-2 focus:outline-primario"
      >
        {IDIOMAS_DISPONIBLES.map((idioma) => (
          <option key={idioma} value={idioma} className="bg-superficie text-sobre-superficie">
            {nombreDelIdioma[idioma]}
          </option>
        ))}
      </select>
    </label>
  );
}
