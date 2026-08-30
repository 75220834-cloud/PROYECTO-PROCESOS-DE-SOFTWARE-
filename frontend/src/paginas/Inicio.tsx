/**
 * Página de inicio.
 *
 * Sigue el diseño de la pantalla «Inicio» de Stitch: etiqueta de región,
 * título grande, subtítulo, botón principal, y las tres tarjetas que explican
 * cómo funciona la plataforma.
 *
 * Las secciones de atractivos destacados y de provincias con foto llegan en
 * la Fase 1, cuando exista el catálogo real. No se ponen datos inventados
 * mientras tanto: es la regla de honestidad con los datos del proyecto.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

import { consultarSalud, type SaludComponente } from '@/servicios/api';

/** Iconos de los tres pasos. Dibujados en SVG, sin dependencias externas. */
const ICONOS_PASOS = [
  // Paso 1 — corazón: lo que te gusta
  <path
    key="1"
    d="M20.8 8.6a5 5 0 0 0-8.8-2.9A5 5 0 0 0 3.2 8.6c0 5 8.8 10.4 8.8 10.4s8.8-5.4 8.8-10.4z"
  />,
  // Paso 2 — mapa con ruta
  <path key="2" d="M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 7 9 4zm0 0v13m6-10v12.5" />,
  // Paso 3 — apretón de manos / coordinación
  <path key="3" d="M4 12h3l3 3 2-2 3 3h3M2 8h5m10 0h5M7 8v8m10-8v8" />,
];

function IndicadorEstado({ componente }: { componente: SaludComponente }) {
  const { t } = useTranslation();
  const esOperativo = componente.estado === 'operativo';

  return (
    <span
      title={componente.detalle}
      className={
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ' +
        (esOperativo
          ? 'bg-secundario-contenedor text-sobre-secundario-contenedor'
          : 'bg-error-contenedor text-sobre-error-contenedor')
      }
    >
      <span
        aria-hidden="true"
        className={'h-2 w-2 rounded-full ' + (esOperativo ? 'bg-secundario' : 'bg-error')}
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

  const pasos = [1, 2, 3] as const;

  return (
    <main>
      {/* ---------------------------------------------------------------
          Sección principal (héroe)
          --------------------------------------------------------------- */}
      <section className="bg-superficie-contenedor-bajo">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-28"
        >
          <span className="inline-block rounded-full bg-terciario-contenedor px-3 py-1 text-xs font-semibold tracking-wide text-sobre-terciario-contenedor">
            {t('inicio.etiqueta_region')}
          </span>

          <h1 className="mt-6 font-titulo text-4xl font-extrabold text-balance text-sobre-superficie sm:text-5xl">
            {t('inicio.titulo')}
          </h1>

          <p className="mx-auto mt-5 max-w-xl text-lg text-sobre-superficie-variante">
            {t('inicio.subtitulo')}
          </p>

          <button
            type="button"
            className="mt-9 rounded-md bg-primario px-8 py-3.5 font-semibold text-sobre-primario shadow-elevada transition-transform hover:-translate-y-0.5"
          >
            {t('inicio.planificar')}
          </button>

          {/* El div envolvente fuerza un salto de linea: sin el, la etiqueta
              quedaria al costado del boton, porque ambos son inline-block. */}
          <div className="mt-8">
            <p className="inline-block rounded-full bg-superficie-contenedor-alto px-3 py-1 text-xs text-sobre-superficie-variante">
              {t('inicio.aviso_datos')}
            </p>
          </div>
        </motion.div>
      </section>

      <div className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        {/* ---------------------------------------------------------------
            Cómo funciona: tres pasos
            --------------------------------------------------------------- */}
        <section aria-labelledby="titulo-como-funciona">
          <h2
            id="titulo-como-funciona"
            className="text-center font-titulo text-2xl font-bold text-sobre-superficie"
          >
            {t('inicio.como_funciona')}
          </h2>

          <ol className="mt-10 grid gap-6 md:grid-cols-3">
            {pasos.map((numero, indice) => (
              <motion.li
                key={numero}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: indice * 0.1 }}
                className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-6 shadow-suave"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primario-suave text-primario">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-5 w-5"
                    aria-hidden="true"
                  >
                    {ICONOS_PASOS[indice]}
                  </svg>
                </span>

                <h3 className="mt-4 font-titulo text-lg font-semibold text-sobre-superficie">
                  {numero}. {t(`inicio.paso_${numero}_titulo`)}
                </h3>

                <p className="mt-2 text-sm text-sobre-superficie-variante">
                  {t(`inicio.paso_${numero}_texto`)}
                </p>
              </motion.li>
            ))}
          </ol>
        </section>

        {/* ---------------------------------------------------------------
            Estado de la plataforma.
            Comprobación visible de que el frontend habla con el backend.
            --------------------------------------------------------------- */}
        <section
          aria-labelledby="titulo-estado"
          className="mt-16 rounded-lg border border-contorno-variante bg-superficie-contenedor p-6"
        >
          <h2
            id="titulo-estado"
            className="font-titulo text-lg font-semibold text-sobre-superficie"
          >
            {t('estado.titulo')}
          </h2>

          {isLoading && (
            <p className="mt-4 text-sm text-sobre-superficie-variante">{t('estado.cargando')}</p>
          )}

          {isError && <p className="mt-4 text-sm text-error">{t('estado.error')}</p>}

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
                  <dt className="text-sm text-sobre-superficie-variante">{t(clave)}</dt>
                  <dd>
                    <IndicadorEstado componente={componente} />
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      </div>
    </main>
  );
}
