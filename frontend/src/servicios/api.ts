/**
 * Cliente de la API de RutaVivaMantaro.
 *
 * Centralizar aquí todas las llamadas evita repetir la dirección del servidor
 * y el manejo de errores en cada componente.
 */

/** Dirección del backend. Viene del .env; en desarrollo es localhost:8000. */
import type { AvisoDelBackend } from '@/utilidades/avisos';

export type { AvisoDelBackend };

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

// ---------------------------------------------------------------------------
// Autenticación y preferencias de viaje (Incremento 2)
// ---------------------------------------------------------------------------

/** Datos públicos de un usuario. Nunca incluye el hash de la contraseña. */
export interface UsuarioPublico {
  id: number;
  correo: string;
  nombre: string;
  rol: 'visitante' | 'operador' | 'proveedor' | 'gestor' | 'administrador';
  idioma_preferido: string;
  creado_en: string;
}

/** Lo que devuelven el registro y el inicio de sesión. */
export interface RespuestaSesion {
  token_de_acceso: string;
  tipo_de_token: string;
  expira_en_minutos: number;
  usuario: UsuarioPublico;
}

/** Lo que el visitante responde en el asistente de seis pasos. */
export interface DatosPreferencia {
  fecha_inicio: string;
  fecha_fin: string;
  distrito_origen: string;
  presupuesto_soles: string;
  intereses: string[];
  movilidad: 'caminando' | 'transporte_publico' | 'taxi' | 'combinado';
  requiere_accesibilidad: boolean;
  ritmo: 'relajado' | 'moderado' | 'intenso';
  idioma: string;
}

/** Una preferencia ya guardada. */
export interface PreferenciaPublica extends DatosPreferencia {
  id: number;
  usuario_id: number | null;
  duracion_dias: number;
  creado_en: string;
}

/** Valores para dibujar cada paso del asistente. */
export interface OpcionesDelAsistente {
  intereses: string[];
  movilidades: string[];
  ritmos: string[];
  distritos: string[];
}

/**
 * Error de la API que conserva el código de estado.
 *
 * Sin esto, el frontend no puede distinguir «ese correo ya existe» (409) de
 * «los datos no son válidos» (422) ni mostrar el mensaje adecuado.
 */
export class ErrorDeApi extends Error {
  // Se declara el campo aparte en vez de usar la forma abreviada del
  // constructor: esa sintaxis genera codigo en tiempo de ejecucion y el
  // proyecto compila con erasableSyntaxOnly, que solo admite sintaxis de
  // tipos que se pueda borrar sin dejar rastro.
  readonly estado: number;

  /**
   * Los motivos, cuando el error trae varios.
   *
   * Solo lo llena el 409 al pedir un servicio no disponible, que devuelve
   * TODOS los motivos y no el primero: decirle a alguien «no hay sitio» y,
   * cuando lo arregla, «además llegas tarde», hace abandonar un formulario.
   *
   * Van sin redactar, como el resto de avisos. `traducirError` los junta.
   */
  readonly motivos: AvisoDelBackend[];

  constructor(estado: number, mensaje: string, motivos: AvisoDelBackend[] = []) {
    super(mensaje);
    this.name = 'ErrorDeApi';
    this.estado = estado;
    this.motivos = motivos;
  }
}

/**
 * Los motivos de un error, si los trae.
 *
 * Se saca aparte de `mensajeDeError` porque esa función devuelve un texto y
 * estos son datos: aplanarlos ahí obligaría a volver a partirlos después.
 */
function motivosDeError(cuerpo: unknown): AvisoDelBackend[] {
  if (typeof cuerpo !== 'object' || cuerpo === null || !('detail' in cuerpo)) return [];

  const detalle = (cuerpo as { detail: unknown }).detail;

  if (typeof detalle !== 'object' || detalle === null || Array.isArray(detalle)) return [];

  const motivos = (detalle as { motivos?: unknown }).motivos;

  return Array.isArray(motivos) ? (motivos as AvisoDelBackend[]) : [];
}

