/**
 * Contexto y gancho de la sesión del usuario.
 *
 * NOMBRE EN INGLÉS A PROPÓSITO: React identifica los ganchos por el prefijo
 * "use". Ver docs/decisiones/2026-08-28-prefijo-use-en-los-ganchos.md
 *
 * DÓNDE SE GUARDA EL TOKEN. En `localStorage`. Es una decisión con un peaje
 * conocido: un token en localStorage es accesible desde JavaScript, así que
 * un fallo de XSS lo expondría. La alternativa más segura —una cookie
 * `HttpOnly`— exige que el backend y el frontend compartan dominio y traer
 * protección contra CSRF, y este proyecto corre en local sin despliegue.
 * Se documenta aquí para poder defenderlo en vez de fingir que no existe.
 */
import { createContext, useContext } from 'react';

import type { UsuarioPublico } from '@/servicios/api';

/** Clave con la que se recuerda el token en el navegador. */
export const CLAVE_TOKEN = 'rutaviva.token';

/**
 * Clave con la que se recuerda la preferencia creada SIN cuenta.
 *
 * Es lo que permite armar el viaje sin registrarse: el identificador vive en
 * el navegador de esa persona, y solo ella lo tiene.
 */
export const CLAVE_PREFERENCIA_ANONIMA = 'rutaviva.preferencia';

export interface ValorContextoSesion {
  usuario: UsuarioPublico | null;
  token: string | null;
  /** true mientras se comprueba si el token guardado sigue siendo válido. */
  cargando: boolean;
  iniciarSesion: (correo: string, contrasena: string) => Promise<void>;
  registrarse: (correo: string, contrasena: string, nombre: string) => Promise<void>;
  cerrarSesion: () => void;
}

export const ContextoSesion = createContext<ValorContextoSesion | null>(null);

/** Devuelve el usuario de la sesión y las funciones para entrar y salir. */
export function useSesion(): ValorContextoSesion {
  const valor = useContext(ContextoSesion);

  if (valor === null) {
    throw new Error('useSesion debe usarse dentro de <ProveedorSesion>');
  }

  return valor;
}

/** Lee el token guardado, tolerando que el almacenamiento esté bloqueado. */
export function leerTokenGuardado(): string | null {
  if (typeof window === 'undefined') return null;

  try {
    return window.localStorage.getItem(CLAVE_TOKEN);
  } catch {
    // Modo privado o cookies desactivadas: se sigue sin sesión persistente.
    return null;
  }
}

/** Guarda o borra el token. */
export function guardarToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(CLAVE_TOKEN);
    } else {
      window.localStorage.setItem(CLAVE_TOKEN, token);
    }
  } catch {
    // Sin almacenamiento, la sesión dura lo que dure la pestaña.
  }
}

/** Lee el identificador de la preferencia creada sin cuenta. */
export function leerPreferenciaAnonima(): number | null {
  try {
    const guardado = window.localStorage.getItem(CLAVE_PREFERENCIA_ANONIMA);
    const numero = Number(guardado);
    return guardado !== null && Number.isFinite(numero) ? numero : null;
  } catch {
    return null;
  }
}

/** Guarda o borra el identificador de la preferencia creada sin cuenta. */
export function guardarPreferenciaAnonima(id: number | null): void {
  try {
    if (id === null) {
      window.localStorage.removeItem(CLAVE_PREFERENCIA_ANONIMA);
    } else {
      window.localStorage.setItem(CLAVE_PREFERENCIA_ANONIMA, String(id));
    }
  } catch {
    // Sin almacenamiento no se puede recuperar la preferencia al recargar.
  }
}
