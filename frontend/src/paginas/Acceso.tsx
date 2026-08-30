/**
 * Página de registro e inicio de sesión.
 *
 * Sigue el diseño de Stitch: dos pestañas en el mismo formulario y, bien
 * visible, el mensaje que resume la regla del proyecto — *no hace falta
 * cuenta para armar el viaje*.
 */
import { motion } from 'framer-motion';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { useSesion } from '@/hooks/useSesion';
import { medirFuerza } from '@/utilidades/formato';
import { traducirError } from '@/utilidades/avisos';

type Pestana = 'entrar' | 'crear';

export function Acceso() {
  const { t } = useTranslation();
  const navegar = useNavigate();
  const { iniciarSesion, registrarse } = useSesion();

  const [pestana, establecerPestana] = useState<Pestana>('entrar');
  const [correo, establecerCorreo] = useState('');
  const [contrasena, establecerContrasena] = useState('');
  const [confirmacion, establecerConfirmacion] = useState('');
  const [nombre, establecerNombre] = useState('');
  const [error, establecerError] = useState<string | null>(null);
  const [enviando, establecerEnviando] = useState(false);

  const fuerza = medirFuerza(contrasena);
  const coloresDeFuerza = [
    'bg-superficie-contenedor-alto',
    'bg-error',
    'bg-terciario',
    'bg-secundario',
    'bg-secundario',
  ];

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    establecerError(null);

    if (pestana === 'crear' && contrasena !== confirmacion) {
      establecerError(t('acceso.error_confirmacion'));
      return;
    }

    establecerEnviando(true);

    try {
      if (pestana === 'entrar') {
        await iniciarSesion(correo, contrasena);
      } else {
        await registrarse(correo, contrasena, nombre);
      }
      navegar('/mis-viajes');
    } catch (fallo) {
      establecerError(traducirError(t, fallo, t('acceso.error')));
    } finally {
      establecerEnviando(false);
    }
  }

  const clasesDeCampo =
    'w-full rounded-md border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2.5 text-sobre-superficie transition-colors focus:border-primario focus:outline-2 focus:outline-offset-1 focus:outline-primario';

  const clasesDePestana = (activa: boolean) =>
    'flex-1 rounded-md px-4 py-2.5 text-sm font-semibold transition-colors ' +
    (activa
      ? 'bg-primario text-sobre-primario'
      : 'text-sobre-superficie-variante hover:text-primario');

  return (
    <main className="mx-auto max-w-md px-4 py-14 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        {/* Aviso principal: la aplicación no exige cuenta. */}
        <p className="rounded-lg bg-secundario-contenedor p-4 text-sm text-sobre-secundario-contenedor">
          {t('acceso.no_hace_falta_cuenta')}{' '}
          <Link to="/preferencias" className="font-semibold underline">
            {t('acceso.continuar_sin_cuenta')}
          </Link>
        </p>

        <div className="mt-8 rounded-lg border border-contorno-variante bg-superficie-contenedor-bajo p-6">
          <div role="tablist" className="flex gap-1 rounded-md bg-superficie-contenedor-alto p-1">
            <button
              type="button"
              role="tab"
              aria-selected={pestana === 'entrar'}
              onClick={() => establecerPestana('entrar')}
              className={clasesDePestana(pestana === 'entrar')}
            >
              {t('acceso.iniciar_sesion')}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={pestana === 'crear'}
              onClick={() => establecerPestana('crear')}
              className={clasesDePestana(pestana === 'crear')}
            >
              {t('acceso.crear_cuenta')}
            </button>
          </div>

          <form onSubmit={enviar} className="mt-6 space-y-4">
            {pestana === 'crear' && (
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold">{t('acceso.nombre')}</span>
                <input
                  type="text"
                  required
                  minLength={2}
                  value={nombre}
                  onChange={(evento) => establecerNombre(evento.target.value)}
                  className={clasesDeCampo}
                />
              </label>
            )}

            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold">{t('acceso.correo')}</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={correo}
                onChange={(evento) => establecerCorreo(evento.target.value)}
                className={clasesDeCampo}
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold">{t('acceso.contrasena')}</span>
              <input
                type="password"
                required
                minLength={pestana === 'crear' ? 8 : undefined}
                autoComplete={pestana === 'crear' ? 'new-password' : 'current-password'}
                value={contrasena}
                onChange={(evento) => establecerContrasena(evento.target.value)}
                className={clasesDeCampo}
              />
            </label>

            {pestana === 'crear' && (
              <>
                {/* Indicador de fuerza: orientativo, no bloquea nada. */}
                <div>
                  <div className="flex gap-1" aria-hidden="true">
                    {[1, 2, 3, 4].map((nivel) => (
                      <span
                        key={nivel}
                        className={
                          'h-1.5 flex-1 rounded-full transition-colors ' +
                          (fuerza >= nivel
                            ? coloresDeFuerza[fuerza]
                            : 'bg-superficie-contenedor-alto')
                        }
                      />
                    ))}
                  </div>
                  <p className="mt-1.5 text-xs text-sobre-superficie-variante">
                    {t(`acceso.fuerza_${fuerza}`)}
                  </p>
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-sm font-semibold">
                    {t('acceso.confirmar')}
                  </span>
                  <input
                    type="password"
                    required
                    autoComplete="new-password"
                    value={confirmacion}
                    onChange={(evento) => establecerConfirmacion(evento.target.value)}
                    className={clasesDeCampo}
                  />
                </label>
              </>
            )}

            {error && (
              <p role="alert" className="text-sm text-error">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={enviando}
              className="w-full rounded-md bg-primario px-6 py-3 font-semibold text-sobre-primario shadow-suave transition-transform enabled:hover:-translate-y-0.5 disabled:opacity-60"
            >
              {enviando
                ? t('acceso.enviando')
                : pestana === 'entrar'
                  ? t('acceso.iniciar_sesion')
                  : t('acceso.crear_cuenta')}
            </button>
          </form>
        </div>

        {/* Credenciales de demostración, visibles solo en desarrollo. */}
        {import.meta.env.DEV && (
          <details className="mt-6 rounded-lg border border-contorno-variante p-4 text-sm">
            <summary className="cursor-pointer font-semibold text-sobre-superficie-variante">
              {t('acceso.usuarios_demo')}
            </summary>
            <ul className="mt-3 space-y-1 text-xs text-sobre-superficie-variante">
              {['visitante', 'proveedor', 'operador', 'gestor', 'administrador'].map((rol) => (
                <li key={rol}>
                  <code>{rol}@rutavivamantaro.pe</code> · <code>RutaViva2026</code>
                </li>
              ))}
            </ul>
          </details>
        )}
      </motion.div>
    </main>
  );
}
