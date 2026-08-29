/**
 * Página «Mis viajes»: las preferencias guardadas del usuario.
 *
 * En la Fase 2 lista las preferencias registradas. Los itinerarios completos,
 * con su mapa en miniatura y sus totales, llegan en la Fase 4: no se dibujan
 * tarjetas con datos de relleno mientras tanto.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { ResumenPreferencia } from '@/componentes/ResumenPreferencia';
import { useSesion } from '@/hooks/useSesion';
import { listarMisPreferencias } from '@/servicios/api';
import { formatearFecha, formatearNombrePropio } from '@/utilidades/formato';

export function MisViajes() {
  const { t, i18n } = useTranslation();
  const { token, usuario, cargando } = useSesion();
  const idioma = i18n.resolvedLanguage?.slice(0, 2) ?? 'es';

  const {
    data: lista,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['mis-preferencias'],
    queryFn: () => listarMisPreferencias(token as string),
    enabled: Boolean(token),
  });

  // Mientras se comprueba el token guardado no se decide nada: si no, quien
  // recarga la página vería un parpadeo de «inicia sesión» antes de entrar.
  if (cargando) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('catalogo.cargando')}</p>
      </main>
    );
  }

  if (!usuario) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
        <h1 className="font-titulo text-2xl font-bold text-sobre-superficie">
          {t('misviajes.necesitas_cuenta')}
        </h1>
        <p className="mt-3 text-sobre-superficie-variante">
          {t('misviajes.necesitas_cuenta_texto')}
        </p>

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            to="/acceso"
            className="rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario shadow-suave transition-transform hover:-translate-y-0.5"
          >
            {t('acceso.iniciar_sesion')}
          </Link>
          <Link
            to="/preferencias"
            className="rounded-md border border-contorno-variante px-5 py-2.5 font-semibold text-sobre-superficie transition-colors hover:border-primario hover:text-primario"
          >
            {t('misviajes.planificar_sin_cuenta')}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-contenido px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-titulo text-3xl font-extrabold text-sobre-superficie">
            {t('misviajes.titulo')}
          </h1>
          <p className="mt-2 text-sobre-superficie-variante">
            {t('misviajes.saludo', { nombre: usuario.nombre })}
          </p>
        </div>

        <Link
          to="/preferencias"
          className="rounded-md bg-primario px-5 py-2.5 font-semibold text-sobre-primario shadow-suave transition-transform hover:-translate-y-0.5"
        >
          {t('misviajes.planificar_nuevo')}
        </Link>
      </header>

      {isLoading && (
        <p className="mt-10 text-sobre-superficie-variante">{t('catalogo.cargando')}</p>
      )}

      {isError && <p className="mt-10 text-error">{t('misviajes.error')}</p>}

      {lista && lista.total === 0 && (
        <section className="mt-10 rounded-lg border border-contorno-variante bg-superficie-contenedor p-10 text-center">
          <p className="font-titulo text-lg font-semibold text-sobre-superficie">
            {t('misviajes.vacio_titulo')}
          </p>
          <p className="mt-2 text-sobre-superficie-variante">{t('misviajes.vacio_texto')}</p>

          <Link
            to="/preferencias"
            className="mt-6 inline-block rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario"
          >
            {t('misviajes.planificar_nuevo')}
          </Link>
        </section>
      )}

      {lista && lista.total > 0 && (
        <ul className="mt-8 space-y-4">
          {lista.elementos.map((preferencia, indice) => (
            <motion.li
              key={preferencia.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(indice, 6) * 0.05 }}
              className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-6 shadow-suave"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
                  {t('misviajes.viaje_a', {
                    distrito: formatearNombrePropio(preferencia.distrito_origen),
                    fecha: formatearFecha(preferencia.fecha_inicio, idioma),
                  })}
                </h2>

                <Link
                  to={`/preferencias/${preferencia.id}`}
                  className="text-sm font-semibold text-primario hover:underline"
                >
                  {t('misviajes.ver_detalle')}
                </Link>
              </div>

              <div className="mt-4">
                <ResumenPreferencia preferencia={preferencia} />
              </div>
            </motion.li>
          ))}
        </ul>
      )}
    </main>
  );
}
