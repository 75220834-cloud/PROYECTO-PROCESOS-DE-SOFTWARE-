/**
 * Mapa de los recursos turísticos del Valle del Mantaro.
 *
 * Usa Leaflet con teselas de OpenStreetMap. Los marcadores se agrupan: con
 * 234 recursos, dibujarlos sueltos convierte Huancayo en una mancha ilegible.
 * Al acercar el zoom, los grupos se abren solos.
 *
 * Los recursos SIN coordenada no aparecen aquí. No se les inventa una
 * ubicación aproximada: el backend ya los excluye del GeoJSON y la lista de
 * al lado los muestra con su aviso.
 */
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import GrupoDeMarcadores from 'react-leaflet-cluster';
import { Link } from 'react-router-dom';

import type { RasgoRecurso } from '@/servicios/api';

/** Encuadre de partida, mientras no han llegado los datos. En cuanto llegan,
 *  el mapa se ajusta solo a los marcadores (ver AjustarAlContenedor). */
const CENTRO_DEL_VALLE: [number, number] = [-11.98, -75.3];
const ZOOM_INICIAL = 10;

/**
 * Icono del marcador, dibujado en SVG.
 *
 * Leaflet trae iconos en PNG cuyas rutas se rompen al empaquetar con Vite: es
 * un problema conocido que produce marcadores invisibles. Dibujarlos aquí en
 * SVG lo evita del todo, y además permite darles el color de la marca:
 * terracota para los validados, ocre para los que no pasaron la validación.
 */
function crearIcono(estaValidado: boolean): L.DivIcon {
  const color = estaValidado ? '#a23919' : '#936f00';

  return L.divIcon({
    className: '', // sin clase: Leaflet añadiría un fondo blanco por omisión
    html: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="26" height="34"
           style="filter: drop-shadow(0 2px 3px rgba(0,0,0,.35))">
        <path fill="${color}" stroke="#fff" stroke-width="1.5"
              d="M12 1C6.5 1 2 5.5 2 11c0 7.5 10 20 10 20s10-12.5 10-20c0-5.5-4.5-10-10-10z"/>
        <circle cx="12" cy="11" r="3.6" fill="#fff"/>
      </svg>`,
    iconSize: [26, 34],
    // El ancla va en la punta inferior del alfiler, no en su centro: si no,
    // el marcador señalaría un punto desplazado hacia arriba.
    iconAnchor: [13, 34],
    popupAnchor: [0, -30],
  });
}

const ICONO_VALIDADO = crearIcono(true);
const ICONO_NO_VALIDADO = crearIcono(false);

/**
 * Hace que el mapa se mida bien y encuadre los marcadores que muestra.
 *
 * Va como componente hijo y no como código suelto porque el gancho useMap de
 * react-leaflet solo entrega la instancia del mapa a los descendientes de
 * MapContainer.
 */
function AjustarAlContenedor({ posiciones }: { posiciones: [number, number][] }) {
  const mapa = useMap();

  useEffect(() => {
    /**
     * El ORDEN de estas dos operaciones importa, y equivocarlo cuesta caro:
     *
     * 1. invalidateSize() obliga a Leaflet a volver a medir su contenedor.
     *    Leaflet lo mide una sola vez, al crearse, y en ese instante el
     *    contenedor todavía no tiene su tamaño definitivo. Sin esto, el mapa
     *    cree medir unos pocos píxeles y solo dibuja una franja de teselas.
     *
     * 2. fitBounds() encuadra los marcadores. Calcula el zoom a partir del
     *    tamaño que Leaflet CREE tener, así que si se llama antes del paso 1
     *    encuadra contra una medida falsa y acaba en un zoom absurdo.
     */
    function ajustar() {
      mapa.invalidateSize();

      if (posiciones.length === 0) return;

      mapa.fitBounds(L.latLngBounds(posiciones), {
        padding: [40, 40],
        // Tope de acercamiento: con un solo recurso, fitBounds llegaría al
        // zoom máximo y se vería el tejado del edificio sin contexto alguno.
        maxZoom: 14,
        animate: false,
      });
    }

    // Se usa setTimeout y NO requestAnimationFrame. rAF solo se dispara
    // cuando el navegador pinta, y una pestaña en segundo plano no pinta: el
    // mapa se quedaría sin encuadrar hasta que el visitante la mirase.
    // setTimeout sí se ejecuta igualmente. El retardo cero basta: solo hace
    // falta ceder el turno para que el diseño de la página se aplique.
    const temporizador = setTimeout(ajustar, 0);

    // Si el contenedor cambia de tamaño después (al girar el móvil, al abrir
    // el menú lateral), se vuelve a ajustar.
    const observador = new ResizeObserver(() => mapa.invalidateSize());
    observador.observe(mapa.getContainer());

    return () => {
      clearTimeout(temporizador);
      observador.disconnect();
    };
  }, [mapa, posiciones]);

  return null;
}

export function MapaRecursos({ rasgos }: { rasgos: RasgoRecurso[] }) {
  const { t } = useTranslation();

  // Se calcula una sola vez por cambio de datos: convertir 234 rasgos en cada
  // redibujado sería trabajo desperdiciado.
  const marcadores = useMemo(
    () =>
      rasgos.map((rasgo) => {
        // GeoJSON guarda [longitud, latitud]; Leaflet espera [latitud, longitud].
        const [longitud, latitud] = rasgo.geometry.coordinates;
        return { rasgo, posicion: [latitud, longitud] as [number, number] };
      }),
    [rasgos],
  );

  // Se memoriza aparte: si se calculara en línea al pasarlo al hijo, sería un
  // arreglo nuevo en cada renderizado y el encuadre automático se dispararía
  // sin parar, en bucle.
  const posiciones = useMemo(() => marcadores.map((marcador) => marcador.posicion), [marcadores]);

  return (
    <MapContainer
      center={CENTRO_DEL_VALLE}
      zoom={ZOOM_INICIAL}
      scrollWheelZoom
      className="h-full w-full rounded-lg"
      // El mapa es decorativo para quien navega con teclado: la misma
      // información está en la lista de al lado, que sí es accesible.
      aria-label={t('catalogo.mapa_etiqueta')}
    >
      <AjustarAlContenedor posiciones={posiciones} />

      <TileLayer
        attribution='&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <GrupoDeMarcadores chunkedLoading maxClusterRadius={45}>
        {marcadores.map(({ rasgo, posicion }) => (
          <Marker
            key={rasgo.properties.id}
            position={posicion}
            icon={rasgo.properties.esta_validado ? ICONO_VALIDADO : ICONO_NO_VALIDADO}
          >
            <Popup>
              <p className="font-titulo text-sm font-semibold">{rasgo.properties.nombre}</p>
              <p className="mt-0.5 text-xs">
                {rasgo.properties.distrito} · {rasgo.properties.provincia}
              </p>
              {rasgo.properties.categoria && (
                <p className="mt-0.5 text-xs opacity-70">{rasgo.properties.categoria}</p>
              )}
              <Link
                to={`/recursos/${rasgo.properties.id}`}
                className="mt-2 inline-block text-xs font-semibold underline"
              >
                {t('catalogo.ver_detalle')}
              </Link>
            </Popup>
          </Marker>
        ))}
      </GrupoDeMarcadores>
    </MapContainer>
  );
}
