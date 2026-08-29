/**
 * Página del catálogo de recursos turísticos (Incremento 1).
 *
 * Reúne las cuatro piezas que pide la fase: buscador, filtros, listado en
 * tarjetas y mapa con los marcadores agrupados.
 *
 * Los filtros viven en la barra de direcciones (?provincia=JAUJA&texto=...).
 * Eso permite compartir un enlace con la búsqueda ya hecha y que el botón
 * "atrás" del navegador funcione como la gente espera.
 */
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { MapaRecursos } from '@/componentes/MapaRecursos';
import { TarjetaRecurso } from '@/componentes/TarjetaRecurso';
import {
  listarRecursos,
  obtenerFiltros,
  obtenerIndicadorCatalogo,
  obtenerRecursosDelMapa,
} from '@/servicios/api';
import { formatearCategoria, formatearNombrePropio } from '@/utilidades/formato';

const TAMANO_PAGINA = 24;

/** Espera a que el usuario deje de escribir antes de consultar a la API. */
function useValorRetardado<T>(valor: T, milisegundos = 350): T {
  const [retardado, establecerRetardado] = useState(valor);

  useEffect(() => {
    const temporizador = setTimeout(() => establecerRetardado(valor), milisegundos);
    return () => clearTimeout(temporizador);
  }, [valor, milisegundos]);

  return retardado;
}

