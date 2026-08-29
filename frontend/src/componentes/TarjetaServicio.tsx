/**
 * Tarjeta de un servicio ofrecido por un proveedor (Incremento 5).
 *
 * **Todo lo que muestra está ahí para cerrar la brecha 5**: *la capacidad y
 * condiciones del proveedor no son verificables al decidir*. Hasta ahora,
 * saber si un taller podía atender a doce personas un sábado exigía llamar y
 * esperar respuesta. Aquí se lee de un vistazo:
 *
 * - a cuánta gente atiende,
 * - con cuánta antelación hay que avisar,
 * - qué días y a qué horas abre,
 * - cuánto cuesta, como rango y con su fecha.
 *
 * Y la marca de demostración, que no es un detalle: los proveedores sembrados
 * no existen, y quien mire esta tarjeta tiene que saberlo antes de fiarse de
 * un teléfono.
 */
import { useTranslation } from 'react-i18next';

import type { ServicioPublico } from '@/servicios/api';
import { formatearDuracion, formatearPrecio } from '@/utilidades/formato';

/** Icono de cada tipo de servicio. */
const ICONO_DE_TIPO: Record<string, string> = {
  transporte: '🚐',
  alimentacion: '🍽️',
  hospedaje: '🛏️',
  guiado: '🧭',
  taller: '🪵',
  artesania: '🧶',
};

/** Los siete días, en el orden de `date.weekday()`: 0 es lunes. */
const DIAS = [0, 1, 2, 3, 4, 5, 6];

interface Propiedades {
  servicio: ServicioPublico;
  /** Se llama cuando el visitante quiere pedirlo. */
  alPedir?: (servicio: ServicioPublico) => void;
}

export default function TarjetaServicio({ servicio, alPedir }: Propiedades) {
  const { t } = useTranslation();

  const diasQueAtiende = new Set(servicio.disponibilidad.map((tramo) => tramo.dia_semana));

  return (
    <li className="flex flex-col rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-titulo leading-snug font-semibold text-sobre-superficie">
            <span aria-hidden="true" className="mr-1.5">
              {ICONO_DE_TIPO[servicio.tipo] ?? '•'}
            </span>
            {servicio.nombre}
          </h3>
          <p className="mt-0.5 text-sm text-sobre-superficie-variante">
            {servicio.proveedor.nombre} · {servicio.proveedor.distrito}
          </p>
        </div>

        <span className="shrink-0 rounded-full bg-secundario-contenedor px-2.5 py-1 text-xs font-semibold text-sobre-secundario-contenedor">
          {t(`coordinacion.tipo.${servicio.tipo}`)}
        </span>
      </div>

      {/* La marca de demostración, como etiqueta corta.
          El texto completo va UNA VEZ arriba de la pantalla: repetir el párrafo
          entero en cada tarjeta lo convierte en ruido que nadie lee, y entonces
          el aviso deja de avisar. Aquí basta con la palabra y su explicación al
          pasar el ratón, porque lo que hay que evitar es que alguien marque un
          teléfono creyendo que contesta. */}
      {servicio.proveedor.es_demostracion && (
        <p
          className="mt-3 inline-flex w-fit items-center rounded border border-terciario bg-terciario-contenedor px-2 py-0.5 text-xs font-semibold text-sobre-terciario-contenedor"
          title={t('coordinacion.avisoDemostracion')}
        >
          {t('coordinacion.etiquetaDemostracion')}
        </p>
      )}

      {servicio.descripcion && (
        <p className="mt-3 text-sm text-sobre-superficie-variante">{servicio.descripcion}</p>
      )}

      {/* Las condiciones verificables: el corazón de la brecha 5. */}
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-sobre-superficie-variante">
        <li>{t('coordinacion.capacidad', { personas: servicio.capacidad_maxima })}</li>
        <li>{t('coordinacion.antelacion', { horas: servicio.antelacion_minima_horas })}</li>
        {servicio.duracion_min !== null && <li>{formatearDuracion(servicio.duracion_min)}</li>}
        {servicio.es_accesible && <li>{t('coordinacion.accesible')}</li>}
        {servicio.idiomas && <li>{servicio.idiomas}</li>}
      </ul>

      {/* Qué días atiende, como una fila de siete casillas. Es más rápido de
          leer que «lunes, martes, miércoles, jueves y viernes». */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-sobre-superficie-variante">{t('coordinacion.atiende')}</span>
        <div className="flex gap-1" role="img" aria-label={etiquetaDeDias(diasQueAtiende, t)}>
          {DIAS.map((dia) => (
            <span
              key={dia}
              aria-hidden="true"
              className={`flex h-6 w-6 items-center justify-center rounded text-xs font-semibold ${
                diasQueAtiende.has(dia)
                  ? 'bg-secundario text-sobre-secundario'
                  : 'bg-superficie-contenedor-alto text-sobre-superficie-variante'
              }`}
            >
              {t(`coordinacion.dias.${dia}`)}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-titulo font-semibold text-sobre-superficie">
            {formatearPrecio(servicio.precio_min_soles, servicio.precio_max_soles)}
          </p>
          <p className="text-xs text-sobre-superficie-variante">
            {t(`coordinacion.unidad.${servicio.unidad_precio}`)} · {servicio.fecha_referencia}
          </p>
        </div>

        {alPedir && (
          <button
            type="button"
            onClick={() => alPedir(servicio)}
            className="rounded-full bg-primario px-5 py-2 text-sm font-semibold text-sobre-primario transition-transform hover:-translate-y-0.5"
          >
            {t('coordinacion.pedir')}
          </button>
        )}
      </div>
    </li>
  );
}

/**
 * Los días que atiende, en palabras, para el lector de pantalla.
 *
 * Siete casillas de colores no significan nada sin vista, y la fila de días es
 * justo el dato que hace verificable la disponibilidad.
 */
function etiquetaDeDias(dias: Set<number>, t: (clave: string) => string): string {
  if (dias.size === 0) return t('coordinacion.sinHorarios');

  const nombres = DIAS.filter((dia) => dias.has(dia)).map((dia) => t(`coordinacion.dias.${dia}`));

  return `${t('coordinacion.atiende')}: ${nombres.join(', ')}`;
}
