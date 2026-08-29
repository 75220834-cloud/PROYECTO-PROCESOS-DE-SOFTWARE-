/**
 * Barra superior de la aplicacion: logotipo, nombre y los dos controles
 * globales (idioma y tema). Se mantiene visible en todas las paginas.
 */
import { useTranslation } from 'react-i18next';

import { InterruptorTema } from '@/componentes/InterruptorTema';
import { SelectorIdioma } from '@/componentes/SelectorIdioma';

export function Encabezado() {
  const { t } = useTranslation();

  return (
    <header className="sticky top-0 z-10 border-b border-pizarra-100 bg-white/90 backdrop-blur dark:border-pizarra-800 dark:bg-pizarra-900/90">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <img
            src="/logo_rutavivamantaro.png"
            alt={t('aplicacion.logotipo_alternativo')}
            className="h-10 w-10 rounded-lg object-contain"
          />
          <div>
            <p className="text-lg leading-tight font-semibold text-valle-700 dark:text-valle-300">
              {t('aplicacion.nombre')}
            </p>
            <p className="text-xs text-pizarra-500 dark:text-pizarra-300">{t('aplicacion.lema')}</p>
          </div>
        </div>

        <nav className="flex items-center gap-2">
          <SelectorIdioma />
          <InterruptorTema />
        </nav>
      </div>
    </header>
  );
}
