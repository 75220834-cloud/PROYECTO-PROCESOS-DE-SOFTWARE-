/**
 * Línea de tiempo vertical del día, con sus traslados y sus costos.
 *
 * Es la pieza que cierra la brecha 4 en la interfaz. Hasta el Incremento 3 el
 * visitante recibía una lista de sitios recomendados y tenía que averiguar por
 * su cuenta en qué orden visitarlos, cuánto tardaría en llegar y cuánto le
 * costaría. Aquí eso ya está resuelto y, sobre todo, **está a la vista**: entre
 * cada dos paradas se ve el traslado con su modo, su duración y su precio.
 *
 * ## Arrastrar para reordenar
 *
 * Las paradas se pueden mover. Se implementa con la API nativa de arrastre del
 * navegador (`draggable`) y no con una biblioteca, por dos razones: son cinco o
 * seis elementos y no hace falta virtualización, y añadir una dependencia de
 * arrastre completa a un proyecto que ya tiene doce sería peso sin beneficio.
 *
 * **Además se puede reordenar con el teclado**, con las flechas arriba y abajo.
 * El arrastre y suelte nativo no es accesible: quien navega con teclado o con
 * lector de pantalla no puede usarlo. Ofrecer solo arrastre dejaría fuera a esa
 * gente de una función central de la aplicación.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import type { ParadaItinerario, TrasladoPublico } from '@/servicios/api';
import { formatearDuracion, formatearNombrePropio, formatearPrecio } from '@/utilidades/formato';

/** Icono de cada modo de transporte. */
const ICONO_DE_MODO: Record<string, string> = {
  caminando: '🚶',
  combi: '🚐',
  colectivo: '🚙',
  taxi: '🚕',
};

/** El bloque de traslado que va entre dos paradas. */
function Traslado({ traslado }: { traslado: TrasladoPublico }) {
  const { t } = useTranslation();

  const esEstimado = traslado.origen_del_calculo === 'linea_recta';

  return (
    <li className="relative ml-4 border-l-2 border-dashed border-contorno-variante py-3 pl-8">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-sobre-superficie-variante">
        <span aria-hidden="true">{ICONO_DE_MODO[traslado.modo] ?? '→'}</span>
        <span className="font-medium">{t(`itinerario.modo.${traslado.modo}`)}</span>
        <span>{formatearDuracion(traslado.minutos)}</span>
        <span>{traslado.distancia_km.toFixed(1)} km</span>

        {traslado.modo !== 'caminando' && (
          <span className="font-medium" title={`${traslado.fuente} (${traslado.fecha_referencia})`}>
            {formatearPrecio(traslado.precio_min_soles, traslado.precio_max_soles)}
          </span>
        )}
      </div>

      {/* El aviso de tramo estimado. No es un detalle: en los distritos sin
          cobertura de OpenStreetMap el tiempo real puede ser muy superior. */}
      {esEstimado && (
        <p className="mt-1.5 flex items-start gap-1.5 text-xs text-sobre-terciario-contenedor">
          <span aria-hidden="true">⚠</span>
          <span>{t('itinerario.tramoEstimado')}</span>
        </p>
      )}
    </li>
  );
}

interface Propiedades {
  paradas: ParadaItinerario[];
  /** Se llama con el orden nuevo cuando el visitante mueve una parada. */
  alReordenar: (recursosEnOrden: number[]) => void;
  /** Bloquea el arrastre mientras el backend recalcula. */
  recalculando?: boolean;
  alSenalar?: (recursoId: number | null) => void;
}

export default function LineaDeTiempo({
  paradas,
  alReordenar,
  recalculando = false,
  alSenalar,
}: Propiedades) {
  const { t } = useTranslation();

  const [arrastrando, setArrastrando] = useState<number | null>(null);

  /** Mueve la parada de una posición a otra y avisa del orden nuevo. */
  function mover(desde: number, hasta: number) {
    if (desde === hasta || hasta < 0 || hasta >= paradas.length) return;

    const nuevo = paradas.map((p) => p.recurso_id);
    const [movida] = nuevo.splice(desde, 1);
    nuevo.splice(hasta, 0, movida);

    alReordenar(nuevo);
  }

  function alPulsarTecla(evento: React.KeyboardEvent, indice: number) {
    // Se exige Alt para no robarle las flechas a la navegación normal de la
    // página: sin el modificador, alguien recorriendo la lista con el teclado
    // reordenaría el viaje sin querer.
    if (!evento.altKey) return;

    if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      mover(indice, indice - 1);
    } else if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      mover(indice, indice + 1);
    }
  }

  if (paradas.length === 0) {
    return (
      <p className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
        {t('itinerario.sinParadas')}
      </p>
    );
  }

  return (
    <ol className="list-none" aria-label={t('itinerario.tituloLinea')}>
      {paradas.map((parada, indice) => (
        <li key={parada.recurso_id} className="list-none">
          {parada.traslado && <Traslado traslado={parada.traslado} />}

          <div
            draggable={!recalculando}
            onDragStart={() => setArrastrando(indice)}
            onDragEnd={() => setArrastrando(null)}
            onDragOver={(evento) => evento.preventDefault()}
            onDrop={() => {
              if (arrastrando !== null) mover(arrastrando, indice);
              setArrastrando(null);
            }}
            onKeyDown={(evento) => alPulsarTecla(evento, indice)}
            onMouseEnter={() => alSenalar?.(parada.recurso_id)}
            onMouseLeave={() => alSenalar?.(null)}
            onFocus={() => alSenalar?.(parada.recurso_id)}
            onBlur={() => alSenalar?.(null)}
            tabIndex={0}
            role="button"
            aria-label={t('itinerario.paradaAccesible', {
              numero: indice + 1,
              total: paradas.length,
              nombre: formatearNombrePropio(parada.nombre),
            })}
            className={`flex gap-4 rounded-lg border p-4 transition-colors ${
              arrastrando === indice
                ? 'border-primario bg-primario-suave'
                : 'border-contorno-variante bg-superficie-contenedor-minimo'
            } ${recalculando ? 'opacity-60' : 'cursor-grab active:cursor-grabbing'}
              focus-visible:ring-2 focus-visible:ring-primario focus-visible:outline-none`}
          >
            {/* El número de parada. Es lo que enlaza esta lista con el mapa. */}
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primario font-titulo text-sm font-bold text-sobre-primario"
              aria-hidden="true"
            >
              {indice + 1}
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-titulo font-semibold text-sobre-superficie">
                  <Link
                    to={`/recursos/${parada.recurso_id}`}
                    className="hover:text-primario"
                    // Sin esto, arrastrar la parada arrastraría el enlace.
                    draggable={false}
                  >
                    {formatearNombrePropio(parada.nombre)}
                  </Link>
                </h3>

                <span className="shrink-0 font-mono text-sm text-sobre-superficie-variante">
                  {parada.hora_llegada.slice(0, 5)} – {parada.hora_salida.slice(0, 5)}
                </span>
              </div>

              <p className="mt-1 text-sm text-sobre-superficie-variante">
                {formatearNombrePropio(parada.distrito)}
                {parada.altitud_msnm !== null && ` · ${parada.altitud_msnm} m s. n. m.`}
                {` · ${formatearDuracion(parada.duracion_visita_min)}`}
              </p>
            </div>

            <span
              className="hidden shrink-0 self-center text-sobre-superficie-variante sm:block"
              aria-hidden="true"
              title={t('itinerario.arrastrar')}
            >
              ⠿
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}
