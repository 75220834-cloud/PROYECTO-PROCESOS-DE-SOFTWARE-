/**
 * Pantalla de cierre del itinerario: valorar la experiencia (Incremento 6).
 *
 * Cierra la brecha 7 desde el lado de quien viajó. Es el último paso del
 * recorrido completo del visitante:
 *
 *   preferencias → recomendaciones → itinerario → coordinar → **valorar**
 *
 * ## Se puede valorar el día, o cada parada
 *
 * Un solo cuadro de «¿qué tal el viaje?» daría una estrella y un párrafo sin
 * destinatario. El gestor necesita saber **qué** estuvo mal, no solo que algo
 * lo estuvo, y para eso la valoración tiene que poder apuntar a un recurso
 * concreto.
 *
 * Se ofrecen las dos: una del día completo, y una por cada parada del
 * itinerario. Ninguna es obligatoria.
 *
 * ## Lo que ya se valoró no se vuelve a pedir
 *
 * Al entrar se consulta qué valoraciones existen ya para este itinerario, y
 * esas paradas se muestran con lo que se dijo en vez de con un formulario
 * vacío. Volver a pedir lo que alguien ya dio es la forma más rápida de que no
 * lo dé una segunda vez.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import FormularioValoracion from '@/componentes/FormularioValoracion';
import { useSesion } from '@/hooks/useSesion';
import {
  armarItinerario,
  obtenerValoraciones,
  type ParadaItinerario,
  type ValoracionPublica,
} from '@/servicios/api';
import { formatearFecha, formatearNombrePropio } from '@/utilidades/formato';

export function Valorar() {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { token } = useSesion();
  const [parametros] = useSearchParams();
  const clienteDeConsultas = useQueryClient();

  const preferenciaId = Number(id);
  const fecha = parametros.get('fecha') ?? undefined;

  const [abierto, establecerAbierto] = useState<number | 'dia' | null>(null);

  // Se rearma el itinerario para saber qué paradas hubo. Es la misma consulta
  // que la pantalla del itinerario, así que React Query la sirve de su caché
  // cuando se llega desde allí.
  const itinerario = useQuery({
    queryKey: ['itinerario', preferenciaId, fecha],
    queryFn: () => armarItinerario(preferenciaId, token, { fecha, guardar: true }),
    enabled: Number.isFinite(preferenciaId),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const itinerarioId = itinerario.data?.itinerario_id ?? null;

  const valoraciones = useQuery({
    queryKey: ['valoraciones', itinerarioId],
    queryFn: () => obtenerValoraciones(itinerarioId as number),
    enabled: itinerarioId !== null,
  });

  const yaValorado = new Map<number | 'dia', ValoracionPublica>();

  for (const valoracion of valoraciones.data ?? []) {
    yaValorado.set(valoracion.recurso_id ?? 'dia', valoracion);
  }

  function alEnviar() {
    establecerAbierto(null);
    void clienteDeConsultas.invalidateQueries({ queryKey: ['valoraciones'] });
    void clienteDeConsultas.invalidateQueries({ queryKey: ['evidencia'] });
    void clienteDeConsultas.invalidateQueries({ queryKey: ['tablero-indicadores'] });
  }

  if (itinerario.isLoading) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('itinerario.calculando')}</p>
      </main>
    );
  }

  if (itinerario.isError || !itinerario.data) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-error-contenedor">{t('itinerario.errorGenerico')}</p>
      </main>
    );
  }

  const plan = itinerario.data;

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-contenido px-4 py-10 sm:px-6"
    >
      <header>
        <p className="text-sm">
          <Link
            to={`/preferencias/${preferenciaId}/itinerario`}
            className="text-primario underline"
          >
            {t('itinerario.volverAResultados')}
          </Link>
        </p>

        <h1 className="mt-2 font-titulo text-3xl font-extrabold text-sobre-superficie">
          {t('valoracion.titulo')}
        </h1>
        <p className="mt-1 text-sobre-superficie-variante">
          {plan.titulo} · {formatearFecha(plan.fecha, i18n.language)}
        </p>
        <p className="mt-2 text-sm text-sobre-superficie-variante">{t('valoracion.subtitulo')}</p>
      </header>

      {/* El día completo. */}
      <section className="mt-6" aria-label={t('valoracion.elDiaCompleto')}>
        <BloqueValorable
          etiqueta={t('valoracion.elDiaCompleto')}
          detalle={plan.titulo}
          valoracion={yaValorado.get('dia')}
          abierto={abierto === 'dia'}
          alAbrir={() => establecerAbierto('dia')}
          alCerrar={() => establecerAbierto(null)}
          itinerarioId={itinerarioId}
          recursoId={null}
          alEnviar={alEnviar}
        />
      </section>

      {/* Cada parada. */}
      {plan.paradas.length > 0 && (
        <section className="mt-8" aria-label={t('valoracion.queValoras')}>
          <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
            {t('valoracion.queValoras')}
          </h2>

          <ul className="mt-4 grid list-none gap-4">
            {plan.paradas.map((parada) => (
              <li key={parada.recurso_id}>
                <BloqueValorable
                  etiqueta={formatearNombrePropio(parada.nombre)}
                  detalle={detalleDeLaParada(parada)}
                  valoracion={yaValorado.get(parada.recurso_id)}
                  abierto={abierto === parada.recurso_id}
                  alAbrir={() => establecerAbierto(parada.recurso_id)}
                  alCerrar={() => establecerAbierto(null)}
                  itinerarioId={itinerarioId}
                  recursoId={parada.recurso_id}
                  alEnviar={alEnviar}
                />
              </li>
            ))}
          </ul>
        </section>
      )}
    </motion.main>
  );
}

