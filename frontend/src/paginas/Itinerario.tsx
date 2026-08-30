/**
 * Página del itinerario de un día (Incremento 4).
 *
 * Es donde se ve cerrada la brecha 4: *el proceso no incorporaba la
 * distribución geográfica ni el tiempo y costo de desplazamiento*. La pantalla
 * de resultados del Incremento 3 decía **qué** visitar; esta dice **en qué
 * orden, a qué hora, cómo llegar y cuánto cuesta**.
 *
 * Tres decisiones de esta pantalla que conviene poder defender:
 *
 * 1. **El mapa y la línea de tiempo están sincronizados.** Pasar el ratón por
 *    una parada la resalta en el mapa. Sin eso, son dos vistas del mismo día
 *    que el visitante tiene que reconciliar de cabeza.
 *
 * 2. **Reordenar es optimista pero honesto.** Al soltar una parada, la lista
 *    se reordena al instante para que la interfaz responda, pero los horarios
 *    y los costos se muestran atenuados hasta que el backend devuelve los
 *    números reales. Enseñar horarios viejos junto a un orden nuevo sería
 *    enseñar datos falsos.
 *
 * 3. **Los avisos van arriba y no al final.** Un aviso de que un tramo se
 *    estimó, o de que se va a subir a 4 000 m, no es una nota al pie.
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import LineaDeTiempo from '@/componentes/LineaDeTiempo';
import MapaItinerario from '@/componentes/MapaItinerario';
import TotalesDelDia from '@/componentes/TotalesDelDia';
import { useSesion } from '@/hooks/useSesion';
import {
  armarItinerario,
  obtenerPreferencia,
  reordenarItinerario,
  type RespuestaItinerario,
} from '@/servicios/api';
import { formatearFecha } from '@/utilidades/formato';

export function Itinerario() {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { token } = useSesion();

  const identificador = Number(id);
  const habilitado = Number.isFinite(identificador);

  /** Qué día del viaje se está planificando. */
  const [fecha, establecerFecha] = useState<string | undefined>(undefined);

  /** Parada resaltada, para sincronizar la lista con el mapa. */
  const [paradaActiva, establecerParadaActiva] = useState<number | null>(null);

  /**
   * Orden que el visitante acaba de pedir, mientras el backend recalcula.
   *
   * Se guarda **solo el orden** y no el itinerario entero. Guardar el
   * itinerario obligaría a copiarlo de la consulta al estado con un efecto, y
   * eso provoca renders en cascada: el componente se pinta con el dato viejo,
   * el efecto lo cambia, y se vuelve a pintar. Con el orden aparte, el
   * itinerario que se enseña se **deriva** en el render y no hay efecto ninguno.
   */
  const [ordenOptimista, establecerOrdenOptimista] = useState<number[] | null>(null);

  const { data: preferencia } = useQuery({
    queryKey: ['preferencia', identificador],
    queryFn: () => obtenerPreferencia(identificador, token),
    enabled: habilitado,
  });

  const {
    data: calculado,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['itinerario', identificador, fecha],
    queryFn: () => armarItinerario(identificador, token, { fecha }),
    enabled: habilitado,
    retry: false,
    // El ruteo tarda unos segundos: no tiene sentido rehacerlo cada vez que la
    // ventana recupera el foco.
    refetchOnWindowFocus: false,
  });

  const reordenar = useMutation({
    mutationFn: (recursosEnOrden: number[]) =>
      reordenarItinerario(identificador, recursosEnOrden, token, { fecha }),
    // Llegaron los números reales: el orden provisional ya no hace falta.
    onSuccess: () => establecerOrdenOptimista(null),
  });

  // Lo último que dijo el backend: la respuesta de reordenar si la hay, y si
  // no el cálculo inicial del día.
  const base = reordenar.data ?? calculado ?? null;

  /**
   * El itinerario que se enseña, con el orden provisional aplicado si lo hay.
   *
   * Se deriva en cada render en vez de guardarse en estado. Así arrastrar se
   * siente inmediato —el orden cambia al soltar— sin que la interfaz tenga que
   * mantener una copia del itinerario que podría quedarse desincronizada.
   */
  const itinerario = useMemo<RespuestaItinerario | null>(() => {
    if (!base || !ordenOptimista) return base;

    const porId = new Map(base.paradas.map((p) => [p.recurso_id, p]));

    const paradas = ordenOptimista
      .map((recursoId) => porId.get(recursoId))
      .filter((parada): parada is NonNullable<typeof parada> => parada !== undefined)
      .map((parada, indice) => ({ ...parada, orden: indice }));

    return paradas.length > 0 ? { ...base, paradas } : base;
  }, [base, ordenOptimista]);

  /**
   * Aplica el orden nuevo al instante y pide al backend los números reales.
   *
   * Los horarios y costos que se ven mientras tanto son los del orden
   * anterior, así que la lista se atenúa hasta que llega la respuesta: enseñar
   * un orden nuevo con horarios viejos sin avisar sería enseñar datos falsos.
   */
  function alReordenar(recursosEnOrden: number[]) {
    establecerOrdenOptimista(recursosEnOrden);
    reordenar.mutate(recursosEnOrden);
  }

  /** Cambia de día y descarta lo que se estuviera enseñando del anterior. */
  function alCambiarDeDia(dia: string) {
    establecerFecha(dia);
    establecerOrdenOptimista(null);
    // Sin esto, la respuesta de un reordenamiento del día anterior seguiria
    // teniendo prioridad sobre el calculo del dia nuevo.
    reordenar.reset();
  }

  if (!habilitado) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <p className="text-sobre-superficie-variante">{t('itinerario.identificadorInvalido')}</p>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <h1 className="font-titulo text-2xl font-bold text-sobre-superficie">
          {t('itinerario.titulo')}
        </h1>
        <p className="mt-3 text-sobre-superficie-variante">{t('itinerario.calculando')}</p>
        <p className="mt-1 text-sm text-sobre-superficie-variante">
          {t('itinerario.calculandoDetalle')}
        </p>
      </main>
    );
  }

  if (isError || !itinerario) {
    return (
      <main className="mx-auto max-w-contenido px-4 py-16 sm:px-6">
        <h1 className="font-titulo text-2xl font-bold text-sobre-superficie">
          {t('itinerario.titulo')}
        </h1>
        <p className="mt-3 text-sobre-error-contenedor">
          {error instanceof Error ? error.message : t('itinerario.errorGenerico')}
        </p>
        <Link
          to={`/preferencias/${identificador}/resultados`}
          className="mt-4 inline-block text-sm text-primario underline"
        >
          {t('itinerario.volverAResultados')}
        </Link>
      </main>
    );
  }

  const dias = diasDelViaje(preferencia?.fecha_inicio, preferencia?.fecha_fin);

  return (
    <main className="mx-auto max-w-contenido px-4 py-10 sm:px-6">
      <motion.header
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <p className="text-sm text-sobre-superficie-variante">
          <Link
            to={`/preferencias/${identificador}/resultados`}
            className="text-primario underline"
          >
            {t('itinerario.volverAResultados')}
          </Link>
        </p>

        <h1 className="mt-2 font-titulo text-3xl font-bold text-sobre-superficie">
          {itinerario.titulo}
        </h1>
        <p className="mt-1 text-sobre-superficie-variante">
          {formatearFecha(itinerario.fecha, i18n.language)}
        </p>
      </motion.header>

      {/* Selector de día, solo si el viaje dura más de uno. Cada día se
          optimiza por separado: el visitante duerme entre medias. */}
      {dias.length > 1 && (
        <nav className="mt-5 flex flex-wrap gap-2" aria-label={t('itinerario.elegirDia')}>
          {dias.map((dia, indice) => {
            const activo = (fecha ?? dias[0]) === dia;

            return (
              <button
                key={dia}
                type="button"
                onClick={() => alCambiarDeDia(dia)}
                aria-current={activo ? 'true' : undefined}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  activo
                    ? 'bg-primario text-sobre-primario'
                    : 'border border-contorno-variante text-sobre-superficie-variante hover:bg-superficie-contenedor'
                }`}
              >
                {t('itinerario.dia', { numero: indice + 1 })}
              </button>
            );
          })}
        </nav>
      )}

      {/* Los avisos, arriba. Un aviso de altitud o de tramo estimado no es una
          nota al pie: puede cambiar lo que el visitante mete en la mochila. */}
      {itinerario.avisos.length > 0 && (
        <div
          className="mt-6 rounded-lg border border-terciario bg-terciario-contenedor p-4"
          role="status"
        >
          <h2 className="font-titulo text-sm font-semibold text-sobre-terciario-contenedor">
            {t('itinerario.avisos')}
          </h2>
          <ul className="mt-2 space-y-1.5">
            {itinerario.avisos.map((aviso) => (
              <li
                key={aviso}
                className="flex items-start gap-2 text-sm text-sobre-terciario-contenedor"
              >
                <span aria-hidden="true">•</span>
                <span>{aviso}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6">
        <TotalesDelDia itinerario={itinerario} />
      </div>

      {/* El paso al Incremento 5. Se lleva el identificador y la fecha para que
          pedir un almuerzo para el dia ya planificado no obligue a volver a
          escribirla. */}
      {itinerario.paradas.length > 0 && (
        <section className="mt-6 rounded-lg border border-secundario bg-secundario-contenedor p-5">
          <h2 className="font-titulo font-semibold text-sobre-secundario-contenedor">
            {t('itinerario.coordinarTitulo')}
          </h2>
          <p className="mt-1 text-sm text-sobre-secundario-contenedor">
            {t('itinerario.coordinarDetalle')}
          </p>
          <Link
            to={`/coordinar?itinerario=${identificador}&fecha=${itinerario.fecha}`}
            className="mt-3 inline-block rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario transition-transform hover:-translate-y-0.5"
          >
            {t('itinerario.coordinarBoton')}
          </Link>
        </section>
      )}

      {/* El cierre del recorrido: valorar lo vivido. Va despues de coordinar
          porque es lo ultimo que ocurre, y solo se ofrece si hubo paradas: no
          se puede valorar un dia que no se armo. */}
      {itinerario.paradas.length > 0 && (
        <section className="mt-4 rounded-lg border border-contorno-variante bg-superficie-contenedor p-5">
          <h2 className="font-titulo font-semibold text-sobre-superficie">
            {t('itinerario.valorarTitulo')}
          </h2>
          <p className="mt-1 text-sm text-sobre-superficie-variante">
            {t('itinerario.valorarDetalle')}
          </p>
          <Link
            to={`/preferencias/${identificador}/valorar?fecha=${itinerario.fecha}`}
            className="mt-3 inline-block rounded-full border border-primario px-5 py-2 text-sm font-semibold text-primario transition-colors hover:bg-primario hover:text-sobre-primario"
          >
            {t('itinerario.valorarBoton')}
          </Link>
        </section>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <section aria-label={t('itinerario.tituloLinea')}>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
              {t('itinerario.tituloLinea')}
            </h2>
            {reordenar.isPending && (
              <span className="text-xs text-sobre-superficie-variante">
                {t('itinerario.recalculando')}
              </span>
            )}
          </div>

          <p className="mb-3 text-xs text-sobre-superficie-variante">
            {t('itinerario.comoReordenar')}
          </p>

          <LineaDeTiempo
            paradas={itinerario.paradas}
            alReordenar={alReordenar}
            recalculando={reordenar.isPending}
            alSenalar={establecerParadaActiva}
          />

          {reordenar.isError && (
            <p className="mt-3 text-sm text-sobre-error-contenedor" role="alert">
              {t('itinerario.errorAlReordenar')}
            </p>
          )}
        </section>

        <div className="lg:sticky lg:top-6 lg:h-[32rem]">
          <MapaItinerario paradas={itinerario.paradas} paradaActiva={paradaActiva} />
        </div>
      </div>
    </main>
  );
}

/**
 * Devuelve las fechas del viaje, una por día, en formato ISO.
 *
 * Se construyen sumando días a la fecha de inicio en UTC para que no se
 * desplacen por la zona horaria: en Perú (UTC−5), crear una fecha a partir de
 * `2026-09-12` y leer su día local daría el 11.
 */
function diasDelViaje(inicio?: string, fin?: string): string[] {
  if (!inicio || !fin) return [];

  const primero = new Date(`${inicio}T12:00:00Z`);
  const ultimo = new Date(`${fin}T12:00:00Z`);

  const dias: string[] = [];

  for (
    let dia = new Date(primero);
    dia <= ultimo && dias.length < 31;
    dia.setUTCDate(dia.getUTCDate() + 1)
  ) {
    dias.push(dia.toISOString().slice(0, 10));
  }

  return dias;
}
