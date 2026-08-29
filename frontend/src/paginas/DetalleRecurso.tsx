/**
 * Página de detalle de un recurso turístico.
 *
 * En la Fase 1 muestra lo que la fuente oficial trae de verdad. Las
 * fotografías, la descripción larga y las valoraciones llegan en fases
 * posteriores; mientras tanto se dice que faltan en vez de rellenarlas con
 * texto o imágenes inventadas.
 */
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { MapaRecursos } from '@/componentes/MapaRecursos';

import { obtenerRecurso, type RasgoRecurso } from '@/servicios/api';
import { formatearCategoria, formatearNombrePropio } from '@/utilidades/formato';

export function DetalleRecurso() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const identificador = Number(id);

  const {
    data: recurso,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['recurso', identificador],
    queryFn: () => obtenerRecurso(identificador),
    enabled: Number.isFinite(identificador),
  });

  if (isLoading) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('catalogo.cargando')}</p>
      </main>
    );
  }

  if (isError || !recurso) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-error">{t('detalle.no_encontrado')}</p>
        <Link to="/explorar" className="mt-4 inline-block font-semibold text-primario underline">
          {t('detalle.volver')}
        </Link>
      </main>
    );
  }

  // El mapa reutiliza el mismo componente del catálogo, con un solo punto.
  const rasgo: RasgoRecurso[] =
    recurso.latitud !== null && recurso.longitud !== null
      ? [
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [recurso.longitud, recurso.latitud] },
            properties: {
              id: recurso.id,
              nombre: recurso.nombre,
              provincia: recurso.provincia,
              distrito: recurso.distrito,
              categoria: recurso.categoria,
              esta_validado: recurso.esta_validado,
            },
          },
        ]
      : [];

  const etiquetas = [
    recurso.categoria && formatearCategoria(recurso.categoria),
    recurso.tipo,
    recurso.subtipo,
  ].filter(Boolean) as string[];

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="mx-auto max-w-contenido px-4 py-10 sm:px-6"
    >
      <Link
        to="/explorar"
        className="text-sm font-semibold text-sobre-superficie-variante hover:text-primario"
      >
        ← {t('detalle.volver')}
      </Link>

      <h1 className="mt-4 font-titulo text-3xl font-extrabold text-balance text-sobre-superficie">
        {recurso.nombre}
      </h1>

      <p className="mt-2 text-lg text-sobre-superficie-variante">
        {formatearNombrePropio(recurso.distrito)} · {formatearNombrePropio(recurso.provincia)}
      </p>

      {etiquetas.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {etiquetas.map((etiqueta) => (
            <li
              key={etiqueta}
              className="rounded-full bg-superficie-contenedor px-3 py-1 text-xs text-sobre-superficie-variante"
            >
              {etiqueta}
            </li>
          ))}
        </ul>
      )}

      {/* Sello de dato verificado: es el argumento central del Incremento 1. */}
      <p
        className={
          'mt-6 inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm ' +
          (recurso.esta_validado
            ? 'bg-secundario-contenedor text-sobre-secundario-contenedor'
            : 'bg-terciario-contenedor text-sobre-terciario-contenedor')
        }
      >
        {recurso.esta_validado
          ? t('detalle.sello_verificado', { fecha: recurso.fecha_corte ?? '—' })
          : t('detalle.sello_incompleto', { motivos: recurso.motivos_invalidez ?? '' })}
      </p>

      <div className="mt-10 grid gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="font-titulo text-xl font-bold text-sobre-superficie">
            {t('detalle.ubicacion')}
          </h2>

          {rasgo.length > 0 ? (
            <div className="mt-4 h-80 overflow-hidden rounded-lg border border-contorno-variante">
              <MapaRecursos rasgos={rasgo} />
            </div>
          ) : (
            <p className="mt-4 rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
              {t('detalle.sin_ubicacion')}
            </p>
          )}

          <h2 className="mt-10 font-titulo text-xl font-bold text-sobre-superficie">
            {t('detalle.descripcion')}
          </h2>
          <p className="mt-3 text-sobre-superficie-variante">
            {recurso.descripcion_es ?? t('detalle.sin_descripcion')}
          </p>
        </section>

        <aside>
          <h2 className="font-titulo text-xl font-bold text-sobre-superficie">
            {t('detalle.ficha')}
          </h2>

          <dl className="mt-4 space-y-3 rounded-lg border border-contorno-variante bg-superficie-contenedor p-5 text-sm">
            {(
              [
                ['detalle.codigo', recurso.codigo_mincetur],
                ['detalle.fecha_corte', recurso.fecha_corte ?? '—'],
                [
                  'detalle.coordenadas',
                  recurso.latitud !== null && recurso.longitud !== null
                    ? `${recurso.latitud.toFixed(5)}, ${recurso.longitud.toFixed(5)}`
                    : t('detalle.no_disponible'),
                ],
                [
                  'detalle.altitud',
                  recurso.altitud_msnm
                    ? `${recurso.altitud_msnm} m s. n. m.`
                    : t('detalle.no_disponible'),
                ],
              ] as const
            ).map(([clave, valor]) => (
              <div key={clave} className="flex justify-between gap-4">
                <dt className="text-sobre-superficie-variante">{t(clave)}</dt>
                <dd className="text-right font-medium text-sobre-superficie">{valor}</dd>
              </div>
            ))}
          </dl>

          {recurso.url_ficha && (
            <a
              href={recurso.url_ficha}
              target="_blank"
              rel="noreferrer"
              className="mt-4 block rounded-md border border-contorno-variante px-4 py-2.5 text-center text-sm font-semibold text-sobre-superficie transition-colors hover:border-primario hover:text-primario"
            >
              {t('detalle.ficha_oficial')}
            </a>
          )}
        </aside>
      </div>
    </motion.main>
  );
}
