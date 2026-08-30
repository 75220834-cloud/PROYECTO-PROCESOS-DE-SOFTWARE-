/**
 * Formulario de valoración al cerrar un itinerario (Incremento 6).
 *
 * ## Las estrellas son botones de verdad, no un `<input type="range">`
 *
 * Un deslizador se entiende con el ratón y no se entiende con teclado ni con
 * lector de pantalla. Aquí cada estrella es un `<button>` con su etiqueta
 * («elegir 4 de 5 estrellas»), así que se puede tabular y pulsar con Enter, y
 * un lector de pantalla anuncia exactamente qué hace cada una.
 *
 * ## Lo que el sistema entendió se enseña al visitante
 *
 * Después de enviar, la tarjeta muestra el sentimiento detectado, los temas y
 * **con qué vía se analizó**. No es un adorno técnico: la persona acaba de
 * ceder una opinión para que un sistema la clasifique, y tiene derecho a ver
 * qué entendió y a saber si lo hizo un modelo o un diccionario.
 *
 * Si el sistema se equivoca, verlo es la única forma de que alguien lo diga.
 */
import { useMutation } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSesion } from '@/hooks/useSesion';
import { crearValoracion, ErrorDeApi, type ValoracionPublica } from '@/servicios/api';

/** Las cinco estrellas, de menos a más. */
const ESTRELLAS = [1, 2, 3, 4, 5];

/** Color de la etiqueta de sentimiento. */
const ESTILO_DE_SENTIMIENTO: Record<string, string> = {
  positivo: 'bg-secundario-contenedor text-sobre-secundario-contenedor',
  neutro: 'bg-superficie-contenedor-alto text-sobre-superficie-variante',
  negativo: 'bg-error-contenedor text-sobre-error-contenedor',
};

interface Propiedades {
  itinerarioId: number;
  /** Recurso concreto que se valora. Sin él, se valora el día completo. */
  recursoId?: number | null;
  /** Nombre de lo que se valora, para el título. */
  queSeValora?: string;
  alEnviar?: (valoracion: ValoracionPublica) => void;
  alCerrar?: () => void;
}