export function Catalogo() {
  const { t } = useTranslation();
  const [parametros, establecerParametros] = useSearchParams();

  const provincia = parametros.get('provincia') ?? '';
  const distrito = parametros.get('distrito') ?? '';
  const categoria = parametros.get('categoria') ?? '';
  const soloValidados = parametros.get('solo_validados') === 'true';
  const pagina = Number(parametros.get('pagina') ?? 1);

  // El texto se lleva en estado local además de en la URL: así el campo
  // responde a cada tecla, pero la API solo se consulta cuando el usuario para.
  const [texto, establecerTexto] = useState(parametros.get('texto') ?? '');
  const textoRetardado = useValorRetardado(texto);

  function cambiarParametro(clave: string, valor: string) {
    const nuevos = new URLSearchParams(parametros);

    if (valor) {
      nuevos.set(clave, valor);
    } else {
      nuevos.delete(clave);
    }

    // Cualquier cambio de filtro devuelve a la primera página: quedarse en la
    // página 7 de un resultado que ahora tiene 2 mostraría una lista vacía.
    if (clave !== 'pagina') nuevos.delete('pagina');

    establecerParametros(nuevos);
  }

  // El texto retardado se sincroniza con la URL por separado.
  useEffect(() => {
    const actual = parametros.get('texto') ?? '';
    if (textoRetardado !== actual) {
      cambiarParametro('texto', textoRetardado);
    }
    // Solo debe reaccionar al texto retardado, no a cada cambio de parámetros.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textoRetardado]);

  const filtros = {
    provincia: provincia || undefined,
    distrito: distrito || undefined,
    categoria: categoria || undefined,
    texto: textoRetardado || undefined,
  };

  const { data: opciones } = useQuery({ queryKey: ['filtros'], queryFn: obtenerFiltros });

  const { data: indicador } = useQuery({
    queryKey: ['indicador-catalogo'],
    queryFn: obtenerIndicadorCatalogo,
    retry: false, // si nunca se validó, no tiene sentido reintentar
  });

  const {
    data: paginaDeRecursos,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['recursos', filtros, soloValidados, pagina],
    queryFn: () =>
      listarRecursos({
        ...filtros,
        solo_validados: soloValidados,
        pagina,
        tamano_pagina: TAMANO_PAGINA,
      }),
  });

  const { data: mapa } = useQuery({
    queryKey: ['recursos-mapa', filtros],
    queryFn: () => obtenerRecursosDelMapa(filtros),
  });

  const totalPaginas = paginaDeRecursos
    ? Math.max(1, Math.ceil(paginaDeRecursos.total / TAMANO_PAGINA))
    : 1;

  const clasesDeCampo =
    'w-full rounded-md border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2 text-sm text-sobre-superficie transition-colors focus:border-primario focus:outline-2 focus:outline-offset-1 focus:outline-primario';

  return (
    <main className="mx-auto max-w-contenido px-4 py-10 sm:px-6">
      <header>
        <h1 className="font-titulo text-3xl font-extrabold text-sobre-superficie">
          {t('catalogo.titulo')}
        </h1>
        <p className="mt-2 max-w-2xl text-sobre-superficie-variante">{t('catalogo.subtitulo')}</p>

        {/* Indicador del Incremento 1, a la vista. No es un adorno: es la
            evidencia de que el catálogo está validado y con qué calidad. */}
        {indicador && (
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(
              [
                ['catalogo.indicador_total', indicador.total_recursos, ''],
                [
                  'catalogo.indicador_validados',
                  indicador.validados,
                  `${indicador.porcentaje_validado} %`,
                ],
                ['catalogo.indicador_con_coordenadas', indicador.con_coordenadas, ''],
                [
                  'catalogo.indicador_vigentes',
                  indicador.vigentes,
                  `${indicador.porcentaje_vigente} %`,
                ],
              ] as const
            ).map(([clave, valor, porcentaje]) => (
              <div
                key={clave}
                className="rounded-lg border border-contorno-variante bg-superficie-contenedor p-4"
              >
                <dt className="text-xs text-sobre-superficie-variante">{t(clave)}</dt>
                <dd className="mt-1 font-titulo text-2xl font-bold text-primario">
                  {valor}
                  {porcentaje && (
                    <span className="ml-1.5 text-sm font-normal text-sobre-superficie-variante">
                      {porcentaje}
                    </span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </header>

      {/* ------------------------------------------------------------------
          Filtros
          ------------------------------------------------------------------ */}
      <section
        aria-label={t('catalogo.filtros')}
        className="mt-8 grid gap-3 rounded-lg border border-contorno-variante bg-superficie-contenedor-bajo p-4 md:grid-cols-4"
      >
        <label className="block">
          <span className="mb-1 block text-xs font-semibold text-sobre-superficie-variante">
            {t('catalogo.buscar')}
          </span>
          <input
            type="search"
            value={texto}
            onChange={(evento) => establecerTexto(evento.target.value)}
            placeholder={t('catalogo.buscar_ejemplo')}
            className={clasesDeCampo}
          />
        </label>

        {(
          [
            ['provincia', provincia, opciones?.provincias ?? []],
            ['distrito', distrito, opciones?.distritos ?? []],
            ['categoria', categoria, opciones?.categorias ?? []],
          ] as const
        ).map(([clave, valor, listaDeOpciones]) => (
          <label key={clave} className="block">
            <span className="mb-1 block text-xs font-semibold text-sobre-superficie-variante">
              {t(`catalogo.${clave}`)}
            </span>
            <select
              value={valor}
              onChange={(evento) => cambiarParametro(clave, evento.target.value)}
              className={clasesDeCampo}
            >
              <option value="">{t('catalogo.todas')}</option>
              {listaDeOpciones.map((opcion) => (
                <option key={opcion} value={opcion}>
                  {clave === 'categoria'
                    ? formatearCategoria(opcion)
                    : formatearNombrePropio(opcion)}
                </option>
              ))}
            </select>
          </label>
        ))}

        <label className="flex items-center gap-2 md:col-span-4">
          <input
            type="checkbox"
            checked={soloValidados}
            onChange={(evento) =>
              cambiarParametro('solo_validados', evento.target.checked ? 'true' : '')
            }
            className="h-4 w-4 accent-[var(--color-primario)]"
          />
          <span className="text-sm text-sobre-superficie-variante">
            {t('catalogo.solo_validados')}
          </span>
        </label>
      </section>

      {/* ------------------------------------------------------------------
          Mapa
          ------------------------------------------------------------------ */}
      <section aria-label={t('catalogo.mapa_etiqueta')} className="mt-8">
        <div className="h-[26rem] overflow-hidden rounded-lg border border-contorno-variante">
          {mapa && <MapaRecursos rasgos={mapa.features} />}
        </div>

        <p className="mt-2 text-xs text-sobre-superficie-variante">
          {t('catalogo.aviso_mapa', { cantidad: mapa?.features.length ?? 0 })}
        </p>
      </section>

      {/* ------------------------------------------------------------------
          Listado
          ------------------------------------------------------------------ */}
      <section aria-label={t('catalogo.listado')} className="mt-10">
        {isLoading && <p className="text-sobre-superficie-variante">{t('catalogo.cargando')}</p>}

        {isError && <p className="text-error">{t('catalogo.error')}</p>}

        {paginaDeRecursos && (
          <>
            <p className="text-sm text-sobre-superficie-variante">
              {t('catalogo.resultados', { total: paginaDeRecursos.total })}
            </p>

            {paginaDeRecursos.elementos.length === 0 ? (
              <p className="mt-8 rounded-lg border border-contorno-variante bg-superficie-contenedor p-8 text-center text-sobre-superficie-variante">
                {t('catalogo.sin_resultados')}
              </p>
            ) : (
              <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {paginaDeRecursos.elementos.map((recurso, indice) => (
                  <TarjetaRecurso key={recurso.id} recurso={recurso} indice={indice} />
                ))}
              </ul>
            )}

            {totalPaginas > 1 && (
              <nav
                aria-label={t('catalogo.paginacion')}
                className="mt-8 flex items-center justify-center gap-3"
              >
                <button
                  type="button"
                  disabled={pagina <= 1}
                  onClick={() => cambiarParametro('pagina', String(pagina - 1))}
                  className="rounded-md border border-contorno-variante px-4 py-2 text-sm font-semibold text-sobre-superficie transition-colors enabled:hover:border-primario enabled:hover:text-primario disabled:opacity-40"
                >
                  {t('catalogo.anterior')}
                </button>

                <span className="text-sm text-sobre-superficie-variante">
                  {t('catalogo.pagina_de', { pagina, total: totalPaginas })}
                </span>

                <button
                  type="button"
                  disabled={pagina >= totalPaginas}
                  onClick={() => cambiarParametro('pagina', String(pagina + 1))}
                  className="rounded-md border border-contorno-variante px-4 py-2 text-sm font-semibold text-sobre-superficie transition-colors enabled:hover:border-primario enabled:hover:text-primario disabled:opacity-40"
                >
                  {t('catalogo.siguiente')}
                </button>
              </nav>
            )}
          </>
        )}
      </section>
    </main>
  );
}
