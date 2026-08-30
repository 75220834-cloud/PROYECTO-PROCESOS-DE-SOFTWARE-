/**
 * Asistente de preferencias del viaje, en seis pasos (Incremento 2).
 *
 * Cierra la brecha 3: *las preferencias del visitante no se registran ni se
 * usan sistemáticamente*.
 *
 * Dos decisiones de diseño que conviene poder explicar:
 *
 * 1. **Un paso a la vez.** Un formulario con dieciocho campos a la vez
 *    intimida y se abandona. Seis preguntas cortas, con barra de progreso y
 *    botón de volver, se contestan.
 *
 * 2. **No hace falta cuenta.** El asistente se completa entero sin
 *    registrarse. Solo al final se ofrece crear una cuenta para guardar el
 *    viaje. Es la regla del proyecto, y está probada en el backend.
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { guardarPreferenciaAnonima, useSesion } from '@/hooks/useSesion';
import {
  guardarPreferencia,
  obtenerOpcionesDelAsistente,
  type DatosPreferencia,
} from '@/servicios/api';
import { formatearNombrePropio } from '@/utilidades/formato';
import { traducirError } from '@/utilidades/avisos';

const TOTAL_DE_PASOS = 6;

/** Devuelve la fecha de hoy más los días indicados, en formato AAAA-MM-DD. */
function fechaRelativa(dias: number): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + dias);
  return fecha.toISOString().slice(0, 10);
}

/** Respuestas por omisión: un viaje de fin de semana dentro de una semana. */
function respuestasIniciales(idioma: string): DatosPreferencia {
  return {
    fecha_inicio: fechaRelativa(7),
    fecha_fin: fechaRelativa(9),
    distrito_origen: '',
    presupuesto_soles: '200',
    intereses: [],
    movilidad: 'combinado',
    requiere_accesibilidad: false,
    ritmo: 'moderado',
    idioma,
  };
}

