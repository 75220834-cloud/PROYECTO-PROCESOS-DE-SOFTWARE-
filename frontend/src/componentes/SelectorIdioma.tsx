/**
 * Selector de idioma (espanol / ingles).
 *
 * Al cambiar, i18next recarga todos los textos de la interfaz al vuelo y
 * guarda la eleccion en localStorage, de modo que la proxima visita ya abre
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
    <label className="flex items-center gap-2 text-sm">
      <span className="sr-only">{t('encabezado.idioma')}</span>
      <select
        value={idiomaActual}
        onChange={(evento) => void i18n.changeLanguage(evento.target.value)}
        aria-label={t('encabezado.idioma')}
        className="rounded-lg border border-pizarra-300 bg-transparent px-2 py-1.5 text-pizarra-700 transition-colors hover:bg-pizarra-100 dark:border-pizarra-700 dark:text-pizarra-100 dark:hover:bg-pizarra-800"
      >
        {IDIOMAS_DISPONIBLES.map((idioma) => (
          <option key={idioma} value={idioma} className="text-pizarra-800">
            {nombreDelIdioma[idioma]}
          </option>
        ))}
      </select>
    </label>
  );
}
