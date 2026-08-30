/**
 * Los seis indicadores del proyecto en un solo lugar (Incremento 6).
 *
 * Es lo que pide el plan de trabajo: *«el tablero del gestor muestra los
 * indicadores de los seis incrementos en un solo lugar»*.
 *
 * ## La salvedad se enseña, no se esconde
 *
 * Cada tarjeta muestra su valor **y lo que ese valor no dice**. Cuatro de los
 * seis indicadores miden algo distinto de lo que su nombre sugiere a primera
 * vista, porque el dato que haría falta para medir lo prometido no existe.
 *
 * Enseñar seis números sin esa letra pequeña sería exactamente el problema que
 * este proyecto dice combatir: presentar como hecho algo que es una
 * aproximación. Por eso la salvedad viaja **dentro del dato** que devuelve la
 * API, y no como una nota al pie que la interfaz pueda decidir no pintar.
 *
 * ## «Sin dato» no es cero
 *
 * Un indicador que todavía no se puede medir muestra «Sin dato todavía» y no un
 * cero. Cero es una medición; la ausencia de una es otra cosa.
 */
import { useTranslation } from 'react-i18next';

import type { IndicadorDelIncremento, TableroDeIndicadores } from '@/servicios/api';
import { redactarAviso } from '@/utilidades/avisos';

export default function SeisIndicadores({ tablero }: { tablero: TableroDeIndicadores }) {
  const { t, i18n } = useTranslation();

  return (
    <section aria-label={t('valoracion.seisIndicadores')}>
      <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {t('valoracion.seisIndicadores')}
      </h2>

      <ul className="mt-4 grid list-none gap-4 md:grid-cols-2">
        {tablero.indicadores.map((indicador) => (
          <TarjetaDeIndicador key={indicador.incremento} indicador={indicador} />
        ))}
      </ul>

      <p className="mt-4 text-xs text-sobre-superficie-variante">
        {t('valoracion.generadoEn', {
          fecha: new Date(tablero.generado_en).toLocaleString(
            i18n.language === 'en' ? 'en-GB' : 'es-PE',
          ),
        })}
      </p>
    </section>
  );
}

function TarjetaDeIndicador({ indicador }: { indicador: IndicadorDelIncremento }) {
  const { t } = useTranslation();

  // El nombre, la brecha y la salvedad NO vienen del backend: son constantes
  // por indicador y viven aquí, en los archivos de idioma. Mandarlas en cada
  // respuesta era mandar una constante en español que no se podía traducir.
  const nombre = t(`indicadores.${indicador.incremento}.nombre`);
  const brecha = t(`indicadores.${indicador.incremento}.brecha`);
  const salvedad = t(`indicadores.${indicador.incremento}.salvedad`);

  return (
    <li className="flex flex-col rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs tracking-wide text-sobre-superficie-variante uppercase">
            {t('valoracion.incremento', { numero: indicador.incremento })}
          </p>
          <h3 className="mt-0.5 font-titulo leading-snug font-semibold text-sobre-superficie">
            {nombre}
          </h3>
        </div>

        <span
          className={`shrink-0 rounded-full px-3 py-1 font-titulo text-lg font-bold ${
            indicador.hay_dato
              ? 'bg-primario text-sobre-primario'
              : 'bg-superficie-contenedor-alto text-sobre-superficie-variante'
          }`}
        >
          {/* El valor es una cifra —«79.32 %»— salvo en dos indicadores,
              donde es una frase y hay que redactarla. */}
          {!indicador.hay_dato
            ? t('valoracion.sinDato')
            : indicador.valor_traducible
              ? redactarAviso(t, indicador.valor_traducible)
              : indicador.valor}
        </span>
      </div>

      {indicador.detalle && (
        <p className="mt-2 text-sm text-sobre-superficie-variante">
          {redactarAviso(t, indicador.detalle)}
        </p>
      )}

      {/* Cuando no hay dato, el motivo sustituye al detalle: decir «—» sin
          explicar por qué deja al gestor pensando que algo se rompió. */}
      {!indicador.hay_dato && indicador.sin_dato_porque && (
        <p className="mt-2 text-sm text-sobre-superficie-variante">
          {redactarAviso(t, indicador.sin_dato_porque)}
        </p>
      )}

      <p className="mt-2 text-xs text-sobre-superficie-variante">
        {t('valoracion.brechaQueCierra')} {brecha}
      </p>

      {/* La letra pequeña, que aquí es lo importante. */}
      {salvedad && (
        <div className="mt-3 rounded border-l-4 border-terciario bg-superficie-contenedor px-3 py-2">
          <p className="text-xs font-semibold text-sobre-superficie-variante">
            {t('valoracion.loQueNoDice')}
          </p>
          <p className="mt-0.5 text-xs text-sobre-superficie-variante">{salvedad}</p>
        </div>
      )}
    </li>
  );
}
