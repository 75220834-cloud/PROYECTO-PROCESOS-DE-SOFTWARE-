/**
 * Panel de gestión, con pestañas según el rol (Incremento 5).
 *
 * | Rol | Qué ve |
 * |---|---|
 * | Proveedor | Las solicitudes de sus servicios, y sus servicios |
 * | Operador | Todas las solicitudes, para coordinar |
 * | Gestor | El catálogo y su estado de validación |
 * | Administrador | Todo |
 *
 * ## La comprobación de rol de esta pantalla no es la que protege nada
 *
 * Aquí se oculta lo que no corresponde al rol, pero **eso es comodidad, no
 * seguridad**. Quien tenga la dirección puede abrirla igual, y quien sepa usar
 * la consola del navegador puede llamar a la API directamente.
 *
 * Lo que de verdad protege está en el backend: `servicios/coordinacion.py`
 * decide qué solicitudes devuelve cada rol, y los endpoints de publicación
 * responden 403 a quien no es proveedor. Hay pruebas para las dos cosas. Esta
 * pantalla solo evita enseñar pestañas vacías.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import TarjetaServicio from '@/componentes/TarjetaServicio';
import TarjetaSolicitud from '@/componentes/TarjetaSolicitud';
import { useSesion } from '@/hooks/useSesion';
import {
  cambiarEstadoDeSolicitud,
  obtenerIndicadorDeCoordinacion,
  obtenerIndicadorCatalogo,
  obtenerMisServicios,
  obtenerSolicitudes,
  type EstadoSolicitud,
  type SolicitudPublica,
} from '@/servicios/api';

/** Qué pestañas ve cada rol. El orden es el de uso más frecuente. */
const PESTANAS_POR_ROL: Record<string, string[]> = {
  proveedor: ['solicitudes', 'servicios', 'indicador'],
  operador: ['solicitudes', 'indicador'],
  gestor: ['catalogo', 'indicador'],
  administrador: ['solicitudes', 'servicios', 'catalogo', 'indicador'],
};

const ROLES_CON_PANEL = Object.keys(PESTANAS_POR_ROL);

