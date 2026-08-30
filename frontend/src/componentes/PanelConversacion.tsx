/**
 * Asistente conversacional: botón flotante y panel lateral.
 *
 * Está disponible en toda la aplicación porque es **capa de interacción**: una
 * forma alternativa de pedir lo que ya se puede pedir por formulario. Por eso
 * acompaña al visitante esté donde esté, en vez de vivir en una pantalla suya.
 *
 * Dos decisiones que conviene poder explicar:
 *
 * 1. **Se enseña qué funciones se ejecutaron.** No es un adorno técnico: es lo
 *    que hace la conversación auditable. Quien lea la respuesta puede ver que
 *    salió de una consulta al catálogo y no de la imaginación del modelo.
 * 2. **Si Ollama no está, se dice y se ofrece el formulario.** El plan de
 *    trabajo lo exige con esas palabras: no fallar en silencio.
 */
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import {
  consultarEstadoDelAsistente,
  enviarMensajeAlAsistente,
  type FuncionUsada,
  type MensajeDeConversacion,
} from '@/servicios/api';

/**
 * Cuántos turnos se conservan.
 *
 * El backend acepta veinte y los valida; aquí se recorta antes de enviar para
 * que el visitante nunca se encuentre con un 422 por haber conversado mucho.
 * Se quedan los últimos, que son los que dan contexto a lo que se pregunta.
 */
const TURNOS_QUE_SE_ENVIAN = 20;

