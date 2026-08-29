/**
 * Proveedor del tema claro/oscuro.
 *
 * Envuelve toda la aplicación y es el único lugar donde vive el estado del
 * tema. Cómo funciona por dentro:
 *
 * 1. Al montarse, lee si el usuario ya eligió un tema antes (guardado en el
 *    navegador). Si nunca eligió, usa la preferencia del sistema operativo.
 * 2. Cuando el tema cambia, añade o quita la clase "oscuro" del elemento
 *    <html>. Esa clase es la que activa todas las variantes  dark:  de
 *    Tailwind (ver @custom-variant en estilos/index.css).
 * 3. Guarda la elección para la próxima visita.
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  CLASE_OSCURO,
  CLAVE_TEMA,
  ContextoTema,
  leerTemaInicial,
  type Tema,
} from '@/hooks/useTema';

export function ProveedorTema({ children }: { children: ReactNode }) {
  const [tema, establecerTema] = useState<Tema>(leerTemaInicial);

  useEffect(() => {
    document.documentElement.classList.toggle(CLASE_OSCURO, tema === 'oscuro');

    try {
      window.localStorage.setItem(CLAVE_TEMA, tema);
    } catch {
      // Si no se puede guardar, el tema sigue funcionando en esta sesión.
    }
  }, [tema]);

  const alternarTema = useCallback(() => {
    establecerTema((actual) => (actual === 'oscuro' ? 'claro' : 'oscuro'));
  }, []);

  // useMemo evita crear un objeto nuevo en cada renderizado, lo que obligaría
  // a redibujar todos los componentes que consumen el contexto sin necesidad.
  const valor = useMemo(() => ({ tema, alternarTema, establecerTema }), [tema, alternarTema]);

  return <ContextoTema.Provider value={valor}>{children}</ContextoTema.Provider>;
}