/** Extrae un mensaje legible del cuerpo de error que devuelve FastAPI. */
function mensajeDeError(cuerpo: unknown, estado: number): string {
  if (typeof cuerpo === 'object' && cuerpo !== null && 'detail' in cuerpo) {
    const detalle = (cuerpo as { detail: unknown }).detail;

    if (typeof detalle === 'string') return detalle;

    // Los errores de validación de Pydantic vienen como lista de objetos.
    if (Array.isArray(detalle) && detalle.length > 0) {
      const primero = detalle[0] as { msg?: string };
      if (primero.msg) return primero.msg.replace(/^Value error,\s*/, '');
    }

    // Cuando un servicio no está disponible, la API devuelve el motivo (o los
    // motivos) dentro de un objeto. Sin este caso se perdían y el visitante
    // veía «La API respondió 409», que no le dice cómo arreglarlo.
    // Los errores propios viajan como { codigo }, no como frase: se devuelve
    // el código y la interfaz lo redacta con traducirError.
    if (typeof detalle === 'object' && detalle !== null) {
      const conCodigo = detalle as { codigo?: unknown };

      if (typeof conCodigo.codigo === 'string') return conCodigo.codigo;
    }
  }

  return `La API respondió ${estado}`;
}

/** Envía datos a la API con el método indicado. */
async function enviar<T>(
  ruta: string,
  metodo: 'POST' | 'PUT',
  cuerpo?: unknown,
  token?: string | null,
): Promise<T> {
  const respuesta = await fetch(`${URL_API}${ruta}`, {
    method: metodo,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });

  const datos = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    throw new ErrorDeApi(
      respuesta.status,
      mensajeDeError(datos, respuesta.status),
      motivosDeError(datos),
    );
  }

  return datos as T;
}