/** Icono de conversación. SVG en línea: sin dependencias y hereda el color. */
function IconoConversacion({ clase }: { clase: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={clase}
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

/** Icono de cerrar. */
function IconoCerrar({ clase }: { clase: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className={clase}
      aria-hidden="true"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

/**
 * Las funciones que se ejecutaron para responder.
 *
 * Se traduce el nombre técnico a una frase que se entienda: al visitante no le
 * dice nada «buscar_recursos», pero «consultó el catálogo» sí.
 */
function FuncionesEjecutadas({ funciones }: { funciones: FuncionUsada[] }) {
  const { t } = useTranslation();

  if (funciones.length === 0) {
    return null;
  }

  return (
    <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-sobre-superficie-variante">
      <span className="sr-only">{t('conversacion.funcionesAria')}</span>

      {funciones.map((funcion, indice) => (
        <span
          key={`${funcion.nombre}-${indice}`}
          className="rounded-full bg-superficie-contenedor-alto px-2 py-0.5"
        >
          {/* Si mañana se añade una función y falta su traducción, i18next
              devuelve la clave. Se pasa el nombre técnico como respaldo para
              que se lea algo comprensible en vez de «conversacion.funcion.x». */}
          {t(`conversacion.funcion.${funcion.nombre}`, { defaultValue: funcion.nombre })}
        </span>
      ))}
    </p>
  );
}

export function PanelConversacion() {
  const { t, i18n } = useTranslation();

  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState<MensajeDeConversacion[]>([]);
  const [funcionesPorMensaje, setFuncionesPorMensaje] = useState<Record<number, FuncionUsada[]>>(
    {},
  );
  const [borrador, setBorrador] = useState('');
  const [pensando, setPensando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const campo = useRef<HTMLTextAreaElement>(null);
  const finDeLaLista = useRef<HTMLDivElement>(null);

  // El estado se consulta una vez y se guarda: preguntarlo en cada apertura
  // añadiría dos segundos de espera para saber algo que rara vez cambia
  // mientras alguien navega.
  const { data: estado } = useQuery({
    queryKey: ['estado-asistente'],
    queryFn: consultarEstadoDelAsistente,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // Al abrir se enfoca el campo; con el panel cerrado no hay nada que enfocar.
  useEffect(() => {
    if (abierto) {
      campo.current?.focus();
    }
  }, [abierto]);

  // Cerrar con Escape. Es lo que espera cualquiera que use el teclado, y sin
  // esto el panel solo se cierra con el ratón.
  useEffect(() => {
    if (!abierto) {
      return;
    }

    function alPulsarTecla(evento: KeyboardEvent) {
      if (evento.key === 'Escape') {
        setAbierto(false);
      }
    }

    window.addEventListener('keydown', alPulsarTecla);
    return () => window.removeEventListener('keydown', alPulsarTecla);
  }, [abierto]);

  // Bajar a lo último cada vez que llega un mensaje.
  useEffect(() => {
    finDeLaLista.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes, pensando]);

  async function enviar() {
    const texto = borrador.trim();

    if (texto === '' || pensando) {
      return;
    }

    const conElNuevo: MensajeDeConversacion[] = [...mensajes, { rol: 'user', contenido: texto }];

    setMensajes(conElNuevo);
    setBorrador('');
    setPensando(true);
    setError(null);

    try {
      const respuesta = await enviarMensajeAlAsistente(
        conElNuevo.slice(-TURNOS_QUE_SE_ENVIAN),
        i18n.language,
      );

      setMensajes((anteriores) => {
        const siguientes: MensajeDeConversacion[] = [
          ...anteriores,
          { rol: 'assistant', contenido: respuesta.mensaje },
        ];

        // Las funciones se guardan indexadas por la posición del mensaje que
        // las provocó, no dentro del mensaje, para que el tipo que viaja al
        // backend siga siendo exactamente el que espera.
        setFuncionesPorMensaje((previas) => ({
          ...previas,
          [siguientes.length - 1]: respuesta.funciones_usadas,
        }));

        return siguientes;
      });
    } catch {
      setError(t('conversacion.error'));
    } finally {
      setPensando(false);
    }
  }

  const noDisponible = estado !== undefined && !estado.disponible;

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto((previo) => !previo)}
        aria-expanded={abierto}
        aria-label={t('conversacion.abrir')}
        title={t('conversacion.abrir')}
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-primario text-sobre-primario shadow-lg transition-transform hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario"
      >
        {abierto ? <IconoCerrar clase="h-6 w-6" /> : <IconoConversacion clase="h-6 w-6" />}
      </button>

      <AnimatePresence>
        {abierto && (
          <motion.aside
            role="dialog"
            aria-label={t('conversacion.titulo')}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.18 }}
            className="fixed bottom-24 right-5 z-40 flex max-h-[min(32rem,calc(100vh-8rem))] w-[min(24rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-xl border border-contorno-variante bg-superficie shadow-2xl"
          >
            <header className="border-b border-contorno-variante bg-superficie-contenedor-bajo px-4 py-3">
              <h2 className="font-titulo font-bold text-sobre-superficie">
                {t('conversacion.titulo')}
              </h2>

              <p className="mt-0.5 text-xs text-sobre-superficie-variante">
                {t('conversacion.subtitulo')}
              </p>
            </header>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              {noDisponible ? (
                <div className="rounded-lg bg-error-contenedor px-3 py-3 text-sm text-sobre-error-contenedor">
                  <p className="font-semibold">{t('conversacion.noDisponible')}</p>

                  {/* El motivo técnico se enseña porque quien monte el proyecto
                      necesita saber si le falta Ollama o le falta el modelo. */}
                  {estado?.motivo !== null && estado?.motivo !== undefined && (
                    <p className="mt-1 text-xs opacity-80">{estado.motivo}</p>
                  )}

                  <Link
                    to="/preferencias"
                    onClick={() => setAbierto(false)}
                    className="mt-2 inline-block font-semibold underline"
                  >
                    {t('conversacion.usarFormulario')}
                  </Link>
                </div>
              ) : (
                mensajes.length === 0 && (
                  <div className="space-y-3">
                    <p className="text-sm text-sobre-superficie-variante">
                      {t('conversacion.bienvenida')}
                    </p>

                    <ul className="space-y-1.5">
                      {(
                        [
                          'conversacion.ejemplo1',
                          'conversacion.ejemplo2',
                          'conversacion.ejemplo3',
                        ] as const
                      ).map((clave) => (
                        <li key={clave}>
                          <button
                            type="button"
                            onClick={() => {
                              setBorrador(t(clave));
                              campo.current?.focus();
                            }}
                            className="w-full rounded-lg border border-contorno-variante px-3 py-2 text-left text-sm text-sobre-superficie transition-colors hover:bg-superficie-contenedor"
                          >
                            {t(clave)}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              )}

              {mensajes.map((mensaje, indice) => (
                <div
                  key={indice}
                  className={mensaje.rol === 'user' ? 'flex justify-end' : 'flex justify-start'}
                >
                  <div
                    className={
                      mensaje.rol === 'user'
                        ? 'max-w-[85%] rounded-2xl rounded-br-sm bg-primario px-3 py-2 text-sm text-sobre-primario'
                        : 'max-w-[85%] rounded-2xl rounded-bl-sm bg-superficie-contenedor px-3 py-2 text-sm text-sobre-superficie'
                    }
                  >
                    {/* El modelo separa párrafos con saltos de línea; sin esto
                        se leerían todos pegados en un solo bloque. */}
                    <p className="whitespace-pre-wrap">{mensaje.contenido}</p>

                    {mensaje.rol === 'assistant' && (
                      <FuncionesEjecutadas funciones={funcionesPorMensaje[indice] ?? []} />
                    )}
                  </div>
                </div>
              ))}

              {pensando && (
                <p
                  className="text-sm text-sobre-superficie-variante"
                  role="status"
                  aria-live="polite"
                >
                  {t('conversacion.pensando')}
                </p>
              )}

              {error !== null && (
                <p className="rounded-lg bg-error-contenedor px-3 py-2 text-sm text-sobre-error-contenedor">
                  {error}
                </p>
              )}

              <div ref={finDeLaLista} />
            </div>

            <form
              className="border-t border-contorno-variante bg-superficie-contenedor-bajo px-3 py-3"
              onSubmit={(evento) => {
                evento.preventDefault();
                void enviar();
              }}
            >
              <div className="flex items-end gap-2">
                <textarea
                  ref={campo}
                  value={borrador}
                  onChange={(evento) => setBorrador(evento.target.value)}
                  onKeyDown={(evento) => {
                    // Enter envía; Mayúsculas+Enter hace un salto de línea. Es
                    // lo que hace cualquier chat, y sin ello escribir un texto
                    // de dos párrafos obliga a usar el ratón.
                    if (evento.key === 'Enter' && !evento.shiftKey) {
                      evento.preventDefault();
                      void enviar();
                    }
                  }}
                  rows={2}
                  disabled={noDisponible}
                  placeholder={t('conversacion.escribe')}
                  aria-label={t('conversacion.escribe')}
                  className="flex-1 resize-none rounded-lg border border-contorno-variante bg-superficie px-3 py-2 text-sm text-sobre-superficie placeholder:text-sobre-superficie-variante focus:border-primario focus:outline-none disabled:opacity-50"
                />

                <button
                  type="submit"
                  disabled={pensando || noDisponible || borrador.trim() === ''}
                  className="rounded-lg bg-primario px-3 py-2 text-sm font-semibold text-sobre-primario transition-opacity disabled:opacity-40"
                >
                  {t('conversacion.enviar')}
                </button>
              </div>

              {/* La advertencia va fija, no solo la primera vez: el visitante
                  puede llegar a esta conversación por cualquier pantalla y no
                  haber leído nada antes sobre de dónde salen los datos. */}
              <p className="mt-2 text-[0.7rem] leading-snug text-sobre-superficie-variante">
                {t('conversacion.advertencia')}
              </p>
            </form>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
