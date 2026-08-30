"""Los avisos que el backend le da al visitante, en forma traducible.

## Por qué un código y unos parámetros, y no una frase

Hasta la Fase 7 el backend redactaba los avisos en español y los mandaba ya
escritos. La interfaz solo los pintaba. Funcionaba, pero tenía dos problemas
que se destaparon al recorrer la aplicación en inglés:

1. **No se podían traducir.** Un visitante que usaba la aplicación en inglés
   veía la interfaz en inglés y estos avisos en español.
2. **Los plurales se concordaban a mano**, y se colaban errores como «1
   valoración(es)» o «1 de los 1 recursos valorados tienen».

Ahora un aviso viaja como ``{"codigo": "altitud", "parametros": {"metros":
3706}}`` y la interfaz lo redacta con i18next. Eso resuelve los dos problemas
a la vez: la traducción es obvia, y los plurales los resuelve i18next con sus
formas ``_one`` y ``_other``, que además funcionan en idiomas cuyas reglas de
plural no son las del español.

## La consecuencia menos evidente, y la más útil

**El aviso deja de ser texto y pasa a ser un dato.** Se puede contar cuántos
itinerarios avisaron de altitud sin buscar subcadenas, y una prueba puede
comprobar que se avisó de algo sin depender de cómo esté redactado. Antes,
cambiar una coma en un aviso rompía pruebas.

## Dónde vive cada mitad

- El **código y los parámetros** los produce el backend: son la decisión de
  «hay algo que decir aquí».
- La **frase** vive en ``frontend/src/i18n/es.json`` y ``en.json``, bajo la
  clave ``avisos``. Es la decisión de «cómo se dice».

Cada código nuevo necesita su entrada en los dos idiomas. La prueba
``test_todos_los_codigos_estan_traducidos`` lo comprueba, así que no se puede
olvidar sin que salte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Aviso:
    """Algo que hay que decirle al visitante, sin decidir todavía en qué idioma.

    Es inmutable (``frozen=True``) porque un aviso ya emitido describe algo que
    pasó: no tiene sentido cambiarlo después. Además así se puede meter en
    conjuntos y comparar sin sorpresas.
    """

    #: Identifica qué se está avisando. Va en minúsculas y con guiones bajos,
    #: como las claves de i18next, para que se lea igual en los dos lados.
    codigo: str

    #: Los datos que la frase necesita para completarse: metros, cuántos
    #: recursos, qué distritos. Nunca texto ya redactado —eso sería volver al
    #: problema— salvo nombres propios, que no se traducen.
    parametros: dict[str, Any] = field(default_factory=dict)

    def a_diccionario(self) -> dict[str, Any]:
        """Como lo manda el API."""
        return {"codigo": self.codigo, "parametros": self.parametros}


#: Todos los códigos que el backend puede emitir.
#:
#: Se declaran aquí y no se dejan sueltos por el código para que exista **una
#: lista** contra la que comprobar que las traducciones están completas. Sin
#: esto, añadir un aviso y olvidar su traducción no daría error: saldría la
#: clave cruda en pantalla, y probablemente nadie lo vería hasta la defensa.
#:
#: El comentario de cada uno dice cuándo se emite, porque el código solo no
#: siempre lo deja claro.
CODIGOS_CONOCIDOS: frozenset[str] = frozenset(
    {
        # --- Itinerario (servicios/ruteo.py) ---
        "altitud",  # una parada pasa del umbral de soroche
        "esfuerzo_del_dia",  # el día exige bastante subida acumulada
        "tramos_estimados",  # hubo tramos sin red vial cerca
        "sin_horario_ninguno",  # ninguno de los recursos publica horario
        "sin_horario_algunos",  # solo algunos lo publican
        "sin_horario_el_unico",  # solo se consideró uno, y no lo publica
        "sin_coordenadas",  # ninguna recomendación está georreferenciada
        "sin_itinerario_posible",  # no cabe nada con el tiempo y el dinero
        "resuelto_por_reglas",  # el optimizador no encontró solución
        "paradas_recortadas",  # se quitaron paradas al recalcular traslados
        "un_solo_recurso_al_alcance",  # desde ese origen solo hay uno
        "corto_por_presupuesto_agotado",  # se acabó el dinero de traslados
        "corto_por_presupuesto_insuficiente",  # no alcanza ni para el primero
        "paradas_omitidas_al_reordenar",  # las arrastradas ya no se recomiendan
        "ninguna_sigue_recomendada",  # ninguna de las arrastradas vale ya
        "por_encima_del_presupuesto",  # el orden elegido a mano se pasa
        # --- Recomendaciones (servicios/recomendador.py) ---
        "presupuesto_alcanza",  # para cuántas visitas da el presupuesto
        "presupuesto_no_alcanza",  # no llega ni para una visita
        "origen_sin_coordenadas",  # el distrito de origen no tiene recursos ubicados
        "ninguno_cumple_restricciones",  # nada pasa los filtros duros
        "ninguno_coincide_con_intereses",  # pasan los filtros pero no encajan
        # Motivos por los que un recurso quedó fuera. Se enseñan en la lista de
        # descartados, que es lo que hace auditable el filtrado: sin ella, el
        # visitante no sabe qué NO se le está enseñando ni por qué.
        "descarte_sin_coordenadas",
        "descarte_sin_validar",
        "descarte_fuera_de_alcance",
        # --- Afluencia esperada (ia/afluencia.py) ---
        # El motivo NO es decorativo: sin él, «va a haber mucha gente» es una
        # afirmación que el visitante tiene que creerse sin más, y eso es
        # justamente lo que la brecha 2 critica del proceso actual.
        "afluencia_feria_dominical",
        "afluencia_festividad",
        "afluencia_feriado_nacional",
        "afluencia_festividad_cercana",
        "afluencia_fin_de_semana",
        "afluencia_temporada_alta",
        "afluencia_dia_normal",
        # --- Tarjetas del tablero de indicadores (rutas/valoraciones.py) ---
        # El nombre, la brecha y la salvedad de cada indicador NO viajan: son
        # constantes por incremento y la interfaz las saca de su número. Aquí
        # solo están las partes que cambian con los datos.
        "detalle_indicador_1",
        "detalle_indicador_2",
        "detalle_indicador_3",
        "detalle_indicador_4",
        "detalle_indicador_5",
        "detalle_indicador_6",
        "sin_validacion_todavia",
        "sin_preferencias_todavia",
        "sin_itinerarios_todavia",
        # El «valor» de casi todos los indicadores es una cifra con símbolo
        # —«79.32 %»— que se lee igual en los dos idiomas. Estos dos no: son
        # frases, y por eso viajan como código.
        "valor_indicador_4",
        "valor_indicador_5",
        # --- Por qué NO se puede pedir un servicio (servicios/coordinacion.py) ---
        # Es lo que cierra la brecha 5: la capacidad del proveedor deja de ser
        # una llamada de teléfono y pasa a ser algo comprobable antes de pedir.
        "servicio_no_publicado",
        "supera_la_capacidad",
        "falta_antelacion",
        "no_atiende_ese_dia",
        "no_atiende_a_esa_hora",
        "sin_plazas_suficientes",
        # --- Errores que ve el visitante (rutas/*.py) ---
        # Viajan en el `detail` de la respuesta HTTP. Son códigos por el mismo
        # motivo que todo lo demás: «Correo o contraseña incorrectos» es de las
        # frases que más se leen en la aplicación, y estaba solo en español.
        "credenciales_incorrectas",
        "correo_ya_registrado",
        "ano_fuera_de_rango",
        "servicio_ajeno",
        "sin_itinerario",
        "sin_recurso",
        "sin_servicio",
        "sin_preferencia",
        "sin_solicitud",
        "falta_precio_acordado",
        "solo_proveedores_publican",
        "sin_ficha_de_proveedor",
        "ya_valoraste",
        "servicio_no_disponible",
        "catalogo_sin_validar",
        "proveedor_sin_ficha_asociada",
        # --- Tablero de evidencia (servicios/evidencia.py) ---
        "sin_valoraciones",  # todavía no hay ninguna
        "pocas_valoraciones",  # menos de las necesarias para fiarse
        "recursos_poco_fiables",  # recursos con muy pocas valoraciones
        "valoraciones_sin_comentario",  # solo puntuación, sin texto
        "todo_por_reglas",  # el sentimiento se analizó sin el modelo
    }
)


def comprobar_codigo(aviso: Aviso) -> Aviso:
    """Falla pronto si alguien inventa un código que no está declarado.

    Se llama al construir los avisos, no al enviarlos, para que el error
    aparezca en la prueba que lo produjo y no en una respuesta HTTP a medio
    camino. Un código sin declarar se vería en pantalla como la clave cruda
    —«avisos.lo_que_sea»— y eso es lo que hay que evitar.
    """
    if aviso.codigo not in CODIGOS_CONOCIDOS:
        raise ValueError(
            f"El código de aviso «{aviso.codigo}» no está en CODIGOS_CONOCIDOS. "
            "Añádelo ahí y añade su traducción en es.json y en.json."
        )

    return aviso


def aviso(codigo: str, **parametros: Any) -> Aviso:
    """Atajo para construir un aviso comprobado.

    Se usa así::

        avisos.append(aviso("altitud", metros=3706))

    en vez de::

        avisos.append(Aviso("altitud", {"metros": 3706}))

    Es la misma cosa, pero la primera forma se lee y se escribe mejor, y es la
    que aparece quince veces en `ruteo`.
    """
    return comprobar_codigo(Aviso(codigo, parametros))