function detalleDeLaParada(parada: ParadaItinerario): string {
  return `${formatearNombrePropio(parada.distrito)} · ${parada.hora_llegada.slice(0, 5)}`;
}

/**
 * Un bloque que se puede valorar: o enseña lo que ya se dijo, o el formulario.
 *
 * Los tres estados son deliberados. Un formulario abierto por cada parada
 * llenaría la pantalla de cajas de texto vacías y nadie rellenaría ninguna.
 */
function BloqueValorable({
  etiqueta,
  detalle,
  valoracion,
  abierto,
  alAbrir,
  alCerrar,
  itinerarioId,
  recursoId,
  alEnviar,
}: {
  etiqueta: string;
  detalle: string;
  valoracion?: ValoracionPublica;
  abierto: boolean;
  alAbrir: () => void;
  alCerrar: () => void;
  itinerarioId: number | null;
  recursoId: number | null;
  alEnviar: () => void;
}) {
  const { t } = useTranslation();

  // Ya valorado: se enseña lo que se dijo, no un formulario.
  if (valoracion) {
    return (
      <div className="rounded-lg border border-secundario bg-superficie-contenedor p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="font-titulo font-semibold text-sobre-superficie">{etiqueta}</span>
          <span
            className="text-terciario"
            aria-label={t('valoracion.estrellas', { count: valoracion.puntuacion })}
          >
            <span aria-hidden="true">{'★'.repeat(valoracion.puntuacion)}</span>
          </span>
        </div>

        {valoracion.comentario && (
          <p className="mt-2 text-sm text-sobre-superficie-variante">«{valoracion.comentario}»</p>
        )}

        {valoracion.temas.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1">
            {valoracion.temas.map((tema) => (
              <li
                key={tema}
                className="rounded bg-superficie-contenedor-alto px-1.5 py-0.5 text-xs text-sobre-superficie-variante"
              >
                {t(`valoracion.temas.${tema}`)}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (abierto && itinerarioId !== null) {
    return (
      <FormularioValoracion
        itinerarioId={itinerarioId}
        recursoId={recursoId}
        queSeValora={etiqueta}
        alEnviar={alEnviar}
        alCerrar={alCerrar}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={alAbrir}
      disabled={itinerarioId === null}
      className="flex w-full flex-wrap items-center justify-between gap-3 rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-4 text-left transition-colors hover:bg-superficie-contenedor disabled:opacity-60"
    >
      <span>
        <span className="block font-titulo font-semibold text-sobre-superficie">{etiqueta}</span>
        <span className="block text-sm text-sobre-superficie-variante">{detalle}</span>
      </span>

      <span className="shrink-0 rounded-full bg-primario px-4 py-1.5 text-sm font-semibold text-sobre-primario">
        {t('navegacion.valorar')}
      </span>
    </button>
  );
}