export default function FormularioValoracion({
  itinerarioId,
  recursoId = null,
  queSeValora,
  alEnviar,
  alCerrar,
}: Propiedades) {
  const { t } = useTranslation();
  const { token } = useSesion();
  const idBase = useId();

  const [puntuacion, establecerPuntuacion] = useState(0);
  const [comentario, establecerComentario] = useState('');

  const envio = useMutation({
    mutationFn: () =>
      crearValoracion(
        {
          itinerario_id: itinerarioId,
          puntuacion,
          comentario: comentario.trim() || null,
          recurso_id: recursoId,
        },
        token,
      ),
    onSuccess: (valoracion) => alEnviar?.(valoracion),
  });

  // Después de enviar se enseña lo que el sistema entendió, no un «gracias» a
  // secas: la persona tiene derecho a ver cómo se clasificó su opinión.
  if (envio.isSuccess) {
    return <LoQueEntendimos valoracion={envio.data} alCerrar={alCerrar} />;
  }

  return (
    <form
      onSubmit={(evento) => {
        evento.preventDefault();
        if (puntuacion > 0) envio.mutate();
      }}
      className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5"
    >
      <h3 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {queSeValora ?? t('valoracion.titulo')}
      </h3>
      <p className="mt-1 text-sm text-sobre-superficie-variante">{t('valoracion.subtitulo')}</p>

      {/* Las estrellas. Cada una es un botón con su etiqueta. */}
      <fieldset className="mt-4">
        <legend className="text-sm font-medium text-sobre-superficie">
          {t('valoracion.puntuacion')}
        </legend>

        <div className="mt-2 flex items-center gap-1">
          {ESTRELLAS.map((numero) => (
            <button
              key={numero}
              type="button"
              onClick={() => establecerPuntuacion(numero)}
              aria-label={t('valoracion.elegirEstrellas', { numero })}
              aria-pressed={puntuacion === numero}
              className={`rounded p-1 text-2xl transition-transform hover:scale-110 focus-visible:ring-2 focus-visible:ring-primario focus-visible:outline-none ${
                numero <= puntuacion ? 'text-terciario' : 'text-superficie-contenedor-alto'
              }`}
            >
              <span aria-hidden="true">★</span>
            </button>
          ))}

          {puntuacion > 0 && (
            <span className="ml-2 text-sm text-sobre-superficie-variante">
              {t('valoracion.estrellas', { count: puntuacion })}
            </span>
          )}
        </div>
      </fieldset>

      <div className="mt-4">
        <label
          htmlFor={`${idBase}-comentario`}
          className="block text-sm font-medium text-sobre-superficie"
        >
          {t('valoracion.comentario')}
        </label>
        <textarea
          id={`${idBase}-comentario`}
          value={comentario}
          onChange={(evento) => establecerComentario(evento.target.value)}
          rows={4}
          maxLength={4000}
          className="mt-1 w-full rounded border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2 text-sm text-sobre-superficie focus-visible:ring-2 focus-visible:ring-primario focus-visible:outline-none"
        />
        <p className="mt-1 text-xs text-sobre-superficie-variante">
          {t('valoracion.comentarioAyuda')}
        </p>
      </div>

      {envio.isError && (
        <p className="mt-3 text-sm text-sobre-error-contenedor" role="alert">
          {envio.error instanceof ErrorDeApi ? envio.error.message : t('valoracion.error')}
        </p>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={envio.isPending || puntuacion === 0}
          className="rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario transition-transform hover:-translate-y-0.5 disabled:opacity-60"
        >
          {envio.isPending ? t('valoracion.enviando') : t('valoracion.enviar')}
        </button>

        {alCerrar && (
          <button
            type="button"
            onClick={alCerrar}
            className="rounded-full border border-contorno-variante px-5 py-2 text-sm font-semibold text-sobre-superficie-variante"
          >
            {t('valoracion.cerrar')}
          </button>
        )}

        {/* El botón se desactiva sin estrellas, así que hay que decir por qué:
            un botón muerto sin explicación es de las cosas más frustrantes que
            puede hacer un formulario. */}
        {puntuacion === 0 && (
          <span className="text-xs text-sobre-superficie-variante">
            {t('valoracion.sinPuntuacion')}
          </span>
        )}
      </div>
    </form>
  );
}

/**
 * Lo que el sistema entendió del comentario, enseñado a quien lo escribió.
 *
 * Se muestra el sentimiento, los temas y la vía de análisis. Lo último es la
 * trazabilidad de la regla de oro de la IA del proyecto: quien lee esto sabe
 * si su comentario lo interpretó un modelo de lenguaje o un diccionario.
 */
function LoQueEntendimos({
  valoracion,
  alCerrar,
}: {
  valoracion: ValoracionPublica;
  alCerrar?: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="rounded-lg border border-secundario bg-secundario-contenedor p-5" role="status">
      <p className="font-titulo font-semibold text-sobre-secundario-contenedor">
        {t('valoracion.enviada')}
      </p>

      {valoracion.sentimiento && (
        <div className="mt-4 rounded border border-contorno-variante bg-superficie-contenedor-minimo p-4">
          <h4 className="text-xs tracking-wide text-sobre-superficie-variante uppercase">
            {t('valoracion.loQueEntendimos')}
          </h4>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-xs font-bold ${
                ESTILO_DE_SENTIMIENTO[valoracion.sentimiento] ?? ''
              }`}
            >
              {t(`valoracion.sentimiento.${valoracion.sentimiento}`)}
            </span>

            {valoracion.confianza_sentimiento !== null && (
              <span className="text-xs text-sobre-superficie-variante">
                {t('valoracion.confianza', {
                  valor: Math.round(valoracion.confianza_sentimiento * 100),
                })}
              </span>
            )}
          </div>

          {valoracion.temas.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {valoracion.temas.map((tema) => (
                <li
                  key={tema}
                  className="rounded bg-superficie-contenedor px-2 py-0.5 text-xs text-sobre-superficie-variante"
                >
                  {t(`valoracion.temas.${tema}`)}
                </li>
              ))}
            </ul>
          )}

          <p className="mt-3 text-xs text-sobre-superficie-variante">
            {valoracion.analizado_por === 'modelo'
              ? t('valoracion.analizadoPorModelo')
              : t('valoracion.analizadoPorReglas')}
          </p>
        </div>
      )}

      {alCerrar && (
        <button
          type="button"
          onClick={alCerrar}
          className="mt-4 rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario"
        >
          {t('valoracion.cerrar')}
        </button>
      )}
    </div>
  );
}
