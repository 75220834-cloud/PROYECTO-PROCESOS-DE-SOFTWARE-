/**
 * Resumen de una preferencia de viaje, en forma de etiquetas.
 *
 * Se reutiliza en la pantalla de confirmación y en «Mis viajes», para que lo
 * que el visitante pidió se muestre siempre igual.
 */
import { useTranslation } from 'react-i18next';

import type { PreferenciaPublica } from '@/servicios/api';
import { formatearFecha, formatearNombrePropio } from '@/utilidades/formato';

export function ResumenPreferencia({ preferencia }: { preferencia: PreferenciaPublica }) {
  const { t, i18n } = useTranslation();
  const idioma = i18n.resolvedLanguage?.slice(0, 2) ?? 'es';

  const etiquetas: string[] = [
    `${formatearFecha(preferencia.fecha_inicio, idioma)} – ${formatearFecha(preferencia.fecha_fin, idioma)}`,
    t('asistente.duracion', { dias: preferencia.duracion_dias }),
    formatearNombrePropio(preferencia.distrito_origen),
    `S/ ${Number(preferencia.presupuesto_soles).toLocaleString('es-PE')}`,
    t(`ritmo.${preferencia.ritmo}`),
    t(`movilidad.${preferencia.movilidad}`),
  ];

  if (preferencia.requiere_accesibilidad) {
    etiquetas.push(t('asistente.accesibilidad'));
  }

  return (
    <div>
      <ul className="flex flex-wrap gap-2">
        {etiquetas.map((etiqueta) => (
          <li
            key={etiqueta}
            className="rounded-full bg-superficie-contenedor px-3 py-1 text-sm text-sobre-superficie-variante"
          >
            {etiqueta}
          </li>
        ))}
      </ul>

      <ul className="mt-3 flex flex-wrap gap-2">
        {preferencia.intereses.map((interes) => (
          <li
            key={interes}
            className="rounded-full bg-terciario-contenedor px-3 py-1 text-sm font-medium text-sobre-terciario-contenedor"
          >
            {t(`intereses.${interes}`)}
          </li>
        ))}
      </ul>
    </div>
  );
}
