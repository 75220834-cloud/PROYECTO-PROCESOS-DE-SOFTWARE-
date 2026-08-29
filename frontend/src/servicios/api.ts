/**
 * Cliente de la API de RutaVivaMantaro.
 *
 * Centralizar aqui todas las llamadas evita repetir la direccion del servidor
 * y el manejo de errores en cada componente.
 */

/** Direccion del backend. Viene del .env; en desarrollo es localhost:8000. */
export const URL_API = import.meta.env.VITE_URL_API ?? 'http://localhost:8000';

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

/**
 * Realiza una peticion GET a la API y devuelve el JSON ya tipado.
 *
 * fetch no lanza error cuando el servidor responde 404 o 500: solo falla si
 * la red se cae. Por eso hay que comprobar respuesta.ok a mano.
 */
async function obtener<T>(ruta: string): Promise<T> {
  const respuesta = await fetch(`${URL_API}${ruta}`);

  if (!respuesta.ok) {
    throw new Error(`La API respondio ${respuesta.status} en ${ruta}`);
  }

  return (await respuesta.json()) as T;
}

/** Consulta el estado de la API, la base de datos y Ollama. */
export function consultarSalud(): Promise<SaludGeneral> {
  return obtener<SaludGeneral>('/api/salud');
}
