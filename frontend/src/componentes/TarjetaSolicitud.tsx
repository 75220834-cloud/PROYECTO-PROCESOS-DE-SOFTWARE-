/**
 * Tarjeta de una solicitud de coordinación, con su historial (Incremento 5).
 *
 * **El historial es la brecha 6 hecha visible.** La brecha dice que *no existe
 * punto único de coordinación ni registro de lo acordado*. Un estado suelto
 * («confirmada») diría dónde está la solicitud ahora; el historial dice cuándo
 * se envió, cuándo la vio el proveedor, qué contestó y cuánto tardó.
 *
 * Va plegado por omisión porque en el uso normal lo que importa es el estado.
 * Pero está siempre a un clic, y ese clic es la diferencia entre «me dijeron
 * que sí» y poder demostrarlo.
 *
 * Se usa en las dos pantallas: la del visitante, que ve las suyas, y el panel
 * del proveedor, que además puede responder. Lo que cambia es si se le pasan
 * acciones o no.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { EstadoSolicitud, SolicitudPublica } from '@/servicios/api';
import { formatearPrecio } from '@/utilidades/formato';

/** Color de la etiqueta de estado. Verde cerrado, ámbar en curso, rojo no. */
const ESTILO_DE_ESTADO: Record<EstadoSolicitud, string> = {
  enviada: 'bg-superficie-contenedor-alto text-sobre-superficie-variante',
  en_revision: 'bg-terciario-contenedor text-sobre-terciario-contenedor',
  contrapropuesta: 'bg-terciario-contenedor text-sobre-terciario-contenedor',
  confirmada: 'bg-secundario-contenedor text-sobre-secundario-contenedor',
  rechazada: 'bg-error-contenedor text-sobre-error-contenedor',
  cancelada: 'bg-superficie-contenedor-alto text-sobre-superficie-variante',
};

/** Formatea una marca de tiempo ISO como «12/09/2026 14:30». */
function formatearMomento(iso: string, idioma: string): string {
  const fecha = new Date(iso);

  if (Number.isNaN(fecha.getTime())) return iso;

  return fecha.toLocaleString(idioma === 'en' ? 'en-GB' : 'es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface Propiedades {
  solicitud: SolicitudPublica;
  /** Acciones que puede hacer quien mira. Vacío para solo lectura. */
  acciones?: React.ReactNode;
}

export default function TarjetaSolicitud({ solicitud, acciones }: Propiedades) {
  const { t, i18n } = useTranslation();
  const [verHistorial, establecerVerHistorial] = useState(false);

  return (
    <li className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-titulo leading-snug font-semibold text-sobre-superficie">
            {solicitud.servicio_nombre}
          </h3>
          <p className="mt-0.5 text-sm text-sobre-superficie-variante">
            {solicitud.proveedor_nombre}
            {solicitud.proveedor_es_demostracion && (
              <span className="ml-2 rounded bg-terciario-contenedor px-1.5 py-0.5 text-xs text-sobre-terciario-contenedor">
                {t('coordinacion.etiquetaDemostracion')}
              </span>
            )}
          </p>
        </div>

        <span
          title={t(`coordinacion.estadoAyuda.${solicitud.estado}`)}
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${ESTILO_DE_ESTADO[solicitud.estado]}`}
        >
          {t(`coordinacion.estado.${solicitud.estado}`)}
        </span>
      </div>

      <p className="mt-2 text-sm text-sobre-superficie-variante">
        {t('coordinacion.para', { fecha: solicitud.fecha_servicio })}
        {solicitud.hora_servicio && ` · ${solicitud.hora_servicio.slice(0, 5)}`}
        {' · '}
        {t('coordinacion.personasContadas', { count: solicitud.numero_personas })}
      </p>

      {solicitud.mensaje && (
        <p className="mt-2 rounded bg-superficie-contenedor px-3 py-2 text-sm text-sobre-superficie-variante">
          {solicitud.mensaje}
        </p>
      )}

      {/* El precio. Se enseñan los dos: lo acordado y lo que se publicaba, para
          que se vea si el acuerdo cae dentro de lo anunciado. */}
      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {solicitud.precio_acordado_soles !== null && (
          <div>
            <dt className="inline text-sobre-superficie-variante">
              {t('coordinacion.precioAcordado')}:{' '}
            </dt>
            <dd className="inline font-semibold text-sobre-superficie">
              S/ {Number(solicitud.precio_acordado_soles).toFixed(2)}
            </dd>
          </div>
        )}
        <div>
          <dt className="inline text-sobre-superficie-variante">
            {t('coordinacion.precioPublicado')}:{' '}
          </dt>
          <dd className="inline text-sobre-superficie-variante">
            {formatearPrecio(solicitud.precio_min_soles, solicitud.precio_max_soles)}
          </dd>
        </div>
      </dl>

      {solicitud.respuesta_proveedor && (
        <div className="mt-3 rounded border-l-4 border-secundario bg-superficie-contenedor px-3 py-2">
          <p className="text-xs font-semibold text-sobre-superficie-variante">
            {t('coordinacion.respuestaDelProveedor')}
          </p>
          <p className="mt-0.5 text-sm text-sobre-superficie">{solicitud.respuesta_proveedor}</p>
        </div>
      )}

      {acciones && <div className="mt-4">{acciones}</div>}

      {/* El registro de lo acordado. */}
      <div className="mt-4 border-t border-contorno-variante pt-3">
        <button
          type="button"
          onClick={() => establecerVerHistorial((visible) => !visible)}
          aria-expanded={verHistorial}
          className="text-sm font-medium text-primario hover:underline"
        >
          {verHistorial ? t('coordinacion.ocultarHistorial') : t('coordinacion.verHistorial')} (
          {t('coordinacion.interacciones', { count: solicitud.interacciones })})
        </button>

        {verHistorial && (
          <ol className="mt-3 space-y-2">
            {solicitud.historial.map((cambio) => (
              <li
                key={`${cambio.estado_nuevo}-${cambio.ocurrido_en}`}
                className="flex flex-wrap items-baseline gap-x-2 text-sm"
              >
                <span className="font-mono text-xs text-sobre-superficie-variante">
                  {formatearMomento(cambio.ocurrido_en, i18n.language)}
                </span>
                <span className="font-medium text-sobre-superficie">
                  {t(`coordinacion.estado.${cambio.estado_nuevo}`)}
                </span>
                {cambio.rol_de_quien_cambio && (
                  <span className="text-xs text-sobre-superficie-variante">
                    {t('coordinacion.cambioPor', { rol: cambio.rol_de_quien_cambio })}
                  </span>
                )}
                {cambio.nota && (
                  <span className="w-full text-sobre-superficie-variante">«{cambio.nota}»</span>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </li>
  );
}