/** Realiza un GET autenticado. */
async function obtenerConToken<T>(ruta: string, token: string | null): Promise<T> {
  const respuesta = await fetch(`${URL_API}${ruta}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  const datos = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    throw new ErrorDeApi(
      respuesta.status,
      mensajeDeError(datos, respuesta.status),
      motivosDeError(datos),
    );
  }

  return datos as T;
}

/** Crea una cuenta y abre la sesión. */
export function registrarse(
  correo: string,
  contrasena: string,
  nombre: string,
): Promise<RespuestaSesion> {
  return enviar<RespuestaSesion>('/api/autenticacion/registro', 'POST', {
    correo,
    contrasena,
    nombre,
  });
}

/** Inicia sesión con unas credenciales. */
export function iniciarSesion(correo: string, contrasena: string): Promise<RespuestaSesion> {
  return enviar<RespuestaSesion>('/api/autenticacion/sesion', 'POST', { correo, contrasena });
}

/** Comprueba si el token guardado sigue siendo válido. */
export function consultarSesionActual(token: string): Promise<UsuarioPublico> {
  return obtenerConToken<UsuarioPublico>('/api/autenticacion/yo', token);
}

/** Devuelve los valores para dibujar el asistente de preferencias. */
export function obtenerOpcionesDelAsistente(): Promise<OpcionesDelAsistente> {
  return obtener<OpcionesDelAsistente>('/api/preferencias/opciones');
}

/** Guarda una preferencia. Funciona con y sin sesión iniciada. */
export function guardarPreferencia(
  datos: DatosPreferencia,
  token: string | null,
): Promise<PreferenciaPublica> {
  return enviar<PreferenciaPublica>('/api/preferencias', 'POST', datos, token);
}

/** Consulta una preferencia por su identificador. */
export function obtenerPreferencia(id: number, token: string | null): Promise<PreferenciaPublica> {
  return obtenerConToken<PreferenciaPublica>(`/api/preferencias/${id}`, token);
}

/** Devuelve las preferencias guardadas del usuario, para «Mis viajes». */
export function listarMisPreferencias(
  token: string,
): Promise<{ total: number; elementos: PreferenciaPublica[] }> {
  return obtenerConToken('/api/preferencias', token);
}

/** Asocia a la cuenta una preferencia creada sin ella. */
export function reclamarPreferencia(id: number, token: string): Promise<PreferenciaPublica> {
  return enviar<PreferenciaPublica>(`/api/preferencias/${id}/reclamar`, 'POST', undefined, token);
}

// ---------------------------------------------------------------------------
// Recomendación inteligente (Incremento 3)
// ---------------------------------------------------------------------------

/** Cuánta gente se espera en un sitio, y por qué. */
export interface AfluenciaEstimada {
  nivel: 'bajo' | 'medio' | 'alto';
  /** Por qué, como código y parámetros: se redacta con `redactarAviso`. */
  motivo: AvisoDelBackend;
  festividades: string[];
  calculado_por: 'modelo' | 'reglas';
}

/** Un recurso recomendado, con la explicación de por qué lo fue. */
export interface RecomendacionPublica {
  recurso_id: number;
  nombre: string;
  provincia: string;
  distrito: string;
  categoria: string | null;
  latitud: number | null;
  longitud: number | null;
  distancia_km: number | null;
  /** Similitud coseno en bruto. No se muestra: no significa nada por sí sola. */
  puntaje_afinidad: number;
  /** De 0 a 100, relativo al mejor resultado de esta misma búsqueda. */
  puntaje_relativo: number;
  terminos_decisivos: string[];
  intereses_cubiertos: string[];
  afluencia: AfluenciaEstimada;
  generado_por: 'modelo' | 'reglas';

  /**
   * Lo que dice la ficha oficial del MINCETUR sobre cuándo se celebra, literal.
   *
   * 36 de los 295 recursos del catálogo son fiestas, y una fiesta no está ahí
   * todo el año. No es una fecha deducida: muchas son móviles —«el último
   * domingo de enero»— y darles un día exacto sería inventarlo.
   */
  dias_de_celebracion: string | null;

  meses_de_celebracion: number[];

  /**
   * `true` si cae dentro del viaje, `false` si no, y **`null` cuando no
   * aplica**: no es una fiesta, o su ficha no precisa la fecha. Solo se avisa
   * en rojo cuando es `false`; avisar de lo que no sabemos sería mentir.
   */
  esta_en_temporada: boolean | null;

  /** «Libre», «Previa presentación de boleto»… de la ficha oficial. */
  tipo_de_ingreso: string | null;
}

/** Un recurso que no pasó los filtros duros, con su motivo. */
export interface RecursoDescartado {
  recurso_id: number;
  nombre: string;
  /** Por qué quedó fuera, como código y parámetros. */
  motivo: AvisoDelBackend;
}

/** Respuesta completa de la recomendación. */
export interface RespuestaRecomendacion {
  preferencia_id: number;
  fecha_de_referencia: string;
  generado_por: 'modelo' | 'reglas';
  total_evaluados: number;
  total_recomendados: number;
  total_descartados: number;
  recomendaciones: RecomendacionPublica[];
  descartados: RecursoDescartado[];
  avisos: AvisoDelBackend[];
}

/** Una festividad del calendario del valle. */
export interface FestividadPublica {
  nombre: string;
  fecha_inicio: string;
  fecha_fin: string;
  tipo: string;
  distritos: string[];
  es_movil: boolean;
  fuente: string;
}

/** Pide recomendaciones para una preferencia ya guardada. */
export function obtenerRecomendaciones(
  preferenciaId: number,
  token: string | null,
  limite = 20,
): Promise<RespuestaRecomendacion> {
  return enviar<RespuestaRecomendacion>(
    '/api/recomendaciones',
    'POST',
    { preferencia_id: preferenciaId, limite },
    token,
  );
}

/** Devuelve las festividades del valle en un año. */
export function obtenerCalendario(
  anio: number,
): Promise<{ anio: number; total: number; festividades: FestividadPublica[] }> {
  return obtener(`/api/calendario/${anio}`);
}

// ---------------------------------------------------------------------------
// Itinerario geoespacial (Incremento 4)
// ---------------------------------------------------------------------------

/** Cómo se cubre un traslado entre dos paradas. */
export type ModoTransporte = 'caminando' | 'combi' | 'colectivo' | 'taxi';

/**
 * Cómo se calculó la distancia de un tramo.
 *
 * `red_vial` significa que se recorrió el grafo real de OpenStreetMap.
 * `linea_recta` significa que no había red registrada cerca y la distancia es
 * una estimación. La interfaz **tiene que distinguirlos**: el 26,1 % de los
 * recursos del valle está fuera de la cobertura de OSM, y en esos casos el
 * tiempo real puede ser bastante mayor que el mostrado.
 */
export type OrigenDelCalculo = 'red_vial' | 'linea_recta';

/** El desplazamiento desde la parada anterior hasta esta. */
export interface TrasladoPublico {
  modo: ModoTransporte;
  minutos: number;
  distancia_km: number;
  desnivel_m: number;
  /** Rango, nunca un precio único: en el valle no hay tarifa oficial. */
  precio_min_soles: string;
  precio_max_soles: string;
  /** `true` cuando el precio salió de una fórmula y no de una tarifa consultada. */
  es_estimado: boolean;
  fuente: string;
  fecha_referencia: string;
  origen_del_calculo: OrigenDelCalculo;
  /** Coordenadas `[lat, lon]` del camino, para dibujarlo. Vacío si se estimó. */
  trazado: [number, number][];
}

/** Una parada del itinerario, con su horario y cómo se llega a ella. */
export interface ParadaItinerario {
  orden: number;
  recurso_id: number;
  nombre: string;
  distrito: string;
  categoria: string | null;
  latitud: number;
  longitud: number;
  altitud_msnm: number | null;
  hora_llegada: string;
  hora_salida: string;
  duracion_visita_min: number;
  puntaje_relativo: number;
  /** `null` en la primera parada: no se llega a ella desde ningún sitio. */
  traslado: TrasladoPublico | null;
}

/** El itinerario de un día, con sus totales y sus avisos. */
export interface RespuestaItinerario {
  itinerario_id: number | null;
  preferencia_id: number;
  fecha: string;
  titulo: string;
  /** `modelo` (OR-Tools) o `reglas` (vecino más cercano). */
  generado_por: 'modelo' | 'reglas';
  paradas: ParadaItinerario[];
  tiempo_total_min: number;
  costo_min_soles: string;
  costo_max_soles: string;
  distancia_total_km: number;
  subida_total_m: number;
  esfuerzo: 'suave' | 'moderado' | 'exigente';
  hay_tramos_estimados: boolean;
  avisos: AvisoDelBackend[];
}

/** Un itinerario guardado, tal como aparece en el listado. */
export interface ItinerarioGuardado {
  id: number;
  titulo: string;
  fecha: string;
  estado: string;
  generado_por: 'modelo' | 'reglas';
  total_paradas: number;
  tiempo_total_min: number;
  costo_total_soles: string;
  distancia_total_km: number;
  desnivel_total_m: number;
}

/** Opciones para armar un itinerario. */
export interface OpcionesItinerario {
  fecha?: string;
  horaInicio?: string;
  horaFin?: string;
  guardar?: boolean;
  titulo?: string;
}

/** Arma el itinerario de un día para una preferencia ya guardada. */
export function armarItinerario(
  preferenciaId: number,
  token: string | null,
  opciones: OpcionesItinerario = {},
): Promise<RespuestaItinerario> {
  return enviar<RespuestaItinerario>(
    '/api/itinerarios',
    'POST',
    {
      preferencia_id: preferenciaId,
      fecha: opciones.fecha,
      hora_inicio: opciones.horaInicio,
      hora_fin: opciones.horaFin,
      guardar: opciones.guardar ?? false,
      titulo: opciones.titulo,
    },
    token,
  );
}

/**
 * Recalcula el itinerario con el orden que eligió el visitante.
 *
 * No reoptimiza: respeta el orden pedido y recalcula sus consecuencias.
 */
export function reordenarItinerario(
  preferenciaId: number,
  recursosEnOrden: number[],
  token: string | null,
  opciones: OpcionesItinerario = {},
): Promise<RespuestaItinerario> {
  return enviar<RespuestaItinerario>(
    '/api/itinerarios/reordenar',
    'POST',
    {
      preferencia_id: preferenciaId,
      recursos_en_orden: recursosEnOrden,
      fecha: opciones.fecha,
      hora_inicio: opciones.horaInicio,
      hora_fin: opciones.horaFin,
      guardar: opciones.guardar ?? false,
      titulo: opciones.titulo,
    },
    token,
  );
}

/** Lista los itinerarios guardados del usuario que ha iniciado sesión. */
export function obtenerItinerariosGuardados(token: string | null): Promise<ItinerarioGuardado[]> {
  return obtenerConToken<ItinerarioGuardado[]>('/api/itinerarios', token);
}

// ---------------------------------------------------------------------------
// Canal único de coordinación (Incremento 5)
// ---------------------------------------------------------------------------

/** Qué clase de servicio ofrece un proveedor. */
export type TipoServicio =
  'transporte' | 'alimentacion' | 'hospedaje' | 'guiado' | 'taller' | 'artesania';

/** Por dónde va una solicitud de coordinación. */
export type EstadoSolicitud =
  'enviada' | 'en_revision' | 'contrapropuesta' | 'confirmada' | 'rechazada' | 'cancelada';

/** Qué incluye el precio publicado. */
export type UnidadPrecio = 'por_persona' | 'por_grupo' | 'por_noche' | 'por_hora';

/** Quién ofrece el servicio. */
export interface ProveedorPublico {
  id: number;
  nombre: string;
  distrito: string;
  telefono: string | null;
  correo: string | null;
  descripcion: string | null;

  // --- Solo en los reales. Es lo que los hace comprobables ---

  /** El RUC con el que el Estado lo reconoce. Sirve para verificarlo. */
  ruc: string | null;
  direccion: string | null;
  pagina_web: string | null;
  /** «Hostal», «Operador de Turismo»… o las dos si está en dos directorios. */
  clase: string | null;
  /** Su categoría oficial: «2 Estrellas», «Restaurante Un (1) Tenedor». */
  categoria: string | null;
  /** El número de certificado del Estado. Hace «certificado» comprobable. */
  certificado: string | null;
  fuente: string | null;
  fecha_corte: string | null;

  /**
   * `true` cuando el proveedor está inventado para poder enseñar el flujo.
   *
   * La interfaz **tiene que mostrarlo**: nadie debe llamar a un teléfono de
   * demostración creyendo que va a contestar alguien.
   */
  es_demostracion: boolean;
}

/** Un tramo horario en el que el servicio atiende. */
export interface TramoDisponible {
  /** 0 es lunes y 6 es domingo. */
  dia_semana: number;
  hora_inicio: string;
  hora_fin: string;
  cupo: number;
}

/** Un servicio publicado, con lo que hace falta para decidir si sirve. */
export interface ServicioPublico {
  id: number;
  nombre: string;
  tipo: TipoServicio;
  descripcion: string | null;
  proveedor: ProveedorPublico;
  recurso_id: number | null;
  capacidad_maxima: number;
  duracion_min: number | null;
  antelacion_minima_horas: number;
  precio_min_soles: string;
  precio_max_soles: string;
  unidad_precio: UnidadPrecio;
  fecha_referencia: string;
  idiomas: string | null;
  es_accesible: boolean;
  disponibilidad: TramoDisponible[];
}

/** Si el servicio se puede pedir así, y si no, todos los motivos. */
export interface RespuestaDisponibilidad {
  servicio_id: number;
  fecha: string;
  numero_personas: number;
  hay_disponibilidad: boolean;
  /** Todos los motivos por los que no se puede pedir así, como códigos. */
  motivos: AvisoDelBackend[];
  plazas_libres: number | null;
}

/** Un movimiento de la solicitud: es el registro que pide la brecha 6. */
export interface CambioDeEstado {
  estado_anterior: string | null;
  estado_nuevo: string;
  rol_de_quien_cambio: string | null;
  nota: string | null;
  ocurrido_en: string;
}

/** Una solicitud con todo lo acordado y todo lo ocurrido. */
export interface SolicitudPublica {
  id: number;
  servicio_id: number;
  servicio_nombre: string;
  proveedor_nombre: string;
  proveedor_telefono: string | null;
  proveedor_es_demostracion: boolean;
  itinerario_id: number | null;
  fecha_servicio: string;
  hora_servicio: string | null;
  numero_personas: number;
  nombre_contacto: string;
  telefono_contacto: string | null;
  correo_contacto: string | null;
  mensaje: string | null;
  estado: EstadoSolicitud;
  precio_acordado_soles: string | null;
  respuesta_proveedor: string | null;
  precio_min_soles: string;
  precio_max_soles: string;
  creado_en: string;
  actualizado_en: string;
  /** Cuántos movimientos hubo. Es el indicador del Incremento 5. */
  interacciones: number;
  historial: CambioDeEstado[];
}

/** El indicador del Incremento 5, calculado sobre lo registrado. */
export interface ResumenDeCoordinacion {
  total_solicitudes: number;
  confirmadas: number;
  rechazadas: number;
  pendientes: number;
  /** `null` si todavía no hay ninguna confirmada: cero casos no es cero. */
  interacciones_medias_hasta_confirmar: number | null;
  horas_medias_hasta_confirmar: number | null;
  canales_para_confirmar: number;
}

/** Lo que el visitante manda al proveedor. */
export interface SolicitudNueva {
  servicio_id: number;
  fecha_servicio: string;
  hora_servicio?: string | null;
  numero_personas: number;
  nombre_contacto: string;
  telefono_contacto?: string | null;
  correo_contacto?: string | null;
  mensaje?: string | null;
  itinerario_id?: number | null;
}

/** Filtros del catálogo de servicios. */
export interface FiltrosDeServicios {
  tipo?: TipoServicio;
  distrito?: string;
  recursoId?: number;
}

/** Devuelve los servicios publicados por los proveedores. */
export function obtenerServicios(filtros: FiltrosDeServicios = {}): Promise<ServicioPublico[]> {
  return obtener<ServicioPublico[]>('/api/servicios', {
    tipo: filtros.tipo,
    distrito: filtros.distrito,
    recurso_id: filtros.recursoId,
  });
}

/** Ficha de un servicio concreto. */
export function obtenerServicio(servicioId: number): Promise<ServicioPublico> {
  return obtener<ServicioPublico>(`/api/servicios/${servicioId}`);
}

/** Pregunta si un servicio se puede pedir para esa fecha y esas personas. */
export function comprobarDisponibilidad(
  servicioId: number,
  fecha: string,
  numeroPersonas: number,
  hora?: string | null,
): Promise<RespuestaDisponibilidad> {
  return enviar<RespuestaDisponibilidad>(`/api/servicios/${servicioId}/disponibilidad`, 'POST', {
    fecha,
    numero_personas: numeroPersonas,
    hora: hora ?? null,
  });
}

/** Envía una solicitud a un proveedor. Funciona sin cuenta. */
export function crearSolicitud(
  datos: SolicitudNueva,
  token: string | null,
): Promise<SolicitudPublica> {
  return enviar<SolicitudPublica>('/api/solicitudes', 'POST', datos, token);
}

/** Las solicitudes que el usuario actual puede ver, según su rol. */
export function obtenerSolicitudes(
  token: string | null,
  estado?: EstadoSolicitud,
): Promise<SolicitudPublica[]> {
  const consulta = estado ? `?estado=${estado}` : '';
  return obtenerConToken<SolicitudPublica[]>(`/api/solicitudes${consulta}`, token);
}

/** Una solicitud con su historial. Las anónimas se recuperan por identificador. */
export function obtenerSolicitud(
  solicitudId: number,
  token: string | null,
): Promise<SolicitudPublica> {
  return obtenerConToken<SolicitudPublica>(`/api/solicitudes/${solicitudId}`, token);
}

/** Mueve una solicitud de estado. Las reglas las aplica el backend. */
export function cambiarEstadoDeSolicitud(
  solicitudId: number,
  nuevoEstado: EstadoSolicitud,
  token: string | null,
  opciones: { nota?: string; precioAcordado?: string } = {},
): Promise<SolicitudPublica> {
  return enviar<SolicitudPublica>(
    `/api/solicitudes/${solicitudId}/estado`,
    'POST',
    {
      nuevo_estado: nuevoEstado,
      nota: opciones.nota ?? null,
      precio_acordado_soles: opciones.precioAcordado ?? null,
    },
    token,
  );
}

/** La ficha de proveedor de quien ha iniciado sesión. */
export function obtenerMiProveedor(token: string | null): Promise<ProveedorPublico> {
  return obtenerConToken<ProveedorPublico>('/api/proveedores/mio', token);
}

/** Los servicios del proveedor actual, incluidos los no publicados. */
export function obtenerMisServicios(token: string | null): Promise<ServicioPublico[]> {
  return obtenerConToken<ServicioPublico[]>('/api/proveedores/mio/servicios', token);
}

/** El indicador del Incremento 5. */
export function obtenerIndicadorDeCoordinacion(): Promise<ResumenDeCoordinacion> {
  return obtener<ResumenDeCoordinacion>('/api/indicadores/coordinacion');
}

// ---------------------------------------------------------------------------
// Valoración de cierre y evidencia (Incremento 6)
// ---------------------------------------------------------------------------

/** Cómo se leyó el comentario. */
export type Sentimiento = 'positivo' | 'neutro' | 'negativo';

/** De qué habla un comentario. Conjunto cerrado, para poder agregarlo. */
export type TemaValoracion =
  | 'limpieza'
  | 'atencion'
  | 'precio'
  | 'acceso'
  | 'senalizacion'
  | 'seguridad'
  | 'comida'
  | 'paisaje'
  | 'infraestructura';

/** Una valoración con lo que la persona puso y lo que el sistema entendió. */
export interface ValoracionPublica {
  id: number;
  itinerario_id: number;
  recurso_id: number | null;
  recurso_nombre: string | null;
  servicio_id: number | null;
  servicio_nombre: string | null;
  puntuacion: number;
  comentario: string | null;
  /** `null` si no había comentario: una puntuación sola no tiene sentimiento. */
  sentimiento: Sentimiento | null;
  confianza_sentimiento: number | null;
  temas: string[];
  /** `modelo` o `reglas`. La trazabilidad de la regla de oro de la IA. */
  analizado_por: 'modelo' | 'reglas' | null;
  version_del_analisis: string | null;
  creado_en: string;
}

/** Lo que el visitante manda al cerrar su itinerario. */
export interface ValoracionNueva {
  itinerario_id: number;
  puntuacion: number;
  comentario?: string | null;
  recurso_id?: number | null;
  servicio_id?: number | null;
}

/** Cuántas valoraciones hay de cada signo. */
export interface DistribucionDeSentimiento {
  positivas: number;
  neutras: number;
  negativas: number;
  total: number;
  /** `null` si no hay valoraciones: un porcentaje de cero casos no es cero. */
  porcentaje_positivo: number | null;
}

/** Cuánto se menciona un tema, y con qué signo. */
export interface TemaAgregado {
  tema: string;
  menciones: number;
  positivas: number;
  neutras: number;
  negativas: number;
  /** El número que dice DÓNDE actuar. */
  porcentaje_negativo: number | null;
}

/** Un recurso con su valoración media. */
export interface RecursoValorado {
  recurso_id: number;
  nombre: string;
  distrito: string;
  total_valoraciones: number;
  puntuacion_media: number;
  temas_frecuentes: string[];
  /** `false` si tiene muy pocas valoraciones para que la media signifique algo. */
  es_fiable: boolean;
}

/** La media de un mes, para dibujar la evolución. */
export interface PuntoEnElTiempo {
  periodo: string;
  total: number;
  puntuacion_media: number;
  positivas: number;
  negativas: number;
}

/** Todo lo que el tablero del gestor necesita. */
export interface ResumenDeEvidencia {
  total_itinerarios: number;
  itinerarios_con_valoracion: number;
  porcentaje_con_valoracion: number;
  total_valoraciones: number;
  con_comentario: number;
  puntuacion_media: number | null;
  sentimiento: DistribucionDeSentimiento;
  temas: TemaAgregado[];
  mejor_valorados: RecursoValorado[];
  peor_valorados: RecursoValorado[];
  evolucion: PuntoEnElTiempo[];
  analizadas_por_modelo: number;
  analizadas_por_reglas: number;
  /** Avisos sobre la fiabilidad de lo que se muestra, como códigos. */
  avisos: AvisoDelBackend[];
}

/** Un indicador cualquiera, en la forma en que lo muestra el tablero. */
export interface IndicadorDelIncremento {
  /**
   * Qué incremento mide. **De aquí salen el nombre, la brecha y la
   * salvedad**: son constantes por indicador y viven en los archivos de
   * idioma, bajo `indicadores.{numero}`.
   */
  incremento: number;
  /** Cifra con símbolo. Vacío cuando el valor es una frase traducible. */
  valor: string;
  /** Para los indicadores cuyo valor es una frase y no una cifra. */
  valor_traducible: AvisoDelBackend | null;
  /** El contexto del valor, como código y parámetros. */
  detalle: AvisoDelBackend | null;
  /** `false` cuando todavía no se puede medir. Cero es una medición; esto no. */
  hay_dato: boolean;
  /** Por qué no hay dato todavía, cuando `hay_dato` es falso. */
  sin_dato_porque: AvisoDelBackend | null;
}

/** Los seis indicadores del proyecto en un solo lugar. */
export interface TableroDeIndicadores {
  indicadores: IndicadorDelIncremento[];
  generado_en: string;
}

/** Valora una experiencia. Funciona sin cuenta. */
export function crearValoracion(
  datos: ValoracionNueva,
  token: string | null,
): Promise<ValoracionPublica> {
  return enviar<ValoracionPublica>('/api/valoraciones', 'POST', datos, token);
}

/** Lo que ya se valoró de un itinerario. */
export function obtenerValoraciones(itinerarioId: number): Promise<ValoracionPublica[]> {
  return obtener<ValoracionPublica[]>('/api/valoraciones', {
    itinerario_id: itinerarioId,
  });
}

/** El tablero de evidencia del gestor. */
export function obtenerEvidencia(): Promise<ResumenDeEvidencia> {
  return obtener<ResumenDeEvidencia>('/api/indicadores/evidencia');
}

/** Los seis indicadores del proyecto. */
export function obtenerTableroDeIndicadores(): Promise<TableroDeIndicadores> {
  return obtener<TableroDeIndicadores>('/api/indicadores/tablero');
}

// ---------------------------------------------------------------------------
// Asistente conversacional (Fase 7)
// ---------------------------------------------------------------------------

/**
 * Un turno de la conversación.
 *
 * Los roles van en inglés («user», «assistant») porque son los que entiende
 * Ollama y viajan sin traducir hasta el modelo. Es la excepción de nombres en
 * inglés que ya se aplica a las bibliotecas de terceros.
 */
export interface MensajeDeConversacion {
  rol: 'user' | 'assistant';
  contenido: string;
}

/** Qué función del backend se ejecutó, y con qué. */
export interface FuncionUsada {
  nombre: string;
  argumentos: Record<string, unknown>;
}

/** Lo que contesta el asistente. */
export interface RespuestaDelAsistente {
  mensaje: string;
  funciones_usadas: FuncionUsada[];
  preferencia_id: number | null;
  esta_disponible: boolean;
  aviso: string | null;
}

/** Si el asistente se puede usar, y si no, por qué. */
export interface EstadoDelAsistente {
  disponible: boolean;
  modelo: string;
  motivo: string | null;
}

/**
 * Pregunta si el asistente está disponible.
 *
 * Se consulta antes de enseñar el botón. Un asistente que no responde y no
 * explica por qué es peor que uno que directamente no está: el visitante se
 * queda esperando sin saber que espera en vano.
 */
export function consultarEstadoDelAsistente(): Promise<EstadoDelAsistente> {
  return obtener<EstadoDelAsistente>('/api/asistente/estado');
}

/**
 * Envía la conversación entera y devuelve la respuesta.
 *
 * Se manda completa en cada petición porque el asistente no guarda memoria en
 * el servidor: la conversación es de quien la tiene.
 */
export function enviarMensajeAlAsistente(
  mensajes: MensajeDeConversacion[],
  idioma: string,
): Promise<RespuestaDelAsistente> {
  return enviar<RespuestaDelAsistente>('/api/asistente/mensaje', 'POST', {
    mensajes,
    // El backend solo acepta «es» o «en»; i18next puede dar «es-PE».
    idioma: idioma.startsWith('en') ? 'en' : 'es',
  });
}

/**
 * El directorio de prestadores REALES del valle.
 *
 * Están certificados por el MINCETUR pero **no tienen convenio con este
 * proyecto**, y la interfaz lo dice. No se les inventa capacidad ni horarios:
 * eso no está publicado.
 */
export function listarPrestadores(clase?: string): Promise<ProveedorPublico[]> {
  return obtener<ProveedorPublico[]>('/api/proveedores', { clase });
}
