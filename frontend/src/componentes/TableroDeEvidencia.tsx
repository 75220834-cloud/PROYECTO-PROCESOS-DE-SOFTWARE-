/**
 * Tablero de evidencia del gestor (Incremento 6).
 *
 * Es la segunda mitad de la brecha 7: *la retroalimentación no retorna
 * estructurada **al proceso ni al gestor***. Guardar las valoraciones cierra la
 * primera mitad; esto cierra la segunda.
 *
 * ## Qué lo separa de «una lista de reseñas»
 *
 * Un listado de comentarios no es evidencia: es trabajo pendiente para quien lo
 * lea. Aquí el gestor puede responder tres preguntas sin leer nada:
 *
 * - ¿de qué habla la gente, y con qué signo?
 * - ¿qué recursos van peor, y por qué?
 * - ¿esto mejora o empeora?
 *
 * ## Los avisos van arriba
 *
 * Un tablero que no dice cuándo sus números son frágiles invita a decidir sobre
 * nada. Con tres valoraciones, la media de un recurso se mueve un punto entero
 * con la siguiente, y eso tiene que verse antes que el número.
 */
import { useTranslation } from 'react-i18next';

import type { RecursoValorado, ResumenDeEvidencia, TemaAgregado } from '@/servicios/api';
import { formatearNombrePropio } from '@/utilidades/formato';

/** Color de cada porción de la barra de sentimiento. */
const COLOR_DE_SENTIMIENTO: Record<string, string> = {
  positivas: 'bg-secundario',
  neutras: 'bg-superficie-contenedor-alto',
  negativas: 'bg-error',
};

