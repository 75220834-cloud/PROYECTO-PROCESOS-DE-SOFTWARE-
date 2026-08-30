"""Capa 2 — Predicción de afluencia por fecha y distrito.

Responde a «¿va a haber mucha gente ese día?». Importa por dos motivos: al
visitante le cambia el plan, y al gestor le sirve para repartir la carga.

**Las dos vías, como exige la regla de oro del proyecto:**

- ``USAR_MODELO_AFLUENCIA = True``  → LightGBM sobre datos históricos
- ``USAR_MODELO_AFLUENCIA = False`` → reglas de calendario explícitas

**Aviso que hay que poder defender:** hoy el modelo NO está entrenado, porque
no hay datos históricos cargados para el Valle del Mantaro. La función de
entrenamiento existe y funciona, pero se niega a entrenar con menos filas de
las mínimas y lo dice. Mientras tanto el sistema usa las reglas, que es
exactamente lo que el documento académico describe como control de riesgo: si
el modelo no supera su línea base, se entrega la alternativa.

Presentar un modelo entrenado con cuatro filas como si fuera predicción sería
mentir con más pasos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.ia.calendario import (
    dias_hasta_la_festividad_mas_cercana,
    es_feriado_nacional,
    festividades_en,
    hay_feria_dominical,
    temporada_de,
)
from app.servicios.avisos import Aviso, aviso


class NivelAfluencia(StrEnum):
    """Los tres niveles que ve el visitante.

    Se usan tres y no un número porque «esperamos 1 847 visitantes» sería
    falsa precisión: no hay datos para sostener esa cifra. «Mucha gente» sí se
    puede sostener con el calendario.
    """

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


#: Mínimo de filas históricas para que entrenar tenga sentido. Con menos, el
#: modelo memoriza en vez de aprender y su métrica engaña.
FILAS_MINIMAS_PARA_ENTRENAR = 120


@dataclass
class CaracteristicasDelDia:
    """Lo que el modelo mira de una fecha. Son datos de calendario, no de uso.

    Detalle importante para la defensa: **ninguna de estas características
    necesita histórico propio de la plataforma.** Todas salen del calendario o
    de fuentes públicas. Por eso este modelo se puede entrenar una vez y no
    necesita MLOps, al contrario que uno que aprendiera del comportamiento de
    los usuarios.
    """

    mes: int
    dia_de_la_semana: int  # 0 = lunes ... 6 = domingo
    es_fin_de_semana: bool
    es_feriado_nacional: bool
    hay_festividad_en_el_distrito: bool
    dias_hasta_la_festividad_mas_cercana: int
    hay_feria_dominical: bool
    temporada: str

    def como_vector(self) -> list[float]:
        """Convierte las características en números para LightGBM."""
        temporadas = {"baja": 0.0, "media": 1.0, "alta": 2.0}

        return [
            float(self.mes),
            float(self.dia_de_la_semana),
            float(self.es_fin_de_semana),
            float(self.es_feriado_nacional),
            float(self.hay_festividad_en_el_distrito),
            float(min(self.dias_hasta_la_festividad_mas_cercana, 60)),
            float(self.hay_feria_dominical),
            temporadas[self.temporada],
        ]

    @staticmethod
    def nombres_de_las_caracteristicas() -> list[str]:
        return [
            "mes",
            "dia_de_la_semana",
            "es_fin_de_semana",
            "es_feriado_nacional",
            "hay_festividad_en_el_distrito",
            "dias_hasta_la_festividad_mas_cercana",
            "hay_feria_dominical",
            "temporada",
        ]


def extraer_caracteristicas(dia: date, distrito: str) -> CaracteristicasDelDia:
    """Calcula las características de calendario de un día en un distrito."""
    festividades = festividades_en(dia, distrito)

    return CaracteristicasDelDia(
        mes=dia.month,
        dia_de_la_semana=dia.weekday(),
        es_fin_de_semana=dia.weekday() >= 5,
        es_feriado_nacional=es_feriado_nacional(dia),
        hay_festividad_en_el_distrito=bool(festividades),
        dias_hasta_la_festividad_mas_cercana=dias_hasta_la_festividad_mas_cercana(dia, distrito),
        hay_feria_dominical=hay_feria_dominical(dia, distrito),
        temporada=temporada_de(dia),
    )


@dataclass
class PrediccionAfluencia:
    """Nivel esperado de gente, con el motivo que lo justifica."""

    nivel: NivelAfluencia
    #: Por qué se espera ese nivel, como código y parámetros. La interfaz lo
    #: redacta en el idioma del visitante.
    motivo: Aviso
    #: Nombres de las fiestas activas ese día, si las hay.
    festividades: list[str] = field(default_factory=list)
    #: Cómo se calculó: 'modelo' o 'reglas'.
    calculado_por: str = "reglas"


# ---------------------------------------------------------------------------
# Vía B — la alternativa por reglas (es la que está activa hoy)
# ---------------------------------------------------------------------------


def predecir_afluencia_con_reglas(dia: date, distrito: str) -> PrediccionAfluencia:
    """Estima la afluencia con reglas de calendario explícitas.

    Las reglas, en orden de prioridad:

    1. **Alto** si hay festividad en el distrito, si es feriado nacional o si
       hay Feria Dominical. Son los días en que el valle se llena.
    2. **Medio** si es fin de semana, si falta menos de tres días para una
       fiesta, o si es temporada alta. La gente se mueve antes de la fecha.
    3. **Bajo** el resto.

    Cada nivel viene con su motivo. Decir «mucha gente» sin explicar por qué
    obliga al visitante a creerse el número, que es justo lo que la brecha 2
    critica del proceso actual.
    """
    caracteristicas = extraer_caracteristicas(dia, distrito)
    festividades = festividades_en(dia, distrito)
    nombres = [festividad.nombre for festividad in festividades]

    if caracteristicas.hay_feria_dominical:
        return PrediccionAfluencia(
            nivel=NivelAfluencia.ALTO,
            motivo=aviso("afluencia_feria_dominical"),
            festividades=nombres,
            calculado_por="reglas",
        )

    if caracteristicas.hay_festividad_en_el_distrito:
        return PrediccionAfluencia(
            nivel=NivelAfluencia.ALTO,
            # Los nombres de las fiestas no se traducen: son nombres propios.
            motivo=aviso("afluencia_festividad", fiestas=", ".join(nombres)),
            festividades=nombres,
            calculado_por="reglas",
        )

    if caracteristicas.es_feriado_nacional:
        return PrediccionAfluencia(
            nivel=NivelAfluencia.ALTO,
            motivo=aviso("afluencia_feriado_nacional"),
            festividades=nombres,
            calculado_por="reglas",
        )

    if caracteristicas.dias_hasta_la_festividad_mas_cercana <= 3:
        return PrediccionAfluencia(
            nivel=NivelAfluencia.MEDIO,
            motivo=aviso(
                "afluencia_festividad_cercana",
                dias=caracteristicas.dias_hasta_la_festividad_mas_cercana,
            ),
            calculado_por="reglas",
        )

    if caracteristicas.es_fin_de_semana:
        return PrediccionAfluencia(
            nivel=NivelAfluencia.MEDIO,
            motivo=aviso("afluencia_fin_de_semana"),
            calculado_por="reglas",
        )

    if caracteristicas.temporada == "alta":
        return PrediccionAfluencia(
            nivel=NivelAfluencia.MEDIO,
            motivo=aviso("afluencia_temporada_alta"),
            calculado_por="reglas",
        )

    return PrediccionAfluencia(
        nivel=NivelAfluencia.BAJO,
        motivo=aviso("afluencia_dia_normal"),
        calculado_por="reglas",
    )


# ---------------------------------------------------------------------------
# Vía A — el modelo LightGBM
# ---------------------------------------------------------------------------


@dataclass
class ResultadoEntrenamiento:
    """Qué pasó al intentar entrenar. Se guarda como evidencia."""

    se_entreno: bool
    filas_disponibles: int
    motivo: str
    error_medio_absoluto: float | None = None
    importancia_de_caracteristicas: dict[str, float] = field(default_factory=dict)


def entrenar_modelo_de_afluencia(
    ejemplos: list[tuple[CaracteristicasDelDia, int]],
) -> ResultadoEntrenamiento:
    """Entrena un LightGBM con los datos históricos disponibles.

    **Se niega a entrenar con pocos datos, a propósito.** Con menos de
    ``FILAS_MINIMAS_PARA_ENTRENAR`` filas, un modelo de árboles memoriza los
    ejemplos y su error de entrenamiento sale precioso mientras que su
    predicción real no vale nada. Devolver «no entrené y este es el motivo» es
    información útil; devolver un modelo inservible es peor que no tener nada.

    Cuando haya datos, este es el sitio donde se entrena. La decisión de
    aceptar o descartar el modelo se documenta en el cuaderno de
    ``backend/notebooks/``.
    """
    if len(ejemplos) < FILAS_MINIMAS_PARA_ENTRENAR:
        return ResultadoEntrenamiento(
            se_entreno=False,
            filas_disponibles=len(ejemplos),
            motivo=(
                f"Solo hay {len(ejemplos)} filas históricas y hacen falta al menos "
                f"{FILAS_MINIMAS_PARA_ENTRENAR}. Se usa la alternativa por reglas. "
                "El Ministerio de Cultura publica series de visitantes, pero apenas "
                "cubren recursos del Valle del Mantaro."
            ),
        )

    # A partir de aquí solo se llega con datos suficientes. Se importa LightGBM
    # dentro de la función para que arrancar la API no cargue la biblioteca si
    # nunca se va a entrenar.
    import lightgbm as lgb
    import numpy as np
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import train_test_split

    X = np.array([caracteristicas.como_vector() for caracteristicas, _ in ejemplos])
    y = np.array([visitantes for _, visitantes in ejemplos])

    X_entrenamiento, X_prueba, y_entrenamiento, y_prueba = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    modelo = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=15,  # pocas hojas: el conjunto es pequeño y se sobreajusta fácil
        random_state=42,
        verbose=-1,
    )
    modelo.fit(X_entrenamiento, y_entrenamiento)

    predicciones = modelo.predict(X_prueba)
    error = float(mean_absolute_error(y_prueba, predicciones))

    nombres = CaracteristicasDelDia.nombres_de_las_caracteristicas()
    importancias = dict(zip(nombres, (float(v) for v in modelo.feature_importances_), strict=True))

    return ResultadoEntrenamiento(
        se_entreno=True,
        filas_disponibles=len(ejemplos),
        motivo="Entrenado correctamente",
        error_medio_absoluto=error,
        importancia_de_caracteristicas=importancias,
    )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def predecir_afluencia(dia: date, distrito: str, usar_modelo: bool = True) -> PrediccionAfluencia:
    """Predice la afluencia por la vía que corresponda.

    Aunque ``usar_modelo`` sea True, si no hay modelo entrenado se recurre a
    las reglas. La configuración expresa una intención; la realidad de los
    datos manda. El campo ``calculado_por`` deja constancia de cuál se usó.
    """
    if usar_modelo and _hay_modelo_entrenado():
        return _predecir_con_modelo(dia, distrito)

    return predecir_afluencia_con_reglas(dia, distrito)


def _hay_modelo_entrenado() -> bool:
    """Comprueba si existe un modelo entrenado y guardado.

    Hoy devuelve siempre False: no hay datos históricos con los que entrenarlo.
    Cuando los haya, aquí se comprobará el archivo del modelo guardado.
    """
    return False


def _predecir_con_modelo(dia: date, distrito: str) -> PrediccionAfluencia:
    """Predice con el modelo entrenado. Todavía no alcanzable."""
    raise NotImplementedError(
        "No hay modelo de afluencia entrenado. Cargue datos históricos y "
        "ejecute el cuaderno de backend/notebooks/."
    )
