/**
 * Formulario para pedir un servicio a su proveedor (Incremento 5).
 *
 * ## La decisión que define esta pantalla
 *
 * **La disponibilidad se comprueba mientras se rellena, no al enviar.** En
 * cuanto hay fecha y número de personas, se pregunta al backend y se enseña la
 * respuesta. Descubrir que no hay sitio después de escribir nombre, teléfono y
 * mensaje es la forma más segura de que alguien no vuelva a intentarlo.
 *
 * Y se enseñan **todos** los motivos a la vez, no el primero: ir corrigiendo de
 * uno en uno («no hay sitio»… «además llegas tarde»… «además ese día cierra»)
 * es peor que no avisar.
 *
 * El botón de enviar no se bloquea cuando no hay disponibilidad: el backend
 * volverá a comprobarlo y responderá con los motivos. Bloquearlo dejaría a
 * quien tenga un problema de red mirando un botón muerto sin saber por qué.
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';

import { useSesion } from '@/hooks/useSesion';
import {
  comprobarDisponibilidad,
  crearSolicitud,
  type ServicioPublico,
  type SolicitudPublica,
} from '@/servicios/api';
import { formatearPrecio } from '@/utilidades/formato';
import { redactarAviso } from '@/utilidades/avisos';
import { traducirError } from '@/utilidades/avisos';

interface Propiedades {
  servicio: ServicioPublico;
  /** Itinerario del que sale la solicitud, si sale de uno. */
  itinerarioId?: number | null;
  /** Fecha propuesta, normalmente la del día del itinerario. */
  fechaPropuesta?: string;
  alEnviar?: (solicitud: SolicitudPublica) => void;
  alCerrar: () => void;
}

