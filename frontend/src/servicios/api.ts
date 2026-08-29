/**
 * Cliente de la API de RutaVivaMantaro.
 *
 * Centralizar aquí todas las llamadas evita repetir la dirección del servidor
 * y el manejo de errores en cada componente.
 */

/** Dirección del backend. Viene del .env; en desarrollo es localhost:8000. */
export const URL_API = import.meta.env.VITE_URL_API ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Estado de la plataforma
// ---------------------------------------------------------------------------

/** Estado de uno de los componentes que reporta GET /api/salud. */
export interface SaludComponente {
  estado: 'operativo' | 'no_disponible';
  detalle: string;
}

/** Respuesta completa de GET /api/salud. */
export interface SaludGeneral {
  aplicacion: string;
  version: string;
  entorno: string;
  estado_general: 'operativo' | 'degradado';
  api: SaludComponente;
  base_datos: SaludComponente;
  ollama: SaludComponente;
}

// ---------------------------------------------------------------------------
// Catálogo de recursos turísticos
// ---------------------------------------------------------------------------

/** Un recurso turístico, en su versión reducida para el listado. */
export interface RecursoResumen {
  id: number;
  codigo_mincetur: string;
  nombre: string;
  provincia: string;
  distrito: string;
  categoria: string | null;
  tipo: string | null;
  latitud: number | null;
  longitud: number | null;
  esta_validado: boolean;
  esta_vigente: boolean;
  fecha_corte: string | null;
  foto_url: string | null;
}

/** Un recurso turístico con todos sus datos. */
export interface RecursoDetalle extends RecursoResumen {
  subtipo: string | null;
  url_ficha: string | null;
  altitud_msnm: number | null;
  descripcion_es: string | null;
  descripcion_en: string | null;
  duracion_visita_min: number | null;
  motivos_invalidez: string | null;
}

/** Una página del listado de recursos. */
export interface PaginaDeRecursos {
  total: number;
  pagina: number;
  tamano_pagina: number;
  elementos: RecursoResumen[];
}

/** Valores disponibles para poblar los desplegables de filtro. */
export interface ResumenFiltros {
  provincias: string[];
  distritos: string[];
  categorias: string[];
}

/** Un recurso expresado como rasgo de GeoJSON, para el mapa. */
export interface RasgoRecurso {
  type: 'Feature';
  geometry: {
    type: 'Point';
    /** GeoJSON exige el orden [longitud, latitud], al revés de como se habla. */
    coordinates: [number, number];
  };
  properties: {
    id: number;
    nombre: string;
    provincia: string;
    distrito: string;
    categoria: string | null;
    esta_validado: boolean;
  };
}

/** Colección de recursos para el mapa. */
export interface ColeccionGeoJSON {
  type: 'FeatureCollection';
  features: RasgoRecurso[];
}

/** Indicador del Incremento 1. */
export interface IndicadorCatalogo {
  fecha: string;
  total_recursos: number;
  validados: number;
  vigentes: number;
  con_coordenadas: number;
  porcentaje_validado: number;
  porcentaje_vigente: number;
  porcentaje_con_coordenadas: number;
}

/** Filtros que acepta el listado del catálogo. */
export interface FiltrosCatalogo {
  provincia?: string;
  distrito?: string;
  categoria?: string;
  texto?: string;
  solo_validados?: boolean;
  pagina?: number;
  tamano_pagina?: number;
}

// ---------------------------------------------------------------------------
// Funciones de acceso
// ---------------------------------------------------------------------------

/**
 * Realiza una petición GET a la API y devuelve el JSON ya tipado.
 *
 * fetch no lanza error cuando el servidor responde 404 o 500: solo falla si
 * la red se cae. Por eso hay que comprobar respuesta.ok a mano.
 */
async function obtener<T>(ruta: string, parametros?: object): Promise<T> {
  const consulta = new URLSearchParams();

  // Object.entries acepta cualquier objeto. Se usa "object" y no
  // Record<string, unknown> porque TypeScript no considera que una interfaz
  // declarada (como FiltrosCatalogo) sea asignable a ese Record: las
  // interfaces no llevan índice implícito, a diferencia de los alias de tipo.
  for (const [clave, valor] of Object.entries(parametros ?? {})) {
    // Se omiten los filtros vacíos para no mandar ?provincia= a la API.
    if (valor !== undefined && valor !== null && valor !== '' && valor !== false) {
      consulta.set(clave, String(valor));
    }
  }

  const cadena = consulta.toString();
  const respuesta = await fetch(`${URL_API}${ruta}${cadena ? `?${cadena}` : ''}`);

  if (!respuesta.ok) {
    throw new Error(`La API respondió ${respuesta.status} en ${ruta}`);
  }

  return (await respuesta.json()) as T;
}

/** Consulta el estado de la API, la base de datos y Ollama. */
export function consultarSalud(): Promise<SaludGeneral> {
  return obtener<SaludGeneral>('/api/salud');
}

/** Lista los recursos del catálogo aplicando los filtros indicados. */
export function listarRecursos(filtros: FiltrosCatalogo = {}): Promise<PaginaDeRecursos> {
  return obtener<PaginaDeRecursos>('/api/recursos', filtros);
}

/** Devuelve los valores disponibles para los desplegables de filtro. */
export function obtenerFiltros(): Promise<ResumenFiltros> {
  return obtener<ResumenFiltros>('/api/recursos/filtros');
}

/** Devuelve los recursos con coordenadas, en GeoJSON, para pintar el mapa. */
export function obtenerRecursosDelMapa(
  filtros: Omit<FiltrosCatalogo, 'pagina' | 'tamano_pagina' | 'solo_validados'> = {},
): Promise<ColeccionGeoJSON> {
  return obtener<ColeccionGeoJSON>('/api/recursos/mapa', filtros);
}

/** Devuelve todos los datos de un recurso. */
export function obtenerRecurso(id: number): Promise<RecursoDetalle> {
  return obtener<RecursoDetalle>(`/api/recursos/${id}`);
}

/** Devuelve el indicador del Incremento 1. */
export function obtenerIndicadorCatalogo(): Promise<IndicadorCatalogo> {
  return obtener<IndicadorCatalogo>('/api/indicadores/catalogo');
}
