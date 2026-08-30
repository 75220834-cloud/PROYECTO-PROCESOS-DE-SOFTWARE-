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

        assert any("altitud" in a.lower() or "aclimat" in a.lower() for a in avisos)

    def test_avisa_de_que_no_se_conocen_los_horarios(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """La limitación del inventario del MINCETUR, dicha en voz alta."""
        avisos = armar(cliente, preferencia.id)["avisos"]

        assert any("horario" in a.lower() for a in avisos)

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
        assert any("omitieron" in a for a in respuesta.json()["avisos"])

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
        assert any(
            "presupuesto de traslado" in a for a in cuerpo["avisos"]
        ), "el itinerario se quedo en una parada sin decir por que"

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

        assert any("no hay recorrido que armar" in a for a in cuerpo["avisos"])

    def test_no_avisa_de_presupuesto_cuando_el_dia_se_lleno(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Si el dia esta lleno no falta nada que explicar, y sobra el ruido."""
        cuerpo = armar(cliente, preferencia.id)

        if len(cuerpo["paradas"]) < 5:
            pytest.skip("el dia no se lleno con estos datos")

        assert not any("presupuesto de traslado" in a for a in cuerpo["avisos"])

    def test_el_aviso_de_horarios_concuerda_en_numero(
        self, cliente: TestClient, preferencia: PreferenciaViaje
    ):
        """Nada de «1 de los 1 recursos considerados no tienen horario»."""
        cuerpo = armar(cliente, preferencia.id)

        aviso = next(a for a in cuerpo["avisos"] if "horario de atención" in a)

        assert "de los 1 recursos" not in aviso
        assert "1 de los 1" not in aviso


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
