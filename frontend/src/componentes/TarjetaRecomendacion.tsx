/**
 * Tarjeta de un recurso recomendado (Incremento 3).
 *
 * Sigue el diseño de Stitch: medalla de afinidad, la razón de la
 * recomendación en una línea, y etiqueta de afluencia con su motivo.
 *
 * **Lo que hace auditable esta tarjeta**, y por qué importa: la brecha 2 del
 * análisis dice que *el análisis y la priorización recaen en el visitante, sin
 * criterios explícitos*. Una recomendación que solo dijera «92 %» seguiría
 * dejando al visitante sin criterios: tendría que creérselo. Por eso cada
 * tarjeta muestra qué términos la provocaron y qué intereses cubre.
 */
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import type { RecomendacionPublica } from '@/servicios/api';
import { formatearCategoria, formatearNombrePropio } from '@/utilidades/formato';
import { redactarAviso } from '@/utilidades/avisos';

/** Colores de la etiqueta de afluencia. Verde tranquilo, ámbar, rojo. */
const ESTILO_DE_AFLUENCIA: Record<string, string> = {
  bajo: 'bg-secundario-contenedor text-sobre-secundario-contenedor',
  medio: 'bg-terciario-contenedor text-sobre-terciario-contenedor',
  alto: 'bg-error-contenedor text-sobre-error-contenedor',
};

export function TarjetaRecomendacion({
  recomendacion,
  indice = 0,
}: {
  recomendacion: RecomendacionPublica;
  indice?: number;
}) {
  const { t } = useTranslation();

  return (
    <motion.li
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(indice, 8) * 0.05 }}
      className="flex flex-col rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5 shadow-suave transition-transform hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-titulo leading-snug font-semibold text-sobre-superficie">
          <Link to={`/recursos/${recomendacion.recurso_id}`} className="hover:text-primario">
            {recomendacion.nombre}
          </Link>
        </h3>

        {/* Medalla de afinidad. El título explica qué significa el número:
            es relativo al mejor resultado, no un porcentaje absoluto. */}
        <span
          title={t('resultados.afinidad_ayuda')}
          className="shrink-0 rounded-full bg-primario px-2.5 py-1 text-xs font-bold text-sobre-primario"
        >
          {recomendacion.puntaje_relativo} %
        </span>
      </div>

      <p className="mt-1.5 text-sm text-sobre-superficie-variante">
        {formatearNombrePropio(recomendacion.distrito)} ·{' '}
        {formatearNombrePropio(recomendacion.provincia)}
        {recomendacion.distancia_km !== null && (
          <span> · {t('resultados.a_km', { km: recomendacion.distancia_km })}</span>
        )}
      </p>

      {recomendacion.categoria && (
        <p className="mt-3">
          <span className="inline-block rounded-full bg-superficie-contenedor px-2.5 py-1 text-xs text-sobre-superficie-variante">
            {formatearCategoria(recomendacion.categoria)}
          </span>
        </p>
      )}

      {/* Por qué se recomienda. Es el corazón de la tarjeta. */}
      {recomendacion.intereses_cubiertos.length > 0 && (
        <p className="mt-4 rounded-md bg-primario-suave px-3 py-2 text-sm text-sobre-superficie">
          {t('resultados.porque', {
            intereses: recomendacion.intereses_cubiertos
              .map((interes) => t(`intereses.${interes}`).toLowerCase())
              .join(', '),
          })}
        </p>
      )}

      {recomendacion.terminos_decisivos.length > 0 && (
        <p className="mt-2 text-xs text-sobre-superficie-variante">
          {t('resultados.terminos', {
            terminos: recomendacion.terminos_decisivos.join(', '),
          })}
        </p>
      )}

      {/* Afluencia esperada, con su motivo debajo. */}
      <div className="mt-auto pt-4">
        <span
          className={
            'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ' +
            (ESTILO_DE_AFLUENCIA[recomendacion.afluencia.nivel] ??
              'bg-superficie-contenedor text-sobre-superficie-variante')
          }
        >
          {t(`afluencia.${recomendacion.afluencia.nivel}`)}
        </span>

        <p className="mt-1.5 text-xs text-sobre-superficie-variante">
          {redactarAviso(t, recomendacion.afluencia.motivo)}
        </p>
      </div>
    </motion.li>
  );
}
