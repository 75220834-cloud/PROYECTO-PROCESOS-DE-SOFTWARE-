/**
 * Proveedor de la sesión del usuario.
 *
 * Envuelve toda la aplicación y es el único sitio donde vive el estado de la
 * sesión. Al arrancar comprueba si el token guardado en el navegador sigue
 * siendo válido, para que quien vuelva al día siguiente no tenga que escribir
 * la contraseña otra vez.
 *
 * Detalle importante del recorrido del proyecto: al iniciar sesión o
 * registrarse, si hay una preferencia creada SIN cuenta guardada en el
 * navegador, se **reclama** automáticamente. Es lo que hace realidad la
 * promesa de «arma tu viaje sin registrarte y guárdalo al final».
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  ContextoSesion,
  guardarPreferenciaAnonima,
  guardarToken,
  leerPreferenciaAnonima,
  leerTokenGuardado,
} from '@/hooks/useSesion';
import {
  consultarSesionActual,
  iniciarSesion as pedirSesion,
  reclamarPreferencia,
  registrarse as pedirRegistro,
  type RespuestaSesion,
  type UsuarioPublico,
} from '@/servicios/api';

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, establecerUsuario] = useState<UsuarioPublico | null>(null);
  const [token, establecerToken] = useState<string | null>(leerTokenGuardado);
  const [cargando, establecerCargando] = useState(true);

  // Al arrancar: si hay token guardado, se comprueba contra la API. Un token
  // caducado se descarta en silencio y el visitante sigue como anónimo.
  useEffect(() => {
    let cancelado = false;

    async function comprobarSesionGuardada() {
      const guardado = leerTokenGuardado();

      if (guardado === null) {
        establecerCargando(false);
        return;
      }

      try {
        const encontrado = await consultarSesionActual(guardado);
        if (!cancelado) establecerUsuario(encontrado);
      } catch {
        if (!cancelado) {
          guardarToken(null);
          establecerToken(null);
        }
      } finally {
        if (!cancelado) establecerCargando(false);
      }
    }

    void comprobarSesionGuardada();

    return () => {
      cancelado = true;
    };
  }, []);

  /** Guarda la sesión recién abierta y reclama la preferencia anónima. */
  const aceptarSesion = useCallback(async (respuesta: RespuestaSesion) => {
    guardarToken(respuesta.token_de_acceso);
    establecerToken(respuesta.token_de_acceso);
    establecerUsuario(respuesta.usuario);

    const preferenciaAnonima = leerPreferenciaAnonima();

    if (preferenciaAnonima !== null) {
      try {
        await reclamarPreferencia(preferenciaAnonima, respuesta.token_de_acceso);
        // Ya tiene dueño: deja de ser anónima y se quita del navegador.
        guardarPreferenciaAnonima(null);
      } catch {
        // Si la preferencia ya no existe o es de otra persona, no pasa nada:
        // la sesión se abre igual. No es motivo para bloquear la entrada.
      }
    }
  }, []);

  const iniciarSesion = useCallback(
    async (correo: string, contrasena: string) => {
      await aceptarSesion(await pedirSesion(correo, contrasena));
    },
    [aceptarSesion],
  );

  const registrarse = useCallback(
    async (correo: string, contrasena: string, nombre: string) => {
      await aceptarSesion(await pedirRegistro(correo, contrasena, nombre));
    },
    [aceptarSesion],
  );

  const cerrarSesion = useCallback(() => {
    guardarToken(null);
    establecerToken(null);
    establecerUsuario(null);
  }, []);

  const valor = useMemo(
    () => ({ usuario, token, cargando, iniciarSesion, registrarse, cerrarSesion }),
    [usuario, token, cargando, iniciarSesion, registrarse, cerrarSesion],
  );

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}
