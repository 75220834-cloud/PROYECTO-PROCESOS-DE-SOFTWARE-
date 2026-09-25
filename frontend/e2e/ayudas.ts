/**
 * Piezas compartidas por las pruebas de extremo a extremo.
 *
 * ## Por qué E2E-03 y E2E-04 crean la preferencia por API y no por la interfaz
 *
 * Porque ya lo hace E2E-02, que es la prueba de esa historia. Repetir los seis
 * pasos en cada una añadiría ~15 segundos por prueba y, peor, haría que un
 * fallo del asistente rompiera cuatro pruebas y no una. Cada prueba falla por
 * lo suyo.
 */

import type { APIRequestContext } from '@playwright/test';

export const API = 'http://localhost:8000';

/** Fecha futura en el formato `YYYY-MM-DD`. */
export function dentroDe(dias: number): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + dias);
  return fecha.toISOString().slice(0, 10);
}

/**
 * Crea una preferencia anónima y devuelve su identificador.
 *
 * Sin cabecera de autorización a propósito: si algún día el endpoint empezara
 * a exigir sesión, esta llamada fallaría y lo sabríamos por aquí además de por
 * E2E-02.
 */
export async function crearPreferencia(peticion: APIRequestContext): Promise<number> {
  const respuesta = await peticion.post(`${API}/api/preferencias`, {
    data: {
      fecha_inicio: dentroDe(10),
      fecha_fin: dentroDe(12),
      distrito_origen: 'HUANCAYO',
      presupuesto_soles: '450.00',
      intereses: ['arqueologia', 'naturaleza', 'gastronomia'],
      movilidad: 'transporte_publico',
      ritmo: 'moderado',
    },
  });

  if (!respuesta.ok()) {
    throw new Error(
      `No se pudo crear la preferencia (${respuesta.status()}). ` +
        `¿Está el backend en ${API}? Respuesta: ${await respuesta.text()}`,
    );
  }

  const cuerpo = (await respuesta.json()) as { id: number };
  return cuerpo.id;
}
