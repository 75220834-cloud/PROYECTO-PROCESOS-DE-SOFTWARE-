/**
 * Convierte los avisos del backend en frases, en el idioma del visitante.
 *
 * El backend manda `{codigo, parametros}` en vez de una frase. El razonamiento
 * está en `backend/app/servicios/avisos.py`; aquí está la otra mitad: cómo se
 * redacta.
 *
 * ## El detalle de `count`
 *
 * i18next elige entre la forma `_one` y la `_other` mirando **un parámetro
 * llamado exactamente `count`**. El backend, sin embargo, nombra sus
 * parámetros por lo que significan: `cuantas`, `cuantos`, `validados`,
 * `libres`. Son mejores nombres —`count` no dice de qué— y no se quieren
 * perder.
 *
 * La conversión se hace aquí: el primer parámetro numérico del aviso se copia
 * además como `count`. Así el backend nombra bien y i18next recibe lo que
 * espera, sin que ninguno de los dos tenga que ceder.
 */
import type { TFunction } from 'i18next';

/** Un aviso tal como llega del backend. */
export interface AvisoDelBackend {
  codigo: string;
  parametros: Record<string, unknown>;
}

/**
 * Los parámetros que NO deben tomarse como el número del plural.
 *
 * `total`, `cupo`, `minimo` y compañía son numéricos pero son referencias, no
 * la cantidad de la que habla la frase: en «3 de los 5 recursos valorados
 * tienen…», lo que decide singular o plural es el 3, no el 5.
 *
 * Sin esta lista, «1 de 5 recursos» tomaría el 5 y saldría en plural una frase
 * que habla de uno solo.
 */
const NO_SON_LA_CANTIDAD = new Set([
  'total',
  'cupo',
  'minimo',
  'pedidas',
  'dia',
  'metros',
  'subida',
]);

/**
 * Redacta un aviso.
 *
 * Si el código no tiene traducción, i18next devolvería la clave cruda
 * —«avisos.lo_que_sea»—, que en pantalla se ve como un error. Se prefiere
 * devolver el código a secas: sigue siendo feo, pero no finge ser una frase.
 * La prueba `test_todos_los_codigos_estan_traducidos` hace que esto no llegue
 * a pasar.
 */
export function redactarAviso(t: TFunction, aviso: AvisoDelBackend): string {
  const parametros: Record<string, unknown> = { ...aviso.parametros };

  // El primer numérico que sí es una cantidad se copia como `count`.
  for (const [clave, valor] of Object.entries(aviso.parametros)) {
    if (typeof valor === 'number' && !NO_SON_LA_CANTIDAD.has(clave)) {
      parametros.count = valor;
      break;
    }
  }

  const clave = `avisos.${aviso.codigo}`;
  const frase = t(clave, { ...parametros, defaultValue: '' });

  return frase === '' ? aviso.codigo : frase;
}

/** Redacta una lista entera. Es lo que necesitan casi todas las pantallas. */
export function redactarAvisos(t: TFunction, avisos: AvisoDelBackend[]): string[] {
  return avisos.map((aviso) => redactarAviso(t, aviso));
}

/**
 * Redacta el error de una petición.
 *
 * Un error puede venir de tres sitios distintos, y los tres acaban aquí:
 *
 * 1. **Del backend, como código** — «credenciales_incorrectas». Se traduce.
 * 2. **Del backend, como varios motivos** — el 409 al pedir un servicio no
 *    disponible devuelve todos los motivos, no el primero. Se redactan y se
 *    juntan.
 * 3. **De Pydantic** — «El campo X es obligatorio». Ya viene redactado por la
 *    biblioteca y no hay clave que buscar, así que se devuelve tal cual.
 *
 * El tercer caso es la razón de que esto no sea un simple `t()`: buscar una
 * traducción que no existe devolvería la clave cruda y perdería un mensaje que
 * sí era útil.
 */
export function traducirError(t: TFunction, error: unknown, respaldo: string): string {
  if (!(error instanceof Error)) {
    return respaldo;
  }

  const conMotivos = error as Error & { motivos?: AvisoDelBackend[] };

  if (conMotivos.motivos !== undefined && conMotivos.motivos.length > 0) {
    return redactarAvisos(t, conMotivos.motivos).join(' ');
  }

  const traducido = t(`avisos.${error.message}`, { defaultValue: '' });

  // Si no hay traducción, el mensaje no era un código nuestro: viene de
  // Pydantic y ya está redactado.
  return traducido === '' ? error.message || respaldo : traducido;
}