export default function TableroDeEvidencia({ resumen }: { resumen: ResumenDeEvidencia }) {
  const { t } = useTranslation();

  if (resumen.total_valoraciones === 0) {
    return (
      <p className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-6 text-sm text-sobre-superficie-variante">
        {t('valoracion.tableroVacio')}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {/* Los avisos, antes que los números. */}
      {resumen.avisos.length > 0 && (
        <section
          className="rounded-lg border border-terciario bg-terciario-contenedor p-4"
          role="status"
        >
          <h3 className="font-titulo text-sm font-semibold text-sobre-terciario-contenedor">
            {t('valoracion.avisosDelTablero')}
          </h3>
          <ul className="mt-2 space-y-1">
            {resumen.avisos.map((aviso) => (
              <li
                key={aviso}
                className="flex items-start gap-2 text-sm text-sobre-terciario-contenedor"
              >
                <span aria-hidden="true">•</span>
                <span>{aviso}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Las cifras de cabecera. */}
      <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Dato
            etiqueta={t('valoracion.cobertura')}
            valor={`${resumen.porcentaje_con_valoracion.toFixed(1)} %`}
            detalle={`${resumen.itinerarios_con_valoracion} / ${resumen.total_itinerarios}`}
          />
          <Dato
            etiqueta={t('valoracion.totalValoraciones')}
            valor={String(resumen.total_valoraciones)}
          />
          <Dato etiqueta={t('valoracion.conComentario')} valor={String(resumen.con_comentario)} />
          <Dato
            etiqueta={t('valoracion.puntuacionMedia')}
            valor={
              resumen.puntuacion_media !== null
                ? `${resumen.puntuacion_media.toFixed(2)} / 5`
                : t('valoracion.sinDato')
            }
          />
        </dl>

        <p className="mt-4 text-xs text-sobre-superficie-variante">
          {t('valoracion.analizadasPor')}: {resumen.analizadas_por_modelo}{' '}
          {t('valoracion.porModelo')} · {resumen.analizadas_por_reglas} {t('valoracion.porReglas')}
        </p>
      </section>

      {/* Distribución de sentimiento. */}
      <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
        <h3 className="font-titulo font-semibold text-sobre-superficie">
          {t('valoracion.distribucion')}
        </h3>

        <BarraDeSentimiento
          positivas={resumen.sentimiento.positivas}
          neutras={resumen.sentimiento.neutras}
          negativas={resumen.sentimiento.negativas}
          total={resumen.sentimiento.total}
        />
      </section>

      {/* Temas. */}
      {resumen.temas.length > 0 && (
        <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
          <h3 className="font-titulo font-semibold text-sobre-superficie">
            {t('valoracion.temasMasMencionados')}
          </h3>

          <ul className="mt-4 space-y-3">
            {resumen.temas.map((tema) => (
              <FilaDeTema key={tema.tema} tema={tema} maximo={resumen.temas[0].menciones} />
            ))}
          </ul>
        </section>
      )}

      {/* Ranquin de recursos. */}
      <div className="grid gap-6 md:grid-cols-2">
        <ListaDeRecursos
          titulo={t('valoracion.mejorValorados')}
          recursos={resumen.mejor_valorados}
        />
        <ListaDeRecursos titulo={t('valoracion.peorValorados')} recursos={resumen.peor_valorados} />
      </div>

      {/* Evolución. */}
      {resumen.evolucion.length > 0 && (
        <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
          <h3 className="font-titulo font-semibold text-sobre-superficie">
            {t('valoracion.evolucion')}
          </h3>

          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-xs tracking-wide text-sobre-superficie-variante uppercase">
                <th className="pb-2">{t('valoracion.periodo')}</th>
                <th className="pb-2">{t('valoracion.totalValoraciones')}</th>
                <th className="pb-2">{t('valoracion.puntuacionMedia')}</th>
                <th className="pb-2">{t('valoracion.sentimiento.positivo')}</th>
                <th className="pb-2">{t('valoracion.sentimiento.negativo')}</th>
              </tr>
            </thead>
            <tbody>
              {resumen.evolucion.map((punto) => (
                <tr key={punto.periodo} className="border-t border-contorno-variante">
                  <td className="py-2 font-mono text-sobre-superficie">{punto.periodo}</td>
                  <td className="py-2 text-sobre-superficie-variante">{punto.total}</td>
                  <td className="py-2 text-sobre-superficie">
                    {punto.puntuacion_media.toFixed(2)}
                  </td>
                  <td className="py-2 text-sobre-superficie-variante">{punto.positivas}</td>
                  <td className="py-2 text-sobre-superficie-variante">{punto.negativas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

/**
 * La barra apilada de sentimiento, con su equivalente en texto.
 *
 * Tres franjas de color no significan nada sin vista, así que la barra lleva
 * `role="img"` con los tres números en palabras, y debajo va la leyenda.
 */
function BarraDeSentimiento({
  positivas,
  neutras,
  negativas,
  total,
}: {
  positivas: number;
  neutras: number;
  negativas: number;
  total: number;
}) {
  const { t } = useTranslation();

  if (total === 0) return null;

  const partes = [
    { clave: 'positivas', valor: positivas, etiqueta: t('valoracion.sentimiento.positivo') },
    { clave: 'neutras', valor: neutras, etiqueta: t('valoracion.sentimiento.neutro') },
    { clave: 'negativas', valor: negativas, etiqueta: t('valoracion.sentimiento.negativo') },
  ];

  return (
    <>
      <div
        className="mt-3 flex h-4 w-full overflow-hidden rounded-full bg-superficie-contenedor"
        role="img"
        aria-label={partes.map((p) => `${p.etiqueta}: ${p.valor}`).join(', ')}
      >
        {partes.map((parte) => (
          <div
            key={parte.clave}
            aria-hidden="true"
            className={COLOR_DE_SENTIMIENTO[parte.clave]}
            // La anchura es un valor calculado, así que va en línea: Tailwind
            // genera sus clases leyendo el código, y una construida en tiempo
            // de ejecución no existiría en la hoja de estilos.
            style={{ width: `${(100 * parte.valor) / total}%` }}
          />
        ))}
      </div>

      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
        {partes.map((parte) => (
          <li key={parte.clave} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={`inline-block h-2.5 w-2.5 rounded-full ${COLOR_DE_SENTIMIENTO[parte.clave]}`}
            />
            <span className="text-sobre-superficie-variante">
              {parte.etiqueta}: <strong className="text-sobre-superficie">{parte.valor}</strong>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

/** Una fila del listado de temas, con su barra proporcional. */
function FilaDeTema({ tema, maximo }: { tema: TemaAgregado; maximo: number }) {
  const { t } = useTranslation();

  return (
    <li>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium text-sobre-superficie">
          {t(`valoracion.temas.${tema.tema}`)}
        </span>
        <span className="text-sm text-sobre-superficie-variante">
          {t('valoracion.menciones', { count: tema.menciones })}
          {tema.porcentaje_negativo !== null && tema.porcentaje_negativo > 0 && (
            <>
              {' · '}
              <span className="text-sobre-error-contenedor">
                {t('valoracion.negativoPorcentaje', { valor: tema.porcentaje_negativo })}
              </span>
            </>
          )}
        </span>
      </div>

      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-superficie-contenedor">
        <div
          className="h-full rounded-full bg-primario"
          style={{ width: `${(100 * tema.menciones) / Math.max(maximo, 1)}%` }}
        />
      </div>
    </li>
  );
}

/** Mejor o peor valorados, con la marca de poca fiabilidad. */
function ListaDeRecursos({ titulo, recursos }: { titulo: string; recursos: RecursoValorado[] }) {
  const { t } = useTranslation();

  return (
    <section className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <h3 className="font-titulo font-semibold text-sobre-superficie">{titulo}</h3>

      {recursos.length === 0 ? (
        <p className="mt-3 text-sm text-sobre-superficie-variante">
          {t('valoracion.tableroVacio')}
        </p>
      ) : (
        <ol className="mt-3 space-y-3">
          {recursos.map((recurso) => (
            <li key={recurso.recurso_id}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-sobre-superficie">
                  {formatearNombrePropio(recurso.nombre)}
                </span>
                <span className="font-titulo font-semibold text-sobre-superficie">
                  {recurso.puntuacion_media.toFixed(1)} ★
                </span>
              </div>

              <p className="text-xs text-sobre-superficie-variante">
                {formatearNombrePropio(recurso.distrito)} · {t('valoracion.totalValoraciones')}:{' '}
                {recurso.total_valoraciones}
              </p>

              {/* Los temas dicen POR QUÉ está donde está. */}
              {recurso.temas_frecuentes.length > 0 && (
                <ul className="mt-1 flex flex-wrap gap-1">
                  {recurso.temas_frecuentes.map((tema) => (
                    <li
                      key={tema}
                      className="rounded bg-superficie-contenedor px-1.5 py-0.5 text-xs text-sobre-superficie-variante"
                    >
                      {t(`valoracion.temas.${tema}`)}
                    </li>
                  ))}
                </ul>
              )}

              {/* Una media de dos valoraciones no es una media, y se dice. */}
              {!recurso.es_fiable && (
                <p
                  className="mt-1 inline-block rounded bg-terciario-contenedor px-1.5 py-0.5 text-xs text-sobre-terciario-contenedor"
                  title={t('valoracion.pocasValoracionesAyuda')}
                >
                  {t('valoracion.pocasValoraciones')}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Dato({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-sobre-superficie-variante uppercase">{etiqueta}</dt>
      <dd className="mt-0.5 font-titulo text-lg font-semibold text-sobre-superficie">{valor}</dd>
      {detalle && <p className="text-xs text-sobre-superficie-variante">{detalle}</p>}
    </div>
  );
}
