"""Crea proveedores y servicios de demostración para el Incremento 5.

Se ejecuta desde ``backend/``:

    python -m app.utilidades.proveedores_semilla

## Estos proveedores NO existen

**Ninguno de los proveedores que crea este guion es real.** El proyecto no
tiene convenios con nadie del valle, no ha hablado con ninguna asociación de
artesanos ni con ningún restaurante, y no tiene sus precios ni sus teléfonos.

Están inventados para poder enseñar el flujo de coordinación, que es lo que
pide el Incremento 5, sin fingir que hay una red de proveedores detrás.

Tres cosas garantizan que nadie se confunda:

1. Cada proveedor lleva ``es_demostracion = True`` en la base de datos.
2. El nombre lleva el sufijo «(demostración)».
3. Los teléfonos usan el prefijo ``+51 900 000 xxx``, que no corresponde a
   ningún rango asignado a operadores peruanos.

El guion se niega a ejecutarse fuera del entorno de desarrollo, igual que el de
usuarios.

## De dónde salen los servicios, entonces

De los **tipos de actividad que el propio catálogo del MINCETUR describe** en
el valle: talleres de mates burilados en Cochas, comedores de trucha en Ingenio,
guiado en el convento de Ocopa. Los sitios son reales y están en el catálogo;
los proveedores concretos y sus precios no lo son.
"""

from __future__ import annotations

import sys
from datetime import date, time

from sqlalchemy import select

from app.base_datos import FabricaDeSesiones
from app.configuracion import obtener_configuracion
from app.modelos.coordinacion import (
    DisponibilidadServicio,
    Proveedor,
    Servicio,
    TipoServicio,
)
from app.modelos.usuario import RolUsuario, Usuario

#: Fecha a la que se refieren los precios de demostración. Es la de hoy porque
#: los precios se acaban de inventar: fecharlos antes seria fingir que se
#: consultaron en su día.
FECHA_DE_LOS_PRECIOS = date(2026, 8, 29)

#: Marca que se añade al nombre de todo proveedor sembrado.
SUFIJO_DEMOSTRACION = "(demostración)"

#: Rango telefónico que no está asignado a ningún operador en Perú. Se usa a
#: propósito para que, si alguien marca, no moleste a nadie real.
PREFIJO_TELEFONO_FALSO = "+51 900 000"

#: Días laborables y fin de semana, en el convenio de ``date.weekday()``.
ENTRE_SEMANA = (0, 1, 2, 3, 4)
FIN_DE_SEMANA = (5, 6)
TODA_LA_SEMANA = (0, 1, 2, 3, 4, 5, 6)