export function AsistentePreferencias() {
  const { t, i18n } = useTranslation();
  const navegar = useNavigate();
  const { token, usuario } = useSesion();

  const [paso, establecerPaso] = useState(1);
  const [respuestas, establecerRespuestas] = useState<DatosPreferencia>(() =>
    respuestasIniciales(i18n.resolvedLanguage?.slice(0, 2) ?? 'es'),
  );

  const { data: opciones } = useQuery({
    queryKey: ['opciones-asistente'],
    queryFn: obtenerOpcionesDelAsistente,
  });

  const guardar = useMutation({
    mutationFn: () => guardarPreferencia(respuestas, token),
    onSuccess: (preferencia) => {
      // Sin cuenta, el identificador se conserva en el navegador: es lo único
      // que permite recuperar el viaje y reclamarlo si luego se registra.
      if (preferencia.usuario_id === null) {
        guardarPreferenciaAnonima(preferencia.id);
      }
      navegar(`/preferencias/${preferencia.id}`);
    },
  });

  function cambiar<C extends keyof DatosPreferencia>(campo: C, valor: DatosPreferencia[C]) {
    establecerRespuestas((actuales) => ({ ...actuales, [campo]: valor }));
  }

  function alternarInteres(interes: string) {
    establecerRespuestas((actuales) => ({
      ...actuales,
      intereses: actuales.intereses.includes(interes)
        ? actuales.intereses.filter((otro) => otro !== interes)
        : [...actuales.intereses, interes],
    }));
  }

  /**
   * Valida el paso actual y devuelve el mensaje de error, o null si está bien.
   *
   * La validación se repite en el backend: esta es para dar respuesta
   * inmediata al visitante, no para proteger los datos. Fiarse solo de la
   * validación del navegador sería un fallo de seguridad, porque se puede
   * saltar con una petición directa a la API.
   */
  const errorDelPaso = useMemo((): string | null => {
    switch (paso) {
      case 1: {
        if (!respuestas.fecha_inicio || !respuestas.fecha_fin) {
          return t('asistente.error_fechas_incompletas');
        }
        if (respuestas.fecha_fin < respuestas.fecha_inicio) {
          return t('asistente.error_fechas_invertidas');
        }
        return null;
      }
      case 2:
        return respuestas.distrito_origen ? null : t('asistente.error_distrito');
      case 3: {
        const monto = Number(respuestas.presupuesto_soles);
        return Number.isFinite(monto) && monto >= 0 ? null : t('asistente.error_presupuesto');
      }
      case 4:
        return respuestas.intereses.length > 0 ? null : t('asistente.error_intereses');
      default:
        return null;
    }
  }, [paso, respuestas, t]);

  const duracion =
    respuestas.fecha_inicio &&
    respuestas.fecha_fin &&
    respuestas.fecha_fin >= respuestas.fecha_inicio
      ? Math.round(
          (new Date(respuestas.fecha_fin).getTime() - new Date(respuestas.fecha_inicio).getTime()) /
            86_400_000,
        ) + 1
      : 0;

  const clasesDeCampo =
    'w-full rounded-md border border-contorno-variante bg-superficie-contenedor-minimo px-3 py-2.5 text-sobre-superficie transition-colors focus:border-primario focus:outline-2 focus:outline-offset-1 focus:outline-primario';

  const clasesDeTarjeta = (seleccionada: boolean) =>
    'rounded-lg border-2 p-4 text-left transition-all ' +
    (seleccionada
      ? 'border-primario bg-primario-suave text-sobre-superficie shadow-suave'
      : 'border-contorno-variante bg-superficie-contenedor-minimo text-sobre-superficie-variante hover:border-primario');

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      {/* Barra de progreso -------------------------------------------------- */}
      <div>
        <div className="flex items-center justify-between text-sm">
          <span className="font-semibold text-primario">
            {t('asistente.paso_de', { paso, total: TOTAL_DE_PASOS })}
          </span>
          <span className="text-sobre-superficie-variante">
            {Math.round((paso / TOTAL_DE_PASOS) * 100)} %
          </span>
        </div>

        <div
          className="mt-2 h-2 overflow-hidden rounded-full bg-superficie-contenedor-alto"
          role="progressbar"
          aria-valuenow={paso}
          aria-valuemin={1}
          aria-valuemax={TOTAL_DE_PASOS}
          aria-label={t('asistente.progreso')}
        >
          {/* El ancho se fija con CSS, no con una animacion de JavaScript.
              framer-motion animaria desde el ancho que el elemento tenga al
              montarse -- que sin ancho declarado es el 100 % -- y la barra
              mostraria el paso 1 como si estuviera completa hasta que la
              animacion terminase. En una pestana en segundo plano, o con el
              movimiento reducido activado, no terminaria nunca. */}
          <div
            className="h-full rounded-full bg-primario transition-[width] duration-300 ease-out"
            style={{ width: `${(paso / TOTAL_DE_PASOS) * 100}%` }}
          />
        </div>
      </div>

      {/* Paso actual --------------------------------------------------------
          Solo se anima la ENTRADA, sin AnimatePresence ni animacion de salida.

          Con AnimatePresence en mode="wait", el paso nuevo no se monta hasta
          que el anterior termina de salir. Si esa animacion no llega a
          ejecutarse -- pestana en segundo plano, movimiento reducido, un
          navegador que limita el pintado -- el visitante se queda mirando el
          paso anterior aunque ya haya avanzado. La interfaz no puede depender
          de que una animacion decorativa termine.

          La clave `key={paso}` hace que React monte una seccion nueva en cada
          paso, y por tanto que la animacion de entrada se repita. */}
      <motion.section
        key={paso}
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.25 }}
        className="mt-10 min-h-[22rem]"
      >
        {/* ---- Paso 1: fechas ---- */}
        {paso === 1 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso1_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso1_ayuda')}</p>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold">
                  {t('asistente.fecha_inicio')}
                </span>
                <input
                  type="date"
                  value={respuestas.fecha_inicio}
                  onChange={(evento) => cambiar('fecha_inicio', evento.target.value)}
                  className={clasesDeCampo}
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold">
                  {t('asistente.fecha_fin')}
                </span>
                <input
                  type="date"
                  value={respuestas.fecha_fin}
                  min={respuestas.fecha_inicio}
                  onChange={(evento) => cambiar('fecha_fin', evento.target.value)}
                  className={clasesDeCampo}
                />
              </label>
            </div>

            {duracion > 0 && (
              <p className="mt-5 inline-block rounded-full bg-secundario-contenedor px-3 py-1.5 text-sm text-sobre-secundario-contenedor">
                {t('asistente.duracion', { dias: duracion })}
              </p>
            )}
          </>
        )}

        {/* ---- Paso 2: distrito de origen ---- */}
        {paso === 2 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso2_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso2_ayuda')}</p>

            <label className="mt-8 block">
              <span className="mb-1.5 block text-sm font-semibold">{t('asistente.distrito')}</span>
              <select
                value={respuestas.distrito_origen}
                onChange={(evento) => cambiar('distrito_origen', evento.target.value)}
                className={clasesDeCampo}
              >
                <option value="">{t('asistente.elige_distrito')}</option>
                {(opciones?.distritos ?? []).map((distrito) => (
                  <option key={distrito} value={distrito}>
                    {formatearNombrePropio(distrito)}
                  </option>
                ))}
              </select>
            </label>

            <p className="mt-3 text-xs text-sobre-superficie-variante">
              {t('asistente.distritos_del_catalogo', {
                cantidad: opciones?.distritos.length ?? 0,
              })}
            </p>
          </>
        )}

        {/* ---- Paso 3: presupuesto ---- */}
        {paso === 3 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso3_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso3_ayuda')}</p>

            <p className="mt-10 text-center font-titulo text-5xl font-extrabold text-primario">
              S/ {Number(respuestas.presupuesto_soles).toLocaleString('es-PE')}
            </p>

            <input
              type="range"
              min={0}
              max={2000}
              step={10}
              value={respuestas.presupuesto_soles}
              onChange={(evento) => cambiar('presupuesto_soles', evento.target.value)}
              aria-label={t('asistente.presupuesto')}
              className="mt-8 w-full accent-[var(--color-primario)]"
            />

            <div className="mt-2 flex justify-between text-xs text-sobre-superficie-variante">
              <span>S/ 0</span>
              <span>S/ 1000</span>
              <span>S/ 2000</span>
            </div>

            <p className="mt-6 text-sm text-sobre-superficie-variante">
              {t('asistente.presupuesto_aviso')}
            </p>
          </>
        )}

        {/* ---- Paso 4: intereses ---- */}
        {paso === 4 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso4_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso4_ayuda')}</p>

            <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {(opciones?.intereses ?? []).map((interes) => {
                const seleccionado = respuestas.intereses.includes(interes);
                return (
                  <button
                    key={interes}
                    type="button"
                    onClick={() => alternarInteres(interes)}
                    aria-pressed={seleccionado}
                    className={clasesDeTarjeta(seleccionado) + ' text-center'}
                  >
                    <span className="block text-sm font-semibold">{t(`intereses.${interes}`)}</span>
                  </button>
                );
              })}
            </div>

            <p className="mt-5 text-sm text-sobre-superficie-variante">
              {t('asistente.intereses_elegidos', { cantidad: respuestas.intereses.length })}
            </p>
          </>
        )}

        {/* ---- Paso 5: movilidad ---- */}
        {paso === 5 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso5_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso5_ayuda')}</p>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {(opciones?.movilidades ?? []).map((movilidad) => (
                <button
                  key={movilidad}
                  type="button"
                  onClick={() => cambiar('movilidad', movilidad as DatosPreferencia['movilidad'])}
                  aria-pressed={respuestas.movilidad === movilidad}
                  className={clasesDeTarjeta(respuestas.movilidad === movilidad)}
                >
                  <span className="block font-semibold">{t(`movilidad.${movilidad}`)}</span>
                  <span className="mt-1 block text-sm opacity-80">
                    {t(`movilidad.${movilidad}_ayuda`)}
                  </span>
                </button>
              ))}
            </div>

            <label className="mt-6 flex items-start gap-3 rounded-lg border border-contorno-variante bg-superficie-contenedor p-4">
              <input
                type="checkbox"
                checked={respuestas.requiere_accesibilidad}
                onChange={(evento) => cambiar('requiere_accesibilidad', evento.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-primario)]"
              />
              <span>
                <span className="block text-sm font-semibold">{t('asistente.accesibilidad')}</span>
                <span className="mt-0.5 block text-xs text-sobre-superficie-variante">
                  {t('asistente.accesibilidad_ayuda')}
                </span>
              </span>
            </label>
          </>
        )}

        {/* ---- Paso 6: ritmo ---- */}
        {paso === 6 && (
          <>
            <h1 className="font-titulo text-2xl font-bold text-sobre-superficie sm:text-3xl">
              {t('asistente.paso6_titulo')}
            </h1>
            <p className="mt-2 text-sobre-superficie-variante">{t('asistente.paso6_ayuda')}</p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {(opciones?.ritmos ?? []).map((ritmo) => (
                <button
                  key={ritmo}
                  type="button"
                  onClick={() => cambiar('ritmo', ritmo as DatosPreferencia['ritmo'])}
                  aria-pressed={respuestas.ritmo === ritmo}
                  className={clasesDeTarjeta(respuestas.ritmo === ritmo)}
                >
                  <span className="block font-semibold">{t(`ritmo.${ritmo}`)}</span>
                  <span className="mt-1 block text-sm opacity-80">{t(`ritmo.${ritmo}_ayuda`)}</span>
                </button>
              ))}
            </div>

            {!usuario && (
              <p className="mt-8 rounded-lg bg-superficie-contenedor p-4 text-sm text-sobre-superficie-variante">
                {t('asistente.sin_cuenta_aviso')}
              </p>
            )}
          </>
        )}
      </motion.section>

      {/* Errores y navegación ----------------------------------------------- */}
      {errorDelPaso && (
        <p role="alert" className="mt-4 text-sm text-error">
          {errorDelPaso}
        </p>
      )}

      {guardar.isError && (
        <p role="alert" className="mt-4 text-sm text-error">
          {traducirError(t, guardar.error, t('preferencia.error'))}
        </p>
      )}

      <nav className="mt-8 flex items-center justify-between gap-4">
        {paso > 1 ? (
          <button
            type="button"
            onClick={() => establecerPaso((actual) => actual - 1)}
            className="rounded-md border border-contorno-variante px-5 py-2.5 font-semibold text-sobre-superficie transition-colors hover:border-primario hover:text-primario"
          >
            {t('asistente.atras')}
          </button>
        ) : (
          <Link
            to="/"
            className="rounded-md px-5 py-2.5 font-semibold text-sobre-superficie-variante transition-colors hover:text-primario"
          >
            {t('asistente.cancelar')}
          </Link>
        )}

        {paso < TOTAL_DE_PASOS ? (
          <button
            type="button"
            disabled={errorDelPaso !== null}
            onClick={() => establecerPaso((actual) => actual + 1)}
            className="rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario shadow-suave transition-transform enabled:hover:-translate-y-0.5 disabled:opacity-40"
          >
            {t('asistente.siguiente')}
          </button>
        ) : (
          <button
            type="button"
            disabled={guardar.isPending}
            onClick={() => guardar.mutate()}
            className="rounded-md bg-primario px-6 py-2.5 font-semibold text-sobre-primario shadow-elevada transition-transform enabled:hover:-translate-y-0.5 disabled:opacity-60"
          >
            {guardar.isPending ? t('asistente.guardando') : t('asistente.generar')}
          </button>
        )}
      </nav>
    </main>
  );
}
