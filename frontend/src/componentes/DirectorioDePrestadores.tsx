/**
 * El directorio de prestadores REALES del valle.
 *
 * Son 162 negocios que existen: hospedajes, agencias de viaje y restaurantes
 * de las cuatro provincias de la ruta, cargados del **Directorio Nacional de
 * Prestadores de Servicios Turísticos Calificados** del MINCETUR, que el
 * Estado publica como datos abiertos.
 *
 * ## Lo que esta lista dice, y lo que no
 *
 * Dice que ese negocio **existe y está certificado por el Estado**, con su
 * RUC y su número de certificado para que cualquiera lo compruebe.
 *
 * **No** dice que tenga ningún trato con este proyecto, y la cabecera lo
 * declara. Tampoco se les inventa capacidad, precios ni horarios: eso no está
 * publicado, y ponerles un número sería exactamente lo que este proyecto dice
 * no hacer. Por eso aquí no se «pide» nada: se enseña a quién llamar.
 *
 * Los cinco proveedores de demostración siguen en su sección, que es donde se
 * puede enseñar el ciclo completo de solicitud y confirmación sin molestar a
 * nadie real.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';

import { listarPrestadores, type ProveedorPublico } from '@/servicios/api';

/** Cuántos se enseñan de golpe. El resto, al pulsar «ver más». */
const DE_ENTRADA = 12;

/**
 * Enlace a Google Maps buscando el negocio por su nombre y dirección.
 *
 * Se construye una búsqueda en vez de guardar coordenadas porque el directorio
 * del MINCETUR no las publica, y geocodificar 162 direcciones a ojo metería
 * errores que nadie detectaría: un hotel puesto tres calles más allá parece
 * un dato bueno.
 */
function enlaceAlMapa(prestador: ProveedorPublico): string {
  const busqueda = [prestador.nombre, prestador.direccion, prestador.distrito, 'Junín, Perú']
    .filter(Boolean)
    .join(', ');

  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(busqueda)}`;
}

/** Normaliza la web del directorio, que a veces viene sin `https://`. */
function enlaceALaWeb(pagina: string): string {
  return /^https?:\/\//i.test(pagina) ? pagina : `https://${pagina}`;
}

function Prestador({ prestador }: { prestador: ProveedorPublico }) {
  const { t } = useTranslation();

  return (
    <li className="rounded-lg border border-contorno-variante bg-superficie-contenedor-minimo p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-titulo font-semibold text-sobre-superficie">{prestador.nombre}</h3>

        {prestador.categoria && (
          <span className="shrink-0 rounded-full bg-secundario-contenedor px-2.5 py-0.5 text-xs font-semibold text-sobre-secundario-contenedor">
            {prestador.categoria}
          </span>
        )}
      </div>

      <p className="mt-1 text-sm text-sobre-superficie-variante">
        {[prestador.clase, prestador.distrito].filter(Boolean).join(' · ')}
      </p>

      {prestador.direccion && (
        <p className="mt-1 text-sm text-sobre-superficie-variante">{prestador.direccion}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {prestador.telefono && (
          <a href={`tel:${prestador.telefono}`} className="font-semibold text-primario underline">
            {prestador.telefono}
          </a>
        )}

        {prestador.pagina_web && (
          <a
            href={enlaceALaWeb(prestador.pagina_web)}
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-primario underline"
          >
            {t('coordinacion.suWeb')}
          </a>
        )}

        <a
          href={enlaceAlMapa(prestador)}
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-primario underline"
        >
          {t('coordinacion.verEnElMapa')}
        </a>
      </div>

      {/* El RUC y el certificado no son adorno: son lo que permite ir al
          directorio del MINCETUR y comprobar que esto es cierto. */}
      {prestador.ruc && (
        <p className="mt-2 text-[0.7rem] text-sobre-superficie-variante">
          {t('coordinacion.ruc')} {prestador.ruc}
          {prestador.certificado && ` · ${prestador.certificado}`}
        </p>
      )}
    </li>
  );
}

export function DirectorioDePrestadores() {
  const { t } = useTranslation();
  const [clase, establecerClase] = useState('');
  const [verTodos, establecerVerTodos] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['prestadores', clase],
    queryFn: () => listarPrestadores(clase || undefined),
  });

  if (isLoading) {
    return <p className="text-sobre-superficie-variante">{t('coordinacion.cargando')}</p>;
  }

  if (isError || !data) {
    return <p className="text-error">{t('coordinacion.error')}</p>;
  }

  const visibles = verTodos ? data : data.slice(0, DE_ENTRADA);

  return (
    <section className="mt-12" aria-label={t('coordinacion.directorioTitulo')}>
      <h2 className="font-titulo text-lg font-semibold text-sobre-superficie">
        {t('coordinacion.directorioTitulo')}
      </h2>

      {/* La honestidad va arriba, no en letra pequeña al final. */}
      <p className="mt-2 rounded-lg bg-secundario-contenedor px-4 py-3 text-sm text-sobre-secundario-contenedor">
        {t('coordinacion.directorioAviso', { total: data.length })}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(['', 'Hotel', 'Hostal', 'Operador de Turismo', 'Restaurante'] as const).map((opcion) => (
          <button
            key={opcion || 'todos'}
            type="button"
            onClick={() => {
              establecerClase(opcion);
              establecerVerTodos(false);
            }}
            className={
              'rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ' +
              (clase === opcion
                ? 'bg-primario text-sobre-primario'
                : 'bg-superficie-contenedor text-sobre-superficie-variante hover:bg-superficie-contenedor-alto')
            }
          >
            {opcion === '' ? t('coordinacion.todos') : opcion}
          </button>
        ))}
      </div>

      {data.length === 0 ? (
        <p className="mt-4 text-sobre-superficie-variante">{t('coordinacion.sinPrestadores')}</p>
      ) : (
        <>
          <ul className="mt-4 grid list-none gap-3 md:grid-cols-2 lg:grid-cols-3">
            {visibles.map((prestador) => (
              <Prestador key={prestador.id} prestador={prestador} />
            ))}
          </ul>

          {!verTodos && data.length > DE_ENTRADA && (
            <button
              type="button"
              onClick={() => establecerVerTodos(true)}
              className="mt-4 rounded-md border border-contorno-variante px-4 py-2 text-sm font-semibold text-sobre-superficie transition-colors hover:border-primario hover:text-primario"
            >
              {t('coordinacion.verTodos', { total: data.length })}
            </button>
          )}
        </>
      )}

      <p className="mt-4 text-xs text-sobre-superficie-variante">
        {t('coordinacion.directorioFuente')}
      </p>
    </section>
  );
}
