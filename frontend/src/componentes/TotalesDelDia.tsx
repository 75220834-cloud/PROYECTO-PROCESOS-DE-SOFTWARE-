/**
 * Los totales del día: tiempo, costo, distancia y esfuerzo físico.
 *
 * ## Por qué el esfuerzo se muestra como barra y no como un número
 *
 * «580 m de desnivel positivo» no le dice nada a quien no hace montaña. La
 * barra sí: se ve de un vistazo si el día es una caminata o una paliza. El
 * número queda debajo para quien sepa leerlo.
 *
 * El desnivel que se muestra es **solo la subida acumulada**, no el desnivel
 * neto. Un día que sube y baja 400 m tres veces es duro aunque termine a la
 * misma altura a la que empezó, y el neto diría cero.
 *
 * ## Por qué el costo es un rango
 *
 * Porque no hay tarifa oficial única en el valle. Enseñar un número redondo
 * afirmaría una precisión que el proyecto sabe que no tiene.
 */
import { useTranslation } from 'react-i18next';

import type { RespuestaItinerario } from '@/servicios/api';
import { formatearDuracion, formatearPrecio } from '@/utilidades/formato';

/**
 * Dónde termina cada tramo de la barra de esfuerzo, en metros de subida.
 *
 * Son los mismos umbrales que usa el backend en `clasificar_esfuerzo`: 300 m
 * es el orden de una cuesta larga urbana, 800 m ya es jornada de montaña. Se
 * repiten aquí porque la barra necesita una escala, y se documenta que vienen
 * de allí para que nadie los cambie en un sitio y no en el otro.
 */
const TOPE_DE_LA_BARRA_M = 1200;

/** Color de la barra según lo duro que sea el día. */
const COLOR_DE_ESFUERZO: Record<string, string> = {
  suave: 'bg-secundario',
  moderado: 'bg-terciario',
  exigente: 'bg-primario',
};

function Dato({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-sobre-superficie-variante uppercase">{etiqueta}</dt>
      <dd className="mt-0.5 font-titulo text-lg font-semibold text-sobre-superficie">{valor}</dd>
      {detalle && <p className="text-xs text-sobre-superficie-variante">{detalle}</p>}
    </div>
  );
}

export default function TotalesDelDia({ itinerario }: { itinerario: RespuestaItinerario }) {
  const { t } = useTranslation();

  const porcentaje = Math.min(100, (itinerario.subida_total_m / TOPE_DE_LA_BARRA_M) * 100);

  return (
    <section
      className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5"
      aria-label={t('itinerario.totales')}
    >
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Dato
          etiqueta={t('itinerario.tiempoTotal')}
          valor={formatearDuracion(itinerario.tiempo_total_min)}
          detalle={t('itinerario.paradasContadas', { count: itinerario.paradas.length })}
        />

        <Dato
          etiqueta={t('itinerario.costoTraslados')}
          valor={formatearPrecio(itinerario.costo_min_soles, itinerario.costo_max_soles)}
          detalle={t('itinerario.soloTraslados')}
        />

        <Dato
          etiqueta={t('itinerario.distancia')}
          valor={`${itinerario.distancia_total_km.toFixed(1)} km`}
        />

        <Dato
          etiqueta={t('itinerario.esfuerzo')}
          valor={t(`itinerario.esfuerzoNivel.${itinerario.esfuerzo}`)}
          detalle={t('itinerario.subidaAcumulada', {
            metros: Math.round(itinerario.subida_total_m),
          })}
        />
      </dl>

      {/* La barra de esfuerzo físico. `role="img"` con su etiqueta porque para
          un lector de pantalla una barra vacía no significa nada: se le da el
          mismo dato en palabras. */}
      <div
        className="mt-4 h-2 w-full overflow-hidden rounded-full bg-superficie-contenedor-alto"
        role="img"
        aria-label={t('itinerario.barraEsfuerzoAccesible', {
          nivel: t(`itinerario.esfuerzoNivel.${itinerario.esfuerzo}`),
          metros: Math.round(itinerario.subida_total_m),
        })}
      >
        {/* La anchura va como estilo en línea y no como clase de Tailwind
            porque es un valor calculado: Tailwind genera sus clases leyendo el
            código fuente, y una clase construida en tiempo de ejecución no
            existiría en la hoja de estilos. */}
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${
            COLOR_DE_ESFUERZO[itinerario.esfuerzo] ?? 'bg-secundario'
          }`}
          style={{ width: `${porcentaje}%` }}
        />
      </div>

      {/* Cómo se generó el itinerario. Es la trazabilidad que exige la regla de
          oro de la IA del proyecto, y se enseña, no se esconde en un registro. */}
      <p className="mt-4 text-xs text-sobre-superficie-variante">
        {itinerario.generado_por === 'modelo'
          ? t('itinerario.generadoPorModelo')
          : t('itinerario.generadoPorReglas')}
      </p>
    </section>
  );
}
