/**
 * Gancho que gestiona el tema claro/oscuro.
 *
 * NOMBRE EN INGLES A PROPOSITO: React identifica los ganchos por el prefijo
 * "use". No es una convencion de estilo, es como el compilador y el revisor
 * de codigo reconocen que esta funcion puede llamar a useState y useEffect.
 * Cae dentro de la excepcion de la regla de idioma del proyecto (palabras
 * reservadas de la biblioteca). La parte propia del nombre, "Tema", sigue
 * en espanol. Ver docs/decisiones/2026-08-28-prefijo-use-en-los-ganchos.md
 *
 * Como funciona por dentro:
 * 1. Al cargar, busca si el usuario ya eligio un tema (guardado en
 *    localStorage). Si nunca eligio, usa la preferencia del sistema operativo.
 * 2. Cuando el tema cambia, anade o quita la clase "oscuro" del elemento
 *    <html>. Esa clase es la que activa todas las variantes  dark:  de
 *    Tailwind (ver la declaracion @custom-variant en estilos/index.css).
 * 3. Guarda la eleccion para la proxima visita.
 */
import { useCallback, useEffect, useState } from 'react';

export type Tema = 'claro' | 'oscuro';

/** Clave con la que se recuerda el tema en el navegador. */
export const CLAVE_TEMA = 'rutaviva.tema';

/** Clase CSS que activa el tema oscuro en todo el arbol del documento. */
const CLASE_OSCURO = 'oscuro';

function leerTemaInicial(): Tema {
  // En las pruebas y en el renderizado del servidor no existe window.
  if (typeof window === 'undefined') return 'claro';

  try {
    const guardado = window.localStorage.getItem(CLAVE_TEMA);
    if (guardado === 'claro' || guardado === 'oscuro') return guardado;
  } catch {
    // El navegador puede tener el almacenamiento bloqueado (modo privado,
    // cookies desactivadas). No es motivo para romper la aplicacion.
  }

  // Sin eleccion previa, se respeta la preferencia del sistema operativo.
  const prefiereOscuro = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  return prefiereOscuro ? 'oscuro' : 'claro';
}

export function useTema() {
  const [tema, establecerTema] = useState<Tema>(leerTemaInicial);

  useEffect(() => {
    const raiz = document.documentElement;
    raiz.classList.toggle(CLASE_OSCURO, tema === 'oscuro');

    try {
      window.localStorage.setItem(CLAVE_TEMA, tema);
    } catch {
      // Si no se puede guardar, el tema sigue funcionando en esta sesion.
    }
  }, [tema]);

  const alternarTema = useCallback(() => {
    establecerTema((actual) => (actual === 'oscuro' ? 'claro' : 'oscuro'));
  }, []);

  return { tema, alternarTema, establecerTema };
}
