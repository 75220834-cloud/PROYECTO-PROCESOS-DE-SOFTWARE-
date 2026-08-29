/**
 * Mapa del itinerario: las paradas numeradas y el camino entre ellas.
 *
 * Se diferencia del mapa del catálogo en dos cosas, y las dos son
 * deliberadas:
 *
 * 1. **Los marcadores no se agrupan.** En el catálogo agrupar es necesario
 *    porque hay 234 puntos; aquí hay cinco o seis y lo que importa es ver el
 *    orden. Un grupo que esconde la parada 3 rompe justo lo que se quiere leer.
 *
 * 2. **El camino se dibuja distinto según cómo se calculó.** Línea continua
 *    cuando se recorrió la red vial real; línea discontinua cuando hubo que
 *    estimarla porque OpenStreetMap no conoce esa zona. No es decoración: en
 *    los distritos sin cobertura el tiempo real puede ser muy superior, y el
 *    visitante tiene que poder distinguir un tramo medido de uno supuesto de
 *    un vistazo.
 */
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';

import type { ParadaItinerario } from '@/servicios/api';
import { formatearNombrePropio } from '@/utilidades/formato';

/** Encuadre de partida, hasta que el mapa se ajusta a las paradas. */
const CENTRO_DEL_VALLE: [number, number] = [-11.98, -75.3];
const ZOOM_INICIAL = 10;

/** Colores del sistema de diseño Mantaro Moderno. */
const TERRACOTA = '#a23919';
const VERDE_VALLE = '#27695c';
const OCRE = '#745800';

/**
 * Marcador numerado de una parada.
 *
 * El número va dentro del alfiler porque el orden ES la información: sin él,
 * el mapa solo diría dónde están los sitios, que es lo que ya hacía el
 * catálogo.
 */
function crearIconoDeParada(numero: number, esPrimera: boolean): L.DivIcon {
  const color = esPrimera ? VERDE_VALLE : TERRACOTA;

  return L.divIcon({
    className: '',
    html: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="30" height="40"
           style="filter: drop-shadow(0 2px 4px rgba(0,0,0,.4))">
        <path fill="${color}" stroke="#fff" stroke-width="1.5"
              d="M12 1C6.5 1 2 5.5 2 11c0 7.5 10 20 10 20s10-12.5 10-20c0-5.5-4.5-10-10-10z"/>
        <text x="12" y="15" text-anchor="middle" fill="#fff"
              font-family="Manrope, system-ui, sans-serif" font-size="11" font-weight="700"
        >${numero}</text>
      </svg>`,
    iconSize: [30, 40],
    // El ancla va en la punta del alfiler: si fuera el centro, el marcador
    // señalaría un punto desplazado hacia arriba.
    iconAnchor: [15, 40],
    popupAnchor: [0, -36],
  });
}

/**
 * Encuadra el mapa sobre las paradas y corrige su tamaño.
 *
 * Va como componente hijo porque el gancho `useMap` solo entrega el mapa a los
 * descendientes de `MapContainer`.
 */
function AjustarAlItinerario({ posiciones }: { posiciones: [number, number][] }) {
  const mapa = useMap();

  useEffect(() => {
    // Leaflet mide el contenedor al montarse. Si en ese momento todavía está
    // ocupando cero píxeles —porque la pestaña se está pintando, o el panel
    // acaba de abrirse— el mapa se queda con ese tamaño y aparece como una
    // franja. `invalidateSize` le hace volver a medir.
    //
    // Se usa setTimeout y no requestAnimationFrame porque una pestaña que no
    // está pintando nunca ejecuta el segundo, y el mapa se quedaría roto.
    const temporizador = window.setTimeout(() => {
      mapa.invalidateSize();

      if (posiciones.length === 1) {
        mapa.setView(posiciones[0], 14);
      } else if (posiciones.length > 1) {
        mapa.fitBounds(L.latLngBounds(posiciones), { padding: [40, 40] });
      }
    }, 120);

    return () => window.clearTimeout(temporizador);
  }, [mapa, posiciones]);

  return null;
}

interface Propiedades {
  paradas: ParadaItinerario[];
  /** Parada resaltada, para sincronizar el mapa con la línea de tiempo. */
  paradaActiva?: number | null;
}

export default function MapaItinerario({ paradas, paradaActiva = null }: Propiedades) {
  const { t } = useTranslation();

  const posiciones: [number, number][] = paradas.map((p) => [p.latitud, p.longitud]);

  if (paradas.length === 0) {
    return (
      <div
        className="flex h-full min-h-80 items-center justify-center rounded-lg border
                   border-contorno-variante bg-superficie-contenedor p-8 text-center text-sm
                   text-sobre-superficie-variante"
      >
        {t('itinerario.mapaVacio')}
      </div>
    );
  }

  return (
    <MapContainer
      center={CENTRO_DEL_VALLE}
      zoom={ZOOM_INICIAL}
      scrollWheelZoom
      className="h-full min-h-80 w-full rounded-lg"
      // El mapa se declara como imagen decorativa para lectores de pantalla:
      // toda su información está también en la línea de tiempo de al lado, que
      // sí es texto navegable. Un mapa de Leaflet no es utilizable con teclado.
      aria-hidden="true"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <AjustarAlItinerario posiciones={posiciones} />

      {paradas.map((parada, indice) => {
        const anterior = paradas[indice - 1];
        if (!anterior || !parada.traslado) return null;

        const esEstimado = parada.traslado.origen_del_calculo === 'linea_recta';

        // Si el backend devolvió el camino real, se dibuja nodo a nodo. Si no,
        // se une con una recta entre las dos paradas: es exactamente lo que se
        // calculó, así que dibujar una curva inventada sería mentir.
        const trazado: [number, number][] =
          parada.traslado.trazado.length > 1
            ? parada.traslado.trazado
            : [
                [anterior.latitud, anterior.longitud],
                [parada.latitud, parada.longitud],
              ];

        return (
          <Polyline
            key={`tramo-${parada.recurso_id}`}
            positions={trazado}
            pathOptions={{
              color: esEstimado ? OCRE : TERRACOTA,
              weight: 4,
              opacity: 0.85,
              // Discontinua cuando el tramo es una estimación. Es la misma
              // distinción que hace el aviso escrito, dicha en el mapa.
              dashArray: esEstimado ? '8 8' : undefined,
            }}
          />
        );
      })}

      {paradas.map((parada, indice) => (
        <Marker
          key={parada.recurso_id}
          position={[parada.latitud, parada.longitud]}
          icon={crearIconoDeParada(indice + 1, indice === 0)}
          zIndexOffset={paradaActiva === parada.recurso_id ? 1000 : 0}
          opacity={paradaActiva === null || paradaActiva === parada.recurso_id ? 1 : 0.55}
        >
          <Popup>
            <p className="font-titulo text-sm font-semibold">
              {indice + 1}. {formatearNombrePropio(parada.nombre)}
            </p>
            <p className="mt-1 text-xs">
              {parada.hora_llegada.slice(0, 5)} – {parada.hora_salida.slice(0, 5)}
            </p>
            <p className="text-xs">{formatearNombrePropio(parada.distrito)}</p>
            {parada.altitud_msnm !== null && (
              <p className="text-xs">{parada.altitud_msnm} m s. n. m.</p>
            )}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