export function Panel() {
  const { t } = useTranslation();
  const { token, usuario } = useSesion();

  const pestanas = usuario ? (PESTANAS_POR_ROL[usuario.rol] ?? []) : [];
  const [activa, establecerActiva] = useState<string | null>(null);

  if (!usuario) {
    return (
      <Mensaje titulo={t('coordinacion.panelTitulo')}>
        <p className="text-sobre-superficie-variante">{t('coordinacion.sinSesion')}</p>
        <Link to="/acceso" className="mt-3 inline-block text-sm text-primario underline">
          {t('navegacion.iniciar_sesion')}
        </Link>
      </Mensaje>
    );
  }

  if (!ROLES_CON_PANEL.includes(usuario.rol)) {
    return (
      <Mensaje titulo={t('coordinacion.panelTitulo')}>
        <p className="text-sobre-superficie-variante">{t('coordinacion.sinPermiso')}</p>
      </Mensaje>
    );
  }

  const pestanaActiva = activa ?? pestanas[0];

  return (
    <main className="mx-auto max-w-contenido px-4 py-10 sm:px-6">
      <h1 className="font-titulo text-3xl font-extrabold text-sobre-superficie">
        {t('coordinacion.panelTitulo')}
      </h1>
      <p className="mt-1 text-sm text-sobre-superficie-variante">
        {usuario.nombre} · {t(`roles.${usuario.rol}`)}
      </p>

      <nav
        className="mt-6 flex flex-wrap gap-2 border-b border-contorno-variante pb-3"
        aria-label={t('coordinacion.panelTitulo')}
      >
        {pestanas.map((pestana) => (
          <button
            key={pestana}
            type="button"
            onClick={() => establecerActiva(pestana)}
            aria-current={pestanaActiva === pestana ? 'page' : undefined}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              pestanaActiva === pestana
                ? 'bg-primario text-sobre-primario'
                : 'text-sobre-superficie-variante hover:bg-superficie-contenedor'
            }`}
          >
            {t(`coordinacion.pestana${pestana.charAt(0).toUpperCase()}${pestana.slice(1)}`)}
          </button>
        ))}
      </nav>

      <div className="mt-6">
        {pestanaActiva === 'solicitudes' && <PestanaSolicitudes token={token} />}
        {pestanaActiva === 'servicios' && <PestanaServicios token={token} />}
        {pestanaActiva === 'catalogo' && <PestanaCatalogo />}
        {pestanaActiva === 'indicador' && <PestanaIndicador />}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Solicitudes — el proveedor responde, el operador coordina
// ---------------------------------------------------------------------------

function PestanaSolicitudes({ token }: { token: string | null }) {
  const { t } = useTranslation();

  const solicitudes = useQuery({
    queryKey: ['solicitudes', 'panel'],
    queryFn: () => obtenerSolicitudes(token),
  });

  if (solicitudes.isLoading) {
    return <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>;
  }

  if (solicitudes.isError) {
    return <p className="text-sobre-error-contenedor">{t('coordinacion.error')}</p>;
  }

  if (!solicitudes.data || solicitudes.data.length === 0) {
    return (
      <p className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
        {t('coordinacion.sinSolicitudesRecibidas')}
      </p>
    );
  }

  return (
    <ul className="grid list-none gap-4">
      {solicitudes.data.map((solicitud) => (
        <TarjetaSolicitud
          key={solicitud.id}
          solicitud={solicitud}
          acciones={<AccionesDeProveedor solicitud={solicitud} token={token} />}
        />
      ))}
    </ul>
  );
}

/**
 * Los botones con los que el proveedor mueve una solicitud.
 *
 * Solo se enseñan las transiciones que el backend acepta desde el estado
 * actual. Enseñar un botón que va a devolver 409 sería prometer algo que no se
 * puede hacer.
 */
function AccionesDeProveedor({
  solicitud,
  token,
}: {
  solicitud: SolicitudPublica;
  token: string | null;
}) {
  const { t } = useTranslation();
  const clienteDeConsultas = useQueryClient();

  const [precio, establecerPrecio] = useState('');
  const [nota, establecerNota] = useState('');

  const cambio = useMutation({
    mutationFn: (estado: EstadoSolicitud) =>
      cambiarEstadoDeSolicitud(solicitud.id, estado, token, {
        nota: nota || undefined,
        precioAcordado: precio || undefined,
      }),
    onSuccess: () => {
      establecerPrecio('');
      establecerNota('');
      void clienteDeConsultas.invalidateQueries({ queryKey: ['solicitudes'] });
      void clienteDeConsultas.invalidateQueries({ queryKey: ['indicador-coordinacion'] });
    },
  });

  const cerrada = ['confirmada', 'rechazada', 'cancelada'].includes(solicitud.estado);

  if (cerrada) return null;

  const puedeRevisar = solicitud.estado === 'enviada';

  return (
    <div className="rounded border border-contorno-variante bg-superficie-contenedor p-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="block font-medium text-sobre-superficie">
            {t('coordinacion.precioAAcordar')}
          </span>
          <input
            type="number"
            min={0}
            step="0.50"
            value={precio}
            onChange={(evento) => establecerPrecio(evento.target.value)}
            className="mt-1 w-full rounded border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-1.5 text-sm text-sobre-superficie"
          />
        </label>

        <label className="text-sm">
          <span className="block font-medium text-sobre-superficie">
            {t('coordinacion.notaParaElVisitante')}
          </span>
          <input
            type="text"
            value={nota}
            maxLength={2000}
            onChange={(evento) => establecerNota(evento.target.value)}
            className="mt-1 w-full rounded border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-1.5 text-sm text-sobre-superficie"
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {puedeRevisar && (
          <button
            type="button"
            disabled={cambio.isPending}
            onClick={() => cambio.mutate('en_revision')}
            className="rounded-full border border-contorno-variante px-4 py-1.5 text-sm font-semibold text-sobre-superficie-variante disabled:opacity-60"
          >
            {t('coordinacion.tomarEnRevision')}
          </button>
        )}

        <button
          type="button"
          disabled={cambio.isPending}
          onClick={() => cambio.mutate('confirmada')}
          className="rounded-full bg-secundario px-4 py-1.5 text-sm font-semibold text-sobre-secundario disabled:opacity-60"
        >
          {t('coordinacion.confirmar')}
        </button>

        <button
          type="button"
          disabled={cambio.isPending}
          onClick={() => cambio.mutate('rechazada')}
          className="rounded-full border border-error px-4 py-1.5 text-sm font-semibold text-sobre-error-contenedor disabled:opacity-60"
        >
          {t('coordinacion.rechazar')}
        </button>
      </div>

      {cambio.isError && (
        <p className="mt-2 text-sm text-sobre-error-contenedor" role="alert">
          {cambio.error instanceof Error
            ? cambio.error.message
            : t('coordinacion.errorAlResponder')}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Servicios del proveedor
// ---------------------------------------------------------------------------

function PestanaServicios({ token }: { token: string | null }) {
  const { t } = useTranslation();

  const servicios = useQuery({
    queryKey: ['mis-servicios'],
    queryFn: () => obtenerMisServicios(token),
    retry: false,
  });

  if (servicios.isLoading) {
    return <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>;
  }

  if (servicios.isError) {
    // El caso más probable: rol de proveedor sin ficha asociada.
    return (
      <p className="rounded-lg border border-terciario bg-terciario-contenedor p-4 text-sm text-sobre-terciario-contenedor">
        {t('coordinacion.sinFichaDeProveedor')}
      </p>
    );
  }

  if (!servicios.data || servicios.data.length === 0) {
    return (
      <p className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
        {t('coordinacion.sinMisServicios')}
      </p>
    );
  }

  return (
    <ul className="grid list-none gap-4 md:grid-cols-2">
      {servicios.data.map((servicio) => (
        <TarjetaServicio key={servicio.id} servicio={servicio} />
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Catálogo — la pestaña del gestor
// ---------------------------------------------------------------------------

function PestanaCatalogo() {
  const { t } = useTranslation();

  const indicadores = useQuery({
    queryKey: ['indicadores-catalogo'],
    queryFn: obtenerIndicadorCatalogo,
  });

  if (!indicadores.data) {
    return <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>;
  }

  const datos = indicadores.data;

  return (
    <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {t('coordinacion.catalogoTitulo')}
      </h2>

      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Dato etiqueta={t('coordinacion.totalRecursos')} valor={String(datos.total_recursos)} />
        <Dato etiqueta={t('coordinacion.validados')} valor={String(datos.validados)} />
        <Dato etiqueta={t('coordinacion.vigentes')} valor={String(datos.vigentes)} />
        <Dato
          etiqueta={t('coordinacion.porcentajeValidado')}
          valor={`${datos.porcentaje_validado.toFixed(2)} %`}
        />
      </dl>

      <p className="mt-4 text-xs text-sobre-superficie-variante">
        {t('coordinacion.fechaMedicion')}: {datos.fecha}
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Indicador del incremento
// ---------------------------------------------------------------------------

function PestanaIndicador() {
  const { t } = useTranslation();

  const resumen = useQuery({
    queryKey: ['indicador-coordinacion'],
    queryFn: obtenerIndicadorDeCoordinacion,
  });

  if (!resumen.data) {
    return <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>;
  }

  const datos = resumen.data;

  return (
    <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {t('coordinacion.indicadorTitulo')}
      </h2>

      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Dato
          etiqueta={t('coordinacion.totalSolicitudes')}
          valor={String(datos.total_solicitudes)}
        />
        <Dato etiqueta={t('coordinacion.confirmadas')} valor={String(datos.confirmadas)} />
        <Dato etiqueta={t('coordinacion.rechazadas')} valor={String(datos.rechazadas)} />
        <Dato etiqueta={t('coordinacion.pendientes')} valor={String(datos.pendientes)} />
      </dl>

      <dl className="mt-6 grid gap-4 sm:grid-cols-3">
        <Dato
          etiqueta={t('coordinacion.interaccionesMedias')}
          valor={
            datos.interacciones_medias_hasta_confirmar !== null
              ? String(datos.interacciones_medias_hasta_confirmar)
              : t('coordinacion.sinDatoTodavia')
          }
          detalle={
            datos.interacciones_medias_hasta_confirmar === null
              ? t('coordinacion.sinDatoExplicacion')
              : undefined
          }
        />
        <Dato
          etiqueta={t('coordinacion.horasMedias')}
          valor={
            datos.horas_medias_hasta_confirmar !== null
              ? String(datos.horas_medias_hasta_confirmar)
              : t('coordinacion.sinDatoTodavia')
          }
        />
        <Dato
          etiqueta={t('coordinacion.canales')}
          valor={String(datos.canales_para_confirmar)}
          detalle={t('coordinacion.canalesExplicacion')}
        />
      </dl>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Piezas compartidas
// ---------------------------------------------------------------------------

function Dato({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-sobre-superficie-variante uppercase">{etiqueta}</dt>
      <dd className="mt-0.5 font-titulo text-lg font-semibold text-sobre-superficie">{valor}</dd>
      {detalle && <p className="mt-1 text-xs text-sobre-superficie-variante">{detalle}</p>}
    </div>
  );
}

function Mensaje({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
      <h1 className="font-titulo text-2xl font-bold text-sobre-superficie">{titulo}</h1>
      <div className="mt-3">{children}</div>
    </main>
  );
}
