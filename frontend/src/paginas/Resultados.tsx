/**
 * Página de resultados de la recomendación (Incremento 3).
 *
 * Muestra los recursos ordenados por afinidad, cada uno explicando por qué se
 * recomienda y cuánta gente se espera.
 *
 * Dos cosas que esta pantalla hace a propósito y que no son habituales:
 *
 * 1. **Enseña lo que se descartó.** Con su motivo. Un buscador que solo
 *    muestra lo que encontró deja al visitante preguntándose por qué no
 *    aparece el sitio que esperaba.
 * 2. **Dice cómo se calculó.** Si la recomendación salió del modelo o de las
 *    reglas. Es la trazabilidad que exige la regla de oro del proyecto.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { ResumenPreferencia } from '@/componentes/ResumenPreferencia';
import { TarjetaRecomendacion } from '@/componentes/TarjetaRecomendacion';
import { useSesion } from '@/hooks/useSesion';
import { obtenerPreferencia, obtenerRecomendaciones } from '@/servicios/api';

export function Resultados() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { token } = useSesion();
  const [verDescartados, establecerVerDescartados] = useState(false);

  const identificador = Number(id);
  const habilitado = Number.isFinite(identificador);

  const { data: preferencia } = useQuery({
    queryKey: ['preferencia', identificador],
    queryFn: () => obtenerPreferencia(identificador, token),
    enabled: habilitado,
  });

  const {
    data: resultado,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['recomendaciones', identificador],
    queryFn: () => obtenerRecomendaciones(identificador, token),
    enabled: habilitado,
    retry: false,
  });

  if (isLoading) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('resultados.calculando')}</p>
      </main>
    );
  }

  if (isError || !resultado) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-error">{(error as Error)?.message ?? t('resultados.error')}</p>
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
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="mx-auto max-w-contenido px-4 py-10 sm:px-6"
    >
      <header>
        <h1 className="font-titulo text-3xl font-extrabold text-sobre-superficie">
          {t('resultados.titulo')}
        </h1>
        <p className="mt-2 text-sobre-superficie-variante">
          {t('resultados.subtitulo', { total: resultado.total_recomendados })}
        </p>
      </header>

      {/* Resumen de lo que pidió, con botón para cambiarlo. */}
      {preferencia && (
        <section
          aria-label={t('preferencia.resumen')}
          className="mt-6 rounded-lg border border-contorno-variante bg-superficie-contenedor-bajo p-5"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h2 className="font-titulo font-semibold text-sobre-superficie">
              {t('preferencia.resumen')}
            </h2>
            <Link
              to="/preferencias"
              className="text-sm font-semibold text-primario hover:underline"
            >
              {t('resultados.cambiar_preferencias')}
            </Link>
          </div>

          <div className="mt-4">
            <ResumenPreferencia preferencia={preferencia} />
          </div>
        </section>
      )}

      {/* Trazabilidad: cómo se calculó esto. */}
      <p className="mt-4 text-xs text-sobre-superficie-variante">
        {t(`resultados.generado_por_${resultado.generado_por}`)} ·{' '}
        {t('resultados.evaluados', { total: resultado.total_evaluados })}
      </p>

      {resultado.avisos.map((aviso) => (
        <p
          key={aviso}
          className="mt-3 rounded-md bg-terciario-contenedor px-4 py-2.5 text-sm text-sobre-terciario-contenedor"
        >
          {aviso}
        </p>
      ))}

      {/* Las recomendaciones. */}
      {resultado.recomendaciones.length === 0 ? (
        <p className="mt-10 rounded-lg border border-contorno-variante bg-superficie-contenedor p-8 text-center text-sobre-superficie-variante">
          {t('resultados.sin_resultados')}
        </p>
      ) : (
        <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {resultado.recomendaciones.map((recomendacion, indice) => (
            <TarjetaRecomendacion
              key={recomendacion.recurso_id}
              recomendacion={recomendacion}
              indice={indice}
            />
          ))}
        </ul>
      )}

      {/* Lo que se descartó y por qué. */}
      {resultado.total_descartados > 0 && (
        <section className="mt-12 rounded-lg border border-contorno-variante bg-superficie-contenedor p-5">
          <button
            type="button"
            onClick={() => establecerVerDescartados((abierto) => !abierto)}
            aria-expanded={verDescartados}
            className="flex w-full items-center justify-between gap-4 text-left"
          >
            <span className="font-titulo font-semibold text-sobre-superficie">
              {t('resultados.descartados_titulo', { total: resultado.total_descartados })}
            </span>
            <span className="text-sm font-semibold text-primario">
              {verDescartados ? t('resultados.ocultar') : t('resultados.ver')}
            </span>
          </button>

          <p className="mt-2 text-sm text-sobre-superficie-variante">
            {t('resultados.descartados_ayuda')}
          </p>

          {verDescartados && (
            <ul className="mt-4 space-y-2">
              {resultado.descartados.map((descartado) => (
                <li
                  key={descartado.recurso_id}
                  className="flex flex-wrap items-baseline gap-x-2 text-sm"
                >
                  <span className="font-medium text-sobre-superficie">{descartado.nombre}</span>
                  <span className="text-sobre-superficie-variante">— {descartado.motivo}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* Honestidad sobre el estado del proyecto. */}
      <p className="mt-10 rounded-lg bg-superficie-contenedor p-4 text-sm text-sobre-superficie-variante">
        {t('resultados.proxima_fase')}
      </p>
    </motion.main>
  );
}
