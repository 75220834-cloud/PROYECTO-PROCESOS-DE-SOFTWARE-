/**
 * Tarjeta de un recurso turístico en el listado del catálogo.
 *
 * Muestra el sello de dato oficial que pide el diseño: el visitante debe
 * poder distinguir de un vistazo qué información viene verificada del
 * inventario del MINCETUR y cuál está incompleta.
 */
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import type { RecursoResumen } from '@/servicios/api';
import { formatearCategoria, formatearNombrePropio } from '@/utilidades/formato';

export function TarjetaRecurso({
  recurso,
  indice = 0,
}: {
  recurso: RecursoResumen;
  indice?: number;
}) {
  const { t } = useTranslation();

  return (
    <motion.li
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      // El retraso se acota: con 24 tarjetas, escalonarlas todas haría esperar
      // más de un segundo a ver la última.
      transition={{ duration: 0.3, delay: Math.min(indice, 8) * 0.04 }}
      className="flex flex-col rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5 shadow-suave transition-transform hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-titulo leading-snug font-semibold text-sobre-superficie">
          <Link to={`/recursos/${recurso.id}`} className="hover:text-primario">
            {recurso.nombre}
          </Link>
        </h3>

        {/* Sello de dato oficial: verde si pasó la validación, ocre si no. */}
        <span
          title={
            recurso.esta_validado
              ? t('catalogo.sello_validado_ayuda')
              : t('catalogo.sello_incompleto_ayuda')
          }
          className={
            'shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ' +
            (recurso.esta_validado
              ? 'bg-secundario-contenedor text-sobre-secundario-contenedor'
              : 'bg-terciario-contenedor text-sobre-terciario-contenedor')
          }
        >
          {recurso.esta_validado ? t('catalogo.validado') : t('catalogo.incompleto')}
        </span>
      </div>

      <p className="mt-1.5 text-sm text-sobre-superficie-variante">
        {formatearNombrePropio(recurso.distrito)} · {formatearNombrePropio(recurso.provincia)}
      </p>

      {recurso.categoria && (
        <p className="mt-3">
          <span className="inline-block rounded-full bg-superficie-contenedor px-2.5 py-1 text-xs text-sobre-superficie-variante">
            {formatearCategoria(recurso.categoria)}
          </span>
        </p>
      )}

      <div className="mt-auto pt-4 text-xs text-sobre-superficie-variante">
        {recurso.latitud === null ? (
          // Honestidad con los datos: se dice que falta la coordenada en vez
          // de omitirlo o inventar una.
          <span className="text-terciario">{t('catalogo.sin_coordenadas')}</span>
        ) : (
          <span>{t('catalogo.fuente_mincetur', { fecha: recurso.fecha_corte ?? '—' })}</span>
        )}
      </div>
    </motion.li>
  );
}
