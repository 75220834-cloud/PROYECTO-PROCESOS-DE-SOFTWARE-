/**
 * Pantalla del visitante para coordinar servicios (Incremento 5).
 *
 * Cierra las dos brechas del incremento desde el lado de quien viaja:
 *
 * - **Brecha 5:** cada servicio enseña su capacidad, su antelación, sus días y
 *   su precio antes de que haya que preguntar nada.
 * - **Brecha 6:** lo que se pide queda registrado y se puede seguir desde
 *   aquí, con el historial completo de lo que fue pasando.
 *
 * Se llega desde el itinerario, y por eso acepta `itinerario` y `fecha` en la
 * dirección: pedir un almuerzo para el día que ya tienes planificado no debería
 * exigir volver a escribir la fecha.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import FormularioSolicitud from '@/componentes/FormularioSolicitud';
import TarjetaServicio from '@/componentes/TarjetaServicio';
import TarjetaSolicitud from '@/componentes/TarjetaSolicitud';
import { useSesion } from '@/hooks/useSesion';
import {
  obtenerServicios,
  obtenerSolicitudes,
  type ServicioPublico,
  type TipoServicio,
} from '@/servicios/api';

/** Los seis tipos, en el orden en que se usan durante un viaje. */
const TIPOS: TipoServicio[] = [
  'guiado',
  'alimentacion',
  'taller',
  'artesania',
  'transporte',
  'hospedaje',
];

export function Coordinacion() {
  const { t } = useTranslation();
  const { token, usuario } = useSesion();
  const clienteDeConsultas = useQueryClient();
  const [parametros] = useSearchParams();

  const itinerarioId = Number(parametros.get('itinerario')) || null;
  const fechaPropuesta = parametros.get('fecha') ?? undefined;

  const [tipo, establecerTipo] = useState<TipoServicio | null>(null);
  const [pidiendo, establecerPidiendo] = useState<ServicioPublico | null>(null);

  const servicios = useQuery({
    queryKey: ['servicios', tipo],
    queryFn: () => obtenerServicios(tipo ? { tipo } : {}),
  });

  // Solo con sesión: sin cuenta no se puede saber cuáles son «las tuyas» sin
  // enseñar las de otros, así que el backend devuelve 401 y no se pregunta.
  const misSolicitudes = useQuery({
    queryKey: ['solicitudes', usuario?.id],
    queryFn: () => obtenerSolicitudes(token),
    enabled: Boolean(token),
  });

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-contenido px-4 py-10 sm:px-6"
    >
      <header>
        {itinerarioId && (
          <p className="text-sm">
            <Link
              to={`/preferencias/${itinerarioId}/itinerario`}
              className="text-primario underline"
            >
              {t('itinerario.volverAResultados')}
            </Link>
          </p>
        )}

        <h1 className="mt-2 font-titulo text-3xl font-extrabold text-sobre-superficie">
          {t('coordinacion.titulo')}
        </h1>
        <p className="mt-2 text-sobre-superficie-variante">{t('coordinacion.subtitulo')}</p>
      </header>

      {/* El aviso de demostración, arriba del todo y una sola vez. Repetirlo en
          cada tarjeta lo convertiría en ruido que nadie lee. */}
      <p className="mt-5 rounded-lg border border-terciario bg-terciario-contenedor p-4 text-sm text-sobre-terciario-contenedor">
        <strong>{t('coordinacion.etiquetaDemostracion')}.</strong>{' '}
        {t('coordinacion.avisoDemostracion')}
      </p>

      {/* Formulario de solicitud, cuando hay uno abierto. */}
      {pidiendo && (
        <div className="mt-6">
          <FormularioSolicitud
            servicio={pidiendo}
            itinerarioId={itinerarioId}
            fechaPropuesta={fechaPropuesta}
            alEnviar={() => {
              // La lista de solicitudes acaba de quedarse vieja.
              void clienteDeConsultas.invalidateQueries({ queryKey: ['solicitudes'] });
              void clienteDeConsultas.invalidateQueries({ queryKey: ['servicios'] });
            }}
            alCerrar={() => establecerPidiendo(null)}
          />
        </div>
      )}

      {/* Filtro por tipo. */}
      <nav className="mt-6 flex flex-wrap gap-2" aria-label={t('coordinacion.titulo')}>
        <BotonDeTipo
          activo={tipo === null}
          alPulsar={() => establecerTipo(null)}
          etiqueta={t('coordinacion.todosLosTipos')}
        />
        {TIPOS.map((cada) => (
          <BotonDeTipo
            key={cada}
            activo={tipo === cada}
            alPulsar={() => establecerTipo(cada)}
            etiqueta={t(`coordinacion.tipo.${cada}`)}
          />
        ))}
      </nav>

      <section className="mt-6" aria-label={t('coordinacion.titulo')}>
        {servicios.isLoading && (
          <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>
        )}

        {servicios.isError && (
          <p className="text-sobre-error-contenedor">{t('coordinacion.error')}</p>
        )}

        {servicios.data?.length === 0 && (
          <p className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
            {t('coordinacion.sinServicios')}
          </p>
        )}

        {servicios.data && servicios.data.length > 0 && (
          <ul className="grid list-none gap-4 md:grid-cols-2">
            {servicios.data.map((servicio) => (
              <TarjetaServicio key={servicio.id} servicio={servicio} alPedir={establecerPidiendo} />
            ))}
          </ul>
        )}
      </section>

      {/* Mis solicitudes: el seguimiento que cierra la brecha 6. */}
      {token && (
        <section className="mt-10" aria-label={t('coordinacion.misSolicitudes')}>
          <h2 className="font-titulo text-xl font-semibold text-sobre-superficie">
            {t('coordinacion.misSolicitudes')}
          </h2>

          {misSolicitudes.data?.length === 0 && (
            <p className="mt-3 text-sm text-sobre-superficie-variante">
              {t('coordinacion.sinSolicitudes')}
            </p>
          )}

          {misSolicitudes.data && misSolicitudes.data.length > 0 && (
            <ul className="mt-4 grid list-none gap-4">
              {misSolicitudes.data.map((solicitud) => (
                <TarjetaSolicitud key={solicitud.id} solicitud={solicitud} />
              ))}
            </ul>
          )}
        </section>
      )}
    </motion.main>
  );
}

function BotonDeTipo({
  activo,
  alPulsar,
  etiqueta,
}: {
  activo: boolean;
  alPulsar: () => void;
  etiqueta: string;
}) {
  return (
    <button
      type="button"
      onClick={alPulsar}
      aria-current={activo ? 'true' : undefined}
      className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
        activo
          ? 'bg-primario text-sobre-primario'
          : 'border border-contorno-variante text-sobre-superficie-variante hover:bg-superficie-contenedor'
      }`}
    >
      {etiqueta}
    </button>
  );
}