export default function FormularioSolicitud({
  servicio,
  itinerarioId = null,
  fechaPropuesta,
  alEnviar,
  alCerrar,
}: Propiedades) {
  const { t } = useTranslation();
  const { token, usuario } = useSesion();
  const idBase = useId();

  const [fecha, establecerFecha] = useState(fechaPropuesta ?? '');
  const [hora, establecerHora] = useState('');
  const [personas, establecerPersonas] = useState(2);
  const [nombre, establecerNombre] = useState(usuario?.nombre ?? '');
  const [telefono, establecerTelefono] = useState('');
  const [correo, establecerCorreo] = useState(usuario?.correo ?? '');
  const [mensaje, establecerMensaje] = useState('');

  // Se pregunta en cuanto hay fecha, sin esperar al envío.
  const disponibilidad = useQuery({
    queryKey: ['disponibilidad', servicio.id, fecha, personas, hora],
    queryFn: () => comprobarDisponibilidad(servicio.id, fecha, personas, hora || null),
    enabled: Boolean(fecha) && personas > 0,
    retry: false,
  });

  const envio = useMutation({
    mutationFn: () =>
      crearSolicitud(
        {
          servicio_id: servicio.id,
          fecha_servicio: fecha,
          hora_servicio: hora || null,
          numero_personas: personas,
          nombre_contacto: nombre,
          telefono_contacto: telefono || null,
          correo_contacto: correo || null,
          mensaje: mensaje || null,
          itinerario_id: itinerarioId,
        },
        token,
      ),
    onSuccess: (solicitud) => alEnviar?.(solicitud),
  });

  if (envio.isSuccess) {
    return (
      <div
        className="rounded-lg border border-secundario bg-secundario-contenedor p-5"
        role="status"
      >
        <p className="font-titulo font-semibold text-sobre-secundario-contenedor">
          {t('coordinacion.enviada')}
        </p>
        <button
          type="button"
          onClick={alCerrar}
          className="mt-3 rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario"
        >
          {t('coordinacion.cerrar')}
        </button>
      </div>
    );
  }

  return (
    <form
      onSubmit={(evento) => {
        evento.preventDefault();
        envio.mutate();
      }}
      className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5"
    >
      <h3 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {t('coordinacion.pedirTitulo', { servicio: servicio.nombre })}
      </h3>
      <p className="mt-1 text-sm text-sobre-superficie-variante">
        {servicio.proveedor.nombre} ·{' '}
        {formatearPrecio(servicio.precio_min_soles, servicio.precio_max_soles)}{' '}
        {t(`coordinacion.unidad.${servicio.unidad_precio}`)}
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Campo
          id={`${idBase}-fecha`}
          etiqueta={t('coordinacion.fecha')}
          tipo="date"
          valor={fecha}
          alCambiar={establecerFecha}
          requerido
        />
        <Campo
          id={`${idBase}-hora`}
          etiqueta={t('coordinacion.hora')}
          tipo="time"
          valor={hora}
          alCambiar={establecerHora}
        />
        <Campo
          id={`${idBase}-personas`}
          etiqueta={t('coordinacion.personas')}
          tipo="number"
          valor={String(personas)}
          alCambiar={(valor) => establecerPersonas(Math.max(1, Number(valor) || 1))}
          requerido
          min={1}
          max={servicio.capacidad_maxima}
        />
      </div>

      {/* La respuesta de disponibilidad, mientras se rellena. */}
      <div className="mt-3 min-h-6" aria-live="polite">
        {disponibilidad.isFetching && (
          <p className="text-sm text-sobre-superficie-variante">{t('coordinacion.comprobando')}</p>
        )}

        {!disponibilidad.isFetching && disponibilidad.data?.hay_disponibilidad && (
          <p className="text-sm text-sobre-secundario-contenedor">
            {t('coordinacion.hayDisponibilidad')}
            {disponibilidad.data.plazas_libres !== null &&
              ` ${t('coordinacion.plazasLibres', {
                plazas: disponibilidad.data.plazas_libres,
              })}`}
          </p>
        )}

        {!disponibilidad.isFetching &&
          disponibilidad.data &&
          !disponibilidad.data.hay_disponibilidad && (
            <div className="rounded border border-terciario bg-terciario-contenedor p-3">
              <p className="text-sm font-semibold text-sobre-terciario-contenedor">
                {t('coordinacion.noHayDisponibilidad')}
              </p>
              <ul className="mt-1 space-y-0.5">
                {disponibilidad.data.motivos.map((motivo) => (
                  <li key={motivo.codigo} className="text-sm text-sobre-terciario-contenedor">
                    • {redactarAviso(t, motivo)}
                  </li>
                ))}
              </ul>
            </div>
          )}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Campo
          id={`${idBase}-nombre`}
          etiqueta={t('coordinacion.nombre')}
          valor={nombre}
          alCambiar={establecerNombre}
          requerido
        />
        <Campo
          id={`${idBase}-telefono`}
          etiqueta={t('coordinacion.telefono')}
          tipo="tel"
          valor={telefono}
          alCambiar={establecerTelefono}
        />
        <Campo
          id={`${idBase}-correo`}
          etiqueta={t('coordinacion.correo')}
          tipo="email"
          valor={correo}
          alCambiar={establecerCorreo}
        />
      </div>

      <div className="mt-4">
        <label
          htmlFor={`${idBase}-mensaje`}
          className="block text-sm font-medium text-sobre-superficie"
        >
          {t('coordinacion.mensaje')}
        </label>
        <textarea
          id={`${idBase}-mensaje`}
          value={mensaje}
          onChange={(evento) => establecerMensaje(evento.target.value)}
          rows={3}
          maxLength={2000}
          className="mt-1 w-full rounded border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2 text-sm text-sobre-superficie focus-visible:ring-2 focus-visible:ring-primario focus-visible:outline-none"
        />
        <p className="mt-1 text-xs text-sobre-superficie-variante">
          {t('coordinacion.mensajeAyuda')}
        </p>
      </div>

      {envio.isError && (
        <p className="mt-3 text-sm text-sobre-error-contenedor" role="alert">
          {mensajeDeError(envio.error, t)}
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={envio.isPending}
          className="rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario transition-transform hover:-translate-y-0.5 disabled:opacity-60"
        >
          {envio.isPending ? t('coordinacion.enviando') : t('coordinacion.enviar')}
        </button>

        <button
          type="button"
          onClick={alCerrar}
          className="rounded-full border border-contorno-variante px-5 py-2 text-sm font-semibold text-sobre-superficie-variante"
        >
          {t('coordinacion.cancelar')}
        </button>
      </div>
    </form>
  );
}

/**
 * Saca los motivos concretos del error del backend.
 *
 * Cuando el servicio no está disponible, la API devuelve un 409 con la lista de
 * motivos. Enseñar «no se pudo enviar» y tirar esa lista sería desperdiciar
 * justo la información que el visitante necesita para arreglarlo.
 */
function mensajeDeError(error: unknown, t: TFunction): string {
  return traducirError(t, error, t('coordinacion.errorAlEnviar'));
}

/** Un campo de formulario con su etiqueta asociada. */
function Campo({
  id,
  etiqueta,
  valor,
  alCambiar,
  tipo = 'text',
  requerido = false,
  min,
  max,
}: {
  id: string;
  etiqueta: string;
  valor: string;
  alCambiar: (valor: string) => void;
  tipo?: string;
  requerido?: boolean;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-sobre-superficie">
        {etiqueta}
        {requerido && <span aria-hidden="true"> *</span>}
      </label>
      <input
        id={id}
        type={tipo}
        value={valor}
        required={requerido}
        min={min}
        max={max}
        onChange={(evento) => alCambiar(evento.target.value)}
        className="mt-1 w-full rounded border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2 text-sm text-sobre-superficie focus-visible:ring-2 focus-visible:ring-primario focus-visible:outline-none"
      />
    </div>
  );
}
