"""Pruebas de los endpoints del itinerario (Incremento 4).

Comprueban tres cosas distintas y las tres importan:

1. que el itinerario que sale por la API respeta las restricciones;
2. que **no se puede ver el itinerario de otra persona**;
3. que reordenar a mano respeta el orden pedido en vez de reoptimizarlo.

## Sobre los datos de estas pruebas

El catálogo de ejemplo del resto de la suite solo tiene dos recursos con
coordenadas, y con dos paradas no se puede comprobar un ordenamiento. Así que
aquí se insertan seis recursos repartidos por el valle, con coordenadas reales
de sus distritos. Son datos de prueba y se declaran como tales: no se cargan en
la base real ni salen de este archivo.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.main import aplicacion
from app.modelos.catalogo import HorarioAtencion, RecursoTuristico
from app.modelos.itinerario import Itinerario
from app.modelos.preferencias import PreferenciaViaje
from app.servicios import ruteo
from pruebas.conftest import codigos, parametros_de

#: Un sábado, para que el día de la semana sea estable en las pruebas de
#: horarios. No se usa ``date.today()`` porque el día de la semana cambiaría
#: cada jornada y las pruebas de horario dejarían de comprobar lo mismo.
SABADO = date(2026, 9, 12)

#: Seis puntos del valle con sus coordenadas y altitudes aproximadas. Están
#: repartidos para que haya traslados de verdad entre ellos: del norte (Jauja)
#: al sur (Sapallanga) hay unos 45 km.
RECURSOS_DE_PRUEBA = [
    # (codigo, nombre, provincia, distrito, categoria, lat, lon, altitud)
    (
        "990001",
        "Plaza Huanca",
        "Huancayo",
        "HUANCAYO",
        "2. MANIFESTACIONES CULTURALES",
        -12.0681,
        -75.2100,
        3250,
    ),
    (
        "990002",
        "Mirador Alto",
        "Huancayo",
        "HUANCAYO",
        "1. SITIOS NATURALES",
        -12.0750,
        -75.2200,
        3290,
    ),
    (
        "990003",
        "Convento de prueba",
        "Concepcion",
        "SANTA ROSA DE OCOPA",
        "2. MANIFESTACIONES CULTURALES",
        -11.8740,
        -75.2944,
        3384,
    ),
    (
        "990004",
        "Iglesia de prueba",
        "Concepcion",
        "CONCEPCION",
        "2. MANIFESTACIONES CULTURALES",
        -11.9184,
        -75.3122,
        3290,
    ),
    (
        "990005",
        "Laguna de prueba",
        "Chupaca",
        "CHUPACA",
        "1. SITIOS NATURALES",
        -12.0592,
        -75.2867,
        3263,
    ),
    (
        "990006",
        "Feria de prueba",
        "Huancayo",
        "SAPALLANGA",
        "3. FOLCLORE",
        -12.1600,
        -75.1800,
        3300,
    ),
]


@pytest.fixture(autouse=True)
def busqueda_corta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Baja el limite de busqueda del optimizador en las pruebas.

    En produccion son cinco segundos por itinerario. Aqui se arman mas de
    veinte y el problema tiene seis nodos: OR-Tools converge al instante y
    agotar el limite solo alargaria la suite de veinte segundos a dos minutos.
    La estrategia de busqueda es exactamente la misma.
    """
    monkeypatch.setattr(ruteo, "SEGUNDOS_DE_BUSQUEDA", 1)


@pytest.fixture
def catalogo_del_valle(sesion: Session) -> Session:
    """Inserta seis recursos repartidos por el valle, ya validados."""
    for codigo, nombre, provincia, distrito, categoria, lat, lon, altitud in RECURSOS_DE_PRUEBA:
        sesion.add(
            RecursoTuristico(
                codigo_mincetur=codigo,
                nombre=nombre,
                provincia=provincia,
                distrito=distrito,
                categoria=categoria,
                tipo="Prueba",
                subtipo="Prueba",
                descripcion_es=f"{nombre}: recurso de prueba en {distrito}.",
                ubicacion=func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})"),
                altitud_msnm=altitud,
                fecha_corte=SABADO,
                esta_validado=True,
                esta_vigente=True,
            )
        )

    sesion.commit()
    return sesion


@pytest.fixture
def cliente(catalogo_del_valle: Session) -> TestClient:
    aplicacion.dependency_overrides[obtener_sesion] = lambda: catalogo_del_valle

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


