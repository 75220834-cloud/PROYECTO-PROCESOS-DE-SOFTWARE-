/**
 * Pruebas de la traducción de los avisos del backend.
 *
 * La primera —`todos los códigos del backend tienen traducción`— es la que
 * sostiene todo lo demás. Sin ella, añadir un aviso en Python y olvidar su
 * frase no daría ningún error: saldría el código crudo en pantalla, y
 * probablemente nadie lo vería hasta la defensa.
 *
 * Lee la lista de códigos **del propio archivo de Python**. Duplicarla aquí
 * sería copiar la lista que se quiere comprobar, que no comprueba nada.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import i18n from 'i18next';
import { beforeEach, describe, expect, it } from 'vitest';

import instancia from '@/i18n';
import { redactarAviso, redactarAvisos, traducirError } from '@/utilidades/avisos';

/** Los códigos que el backend declara, leídos de `servicios/avisos.py`. */
function codigosDelBackend(): string[] {
  const ruta = join(process.cwd(), '..', 'backend', 'app', 'servicios', 'avisos.py');
  const fuente = readFileSync(ruta, 'utf8');

  const bloque = fuente.slice(
    fuente.indexOf('CODIGOS_CONOCIDOS'),
    fuente.indexOf('def comprobar_codigo'),
  );

  // Las entradas son `"codigo",` posiblemente con un comentario detrás.
  return [...bloque.matchAll(/^\s*"([a-z0-9_]+)",/gm)].map((coincidencia) => coincidencia[1]);
}

/**
 * Si una clave existe, contando las formas plurales.
 *
 * i18next guarda `pocas_valoraciones_one` y `pocas_valoraciones_other`, no
 * `pocas_valoraciones`. Un `exists()` a secas fallaría en todas las que llevan
 * plural, que son justo las que más importan.
 */
function tieneTraduccion(idioma: string, codigo: string): boolean {
  const paquete = i18n.getDataByLanguage(idioma)?.translation as
    Record<string, unknown> | undefined;
  const avisos = (paquete?.avisos ?? {}) as Record<string, unknown>;

  return codigo in avisos || `${codigo}_one` in avisos || `${codigo}_other` in avisos;
}

describe('las traducciones de los avisos', () => {
  const codigos = codigosDelBackend();

  it('lee la lista de códigos del backend, y no está vacía', () => {
    // Si el archivo de Python cambia de forma, esta prueba pasaría por vacía y
    // dejaría de comprobar nada. Este número lo impide.
    expect(codigos.length).toBeGreaterThan(50);
  });

  it.each(['es', 'en'])('todos los códigos del backend tienen traducción en %s', (idioma) => {
    const faltan = codigos.filter((codigo) => !tieneTraduccion(idioma, codigo));

    expect(faltan, `Faltan estas frases en ${idioma}.json, bajo «avisos»`).toEqual([]);
  });

  it('no hay traducciones de más', () => {
    // Una frase sin código que la use es código muerto en un archivo que ya es
    // largo. Se excluyen los consejos, que se anidan dentro de otras frases y
    // por eso no tienen código propio en el backend.
    const paquete = i18n.getDataByLanguage('es')?.translation as Record<string, unknown>;
    const avisos = Object.keys((paquete?.avisos ?? {}) as Record<string, unknown>);

    const sinRaiz = avisos
      .filter((clave) => clave !== 'consejo')
      .map((clave) => clave.replace(/_(one|other)$/, ''));

    const sobran = [...new Set(sinRaiz)].filter((clave) => !codigos.includes(clave));

    expect(sobran).toEqual([]);
  });
});

