/**
 * Pagina de inicio.
 *
 * En la Fase 0 solo presenta el proyecto y muestra el estado de los tres
 * componentes de la plataforma. Sirve como comprobacion visible de que el
 * frontend habla con el backend, y de que las traducciones funcionan.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

import { consultarSalud, type SaludComponente } from '@/servicios/api';

function IndicadorEstado({ componente }: { componente: SaludComponente }) {
  const { t } = useTranslation();
  const esOperativo = componente.estado === 'operativo';

  return (
    <span
      title={componente.detalle}
      className={
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ' +
        (esOperativo
          ? 'bg-valle-100 text-valle-700 dark:bg-valle-900 dark:text-valle-300'
          : 'bg-tierra-100 text-tierra-700 dark:bg-tierra-700 dark:text-tierra-100')
      }
    >
      <span
        aria-hidden="true"
        className={'h-2 w-2 rounded-full ' + (esOperativo ? 'bg-valle-500' : 'bg-tierra-500')}
      />
      {esOperativo ? t('estado.operativo') : t('estado.no_disponible')}
    </span>
  );
}

export function Inicio() {
  const { t } = useTranslation();

  // TanStack Query se encarga de la carga, los reintentos y la memoria
  // temporal. No hace falta escribir useEffect ni estados de carga a mano.
  const {
    data: salud,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['salud'],
    queryFn: consultarSalud,
    retry: 1,
  });

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto max-w-5xl px-4 py-12"
    >
      <h1 className="text-3xl font-bold text-pizarra-700 sm:text-4xl dark:text-pizarra-100">
        {t('inicio.titulo')}
      </h1>

      <p className="mt-4 max-w-2xl text-pizarra-500 dark:text-pizarra-300">
        {t('inicio.descripcion')}
      </p>

      <p className="mt-6 inline-block rounded-lg bg-tierra-100 px-3 py-1.5 text-sm text-tierra-700 dark:bg-pizarra-800 dark:text-tierra-300">
        {t('inicio.en_construccion')}
      </p>

      <section className="mt-12 rounded-xl border border-pizarra-100 bg-white p-6 dark:border-pizarra-800 dark:bg-pizarra-800">
        <h2 className="text-lg font-semibold text-pizarra-700 dark:text-pizarra-100">
          {t('estado.titulo')}
        </h2>

        {isLoading && (
          <p className="mt-4 text-sm text-pizarra-500 dark:text-pizarra-300">
            {t('estado.cargando')}
          </p>
        )}

        {isError && (
          <p className="mt-4 text-sm text-tierra-700 dark:text-tierra-300">{t('estado.error')}</p>
        )}

        {salud && (
          <dl className="mt-4 space-y-3">
            {(
              [
                ['estado.api', salud.api],
                ['estado.base_datos', salud.base_datos],
                ['estado.asistente', salud.ollama],
              ] as const
            ).map(([clave, componente]) => (
              <div key={clave} className="flex items-center justify-between gap-4">
                <dt className="text-sm text-pizarra-500 dark:text-pizarra-300">{t(clave)}</dt>
                <dd>
                  <IndicadorEstado componente={componente} />
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </motion.main>
  );
}