@pytest.fixture
def preferencia(catalogo_del_valle: Session) -> PreferenciaViaje:
    """Una preferencia sin cuenta, como la que crea el asistente."""
    fila = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=SABADO,
        fecha_fin=SABADO + timedelta(days=2),
        distrito_origen="HUANCAYO",
        presupuesto_soles=Decimal("450.00"),
        intereses=["arqueologia", "naturaleza"],
        movilidad="transporte_publico",
        requiere_accesibilidad=False,
        idioma="es",
        ritmo="moderado",
    )
    catalogo_del_valle.add(fila)
    catalogo_del_valle.commit()
    catalogo_del_valle.refresh(fila)

    return fila


def armar(cliente: TestClient, preferencia_id: int, **extra) -> dict:
    """Llama al endpoint y devuelve el cuerpo, fallando con el texto si no va."""
    respuesta = cliente.post("/api/itinerarios", json={"preferencia_id": preferencia_id, **extra})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


class TestArmarItinerario:
    def test_devuelve_paradas_numeradas_desde_cero_y_sin_saltos(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        cuerpo = armar(cliente, preferencia.id)

        assert cuerpo["paradas"], "no se armó ninguna parada"
        assert [p["orden"] for p in cuerpo["paradas"]] == list(range(len(cuerpo["paradas"])))

    def test_ninguna_parada_empieza_antes_de_que_acabe_la_anterior(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        paradas = armar(cliente, preferencia.id)["paradas"]

        for anterior, siguiente in zip(paradas, paradas[1:], strict=False):
            assert siguiente["hora_llegada"] >= anterior["hora_salida"]

    def test_ninguna_parada_se_sale_de_la_jornada_indicada(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        cuerpo = armar(cliente, preferencia.id, hora_inicio="09:00:00", hora_fin="16:00:00")

        for parada in cuerpo["paradas"]:
            assert parada["hora_llegada"] >= "09:00:00"
            assert parada["hora_salida"] <= "16:00:00"

    def test_ningun_recurso_se_repite(self, cliente: TestClient, preferencia: PreferenciaViaje):
        recursos = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]

        assert len(recursos) == len(set(recursos))

    def test_declara_como_se_genero(self, cliente: TestClient, preferencia: PreferenciaViaje):
        """La trazabilidad que exige la regla de oro de la IA del proyecto."""
        assert armar(cliente, preferencia.id)["generado_por"] in ("modelo", "reglas")

    def test_cada_traslado_lleva_precio_en_rango_fuente_y_fecha(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """La regla de honestidad con los datos, comprobada en la respuesta.

        Ningún precio puede salir de la API sin decir de dónde viene ni de
        cuándo es.
        """
        cuerpo = armar(cliente, preferencia.id)

        traslados = [p["traslado"] for p in cuerpo["paradas"] if p["traslado"]]
        assert traslados, "el itinerario no tiene ningún traslado que comprobar"

        for traslado in traslados:
            assert float(traslado["precio_max_soles"]) >= float(traslado["precio_min_soles"])
            assert traslado["fuente"], "un precio sin fuente es un rumor"
            assert traslado["fecha_referencia"], "un precio sin fecha caduca en silencio"
            assert traslado["origen_del_calculo"] in ("red_vial", "linea_recta")
            assert isinstance(traslado["es_estimado"], bool)

    def test_la_primera_parada_no_tiene_traslado(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """No se llega a la primera parada desde ningún sitio."""
        assert armar(cliente, preferencia.id)["paradas"][0]["traslado"] is None

    def test_los_totales_cuadran_con_la_suma_de_los_traslados(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        cuerpo = armar(cliente, preferencia.id)

        traslados = [p["traslado"] for p in cuerpo["paradas"] if p["traslado"]]

        suma_km = sum(t["distancia_km"] for t in traslados)
        suma_max = sum(Decimal(str(t["precio_max_soles"])) for t in traslados)

        assert cuerpo["distancia_total_km"] == pytest.approx(suma_km, abs=0.05)
        assert Decimal(str(cuerpo["costo_max_soles"])) == suma_max

    def test_avisa_de_la_altitud_porque_todo_el_valle_esta_sobre_los_3000(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        avisos = armar(cliente, preferencia.id)["avisos"]

        assert "altitud" in codigos(avisos)

    def test_avisa_de_que_no_se_conocen_los_horarios(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """La limitación del inventario del MINCETUR, dicha en voz alta."""
        avisos = armar(cliente, preferencia.id)["avisos"]

        # Cualquiera de los tres avisos de horario vale: lo que se comprueba
        # es que el itinerario no calla que no conoce los horarios.
        assert codigos(avisos) & {
            "sin_horario_ninguno",
            "sin_horario_algunos",
            "sin_horario_el_unico",
        }

    def test_no_guarda_nada_si_no_se_le_pide(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        """Calcular no es guardar: probar combinaciones no debe llenar la tabla."""
        antes = catalogo_del_valle.query(Itinerario).count()

        cuerpo = armar(cliente, preferencia.id)

        assert cuerpo["itinerario_id"] is None
        assert catalogo_del_valle.query(Itinerario).count() == antes

    def test_guarda_cuando_se_le_pide(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        cuerpo = armar(cliente, preferencia.id, guardar=True)

        assert cuerpo["itinerario_id"] is not None

        guardado = catalogo_del_valle.get(Itinerario, cuerpo["itinerario_id"])
        assert guardado is not None
        assert len(guardado.paradas) == len(cuerpo["paradas"])
        assert guardado.generado_por == cuerpo["generado_por"]


class TestValidacionDeEntrada:
    def test_una_preferencia_inexistente_da_404(self, cliente: TestClient):
        assert cliente.post("/api/itinerarios", json={"preferencia_id": 999_999}).status_code == 404

    def test_una_fecha_fuera_del_viaje_da_422(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        respuesta = cliente.post(
            "/api/itinerarios",
            json={
                "preferencia_id": preferencia.id,
                "fecha": (SABADO + timedelta(days=30)).isoformat(),
            },
        )

        assert respuesta.status_code == 422
        assert "fuera del viaje" in respuesta.json()["detail"]

    def test_sin_preferencia_id_da_422(self, cliente: TestClient):
        assert cliente.post("/api/itinerarios", json={}).status_code == 422


class TestReordenar:
    def test_respeta_el_orden_pedido_en_vez_de_reoptimizarlo(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Si el visitante arrastró una parada, se queda donde la puso."""
        recursos = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]

        if len(recursos) < 2:
            pytest.skip("hacen falta al menos dos paradas para reordenar")

        al_reves = list(reversed(recursos))

        respuesta = cliente.post(
            "/api/itinerarios/reordenar",
            json={"preferencia_id": preferencia.id, "recursos_en_orden": al_reves},
        )

        assert respuesta.status_code == 200, respuesta.text
        obtenidos = [p["recurso_id"] for p in respuesta.json()["paradas"]]

        # Puede recortar por el final si el orden nuevo ya no cabe en el día,
        # pero lo que entrega tiene que ser el principio del orden pedido.
        assert obtenidos == al_reves[: len(obtenidos)]

    def test_las_horas_se_recalculan_con_el_orden_nuevo(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        recursos = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]

        if len(recursos) < 2:
            pytest.skip("hacen falta al menos dos paradas para reordenar")

        cuerpo = cliente.post(
            "/api/itinerarios/reordenar",
            json={
                "preferencia_id": preferencia.id,
                "recursos_en_orden": list(reversed(recursos)),
            },
        ).json()

        paradas = cuerpo["paradas"]
        for anterior, siguiente in zip(paradas, paradas[1:], strict=False):
            assert siguiente["hora_llegada"] >= anterior["hora_salida"]

    def test_ignora_los_recursos_que_ya_no_estan_recomendados(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """La pantalla puede haberse quedado con una lista vieja."""
        recursos = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]

        respuesta = cliente.post(
            "/api/itinerarios/reordenar",
            json={"preferencia_id": preferencia.id, "recursos_en_orden": [*recursos, 999_999]},
        )

        assert respuesta.status_code == 200
        assert "paradas_omitidas_al_reordenar" in codigos(respuesta.json()["avisos"])

    def test_una_lista_vacia_da_422(self, cliente: TestClient, preferencia: PreferenciaViaje):
        respuesta = cliente.post(
            "/api/itinerarios/reordenar",
            json={"preferencia_id": preferencia.id, "recursos_en_orden": []},
        )

        assert respuesta.status_code == 422


class TestHorariosDeAtencion:
    """La restricción que hoy no tiene datos, comprobada con datos puestos.

    La tabla ``horario_atencion`` está vacía porque el inventario del MINCETUR
    no publica horarios. Estas pruebas insertan horarios a mano para demostrar
    que la restricción **está implementada y actúa**, no solo declarada. El día
    que aparezca una fuente de horarios, el código ya está listo.
    """

    def test_un_recurso_que_abre_menos_de_lo_que_dura_la_visita_no_entra(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        elegidos = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]
        assert elegidos, "no hay itinerario que restringir"

        # Se le pone un horario imposible a todos: abren media hora, y la
        # visita más corta que contempla el sistema dura una.
        for recurso_id in elegidos:
            catalogo_del_valle.add(
                HorarioAtencion(
                    recurso_id=recurso_id,
                    dia_semana=SABADO.weekday(),
                    hora_apertura=time(10, 0),
                    hora_cierre=time(10, 30),
                )
            )
        catalogo_del_valle.commit()

        despues = [p["recurso_id"] for p in armar(cliente, preferencia.id)["paradas"]]

        assert not set(despues) & set(
            elegidos
        ), "se programaron visitas a recursos que no dan tiempo a visitarse"

    def test_ninguna_visita_termina_despues_del_cierre(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        for recurso in catalogo_del_valle.query(RecursoTuristico).all():
            catalogo_del_valle.add(
                HorarioAtencion(
                    recurso_id=recurso.id,
                    dia_semana=SABADO.weekday(),
                    hora_apertura=time(8, 0),
                    hora_cierre=time(13, 0),
                )
            )
        catalogo_del_valle.commit()

        for parada in armar(cliente, preferencia.id)["paradas"]:
            assert (
                parada["hora_salida"] <= "13:00:00"
            ), f"{parada['nombre']} sale a las {parada['hora_salida']} y cierra a las 13:00"

    def test_ninguna_visita_empieza_antes_de_la_apertura(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        for recurso in catalogo_del_valle.query(RecursoTuristico).all():
            catalogo_del_valle.add(
                HorarioAtencion(
                    recurso_id=recurso.id,
                    dia_semana=SABADO.weekday(),
                    hora_apertura=time(11, 0),
                    hora_cierre=time(18, 0),
                )
            )
        catalogo_del_valle.commit()

        paradas = armar(cliente, preferencia.id)["paradas"]
        assert paradas, "con este horario todavía debería caber algo"

        for parada in paradas:
            assert parada["hora_llegada"] >= "11:00:00"

    def test_un_horario_de_otro_dia_de_la_semana_no_afecta(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        """El sábado no le importa lo que abra el martes."""
        antes = len(armar(cliente, preferencia.id)["paradas"])

        martes = (SABADO.weekday() + 3) % 7
        for recurso in catalogo_del_valle.query(RecursoTuristico).all():
            catalogo_del_valle.add(
                HorarioAtencion(
                    recurso_id=recurso.id,
                    dia_semana=martes,
                    hora_apertura=time(10, 0),
                    hora_cierre=time(10, 30),
                )
            )
        catalogo_del_valle.commit()

        assert len(armar(cliente, preferencia.id)["paradas"]) == antes


class TestAccesoAItinerariosGuardados:
    def test_un_itinerario_sin_dueno_se_recupera_por_identificador(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Es lo que permite compartir un plan sin obligar a registrarse."""
        creado = armar(cliente, preferencia.id, guardar=True)

        respuesta = cliente.get(f"/api/itinerarios/{creado['itinerario_id']}")

        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == creado["itinerario_id"]
        assert len(respuesta.json()["paradas"]) == len(creado["paradas"])

    def test_un_itinerario_inexistente_da_404(self, cliente: TestClient):
        assert cliente.get("/api/itinerarios/999999").status_code == 404

    def test_sin_cuenta_el_listado_va_vacio(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Devolver todos los anónimos sería enseñar viajes de desconocidos."""
        armar(cliente, preferencia.id, guardar=True)

        respuesta = cliente.get("/api/itinerarios")

        assert respuesta.status_code == 200
        assert respuesta.json() == []


class TestElSistemaExplicaPorQueElDiaQuedoCorto:
    """Un itinerario corto sin explicacion parece un fallo, y casi nunca lo es.

    Estas pruebas existen porque los tres casos aparecieron probando la
    aplicacion a mano: itinerarios de una sola parada donde el visitante no
    tenia forma de saber si el sistema se habia roto o si es que no cabia mas.
    """

    def test_avisa_cuando_el_presupuesto_no_da_ni_para_un_traslado(
        self, cliente: TestClient, catalogo_del_valle: Session
    ):
        pobre = PreferenciaViaje(
            usuario_id=None,
            fecha_inicio=SABADO,
            fecha_fin=SABADO,
            distrito_origen="HUANCAYO",
            # Un sol al dia: no alcanza ni para el pasaje mas barato.
            presupuesto_soles=Decimal("1.00"),
            intereses=["arqueologia", "naturaleza"],
            movilidad="taxi",
            requiere_accesibilidad=False,
            idioma="es",
            ritmo="moderado",
        )
        catalogo_del_valle.add(pobre)
        catalogo_del_valle.commit()
        catalogo_del_valle.refresh(pobre)

        cuerpo = armar(cliente, pobre.id)

        assert len(cuerpo["paradas"]) == 1
        assert codigos(cuerpo["avisos"]) & {
            "corto_por_presupuesto_agotado",
            "corto_por_presupuesto_insuficiente",
        }, "el itinerario se quedo en una parada sin decir por que"

    def test_avisa_cuando_solo_hay_un_recurso_al_alcance(
        self, cliente: TestClient, catalogo_del_valle: Session
    ):
        """Caminando el alcance son 8 km: desde Sapallanga casi no hay nada."""
        aislada = PreferenciaViaje(
            usuario_id=None,
            fecha_inicio=SABADO,
            fecha_fin=SABADO,
            distrito_origen="SAPALLANGA",
            presupuesto_soles=Decimal("400.00"),
            intereses=["folclore"],
            movilidad="caminando",
            requiere_accesibilidad=False,
            idioma="es",
            ritmo="relajado",
        )
        catalogo_del_valle.add(aislada)
        catalogo_del_valle.commit()
        catalogo_del_valle.refresh(aislada)

        cuerpo = armar(cliente, aislada.id)

        if len(cuerpo["paradas"]) > 1:
            pytest.skip("con estos datos si hay mas de un recurso al alcance")

        assert "un_solo_recurso_al_alcance" in codigos(cuerpo["avisos"])

    def test_no_avisa_de_presupuesto_cuando_el_dia_se_lleno(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Si el dia esta lleno no falta nada que explicar, y sobra el ruido."""
        cuerpo = armar(cliente, preferencia.id)

        if len(cuerpo["paradas"]) < 5:
            pytest.skip("el dia no se lleno con estos datos")

        assert not codigos(cuerpo["avisos"]) & {
            "corto_por_presupuesto_agotado",
            "corto_por_presupuesto_insuficiente",
        }

    def test_el_aviso_de_horarios_concuerda_en_numero(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Nada de «1 de los 1 recursos considerados no tienen horario».

        Desde la Fase 7 la concordancia la resuelve i18next en la interfaz, así
        que aquí se comprueba lo que decide el backend: **qué código emite**.
        Con un solo recurso tiene que ser el del singular, no el del plural con
        un uno dentro.
        """
        cuerpo = armar(cliente, preferencia.id)
        emitidos = codigos(cuerpo["avisos"])

        if "sin_horario_el_unico" in emitidos:
            return  # es el caso del singular, que es justo el correcto

        if "sin_horario_ninguno" in emitidos:
            assert parametros_de(cuerpo["avisos"], "sin_horario_ninguno")["total"] > 1
        else:
            assert parametros_de(cuerpo["avisos"], "sin_horario_algunos")["total"] > 1


class TestGuardarEsIdempotente:
    """Guardar dos veces el mismo dia no puede crear dos itinerarios.

    El fallo aparecio usando la aplicacion: la pantalla de valoracion rearma el
    itinerario al entrar, y con `guardar: true` creaba una fila nueva cada vez.
    Las valoraciones quedaban colgando de un itinerario distinto del que la
    pantalla enseñaba, y el indicador del Incremento 6 se diluia con duplicados
    que nadie iba a valorar.
    """

    def test_guardar_dos_veces_devuelve_el_mismo_itinerario(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        primero = armar(cliente, preferencia.id, guardar=True)
        segundo = armar(cliente, preferencia.id, guardar=True)

        assert primero["itinerario_id"] == segundo["itinerario_id"]
        assert catalogo_del_valle.query(Itinerario).count() == 1

    def test_guardar_de_nuevo_actualiza_las_paradas(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        """No basta con no duplicar: el itinerario tiene que quedar al dia."""
        primero = armar(cliente, preferencia.id, guardar=True)

        # Se rearma con una jornada mas corta, que deja menos paradas.
        segundo = armar(
            cliente,
            preferencia.id,
            guardar=True,
            hora_inicio="09:00:00",
            hora_fin="11:00:00",
        )

        guardado = catalogo_del_valle.get(Itinerario, segundo["itinerario_id"])

        assert guardado is not None
        assert len(guardado.paradas) == len(segundo["paradas"])
        assert primero["itinerario_id"] == segundo["itinerario_id"]

    def test_dias_distintos_si_son_itinerarios_distintos(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        """La idempotencia es por preferencia Y fecha, no solo por preferencia."""
        primero = armar(cliente, preferencia.id, guardar=True, fecha=SABADO.isoformat())
        segundo = armar(
            cliente,
            preferencia.id,
            guardar=True,
            fecha=(SABADO + timedelta(days=1)).isoformat(),
        )

        assert primero["itinerario_id"] != segundo["itinerario_id"]
        assert catalogo_del_valle.query(Itinerario).count() == 2


def armar_viaje(cliente: TestClient, preferencia_id: int, **extra) -> dict:
    """Llama al endpoint del viaje completo y devuelve el cuerpo."""
    respuesta = cliente.post(
        "/api/itinerarios/viaje", json={"preferencia_id": preferencia_id, **extra}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


class TestArmarViaje:
    """El viaje completo: un día por fecha, y ningún lugar en dos días.

    ## Por qué existe esta clase

    Hasta aquí el itinerario se pedía día a día, y eso tenía un defecto que
    ninguna prueba cazaba: cada petición era independiente, el recomendador
    devuelve lo mismo para la misma preferencia y el optimizador es
    determinista, así que **un viaje de tres días devolvía tres veces el mismo
    día**, con los mismos lugares, las mismas horas y los mismos costos.

    Las pruebas que había miraban un día en aislamiento y todas pasaban. La
    primera prueba de aquí abajo es la que faltaba.
    """

    def test_devuelve_un_dia_por_cada_fecha_del_viaje(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        cuerpo = armar_viaje(cliente, preferencia.id)

        esperadas = [
            (preferencia.fecha_inicio + timedelta(days=n)).isoformat()
            for n in range((preferencia.fecha_fin - preferencia.fecha_inicio).days + 1)
        ]

        assert [dia["fecha"] for dia in cuerpo["dias"]] == esperadas

    def test_ningun_lugar_aparece_en_dos_dias(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """**La prueba que faltaba.** Es la que falla si vuelve el defecto.

        No comprueba que los días sean distintos —eso podría cumplirse cambiando
        solo el orden—, sino lo que de verdad importaba: que **ningún recurso se
        proponga dos veces** en el mismo viaje. Si alguien quitara el reparto,
        los tres días volverían a traer los mismos lugares y esto caería.
        """
        cuerpo = armar_viaje(cliente, preferencia.id)

        vistos: dict[int, str] = {}

        for dia in cuerpo["dias"]:
            for parada in dia["paradas"]:
                recurso = parada["recurso_id"]

                assert recurso not in vistos, (
                    f"«{parada['nombre']}» sale el {dia['fecha']} y ya salía "
                    f"el {vistos[recurso]}: el viaje está repitiendo lugares"
                )

                vistos[recurso] = dia["fecha"]

    def test_el_primer_dia_se_lleva_los_mejores(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """El reparto es en cascada, no un troceado arbitrario.

        El día 1 es el mejor día posible; cada siguiente es el mejor de lo que
        sobró. Así que el mejor puntaje del día 1 no puede ser peor que el del
        día 2: si lo fuera, el reparto estaría dejando lo bueno para después.
        """
        dias = [dia for dia in armar_viaje(cliente, preferencia.id)["dias"] if dia["paradas"]]

        if len(dias) < 2:
            pytest.skip("el catálogo de prueba no da para dos días con paradas")

        mejores = [max(p["puntaje_relativo"] for p in dia["paradas"]) for dia in dias]

        assert mejores == sorted(mejores, reverse=True)

    def test_cuando_se_agotan_los_lugares_el_dia_lo_dice(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Un día sin lugares nuevos sale vacío **y con su motivo**.

        El catálogo de estas pruebas tiene seis recursos y el ritmo es moderado,
        así que un viaje de tres días se queda sin repertorio. Lo que no puede
        pasar es que se rellene repitiendo lo del día 1 ni que salga vacío sin
        explicar por qué.
        """
        dias = armar_viaje(cliente, preferencia.id)["dias"]

        vacios = [dia for dia in dias if not dia["paradas"]]

        if not vacios:
            pytest.skip("el catálogo de prueba alcanzó para todos los días")

        for dia in vacios:
            assert "sin_lugares_sin_repetir" in codigos(dia["avisos"])

    def test_el_aviso_de_repertorio_corto_dice_cuantas_y_cuantas_cabian(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Si se avisa de que el día salió corto, el aviso trae los dos números."""
        dias = armar_viaje(cliente, preferencia.id)["dias"]

        con_aviso = [dia for dia in dias if "lugares_limitados" in codigos(dia["avisos"])]

        if not con_aviso:
            pytest.skip("ningún día se quedó corto por falta de repertorio")

        for dia in con_aviso:
            parametros = parametros_de(dia["avisos"], "lugares_limitados")

            assert parametros["count"] == len(dia["paradas"])
            assert parametros["maximo"] > parametros["count"]

    def test_cada_dia_declara_como_se_genero(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """La trazabilidad de la regla de oro de la IA, día por día."""
        for dia in armar_viaje(cliente, preferencia.id)["dias"]:
            assert dia["generado_por"] in ("modelo", "reglas")

    def test_un_viaje_de_un_solo_dia_devuelve_un_solo_dia(
        self, cliente: TestClient, catalogo_del_valle: Session
    ):
        de_un_dia = PreferenciaViaje(
            usuario_id=None,
            fecha_inicio=SABADO,
            fecha_fin=SABADO,
            distrito_origen="HUANCAYO",
            presupuesto_soles=Decimal("450.00"),
            intereses=["arqueologia", "naturaleza"],
            movilidad="transporte_publico",
            requiere_accesibilidad=False,
            idioma="es",
            ritmo="moderado",
        )
        catalogo_del_valle.add(de_un_dia)
        catalogo_del_valle.commit()
        catalogo_del_valle.refresh(de_un_dia)

        cuerpo = armar_viaje(cliente, de_un_dia.id)

        assert len(cuerpo["dias"]) == 1
        assert cuerpo["dias"][0]["fecha"] == SABADO.isoformat()

    def test_guardar_crea_un_itinerario_por_dia_con_paradas(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        cuerpo = armar_viaje(cliente, preferencia.id, guardar=True)

        con_paradas = [dia for dia in cuerpo["dias"] if dia["paradas"]]

        assert con_paradas, "no se armó ningún día con paradas"
        assert all(dia["itinerario_id"] is not None for dia in con_paradas)
        assert catalogo_del_valle.query(Itinerario).count() == len(con_paradas)

    def test_los_dias_vacios_no_se_guardan(
        self, cliente: TestClient, preferencia: PreferenciaViaje, catalogo_del_valle: Session
    ):
        """Un día sin paradas no es un itinerario: no se guarda una fila vacía."""
        cuerpo = armar_viaje(cliente, preferencia.id, guardar=True)

        for dia in cuerpo["dias"]:
            if not dia["paradas"]:
                assert dia["itinerario_id"] is None

    def test_una_preferencia_que_no_existe_da_404(self, cliente: TestClient):
        respuesta = cliente.post("/api/itinerarios/viaje", json={"preferencia_id": 999999})

        assert respuesta.status_code == 404
        assert respuesta.json()["detail"]["codigo"] == "sin_preferencia"


#: Quince recursos naturales repartidos alrededor de Huancayo.
#:
#: El catálogo de seis recursos de arriba no da para comprobar lo que de verdad
#: importa del viaje: **varios días llenos que no se solapan**. Con seis
#: recursos y el filtro de intereses, el día 1 se lleva lo que hay y los demás
#: salen vacíos, que es correcto pero deja sin probar el caso normal.
#:
#: Las descripciones llevan a propósito palabras de la lista de «naturaleza»
#: —laguna, paisaje, cerro, río— porque el recomendador puntúa sobre el texto:
#: unos recursos sin esas palabras no llegarían a ser candidatos y la prueba
#: comprobaría el filtro en vez del reparto.
RECURSOS_NATURALES_DE_PRUEBA = [
    (
        f"99{100 + numero}",
        f"Laguna de prueba {numero}",
        -12.00 - numero * 0.02,
        -75.18 - numero * 0.01,
    )
    for numero in range(15)
]


@pytest.fixture
def catalogo_amplio(sesion: Session) -> Session:
    """Quince recursos naturales validados, suficientes para varios días."""
    for codigo, nombre, lat, lon in RECURSOS_NATURALES_DE_PRUEBA:
        sesion.add(
            RecursoTuristico(
                codigo_mincetur=codigo,
                nombre=nombre,
                provincia="Huancayo",
                distrito="HUANCAYO",
                categoria="1. SITIOS NATURALES",
                tipo="Prueba",
                subtipo="Prueba",
                descripcion_es=(
                    f"{nombre}: laguna de aguas claras en un paisaje de cerros, "
                    "con flora y fauna del valle junto al rio."
                ),
                ubicacion=func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})"),
                altitud_msnm=3300,
                fecha_corte=SABADO,
                esta_validado=True,
                esta_vigente=True,
            )
        )

    sesion.commit()
    return sesion


@pytest.fixture
def cliente_amplio(catalogo_amplio: Session) -> TestClient:
    aplicacion.dependency_overrides[obtener_sesion] = lambda: catalogo_amplio

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


@pytest.fixture
def preferencia_de_tres_dias(catalogo_amplio: Session) -> PreferenciaViaje:
    """Tres días a ritmo relajado: nueve paradas de las quince disponibles."""
    fila = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=SABADO,
        fecha_fin=SABADO + timedelta(days=2),
        distrito_origen="HUANCAYO",
        presupuesto_soles=Decimal("900.00"),
        intereses=["naturaleza"],
        movilidad="taxi",
        requiere_accesibilidad=False,
        idioma="es",
        ritmo="relajado",
    )
    catalogo_amplio.add(fila)
    catalogo_amplio.commit()
    catalogo_amplio.refresh(fila)

    return fila


class TestViajeConRepertorioSuficiente:
    """El caso normal: tres días llenos, distintos entre sí y sin solaparse.

    Es el escenario que el visitante va a ver de verdad, y el que estaba roto:
    los tres días salían idénticos. Con quince recursos y ritmo relajado hay
    repertorio de sobra, así que si dos días coinciden no es por falta de
    lugares: es porque el reparto no funciona.
    """

    def test_los_tres_dias_tienen_paradas(
        self, cliente_amplio: TestClient, preferencia_de_tres_dias: PreferenciaViaje
    ):
        dias = armar_viaje(cliente_amplio, preferencia_de_tres_dias.id)["dias"]

        assert len(dias) == 3
        assert all(dia["paradas"] for dia in dias), [len(d["paradas"]) for d in dias]

    def test_ningun_lugar_se_repite_entre_los_tres_dias(
        self, cliente_amplio: TestClient, preferencia_de_tres_dias: PreferenciaViaje
    ):
        dias = armar_viaje(cliente_amplio, preferencia_de_tres_dias.id)["dias"]

        por_dia = [{p["recurso_id"] for p in dia["paradas"]} for dia in dias]
        todos = [recurso for conjunto in por_dia for recurso in conjunto]

        assert len(todos) == len(set(todos)), (
            "hay lugares repetidos entre días: " f"{[sorted(c) for c in por_dia]}"
        )

    def test_los_dias_no_son_el_mismo_itinerario(
        self, cliente_amplio: TestClient, preferencia_de_tres_dias: PreferenciaViaje
    ):
        """La comprobación directa del defecto, en los términos en que se vio.

        Lo que se reportó no fue «se repite un lugar»: fue que el día 2 y el
        día 3 eran **el mismo día** que el día 1, con los mismos nombres y los
        mismos horarios. Esto compara las listas completas.
        """
        dias = armar_viaje(cliente_amplio, preferencia_de_tres_dias.id)["dias"]

        listas = [tuple(p["recurso_id"] for p in dia["paradas"]) for dia in dias]

        assert len(set(listas)) == len(listas), f"dos días traen el mismo plan: {listas}"

    def test_ninguno_de_los_dias_avisa_de_falta_de_repertorio(
        self, cliente_amplio: TestClient, preferencia_de_tres_dias: PreferenciaViaje
    ):
        """Con quince recursos para nueve paradas, no debe faltar repertorio.

        Si este aviso saliera aquí, significaría que el reparto está consumiendo
        más candidatos de los que usa, y los últimos días quedarían pobres sin
        motivo.
        """
        dias = armar_viaje(cliente_amplio, preferencia_de_tres_dias.id)["dias"]

        for dia in dias:
            emitidos = codigos(dia["avisos"])

            assert "sin_lugares_sin_repetir" not in emitidos
            assert "lugares_limitados" not in emitidos

    def test_cada_dia_cuadra_sus_propios_horarios(
        self, cliente_amplio: TestClient, preferencia_de_tres_dias: PreferenciaViaje
    ):
        """Repartir no puede estropear lo que cada día ya garantizaba."""
        dias = armar_viaje(cliente_amplio, preferencia_de_tres_dias.id)["dias"]

        for dia in dias:
            paradas = dia["paradas"]

            assert [p["orden"] for p in paradas] == list(range(len(paradas)))

            for anterior, siguiente in zip(paradas, paradas[1:], strict=False):
                assert siguiente["hora_llegada"] >= anterior["hora_salida"]