PROVEEDORES_SEMILLA: list[dict] = [
    {
        "nombre": f"Taller de mates burilados Cochas {SUFIJO_DEMOSTRACION}",
        "distrito": "EL TAMBO",
        "telefono": f"{PREFIJO_TELEFONO_FALSO} 101",
        "correo": "taller.cochas@ejemplo.invalid",
        "descripcion": (
            "Taller familiar de burilado de mates. Proveedor de demostración: "
            "no corresponde a ningún taller real de Cochas."
        ),
        "servicios": [
            {
                "nombre": "Taller de burilado para principiantes",
                "tipo": TipoServicio.TALLER,
                "descripcion": ("Dos horas de introducción al burilado, con el mate incluido."),
                "capacidad_maxima": 12,
                "duracion_min": 120,
                "antelacion_minima_horas": 48,
                "precio_min_soles": "35.00",
                "precio_max_soles": "50.00",
                "unidad_precio": "por_persona",
                "idiomas": "es",
                "es_accesible": True,
                "disponibilidad": [(TODA_LA_SEMANA, time(9, 0), time(16, 0), 12)],
            },
            {
                "nombre": "Venta directa de mates burilados",
                "tipo": TipoServicio.ARTESANIA,
                "descripcion": "Piezas del taller, de tamaño y detalle variables.",
                "capacidad_maxima": 30,
                "antelacion_minima_horas": 2,
                "precio_min_soles": "15.00",
                "precio_max_soles": "180.00",
                "unidad_precio": "por_persona",
                "idiomas": "es",
                "es_accesible": True,
                "disponibilidad": [(TODA_LA_SEMANA, time(8, 0), time(18, 0), 30)],
            },
        ],
    },
    {
        "nombre": f"Truchas del Ingenio {SUFIJO_DEMOSTRACION}",
        "distrito": "INGENIO",
        "telefono": f"{PREFIJO_TELEFONO_FALSO} 102",
        "correo": "truchas.ingenio@ejemplo.invalid",
        "descripcion": (
            "Comedor junto a la piscigranja. Proveedor de demostración: no "
            "corresponde a ningún restaurante real de Ingenio."
        ),
        "servicios": [
            {
                "nombre": "Almuerzo de trucha",
                "tipo": TipoServicio.ALIMENTACION,
                "descripcion": "Trucha frita o al ajo, con guarnición y bebida.",
                "capacidad_maxima": 40,
                "duracion_min": 60,
                "antelacion_minima_horas": 24,
                "precio_min_soles": "25.00",
                "precio_max_soles": "40.00",
                "unidad_precio": "por_persona",
                "idiomas": "es",
                "es_accesible": True,
                "disponibilidad": [(TODA_LA_SEMANA, time(11, 30), time(16, 0), 25)],
            }
        ],
    },
    {
        "nombre": f"Guías del Convento de Ocopa {SUFIJO_DEMOSTRACION}",
        "distrito": "SANTA ROSA DE OCOPA",
        "telefono": f"{PREFIJO_TELEFONO_FALSO} 103",
        "correo": "guias.ocopa@ejemplo.invalid",
        "descripcion": (
            "Guiado en el convento y su biblioteca. Proveedor de demostración: "
            "no corresponde a ningún servicio real del convento."
        ),
        "servicios": [
            {
                "nombre": "Visita guiada al convento",
                "tipo": TipoServicio.GUIADO,
                "descripcion": (
                    "Recorrido por el claustro, la biblioteca y el museo de " "historia natural."
                ),
                "capacidad_maxima": 20,
                "duracion_min": 75,
                "antelacion_minima_horas": 24,
                "precio_min_soles": "10.00",
                "precio_max_soles": "15.00",
                "unidad_precio": "por_persona",
                "idiomas": "es, en",
                "es_accesible": False,
                # Cerrado los lunes: es el día habitual de descanso de los
                # museos, y sirve para que la comprobación de disponibilidad
                # tenga un caso real que rechazar en la demostración.
                "disponibilidad": [
                    ((1, 2, 3, 4), time(9, 0), time(17, 0), 20),
                    (FIN_DE_SEMANA, time(9, 0), time(18, 0), 20),
                ],
            }
        ],
    },
    {
        "nombre": f"Movilidad Valle del Mantaro {SUFIJO_DEMOSTRACION}",
        "distrito": "HUANCAYO",
        "telefono": f"{PREFIJO_TELEFONO_FALSO} 104",
        "correo": "movilidad.mantaro@ejemplo.invalid",
        "descripcion": (
            "Transporte privado por el valle. Proveedor de demostración: no "
            "corresponde a ninguna empresa real."
        ),
        "servicios": [
            {
                "nombre": "Movilidad privada por día",
                "tipo": TipoServicio.TRANSPORTE,
                "descripcion": (
                    "Vehículo con conductor para recorrer el valle durante una "
                    "jornada, con paradas a convenir."
                ),
                "capacidad_maxima": 6,
                "duracion_min": 480,
                "antelacion_minima_horas": 48,
                "precio_min_soles": "180.00",
                "precio_max_soles": "280.00",
                "unidad_precio": "por_grupo",
                "idiomas": "es",
                "es_accesible": False,
                "disponibilidad": [(TODA_LA_SEMANA, time(6, 0), time(19, 0), 3)],
            }
        ],
    },
    {
        "nombre": f"Hospedaje Wanka {SUFIJO_DEMOSTRACION}",
        "distrito": "HUANCAYO",
        "telefono": f"{PREFIJO_TELEFONO_FALSO} 105",
        "correo": "hospedaje.wanka@ejemplo.invalid",
        "descripcion": (
            "Alojamiento céntrico. Proveedor de demostración: no corresponde a "
            "ningún hospedaje real de Huancayo."
        ),
        "servicios": [
            {
                "nombre": "Habitación doble con desayuno",
                "tipo": TipoServicio.HOSPEDAJE,
                "descripcion": "Habitación para dos personas, desayuno incluido.",
                "capacidad_maxima": 2,
                "antelacion_minima_horas": 24,
                "precio_min_soles": "90.00",
                "precio_max_soles": "140.00",
                "unidad_precio": "por_noche",
                "idiomas": "es, en",
                "es_accesible": True,
                "disponibilidad": [(TODA_LA_SEMANA, time(14, 0), time(22, 0), 8)],
            }
        ],
    },
]


