"""Pruebas de los endpoints de valoración y del tablero de evidencia.

Cubren las cuatro comprobaciones que exige el plan de trabajo para el
Incremento 6:

1. Una valoración positiva y una negativa se clasifican correctamente.
2. El tablero del gestor muestra los seis indicadores.
3. Con ``USAR_MODELO_SENTIMIENTO = False`` sigue funcionando.
4. Las pruebas pasan.

Todo se prueba con la vía por reglas: es la que tiene que funcionar en
cualquier máquina, y hacer que la suite dependa de un modelo de cientos de
megas la volvería frágil justo donde importa.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.configuracion import Configuracion, obtener_configuracion
from app.main import aplicacion
from app.modelos.catalogo import RecursoTuristico
from app.modelos.itinerario import Itinerario
from app.modelos.preferencias import PreferenciaViaje
from app.modelos.valoracion import Valoracion
from app.servicios.evidencia import (
    MINIMO_PARA_FIARSE,
    calcular_cobertura,
    guardar_instantanea,
    obtener_instantaneas,
    resumir_evidencia,
)

HOY = date(2026, 9, 12)


@pytest.fixture
def sin_modelo():
    """Fuerza la vía por reglas durante toda la prueba.

    Es también la comprobación del plan: «con USAR_MODELO_SENTIMIENTO = False
    sigue funcionando». Todas las pruebas de este archivo la usan.
    """
    aplicacion.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
        usar_modelo_sentimiento=False
    )
    yield
    aplicacion.dependency_overrides.pop(obtener_configuracion, None)


@pytest.fixture
def cliente(sesion: Session, sin_modelo) -> TestClient:
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


@pytest.fixture
def itinerario(sesion: Session) -> Itinerario:
    """Un itinerario sin dueño, como el que arma alguien sin cuenta."""
    preferencia = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=HOY,
        fecha_fin=HOY + timedelta(days=1),
        distrito_origen="HUANCAYO",
        presupuesto_soles=Decimal("400.00"),
        intereses=["artesania"],
        movilidad="transporte_publico",
        requiere_accesibilidad=False,
        idioma="es",
        ritmo="moderado",
    )
    sesion.add(preferencia)
    sesion.flush()

    fila = Itinerario(
        preferencia_id=preferencia.id,
        titulo="Un día en Huancayo",
        fecha=HOY,
        estado="guardado",
        generado_por="modelo",
    )
    sesion.add(fila)
    sesion.commit()
    sesion.refresh(fila)

    return fila


@pytest.fixture
def recursos(sesion: Session) -> list[RecursoTuristico]:
    """Tres recursos para poder probar el ranquin."""
    creados = []

    for indice, nombre in enumerate(["Taller de Cochas", "Convento", "Mirador"], start=1):
        recurso = RecursoTuristico(
            codigo_mincetur=f"98000{indice}",
            nombre=nombre,
            provincia="Huancayo",
            distrito="EL TAMBO",
            categoria="2. MANIFESTACIONES CULTURALES",
            esta_validado=True,
            esta_vigente=True,
        )
        sesion.add(recurso)
        creados.append(recurso)

    sesion.commit()
    return creados


def valorar(cliente: TestClient, itinerario_id: int, **extra) -> dict:
    """Envía una valoración y devuelve el cuerpo, fallando con el texto si no va."""
    cuerpo = {"itinerario_id": itinerario_id, "puntuacion": 5}
    cuerpo.update(extra)

    respuesta = cliente.post("/api/valoraciones", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text

    return respuesta.json()


# ---------------------------------------------------------------------------
# Valorar — la comprobación central del plan
# ---------------------------------------------------------------------------


class TestValorar:
    def test_una_valoracion_positiva_se_clasifica_como_positiva(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        """Comprobación explícita del plan de trabajo."""
        cuerpo = valorar(
            cliente,
            itinerario.id,
            puntuacion=5,
            comentario="Excelente lugar, el guía muy amable y todo muy limpio.",
        )

        assert cuerpo["sentimiento"] == "positivo"
        assert cuerpo["confianza_sentimiento"] > 0.5

    def test_una_valoracion_negativa_se_clasifica_como_negativa(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        cuerpo = valorar(
            cliente,
            itinerario.id,
            puntuacion=1,
            comentario="Pésimo. Los baños estaban sucios y nos cobraron de más.",
        )

        assert cuerpo["sentimiento"] == "negativo"

    def test_extrae_los_temas_mencionados(self, cliente: TestClient, itinerario: Itinerario):
        cuerpo = valorar(
            cliente,
            itinerario.id,
            puntuacion=2,
            comentario="Los baños sucios, muy caro y difícil llegar.",
        )

        assert set(cuerpo["temas"]) >= {"limpieza", "precio", "acceso"}

    def test_declara_como_se_analizo(self, cliente: TestClient, itinerario: Itinerario):
        """La trazabilidad de la regla de oro de la IA."""
        cuerpo = valorar(cliente, itinerario.id, comentario="Todo excelente")

        assert cuerpo["analizado_por"] == "reglas"
        assert cuerpo["version_del_analisis"]

    def test_guarda_el_comentario_tal_cual(self, cliente: TestClient, itinerario: Itinerario):
        """La capa 1 es el dato crudo y no se toca nunca."""
        original = "Muy bonito, aunque el baño estaba sucio."
        cuerpo = valorar(cliente, itinerario.id, puntuacion=4, comentario=original)

        assert cuerpo["comentario"] == original

    def test_funciona_sin_comentario(self, cliente: TestClient, itinerario: Itinerario):
        """Poner estrellas sin escribir es lo más frecuente."""
        cuerpo = valorar(cliente, itinerario.id, puntuacion=4)

        assert cuerpo["sentimiento"] == "positivo"
        assert cuerpo["temas"] == []

    def test_funciona_sin_cuenta(self, cliente: TestClient, itinerario: Itinerario):
        """Obligar a registrarse al final del viaje perdería la valoración."""
        assert valorar(cliente, itinerario.id)["id"]

    def test_puede_valorar_un_recurso_concreto(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        cuerpo = valorar(cliente, itinerario.id, recurso_id=recursos[0].id, puntuacion=5)

        assert cuerpo["recurso_id"] == recursos[0].id
        assert cuerpo["recurso_nombre"] == "Taller de Cochas"


class TestValidacionDeEntrada:
    def test_un_itinerario_inexistente_da_404(self, cliente: TestClient):
        respuesta = cliente.post(
            "/api/valoraciones", json={"itinerario_id": 999_999, "puntuacion": 5}
        )

        assert respuesta.status_code == 404

    @pytest.mark.parametrize("puntuacion", [0, 6, -1, 100])
    def test_una_puntuacion_fuera_de_rango_da_422(
        self, cliente: TestClient, itinerario: Itinerario, puntuacion: int
    ):
        respuesta = cliente.post(
            "/api/valoraciones",
            json={"itinerario_id": itinerario.id, "puntuacion": puntuacion},
        )

        assert respuesta.status_code == 422

    def test_no_se_puede_valorar_dos_veces_lo_mismo(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        """Sin esto se podría inflar la media de un sitio valorándolo diez veces."""
        valorar(cliente, itinerario.id, puntuacion=5)

        respuesta = cliente.post(
            "/api/valoraciones", json={"itinerario_id": itinerario.id, "puntuacion": 1}
        )

        assert respuesta.status_code == 409
        assert "Ya valoraste" in respuesta.json()["detail"]

    def test_si_se_puede_valorar_dos_recursos_distintos(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id)
        valorar(cliente, itinerario.id, recurso_id=recursos[1].id)

        listado = cliente.get(f"/api/valoraciones?itinerario_id={itinerario.id}").json()

        assert len(listado) == 2


class TestListado:
    def test_devuelve_lo_que_ya_se_valoro(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id, puntuacion=5)

        listado = cliente.get(f"/api/valoraciones?itinerario_id={itinerario.id}").json()

        assert len(listado) == 1
        assert listado[0]["recurso_id"] == recursos[0].id

    def test_un_itinerario_sin_valoraciones_devuelve_lista_vacia(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        assert cliente.get(f"/api/valoraciones?itinerario_id={itinerario.id}").json() == []


# ---------------------------------------------------------------------------
# El indicador del incremento
# ---------------------------------------------------------------------------


class TestIndicadorDeCobertura:
    def test_sin_itinerarios_el_porcentaje_es_cero(self, sesion: Session):
        total, con_valoracion, porcentaje = calcular_cobertura(sesion)

        assert (total, con_valoracion, porcentaje) == (0, 0, 0.0)

    def test_cuenta_itinerarios_y_no_valoraciones(
        self,
        cliente: TestClient,
        sesion: Session,
        itinerario: Itinerario,
        recursos: list[RecursoTuristico],
    ):
        """Diez opiniones de un mismo viaje siguen siendo una experiencia."""
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id)
        valorar(cliente, itinerario.id, recurso_id=recursos[1].id)
        valorar(cliente, itinerario.id, recurso_id=recursos[2].id)

        total, con_valoracion, porcentaje = calcular_cobertura(sesion)

        assert sesion.scalar(select(func.count()).select_from(Valoracion)) == 3
        assert con_valoracion == 1
        assert total == 1
        assert porcentaje == 100.0


# ---------------------------------------------------------------------------
# El tablero de evidencia
# ---------------------------------------------------------------------------


class TestTableroDeEvidencia:
    def test_sin_valoraciones_avisa_en_vez_de_ensenar_ceros(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert cuerpo["total_valoraciones"] == 0
        assert any("Todavía no hay" in a for a in cuerpo["avisos"])

    def test_agrega_la_distribucion_de_sentimiento(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[0].id,
            puntuacion=5,
            comentario="Excelente, muy limpio y amable",
        )
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[1].id,
            puntuacion=1,
            comentario="Pésimo, sucio y carísimo",
        )

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert cuerpo["sentimiento"]["positivas"] == 1
        assert cuerpo["sentimiento"]["negativas"] == 1
        assert cuerpo["sentimiento"]["total"] == 2

    def test_agrega_los_temas_con_su_signo(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        """El número que le dice al gestor DÓNDE actuar."""
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[0].id,
            puntuacion=1,
            comentario="Los baños estaban sucios",
        )
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[1].id,
            puntuacion=1,
            comentario="Mucha suciedad en los baños",
        )

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        limpieza = next(t for t in cuerpo["temas"] if t["tema"] == "limpieza")

        assert limpieza["menciones"] == 2
        assert limpieza["negativas"] == 2
        assert limpieza["porcentaje_negativo"] == 100.0

    def test_ordena_los_temas_por_menciones(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[0].id,
            puntuacion=3,
            comentario="Los baños sucios y muy caro",
        )
        valorar(
            cliente,
            itinerario.id,
            recurso_id=recursos[1].id,
            puntuacion=3,
            comentario="Baños sucios otra vez",
        )

        temas = cliente.get("/api/indicadores/evidencia").json()["temas"]

        assert temas[0]["tema"] == "limpieza"

    def test_construye_el_ranquin_de_recursos(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id, puntuacion=5)
        valorar(cliente, itinerario.id, recurso_id=recursos[1].id, puntuacion=1)

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert cuerpo["mejor_valorados"][0]["recurso_id"] == recursos[0].id
        assert cuerpo["peor_valorados"][0]["recurso_id"] == recursos[1].id

    def test_marca_los_recursos_con_pocas_valoraciones(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        """Una media de una valoración no es una media, y se dice."""
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id, puntuacion=5)

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert cuerpo["mejor_valorados"][0]["es_fiable"] is False
        assert any(str(MINIMO_PARA_FIARSE) in a for a in cuerpo["avisos"])

    def test_declara_cuantas_analizo_cada_via(self, cliente: TestClient, itinerario: Itinerario):
        """La trazabilidad de la regla de oro, agregada."""
        valorar(cliente, itinerario.id, comentario="Excelente todo")

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert cuerpo["analizadas_por_reglas"] == 1
        assert cuerpo["analizadas_por_modelo"] == 0
        assert any("alternativa por reglas" in a for a in cuerpo["avisos"])

    def test_avisa_de_las_valoraciones_sin_comentario(
        self, cliente: TestClient, itinerario: Itinerario
    ):
        valorar(cliente, itinerario.id, puntuacion=5)

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert any("no traen comentario" in a for a in cuerpo["avisos"])

    def test_calcula_la_evolucion_en_el_tiempo(
        self, cliente: TestClient, itinerario: Itinerario, recursos: list[RecursoTuristico]
    ):
        valorar(cliente, itinerario.id, recurso_id=recursos[0].id, puntuacion=5)

        cuerpo = cliente.get("/api/indicadores/evidencia").json()

        assert len(cuerpo["evolucion"]) == 1
        assert cuerpo["evolucion"][0]["total"] == 1


# ---------------------------------------------------------------------------
# El tablero de los seis indicadores
# ---------------------------------------------------------------------------


class TestTableroDeIndicadores:
    def test_muestra_los_seis_incrementos(self, cliente: TestClient):
        """Comprobación explícita del plan de trabajo."""
        cuerpo = cliente.get("/api/indicadores/tablero").json()

        assert len(cuerpo["indicadores"]) == 6
        assert [i["incremento"] for i in cuerpo["indicadores"]] == [1, 2, 3, 4, 5, 6]

    def test_cada_indicador_dice_que_brecha_cierra(self, cliente: TestClient):
        for indicador in cliente.get("/api/indicadores/tablero").json()["indicadores"]:
            assert indicador[
                "brecha"
            ], f"al incremento {indicador['incremento']} le falta la brecha"

    def test_cada_indicador_lleva_su_salvedad(self, cliente: TestClient):
        """Un número sin decir qué NO dice es peor que no tenerlo."""
        for indicador in cliente.get("/api/indicadores/tablero").json()["indicadores"]:
            assert indicador[
                "salvedad"
            ], f"el indicador {indicador['incremento']} no declara sus límites"

    def test_distingue_no_hay_dato_de_cero(self, cliente: TestClient):
        """Cero es una medición; la ausencia de una no es cero."""
        cuerpo = cliente.get("/api/indicadores/tablero").json()

        sin_datos = [i for i in cuerpo["indicadores"] if not i["hay_dato"]]

        # Con la base vacía, varios indicadores no tienen dato todavía.
        assert sin_datos
        assert all(i["valor"] == "—" for i in sin_datos)


# ---------------------------------------------------------------------------
# Las instantáneas
# ---------------------------------------------------------------------------


class TestInstantaneas:
    def test_guarda_una_foto_del_estado(
        self, cliente: TestClient, sesion: Session, itinerario: Itinerario
    ):
        valorar(cliente, itinerario.id, puntuacion=5, comentario="Excelente")

        registro = guardar_instantanea(sesion)
        sesion.commit()

        assert registro.total_itinerarios == 1
        assert registro.itinerarios_con_valoracion == 1
        assert registro.porcentaje_con_valoracion == 100.0
        assert registro.positivas == 1

    def test_las_devuelve_en_orden_cronologico(self, sesion: Session):
        """Es como se dibuja una línea de evolución."""
        primera = guardar_instantanea(sesion)
        segunda = guardar_instantanea(sesion)
        sesion.commit()

        instantaneas = obtener_instantaneas(sesion)

        assert [i.id for i in instantaneas] == [primera.id, segunda.id]


def test_el_resumen_no_revienta_con_la_base_vacia(sesion: Session):
    """El primer día del sistema, todo está vacío y tiene que funcionar igual."""
    resumen = resumir_evidencia(sesion)

    assert resumen.total_valoraciones == 0
    assert resumen.puntuacion_media is None
    assert resumen.avisos
