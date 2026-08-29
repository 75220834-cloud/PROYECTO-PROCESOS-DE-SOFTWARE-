"""Endpoints de las preferencias de viaje (Incremento 2).

- ``GET  /api/preferencias/opciones``   valores para dibujar el asistente
- ``POST /api/preferencias``            guarda una preferencia (con o sin cuenta)
- ``GET  /api/preferencias/{id}``       consulta una preferencia
- ``PUT  /api/preferencias/{id}``       actualiza una preferencia
- ``GET  /api/preferencias``            las del usuario, para «Mis viajes»
- ``POST /api/preferencias/{id}/reclamar`` asocia a la cuenta una preferencia
  creada sin ella

El endpoint de reclamación es el que sostiene la promesa del proyecto: armar
el viaje sin cuenta y registrarse **al final** solo si se quiere guardarlo.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func, select

from app.esquemas.preferencias import (
    CatalogoDeOpciones,
    DatosPreferencia,
    ListaDePreferencias,
    PreferenciaPublica,
)
from app.modelos.catalogo import RecursoTuristico
from app.modelos.preferencias import Interes, Movilidad, PreferenciaViaje, Ritmo
from app.modelos.usuario import Usuario
from app.utilidades.dependencias import SesionBD, UsuarioOpcional, UsuarioRequerido

enrutador = APIRouter(prefix="/api/preferencias", tags=["preferencias"])


def _a_publica(preferencia: PreferenciaViaje) -> PreferenciaPublica:
    """Convierte el modelo en el esquema de salida, añadiendo la duración."""
    return PreferenciaPublica(
        id=preferencia.id,
        usuario_id=preferencia.usuario_id,
        fecha_inicio=preferencia.fecha_inicio,
        fecha_fin=preferencia.fecha_fin,
        duracion_dias=preferencia.duracion_dias,
        distrito_origen=preferencia.distrito_origen,
        presupuesto_soles=preferencia.presupuesto_soles,
        intereses=list(preferencia.intereses),
        movilidad=preferencia.movilidad,
        requiere_accesibilidad=preferencia.requiere_accesibilidad,
        idioma=preferencia.idioma,
        ritmo=preferencia.ritmo,
        creado_en=preferencia.creado_en,
    )


def _comprobar_acceso(preferencia: PreferenciaViaje, usuario: Usuario | None) -> None:
    """Deja pasar solo a quien puede ver o modificar esta preferencia.

    Reglas:
    - Una preferencia **sin dueño** es accesible: la creó alguien sin cuenta y
      su identificador vive únicamente en el navegador de esa persona.
    - Una preferencia **con dueño** solo la ve su dueño.

    Se responde 404 y no 403 cuando la preferencia es de otra persona: un 403
    confirmaría que ese identificador existe, y permitiría contar cuántas
    preferencias hay en el sistema probando números.
    """
    if preferencia.usuario_id is None:
        return

    if usuario is None or preferencia.usuario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )


def _obtener_o_404(sesion, id_preferencia: int) -> PreferenciaViaje:
    preferencia = sesion.get(PreferenciaViaje, id_preferencia)

    if preferencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )

    return preferencia


@enrutador.get("/opciones", response_model=CatalogoDeOpciones, summary="Valores para el asistente")
def obtener_opciones(sesion: SesionBD) -> CatalogoDeOpciones:
    """Devuelve los valores que el asistente necesita para dibujar sus pasos.

    Los distritos salen del catálogo real, no de una lista escrita a mano: el
    visitante solo puede elegir como origen un distrito donde de verdad hay
    recursos turísticos registrados.
    """
    distritos = [
        distrito
        for (distrito,) in sesion.execute(
            select(distinct(RecursoTuristico.distrito)).order_by(RecursoTuristico.distrito)
        )
    ]

    return CatalogoDeOpciones(
        intereses=[interes.value for interes in Interes],
        movilidades=[movilidad.value for movilidad in Movilidad],
        ritmos=[ritmo.value for ritmo in Ritmo],
        distritos=distritos,
    )


@enrutador.post(
    "",
    response_model=PreferenciaPublica,
    status_code=status.HTTP_201_CREATED,
    summary="Guarda una preferencia de viaje",
)
def crear_preferencia(
    datos: DatosPreferencia,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
) -> PreferenciaPublica:
    """Registra lo que el visitante quiere de su viaje.

    **Funciona sin cuenta.** Si no hay sesión iniciada, la preferencia se
    guarda con ``usuario_id`` nulo y el frontend conserva su identificador en
    el navegador. Es la regla del proyecto: no se pide registrarse para
    empezar, solo para guardar.
    """
    preferencia = PreferenciaViaje(
        usuario_id=usuario.id if usuario else None,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        distrito_origen=datos.distrito_origen,
        presupuesto_soles=datos.presupuesto_soles,
        intereses=datos.intereses,
        movilidad=datos.movilidad,
        requiere_accesibilidad=datos.requiere_accesibilidad,
        idioma=datos.idioma,
        ritmo=datos.ritmo,
    )

    sesion.add(preferencia)
    sesion.commit()
    sesion.refresh(preferencia)

    return _a_publica(preferencia)


@enrutador.get("", response_model=ListaDePreferencias, summary="Mis preferencias guardadas")
def listar_mis_preferencias(sesion: SesionBD, usuario: UsuarioRequerido) -> ListaDePreferencias:
    """Devuelve las preferencias del usuario, para la página «Mis viajes»."""
    consulta = (
        select(PreferenciaViaje)
        .where(PreferenciaViaje.usuario_id == usuario.id)
        .order_by(PreferenciaViaje.creado_en.desc())
    )

    elementos = [_a_publica(preferencia) for preferencia in sesion.scalars(consulta)]

    return ListaDePreferencias(total=len(elementos), elementos=elementos)


@enrutador.get(
    "/{id_preferencia}", response_model=PreferenciaPublica, summary="Consulta una preferencia"
)
def obtener_preferencia(
    id_preferencia: int, sesion: SesionBD, usuario: UsuarioOpcional
) -> PreferenciaPublica:
    """Devuelve una preferencia concreta."""
    preferencia = _obtener_o_404(sesion, id_preferencia)
    _comprobar_acceso(preferencia, usuario)

    return _a_publica(preferencia)


@enrutador.put(
    "/{id_preferencia}", response_model=PreferenciaPublica, summary="Actualiza una preferencia"
)
def actualizar_preferencia(
    id_preferencia: int,
    datos: DatosPreferencia,
    sesion: SesionBD,
    usuario: UsuarioOpcional,
) -> PreferenciaPublica:
    """Cambia una preferencia ya guardada.

    Sirve para el botón «Cambiar preferencias» de la pantalla de resultados,
    sin obligar a rehacer el asistente desde cero.
    """
    preferencia = _obtener_o_404(sesion, id_preferencia)
    _comprobar_acceso(preferencia, usuario)

    preferencia.fecha_inicio = datos.fecha_inicio
    preferencia.fecha_fin = datos.fecha_fin
    preferencia.distrito_origen = datos.distrito_origen
    preferencia.presupuesto_soles = datos.presupuesto_soles
    preferencia.intereses = datos.intereses
    preferencia.movilidad = datos.movilidad
    preferencia.requiere_accesibilidad = datos.requiere_accesibilidad
    preferencia.idioma = datos.idioma
    preferencia.ritmo = datos.ritmo

    sesion.commit()
    sesion.refresh(preferencia)

    return _a_publica(preferencia)


@enrutador.post(
    "/{id_preferencia}/reclamar",
    response_model=PreferenciaPublica,
    summary="Asocia a tu cuenta una preferencia creada sin ella",
)
def reclamar_preferencia(
    id_preferencia: int, sesion: SesionBD, usuario: UsuarioRequerido
) -> PreferenciaPublica:
    """Convierte en propia una preferencia que se creó sin cuenta.

    Es el cierre del recorrido que promete el proyecto: el visitante arma su
    viaje sin registrarse y, si al final quiere conservarlo, crea la cuenta y
    reclama lo que ya había hecho, sin repetir el asistente.

    Una preferencia que ya tiene dueño no se puede reclamar.
    """
    preferencia = _obtener_o_404(sesion, id_preferencia)

    if preferencia.usuario_id is not None:
        if preferencia.usuario_id == usuario.id:
            # Ya es suya: se devuelve tal cual en vez de dar error, para que
            # pulsar dos veces no rompa nada.
            return _a_publica(preferencia)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una preferencia con ese identificador",
        )

    preferencia.usuario_id = usuario.id
    sesion.commit()
    sesion.refresh(preferencia)

    return _a_publica(preferencia)


@enrutador.get(
    "/indicadores/resumen",
    summary="Cuántas preferencias se han registrado",
    include_in_schema=False,
)
def resumen_de_preferencias(sesion: SesionBD) -> dict[str, int]:
    """Conteo simple para el tablero del gestor de la Fase 6."""
    total = sesion.scalar(select(func.count()).select_from(PreferenciaViaje)) or 0
    con_cuenta = (
        sesion.scalar(
            select(func.count())
            .select_from(PreferenciaViaje)
            .where(PreferenciaViaje.usuario_id.is_not(None))
        )
        or 0
    )

    return {"total": total, "con_cuenta": con_cuenta, "sin_cuenta": total - con_cuenta}