def _usuario_proveedor(sesion) -> Usuario | None:
    """El usuario de demostración con rol de proveedor, si existe.

    Se asocia al primer proveedor sembrado para que la demostración del panel
    de proveedor tenga servicios que gestionar nada más entrar. Si no existe,
    los proveedores se crean sin dueño y el panel sale vacío, que también es un
    estado legítimo.
    """
    return sesion.scalars(
        select(Usuario).where(Usuario.rol == RolUsuario.PROVEEDOR).limit(1)
    ).first()


def crear_proveedores_semilla() -> tuple[int, int]:
    """Crea los proveedores y servicios que falten.

    Devuelve ``(proveedores_creados, servicios_creados)``. Es idempotente: se
    reconoce por el nombre, que lleva el sufijo de demostración.
    """
    proveedores_creados = 0
    servicios_creados = 0

    with FabricaDeSesiones() as sesion:
        dueno = _usuario_proveedor(sesion)
        primero = True

        for datos in PROVEEDORES_SEMILLA:
            existente = sesion.scalars(
                select(Proveedor).where(Proveedor.nombre == datos["nombre"]).limit(1)
            ).first()

            if existente is not None:
                print(f"  ya existía   {datos['nombre'][:56]}")
                primero = False
                continue

            proveedor = Proveedor(
                # Solo el primero se asocia al usuario de demostración: si
                # todos tuvieran el mismo dueño, la prueba de «un proveedor
                # solo ve lo suyo» no comprobaría nada.
                usuario_id=dueno.id if (primero and dueno is not None) else None,
                nombre=datos["nombre"],
                distrito=datos["distrito"],
                telefono=datos["telefono"],
                correo=datos["correo"],
                descripcion=datos["descripcion"],
                es_demostracion=True,
                esta_activo=True,
            )
            sesion.add(proveedor)
            sesion.flush()

            proveedores_creados += 1
            print(f"  creado       {datos['nombre'][:56]}")

            for datos_servicio in datos["servicios"]:
                disponibilidad = datos_servicio.pop("disponibilidad")

                servicio = Servicio(
                    proveedor_id=proveedor.id,
                    fecha_referencia=FECHA_DE_LOS_PRECIOS,
                    esta_publicado=True,
                    **datos_servicio,
                )
                sesion.add(servicio)
                sesion.flush()

                for dias, inicio, fin, cupo in disponibilidad:
                    for dia in dias:
                        sesion.add(
                            DisponibilidadServicio(
                                servicio_id=servicio.id,
                                dia_semana=dia,
                                hora_inicio=inicio,
                                hora_fin=fin,
                                cupo=cupo,
                            )
                        )

                servicios_creados += 1
                print(f"      servicio {servicio.nombre[:52]}")

                # Se devuelve la clave al diccionario para que el guion se
                # pueda ejecutar dos veces en el mismo proceso.
                datos_servicio["disponibilidad"] = disponibilidad

            primero = False

        sesion.commit()

    return proveedores_creados, servicios_creados


def main() -> int:
    configuracion = obtener_configuracion()

    if configuracion.entorno != "desarrollo":
        print(
            f"ERROR: el entorno es '{configuracion.entorno}'. Estos proveedores "
            "son inventados y no deben crearse fuera de desarrollo.",
            file=sys.stderr,
        )
        return 1

    print("=" * 74)
    print("PROVEEDORES Y SERVICIOS DE DEMOSTRACIÓN")
    print("=" * 74)
    print()
    print("  AVISO: ninguno de estos proveedores es real. No hay convenios con")
    print("  nadie del valle. Sirven para poder enseñar el flujo de coordinación.")
    print()

    proveedores, servicios = crear_proveedores_semilla()

    print()
    print(f"  Proveedores creados en esta ejecución: {proveedores}")
    print(f"  Servicios creados en esta ejecución  : {servicios}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