describe('redactarAviso', () => {
  beforeEach(async () => {
    await instancia.changeLanguage('es');
  });

  it('mete los parámetros en la frase', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'altitud',
      parametros: { metros: 3706 },
    });

    expect(frase).toContain('3706');
  });

  it('elige el singular cuando la cantidad es una', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'pocas_valoraciones',
      parametros: { cuantas: 1, minimo: 5 },
    });

    // Antes de este cambio, aquí salía «1 valoración(es)».
    expect(frase).toContain('1 valoración.');
    expect(frase).not.toContain('valoraciones');
  });

  it('elige el plural cuando son varias', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'pocas_valoraciones',
      parametros: { cuantas: 4, minimo: 5 },
    });

    expect(frase).toContain('4 valoraciones');
  });

  it('no confunde una referencia con la cantidad', () => {
    // «1 de 3 recursos» habla de UNO, aunque el 3 también sea un número. Sin
    // la lista de parámetros que no cuentan, salía «1 de los 3 recursos
    // valorados tienen», que es la falta de concordancia que se venía a
    // arreglar.
    const frase = redactarAviso(instancia.t, {
      codigo: 'recursos_poco_fiables',
      parametros: { cuantos: 1, total: 3, minimo: 5 },
    });

    expect(frase).toContain('1 de 3 recurso valorado tiene');
  });

  it('anida el consejo que corresponde', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'un_solo_recurso_al_alcance',
      parametros: { origen: 'Chupaca', consejo: 'usar_transporte' },
    });

    expect(frase).toContain('Chupaca');
    expect(frase).toContain('moverte en transporte en vez de a pie');
    // Si el anidado fallara, quedaría el marcador crudo en la frase.
    expect(frase).not.toContain('$t(');
  });

  it('nombra el día de la semana en vez de mandar el número', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'no_atiende_ese_dia',
      parametros: { dia: 1 },
    });

    expect(frase).toContain('martes');
    expect(frase).not.toContain('1');
  });

  it('devuelve el código, y no una clave rota, si falta la frase', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'esto_no_existe_y_no_deberia_pasar',
      parametros: {},
    });

    expect(frase).toBe('esto_no_existe_y_no_deberia_pasar');
    expect(frase).not.toContain('avisos.');
  });

  it('redacta una lista entera', () => {
    const frases = redactarAvisos(instancia.t, [
      { codigo: 'altitud', parametros: { metros: 3706 } },
      { codigo: 'sin_coordenadas', parametros: {} },
    ]);

    expect(frases).toHaveLength(2);
    expect(frases[1]).toContain('MINCETUR');
  });
});

describe('redactarAviso en inglés', () => {
  beforeEach(async () => {
    await instancia.changeLanguage('en');
  });

  it('traduce la misma frase', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'altitud',
      parametros: { metros: 3706 },
    });

    expect(frase).toContain('above sea level');
    expect(frase).not.toContain('sobre el nivel del mar');
  });

  it('acierta el plural inglés, que no siempre coincide con el español', () => {
    const una = redactarAviso(instancia.t, {
      codigo: 'supera_la_capacidad',
      parametros: { capacidad: 1, pedidas: 4 },
    });
    const varias = redactarAviso(instancia.t, {
      codigo: 'supera_la_capacidad',
      parametros: { capacidad: 8, pedidas: 12 },
    });

    expect(una).toContain('1 person ');
    expect(varias).toContain('8 people');
  });

  it('nombra el día en inglés', () => {
    const frase = redactarAviso(instancia.t, {
      codigo: 'no_atiende_ese_dia',
      parametros: { dia: 6 },
    });

    expect(frase).toContain('Sundays');
  });
});

describe('traducirError', () => {
  beforeEach(async () => {
    await instancia.changeLanguage('es');
  });

  it('traduce un código de error del backend', () => {
    const error = new Error('credenciales_incorrectas');

    expect(traducirError(instancia.t, error, 'respaldo')).toBe('Correo o contraseña incorrectos.');
  });

  it('junta todos los motivos cuando el error trae varios', () => {
    // Es lo que pasa al pedir un servicio no disponible: se devuelven TODOS
    // los motivos y no el primero, para no hacer arreglar el formulario a
    // trozos.
    const error = Object.assign(new Error('servicio_no_disponible'), {
      motivos: [
        { codigo: 'servicio_no_publicado', parametros: {} },
        { codigo: 'falta_antelacion', parametros: { horas: 48 } },
      ],
    });

    const frase = traducirError(instancia.t, error, 'respaldo');

    expect(frase).toContain('no está publicado');
    expect(frase).toContain('48 horas');
  });

  it('deja pasar los mensajes que ya vienen redactados', () => {
    // Los de Pydantic no son códigos nuestros y no hay clave que buscar.
    const error = new Error('El campo distrito_origen es obligatorio');

    expect(traducirError(instancia.t, error, 'respaldo')).toBe(
      'El campo distrito_origen es obligatorio',
    );
  });

  it('usa el respaldo cuando lo que llega no es un error', () => {
    expect(traducirError(instancia.t, null, 'algo salió mal')).toBe('algo salió mal');
  });
});
