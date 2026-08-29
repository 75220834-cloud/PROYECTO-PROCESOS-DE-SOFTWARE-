/**
 * Contexto y gancho del tema claro/oscuro.
 *
 * NOMBRE EN INGLÉS A PROPÓSITO: React identifica los ganchos por el prefijo
 * "use". No es una convención de estilo, es cómo el compilador y el revisor
 * de código reconocen que esta función puede llamar a useState y useEffect.
 * Cae dentro de la excepción de la regla de idioma del proyecto (palabras
 * reservadas de la biblioteca). La parte propia del nombre, "Tema", sigue en
 * español. Ver docs/decisiones/2026-08-28-prefijo-use-en-los-ganchos.md
 *
 * POR QUÉ UN CONTEXTO Y NO SOLO UN useState:
 * si cada componente que necesita saber el tema guardara su propio estado,
 * tendríamos varias copias que se desincronizan entre sí — por ejemplo, un
 * interruptor en el encabezado de escritorio y otro en el menú del móvil
 * mostrando iconos contradictorios. El contexto garantiza una única fuente
 * de verdad para toda la aplicación.
 */
import { createContext, useContext } from 'react';

export type Tema = 'claro' | 'oscuro';

/** Clave con la que se recuerda el tema en el navegador. */
export const CLAVE_TEMA = 'rutaviva.tema';

/** Clase CSS que activa el tema oscuro en todo el árbol del documento. */
export const CLASE_OSCURO = 'oscuro';

export interface ValorContextoTema {
  tema: Tema;
  alternarTema: () => void;
  establecerTema: (tema: Tema) => void;
}

export const ContextoTema = createContext<ValorContextoTema | null>(null);

/**
 * Lee el tema que el usuario eligió antes; si nunca eligió, usa la
 * preferencia del sistema operativo.
 *
 * Se exporta porque lo necesita el proveedor para calcular el estado inicial.
 */
export function leerTemaInicial(): Tema {
  // En las pruebas y en el renderizado del servidor no existe window.
  if (typeof window === 'undefined') return 'claro';

  try {
    const guardado = window.localStorage.getItem(CLAVE_TEMA);
    if (guardado === 'claro' || guardado === 'oscuro') return guardado;
  } catch {
    // El navegador puede tener el almacenamiento bloqueado (modo privado,
    // cookies desactivadas). No es motivo para romper la aplicación.
  }

  const prefiereOscuro = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  return prefiereOscuro ? 'oscuro' : 'claro';
}

/**
 * Devuelve el tema actual y las funciones para cambiarlo.
 *
 * Falla de forma explícita si se usa fuera del proveedor: es un error de
 * programación y es mejor verlo de inmediato que depurar un tema que no
 * cambia sin saber por qué.
 */
export function useTema(): ValorContextoTema {
  const valor = useContext(ContextoTema);

  if (valor === null) {
    throw new Error('useTema debe usarse dentro de <ProveedorTema>');
  }

  return valor;
}
