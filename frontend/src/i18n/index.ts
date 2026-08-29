/**
 * Configuracion de i18next, el sistema de traducciones.
 *
 * Regla del proyecto: ningun texto visible se escribe directamente en un
 * componente. Todo pasa por t('clave'), de modo que anadir un idioma sea
 * anadir un archivo JSON y no reescribir la interfaz.
 *
 * Las CLAVES estan en espanol (idioma del proyecto). Los VALORES son el texto
 * traducido de cada idioma.
 */
import i18n from 'i18next';
import DetectorDeIdioma from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import es from './es.json';

export const IDIOMAS_DISPONIBLES = ['es', 'en'] as const;
export type Idioma = (typeof IDIOMAS_DISPONIBLES)[number];

/** Clave con la que se recuerda el idioma elegido en el navegador. */
export const CLAVE_IDIOMA = 'rutaviva.idioma';

void i18n
  // Detecta el idioma: primero lo que el usuario eligio antes (guardado en
  // localStorage), y si nunca eligio, el idioma del navegador.
  .use(DetectorDeIdioma)
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
    },
    fallbackLng: 'es',
    supportedLngs: IDIOMAS_DISPONIBLES,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: CLAVE_IDIOMA,
      caches: ['localStorage'],
    },
    interpolation: {
      // React ya escapa el HTML por su cuenta; hacerlo dos veces romperia
      // los acentos y las comillas.
      escapeValue: false,
    },
  });

export default i18n;
