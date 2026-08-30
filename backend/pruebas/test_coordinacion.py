"""Pruebas del canal único de coordinación (Incremento 5).

Cubren las cuatro comprobaciones que exige el plan de trabajo:

1. Una solicitud recorre **enviada → confirmada** y queda registrada con fechas.
2. Un proveedor **solo ve las solicitudes de sus servicios**.
3. Un visitante **no puede acceder** a lo administrativo.
4. Las pruebas pasan.

Los permisos se prueban desde la API y no llamando al servicio a mano: una
regla de acceso que solo se comprueba en la capa de servicio deja abierta la
posibilidad de que un endpoint se la salte, y eso es exactamente el fallo que
hay que evitar.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.main import aplicacion
from app.modelos.coordinacion import (
    DisponibilidadServicio,
    EstadoSolicitud,
    Proveedor,
    Servicio,
    TipoServicio,
)
from app.modelos.usuario import RolUsuario
from app.servicios.usuarios import registrar_usuario
from pruebas.conftest import codigos

#: Fecha del servicio en las pruebas: un sábado lejano, para que siempre pase
#: el filtro de antelación mínima y el día de la semana sea estable.
SABADO = date(2027, 3, 13)

CONTRASENA = "PruebaSegura2026"


@pytest.fixture
def cliente(sesion: Session) -> TestClient:
    aplicacion.dependency_overrides[obtener_sesion] = lambda: sesion

    with TestClient(aplicacion) as cliente_de_prueba:
        yield cliente_de_prueba

    aplicacion.dependency_overrides.clear()


def crear_usuario(sesion: Session, correo: str, rol: str):
    usuario = registrar_usuario(
        sesion, correo=correo, contrasena=CONTRASENA, nombre=f"Usuario {rol}", rol=rol
    )
    sesion.commit()
    return usuario


def cabeceras(cliente: TestClient, correo: str) -> dict[str, str]:
    """Inicia sesión y devuelve la cabecera de autorización."""
    respuesta = cliente.post(
        "/api/autenticacion/sesion", json={"correo": correo, "contrasena": CONTRASENA}
    )
    assert respuesta.status_code == 200, respuesta.text

    return {"Authorization": f"Bearer {respuesta.json()['token_de_acceso']}"}


def crear_servicio(
    sesion: Session,
    proveedor: Proveedor,
    *,
    nombre: str = "Taller de prueba",
    capacidad: int = 10,
    cupo: int = 10,
    antelacion: int = 24,
    dias: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
) -> Servicio:
    servicio = Servicio(
        proveedor_id=proveedor.id,
        nombre=nombre,
        tipo=TipoServicio.TALLER,
        descripcion="Servicio creado para las pruebas.",
        capacidad_maxima=capacidad,
        duracion_min=90,
        antelacion_minima_horas=antelacion,
        precio_min_soles=Decimal("30.00"),
        precio_max_soles=Decimal("45.00"),
        unidad_precio="por_persona",
        fecha_referencia=date(2026, 8, 29),
        idiomas="es",
        es_accesible=True,
        esta_publicado=True,
    )
    sesion.add(servicio)
    sesion.flush()

    for dia in dias:
        sesion.add(
            DisponibilidadServicio(
                servicio_id=servicio.id,
                dia_semana=dia,
                hora_inicio=time(9, 0),
                hora_fin=time(17, 0),
                cupo=cupo,
            )
        )

    sesion.commit()
    return servicio


@pytest.fixture
def escenario(sesion: Session) -> dict:
    """Dos proveedores con un servicio cada uno, y usuarios de cada rol.

    Son **dos** proveedores a propósito: con uno solo, la prueba de «un
    proveedor solo ve lo suyo» pasaría sin comprobar nada.
    """
    dueno_a = crear_usuario(sesion, "proveedor.a@prueba.pe", RolUsuario.PROVEEDOR)
    dueno_b = crear_usuario(sesion, "proveedor.b@prueba.pe", RolUsuario.PROVEEDOR)
    visitante = crear_usuario(sesion, "visitante@prueba.pe", RolUsuario.VISITANTE)
    operador = crear_usuario(sesion, "operador@prueba.pe", RolUsuario.OPERADOR)
    gestor = crear_usuario(sesion, "gestor@prueba.pe", RolUsuario.GESTOR)

    proveedor_a = Proveedor(
        usuario_id=dueno_a.id, nombre="Proveedor A", distrito="HUANCAYO", es_demostracion=True
    )
    proveedor_b = Proveedor(
        usuario_id=dueno_b.id, nombre="Proveedor B", distrito="CONCEPCION", es_demostracion=True
    )
    sesion.add_all([proveedor_a, proveedor_b])
    sesion.commit()

    return {
        "proveedor_a": proveedor_a,
        "proveedor_b": proveedor_b,
        "servicio_a": crear_servicio(sesion, proveedor_a, nombre="Servicio de A"),
        "servicio_b": crear_servicio(sesion, proveedor_b, nombre="Servicio de B"),
        "correo_a": "proveedor.a@prueba.pe",
        "correo_b": "proveedor.b@prueba.pe",
        "correo_visitante": "visitante@prueba.pe",
        "correo_operador": "operador@prueba.pe",
        "correo_gestor": "gestor@prueba.pe",
        "visitante": visitante,
        "operador": operador,
        "gestor": gestor,
    }


def pedir(cliente: TestClient, servicio_id: int, **extra) -> dict:
    """Crea una solicitud y devuelve el cuerpo, fallando con el texto si no va."""
    cuerpo = {
        "servicio_id": servicio_id,
        "fecha_servicio": SABADO.isoformat(),
        "hora_servicio": "10:00:00",
        "numero_personas": 2,
        "nombre_contacto": "Persona de prueba",
        "telefono_contacto": "+51 900 000 999",
    }
    cuerpo.update(extra)

    cabeceras_extra = cuerpo.pop("_cabeceras", None)

    respuesta = cliente.post("/api/solicitudes", json=cuerpo, headers=cabeceras_extra)
    assert respuesta.status_code == 201, respuesta.text

    return respuesta.json()


# ---------------------------------------------------------------------------
# Catálogo de servicios — brecha 5
# ---------------------------------------------------------------------------


class TestCatalogoDeServicios:
    def test_lista_los_servicios_publicados(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.get("/api/servicios")

        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 2

    def test_cada_servicio_declara_su_capacidad_y_su_antelacion(
        self, cliente: TestClient, escenario: dict
    ):
        """Es lo que cierra la brecha 5: antes había que llamar para saberlo."""
        servicio = cliente.get("/api/servicios").json()[0]

        assert servicio["capacidad_maxima"] >= 1
        assert servicio["antelacion_minima_horas"] >= 0
        assert servicio["disponibilidad"], "un servicio sin horarios no es verificable"

    def test_el_precio_es_un_rango_con_fecha_de_referencia(
        self, cliente: TestClient, escenario: dict
    ):
        servicio = cliente.get("/api/servicios").json()[0]

        assert Decimal(servicio["precio_max_soles"]) >= Decimal(servicio["precio_min_soles"])
        assert servicio["fecha_referencia"]
        assert servicio["unidad_precio"] in (
            "por_persona",
            "por_grupo",
            "por_noche",
            "por_hora",
        )

    def test_marca_los_proveedores_de_demostracion(self, cliente: TestClient, escenario: dict):
        """Nadie debe llamar a un teléfono inventado creyendo que contesta alguien."""
        servicio = cliente.get("/api/servicios").json()[0]

        assert servicio["proveedor"]["es_demostracion"] is True

    def test_no_lista_los_servicios_sin_publicar(
        self, cliente: TestClient, escenario: dict, sesion: Session
    ):
        escenario["servicio_a"].esta_publicado = False
        sesion.commit()

        assert len(cliente.get("/api/servicios").json()) == 1

    def test_un_servicio_inexistente_da_404(self, cliente: TestClient):
        assert cliente.get("/api/servicios/999999").status_code == 404


# ---------------------------------------------------------------------------
# Disponibilidad — la capacidad verificable de la brecha 5
# ---------------------------------------------------------------------------


class TestDisponibilidad:
    def test_dice_que_si_cuando_cabe(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/disponibilidad",
            json={"fecha": SABADO.isoformat(), "numero_personas": 2, "hora": "10:00:00"},
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["hay_disponibilidad"] is True
        assert respuesta.json()["motivos"] == []

    def test_rechaza_si_se_piden_mas_personas_que_la_capacidad(
        self, cliente: TestClient, escenario: dict
    ):
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/disponibilidad",
            json={"fecha": SABADO.isoformat(), "numero_personas": 99},
        )

        cuerpo = respuesta.json()
        assert cuerpo["hay_disponibilidad"] is False
        assert "supera_la_capacidad" in codigos(cuerpo["motivos"])

    def test_rechaza_si_no_hay_antelacion_suficiente(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        """El servicio pide 24 horas y se pide para hoy."""
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/disponibilidad",
            json={"fecha": date.today().isoformat(), "numero_personas": 1},
        )

        cuerpo = respuesta.json()
        assert cuerpo["hay_disponibilidad"] is False
        assert "falta_antelacion" in codigos(cuerpo["motivos"])

    def test_rechaza_los_dias_en_que_el_proveedor_no_atiende(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        cerrado = crear_servicio(
            sesion,
            escenario["proveedor_a"],
            nombre="Solo entre semana",
            dias=(0, 1, 2, 3, 4),
        )

        respuesta = cliente.post(
            f"/api/servicios/{cerrado.id}/disponibilidad",
            json={"fecha": SABADO.isoformat(), "numero_personas": 1},
        )

        cuerpo = respuesta.json()
        assert cuerpo["hay_disponibilidad"] is False
        assert "no_atiende_ese_dia" in codigos(cuerpo["motivos"])

    def test_rechaza_las_horas_fuera_del_tramo(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/disponibilidad",
            json={"fecha": SABADO.isoformat(), "numero_personas": 1, "hora": "23:00:00"},
        )

        cuerpo = respuesta.json()
        assert cuerpo["hay_disponibilidad"] is False
        assert "no_atiende_a_esa_hora" in codigos(cuerpo["motivos"])

    def test_devuelve_todos_los_motivos_y_no_solo_el_primero(
        self, cliente: TestClient, escenario: dict
    ):
        """Ir dando los motivos de uno en uno hace abandonar el formulario."""
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/disponibilidad",
            json={
                "fecha": date.today().isoformat(),  # sin antelación
                "numero_personas": 99,  # sobre la capacidad
                "hora": "23:00:00",  # fuera del horario
            },
        )

        assert len(respuesta.json()["motivos"]) >= 3

    def test_las_solicitudes_vivas_consumen_cupo(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        """Una solicitud en revisión todavía puede confirmarse.

        Prometer su plaza a otro es exactamente el problema que describe la
        brecha 5.
        """
        pequeno = crear_servicio(
            sesion, escenario["proveedor_a"], nombre="Aforo mínimo", capacidad=4, cupo=4
        )

        pedir(cliente, pequeno.id, numero_personas=3)

        respuesta = cliente.post(
            f"/api/servicios/{pequeno.id}/disponibilidad",
            json={"fecha": SABADO.isoformat(), "numero_personas": 3},
        )

        cuerpo = respuesta.json()
        assert cuerpo["hay_disponibilidad"] is False
        assert cuerpo["plazas_libres"] == 1


# ---------------------------------------------------------------------------
# El ciclo completo — brecha 6
# ---------------------------------------------------------------------------


class TestCicloDeUnaSolicitud:
    def test_una_solicitud_recorre_enviada_hasta_confirmada(
        self, cliente: TestClient, escenario: dict
    ):
        """La comprobación central del plan de trabajo."""
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        assert solicitud["estado"] == EstadoSolicitud.ENVIADA

        del_proveedor = cabeceras(cliente, escenario["correo_a"])

        en_revision = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "en_revision", "nota": "Mirando la agenda"},
            headers=del_proveedor,
        )
        assert en_revision.status_code == 200, en_revision.text
        assert en_revision.json()["estado"] == "en_revision"

        confirmada = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={
                "nuevo_estado": "confirmada",
                "nota": "Confirmado para las 10:00",
                "precio_acordado_soles": "70.00",
            },
            headers=del_proveedor,
        )

        assert confirmada.status_code == 200, confirmada.text
        cuerpo = confirmada.json()

        assert cuerpo["estado"] == "confirmada"
        assert Decimal(cuerpo["precio_acordado_soles"]) == Decimal("70.00")

    def test_queda_registrada_con_fechas(self, cliente: TestClient, escenario: dict):
        """«Registro de lo acordado», que es literalmente la brecha 6."""
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        del_proveedor = cabeceras(cliente, escenario["correo_a"])

        cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "en_revision"},
            headers=del_proveedor,
        )
        final = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_proveedor,
        ).json()

        historial = final["historial"]

        assert [c["estado_nuevo"] for c in historial] == [
            "enviada",
            "en_revision",
            "confirmada",
        ]
        assert all(c["ocurrido_en"] for c in historial), "un cambio sin fecha no es un registro"
        assert historial[0]["estado_anterior"] is None
        assert historial[1]["estado_anterior"] == "enviada"

    def test_cuenta_las_interacciones(self, cliente: TestClient, escenario: dict):
        """Es el indicador del incremento."""
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        assert solicitud["interacciones"] == 1

        del_proveedor = cabeceras(cliente, escenario["correo_a"])
        final = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_proveedor,
        ).json()

        assert final["interacciones"] == 2

    def test_guarda_quien_hizo_cada_cambio(self, cliente: TestClient, escenario: dict):
        solicitud = pedir(cliente, escenario["servicio_a"].id)

        final = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "rechazada", "nota": "No hay sitio"},
            headers=cabeceras(cliente, escenario["correo_a"]),
        ).json()

        assert final["historial"][-1]["rol_de_quien_cambio"] == "proveedor"

    def test_no_se_puede_confirmar_sin_precio(self, cliente: TestClient, escenario: dict):
        """Un acuerdo sin la cifra que importa no es un acuerdo."""
        solicitud = pedir(cliente, escenario["servicio_a"].id)

        respuesta = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada"},
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"]["codigo"] == "falta_precio_acordado"

    def test_una_solicitud_rechazada_no_resucita(self, cliente: TestClient, escenario: dict):
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        del_proveedor = cabeceras(cliente, escenario["correo_a"])

        cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "rechazada"},
            headers=del_proveedor,
        )

        respuesta = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_proveedor,
        )

        assert respuesta.status_code == 409
        assert "no puede pasar" in respuesta.json()["detail"]

    def test_una_confirmada_solo_se_puede_cancelar(self, cliente: TestClient, escenario: dict):
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        del_proveedor = cabeceras(cliente, escenario["correo_a"])

        cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_proveedor,
        )

        rechazar = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "rechazada"},
            headers=del_proveedor,
        )
        assert rechazar.status_code == 409

        cancelar = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "cancelada"},
            headers=del_proveedor,
        )
        assert cancelar.status_code == 200

    def test_no_se_puede_pedir_un_servicio_sin_disponibilidad(
        self, cliente: TestClient, escenario: dict
    ):
        """Aceptar lo imposible haría perder el tiempo a las dos partes.

        Se piden 50 personas para un servicio de capacidad 10. El número está
        dentro de lo que admite el esquema (hasta 200) a propósito: si se
        pidieran 999, Pydantic devolvería un 422 antes de llegar aquí y la
        prueba no comprobaría la regla de negocio, sino la validación de tipos.
        """
        respuesta = cliente.post(
            "/api/solicitudes",
            json={
                "servicio_id": escenario["servicio_a"].id,
                "fecha_servicio": SABADO.isoformat(),
                "numero_personas": 50,
                "nombre_contacto": "Persona de prueba",
            },
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"]["motivos"]

    def test_un_numero_de_personas_absurdo_lo_para_el_esquema(
        self, cliente: TestClient, escenario: dict
    ):
        """Antes de la regla de negocio está la validación de entrada."""
        respuesta = cliente.post(
            "/api/solicitudes",
            json={
                "servicio_id": escenario["servicio_a"].id,
                "fecha_servicio": SABADO.isoformat(),
                "numero_personas": 999,
                "nombre_contacto": "Persona de prueba",
            },
        )

        assert respuesta.status_code == 422

    def test_funciona_sin_cuenta(self, cliente: TestClient, escenario: dict):
        """La aplicación se usa sin registro, y coordinar no es la excepción."""
        solicitud = pedir(cliente, escenario["servicio_a"].id)

        assert solicitud["id"]
        # Y se puede seguir por identificador, igual que un itinerario.
        assert cliente.get(f"/api/solicitudes/{solicitud['id']}").status_code == 200


# ---------------------------------------------------------------------------
# Permisos — las dos comprobaciones de acceso del plan
# ---------------------------------------------------------------------------


class TestPermisos:
    def test_un_proveedor_solo_ve_las_solicitudes_de_sus_servicios(
        self, cliente: TestClient, escenario: dict
    ):
        """Comprobación explícita del plan de trabajo."""
        pedir(cliente, escenario["servicio_a"].id, nombre_contacto="Para A")
        pedir(cliente, escenario["servicio_b"].id, nombre_contacto="Para B")

        del_a = cliente.get(
            "/api/solicitudes", headers=cabeceras(cliente, escenario["correo_a"])
        ).json()

        assert len(del_a) == 1
        assert del_a[0]["servicio_id"] == escenario["servicio_a"].id
        assert del_a[0]["nombre_contacto"] == "Para A"

    def test_un_proveedor_no_puede_mover_la_solicitud_de_otro(
        self, cliente: TestClient, escenario: dict
    ):
        de_b = pedir(cliente, escenario["servicio_b"].id)

        respuesta = cliente.post(
            f"/api/solicitudes/{de_b['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 403
        assert "no es de ninguno de tus servicios" in respuesta.json()["detail"]

    def test_un_visitante_no_puede_confirmar_su_propia_solicitud(
        self, cliente: TestClient, escenario: dict
    ):
        """Confirmarse a uno mismo sería volver a no tener acuerdo."""
        del_visitante = cabeceras(cliente, escenario["correo_visitante"])

        solicitud = pedir(cliente, escenario["servicio_a"].id, _cabeceras=del_visitante)

        respuesta = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_visitante,
        )

        assert respuesta.status_code == 403

    def test_un_visitante_si_puede_cancelar_la_suya(self, cliente: TestClient, escenario: dict):
        del_visitante = cabeceras(cliente, escenario["correo_visitante"])
        solicitud = pedir(cliente, escenario["servicio_a"].id, _cabeceras=del_visitante)

        respuesta = cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "cancelada"},
            headers=del_visitante,
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "cancelada"

    def test_un_visitante_no_puede_publicar_servicios(self, cliente: TestClient, escenario: dict):
        """La comprobación de «un visitante no accede al panel administrativo»."""
        respuesta = cliente.post(
            "/api/servicios",
            json={
                "nombre": "Servicio pirata",
                "tipo": "taller",
                "capacidad_maxima": 5,
                "precio_min_soles": "10.00",
                "precio_max_soles": "20.00",
                "fecha_referencia": "2026-08-29",
            },
            headers=cabeceras(cliente, escenario["correo_visitante"]),
        )

        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["codigo"] == "solo_proveedores_publican"

    def test_sin_sesion_no_se_puede_publicar_servicios(self, cliente: TestClient):
        respuesta = cliente.post(
            "/api/servicios",
            json={
                "nombre": "Servicio anónimo",
                "tipo": "taller",
                "capacidad_maxima": 5,
                "precio_min_soles": "10.00",
                "precio_max_soles": "20.00",
                "fecha_referencia": "2026-08-29",
            },
        )

        assert respuesta.status_code in (401, 403)

    def test_sin_sesion_no_hay_listado_de_solicitudes(self, cliente: TestClient):
        """Sin cuenta no se sabe cuáles son «las tuyas» sin enseñar las de otros."""
        assert cliente.get("/api/solicitudes").status_code in (401, 403)

    def test_un_visitante_no_ve_las_solicitudes_de_otros(
        self, cliente: TestClient, escenario: dict
    ):
        pedir(cliente, escenario["servicio_a"].id, nombre_contacto="De alguien más")

        suyas = cliente.get(
            "/api/solicitudes", headers=cabeceras(cliente, escenario["correo_visitante"])
        ).json()

        assert suyas == []

    def test_un_operador_ve_todas(self, cliente: TestClient, escenario: dict):
        """Coordinar es su trabajo: sin visión completa no puede hacerlo."""
        pedir(cliente, escenario["servicio_a"].id)
        pedir(cliente, escenario["servicio_b"].id)

        todas = cliente.get(
            "/api/solicitudes", headers=cabeceras(cliente, escenario["correo_operador"])
        ).json()

        assert len(todas) == 2

    def test_un_proveedor_sin_ficha_asociada_no_ve_nada(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        """El fallo grave sería enseñarle todo «porque es proveedor»."""
        crear_usuario(sesion, "proveedor.huerfano@prueba.pe", RolUsuario.PROVEEDOR)

        pedir(cliente, escenario["servicio_a"].id)

        vistas = cliente.get(
            "/api/solicitudes", headers=cabeceras(cliente, "proveedor.huerfano@prueba.pe")
        ).json()

        assert vistas == []

    def test_un_proveedor_no_puede_publicar_en_el_servicio_de_otro(
        self, cliente: TestClient, escenario: dict
    ):
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_b'].id}/tramos",
            json={
                "dia_semana": 3,
                "hora_inicio": "08:00:00",
                "hora_fin": "12:00:00",
                "cupo": 5,
            },
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["codigo"] == "servicio_ajeno"


# ---------------------------------------------------------------------------
# Panel del proveedor
# ---------------------------------------------------------------------------


class TestPanelDelProveedor:
    def test_puede_publicar_un_servicio(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.post(
            "/api/servicios",
            json={
                "nombre": "Servicio nuevo",
                "tipo": "guiado",
                "capacidad_maxima": 8,
                "antelacion_minima_horas": 12,
                "precio_min_soles": "20.00",
                "precio_max_soles": "30.00",
                "fecha_referencia": "2026-08-29",
            },
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["nombre"] == "Servicio nuevo"

    def test_no_puede_publicar_un_precio_invertido(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.post(
            "/api/servicios",
            json={
                "nombre": "Precio al revés",
                "tipo": "guiado",
                "capacidad_maxima": 8,
                "precio_min_soles": "50.00",
                "precio_max_soles": "20.00",
                "fecha_referencia": "2026-08-29",
            },
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 422

    def test_ve_sus_servicios_incluidos_los_no_publicados(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        escenario["servicio_a"].esta_publicado = False
        sesion.commit()

        mios = cliente.get(
            "/api/proveedores/mio/servicios", headers=cabeceras(cliente, escenario["correo_a"])
        ).json()

        assert len(mios) == 1, "un proveedor tiene que ver sus borradores"

    def test_ve_su_propia_ficha(self, cliente: TestClient, escenario: dict):
        respuesta = cliente.get(
            "/api/proveedores/mio", headers=cabeceras(cliente, escenario["correo_a"])
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["nombre"] == "Proveedor A"

    def test_puede_anadir_un_tramo_de_disponibilidad(
        self, cliente: TestClient, sesion: Session, escenario: dict
    ):
        # Se crea un servicio sin ningún tramo para que añadir uno se note.
        vacio = crear_servicio(sesion, escenario["proveedor_a"], nombre="Sin horarios", dias=())

        respuesta = cliente.post(
            f"/api/servicios/{vacio.id}/tramos",
            json={
                "dia_semana": 2,
                "hora_inicio": "10:00:00",
                "hora_fin": "14:00:00",
                "cupo": 6,
            },
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 201, respuesta.text
        assert len(respuesta.json()["disponibilidad"]) == 1

    def test_un_tramo_que_acaba_antes_de_empezar_se_rechaza(
        self, cliente: TestClient, escenario: dict
    ):
        respuesta = cliente.post(
            f"/api/servicios/{escenario['servicio_a'].id}/tramos",
            json={
                "dia_semana": 2,
                "hora_inicio": "14:00:00",
                "hora_fin": "10:00:00",
                "cupo": 6,
            },
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# El indicador
# ---------------------------------------------------------------------------


class TestIndicador:
    def test_sin_confirmadas_las_medias_van_a_nulo_y_no_a_cero(
        self, cliente: TestClient, escenario: dict
    ):
        """Una media de cero casos no es cero: es que no hay dato."""
        pedir(cliente, escenario["servicio_a"].id)

        cuerpo = cliente.get("/api/indicadores/coordinacion").json()

        assert cuerpo["total_solicitudes"] == 1
        assert cuerpo["confirmadas"] == 0
        assert cuerpo["interacciones_medias_hasta_confirmar"] is None

    def test_cuenta_las_interacciones_medias_hasta_confirmar(
        self, cliente: TestClient, escenario: dict
    ):
        solicitud = pedir(cliente, escenario["servicio_a"].id)
        del_proveedor = cabeceras(cliente, escenario["correo_a"])

        cliente.post(
            f"/api/solicitudes/{solicitud['id']}/estado",
            json={"nuevo_estado": "confirmada", "precio_acordado_soles": "70.00"},
            headers=del_proveedor,
        )

        cuerpo = cliente.get("/api/indicadores/coordinacion").json()

        assert cuerpo["confirmadas"] == 1
        assert cuerpo["interacciones_medias_hasta_confirmar"] == 2.0

    def test_declara_que_el_canal_es_uno(self, cliente: TestClient, escenario: dict):
        """Es lo que mide la brecha 6: antes eran teléfono, Facebook y WhatsApp."""
        assert cliente.get("/api/indicadores/coordinacion").json()["canales_para_confirmar"] == 1

    def test_separa_pendientes_de_cerradas(self, cliente: TestClient, escenario: dict):
        pedir(cliente, escenario["servicio_a"].id)
        rechazada = pedir(cliente, escenario["servicio_a"].id, nombre_contacto="Segunda")

        cliente.post(
            f"/api/solicitudes/{rechazada['id']}/estado",
            json={"nuevo_estado": "rechazada"},
            headers=cabeceras(cliente, escenario["correo_a"]),
        )

        cuerpo = cliente.get("/api/indicadores/coordinacion").json()

        assert cuerpo["total_solicitudes"] == 2
        assert cuerpo["rechazadas"] == 1
        assert cuerpo["pendientes"] == 1


# ---------------------------------------------------------------------------
# Enlace con el Incremento 4
# ---------------------------------------------------------------------------


def test_una_solicitud_puede_venir_de_un_itinerario(
    cliente: TestClient, sesion: Session, escenario: dict
):
    """Se pide desde el plan del día, no desde un formulario suelto.

    Es lo que conecta el Incremento 5 con el 4: el visitante ve su itinerario y
    desde ahí pide lo que necesita.
    """
    from app.modelos.itinerario import Itinerario
    from app.modelos.preferencias import PreferenciaViaje

    preferencia = PreferenciaViaje(
        usuario_id=None,
        fecha_inicio=SABADO,
        fecha_fin=SABADO + timedelta(days=1),
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

    itinerario = Itinerario(
        preferencia_id=preferencia.id,
        titulo="Un día en Huancayo",
        fecha=SABADO,
        estado="guardado",
        generado_por="modelo",
    )
    sesion.add(itinerario)
    sesion.commit()

    solicitud = pedir(cliente, escenario["servicio_a"].id, itinerario_id=itinerario.id)

    assert solicitud["itinerario_id"] == itinerario.id
