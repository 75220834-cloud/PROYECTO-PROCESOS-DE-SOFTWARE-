/**
 * Confirmación de que la preferencia quedó registrada.
 *
 * Es la pantalla donde se cierra el recorrido del Incremento 2: se muestra lo
 * que el visitante pidió y, **solo aquí**, se le ofrece crear una cuenta para
 * guardarlo. Nunca antes.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { ResumenPreferencia } from '@/componentes/ResumenPreferencia';
import { useSesion } from '@/hooks/useSesion';
import { obtenerPreferencia } from '@/servicios/api';

export function PreferenciaGuardada() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { token, usuario } = useSesion();

  const identificador = Number(id);

  const {
    data: preferencia,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['preferencia', identificador],
    queryFn: () => obtenerPreferencia(identificador, token),
    enabled: Number.isFinite(identificador),
  });

  if (isLoading) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('catalogo.cargando')}</p>
      </main>
    );
  }

  if (isError || !preferencia) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <p className="text-error">{t('preferencia.no_encontrada')}</p>
        <Link
          to="/preferencias"
          className="mt-4 inline-block font-semibold text-primario underline"
        >
          {t('preferencia.empezar_de_nuevo')}
        </Link>
      </main>
    );
  }

  return (
    <motion.main
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="mx-auto max-w-2xl px-4 py-12 sm:px-6"
    >
      <span className="inline-block rounded-full bg-secundario-contenedor px-3 py-1 text-xs font-semibold text-sobre-secundario-contenedor">
        {t('preferencia.registrada')}
      </span>

      <h1 className="mt-5 font-titulo text-3xl font-extrabold text-balance text-sobre-superficie">
        {t('preferencia.titulo')}
      </h1>

      <p className="mt-3 text-sobre-superficie-variante">{t('preferencia.subtitulo')}</p>

      <section
        aria-label={t('preferencia.resumen')}
        className="mt-8 rounded-lg border border-contorno-variante bg-superficie-contenedor-bajo p-6"
      >
        <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
          {t('preferencia.resumen')}
        </h2>

        <div className="mt-4">
          <ResumenPreferencia preferencia={preferencia} />
        </div>
      </section>

      {/* Aquí, y solo aquí, se ofrece la cuenta. */}
      {preferencia.usuario_id === null && !usuario && (
        <section className="mt-8 rounded-lg border-2 border-primario bg-primario-suave p-6">
          <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
            {t('preferencia.guardar_titulo')}
          </h2>
          <p className="mt-2 text-sm text-sobre-superficie-variante">
            {t('preferencia.guardar_texto')}
          </p>

          <Link
            to="/acceso"
            className="mt-4 inline-block rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario shadow-suave transition-transform hover:-translate-y-0.5"
          >
            {t('preferencia.crear_cuenta')}
          </Link>
        </section>
      )}

      <nav className="mt-10 flex flex-wrap gap-3">
        <Link
          to="/preferencias"
          className="rounded-md border border-contorno-variante px-5 py-2.5 font-semibold text-sobre-superficie transition-colors hover:border-primario hover:text-primario"
        >
          {t('preferencia.cambiar')}
        </Link>

        <Link
          to="/explorar"
          className="rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario shadow-suave transition-transform hover:-translate-y-0.5"
        >
          {t('preferencia.ver_catalogo')}
        </Link>
      </nav>

      {/* Honestidad sobre el estado del proyecto: la recomendación llega en
          la Fase 3. No se promete lo que todavía no existe. */}
      <p className="mt-8 rounded-lg bg-superficie-contenedor p-4 text-sm text-sobre-superficie-variante">
        {t('preferencia.proxima_fase')}
      </p>
    </motion.main>
  );
}
