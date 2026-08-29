"""Crea un usuario de ejemplo por cada rol del proyecto.

Sirve para poder demostrar la aplicación sin tener que registrar cinco cuentas
a mano antes de cada exposición.

**ESTAS CREDENCIALES SON DE DESARROLLO.** Están escritas en el repositorio a
propósito, para que cualquiera del equipo pueda levantar el proyecto y entrar.
No sirven para nada fuera de una base de datos local: no hay despliegue, y si
lo hubiera, este guion no debe ejecutarse allí. El propio guion se niega a
correr si el entorno no es de desarrollo.

Se ejecuta desde ``backend/``:

    python -m app.utilidades.usuarios_semilla
"""

from __future__ import annotations

import sys

from app.base_datos import FabricaDeSesiones
from app.configuracion import obtener_configuracion
from app.modelos.usuario import RolUsuario
from app.servicios.usuarios import buscar_por_correo, registrar_usuario

#: Un usuario por rol. La contraseña es la misma para todos a propósito: son
#: de demostración y recordar cinco distintas no aporta nada.
CONTRASENA_DE_DEMOSTRACION = "RutaViva2026"

USUARIOS_SEMILLA: list[dict[str, str]] = [
    {
        "correo": "visitante@rutavivamantaro.pe",
        "nombre": "Visitante de demostración",
        "rol": RolUsuario.VISITANTE.value,
    },
    {
        "correo": "proveedor@rutavivamantaro.pe",
        "nombre": "Proveedor de demostración",
        "rol": RolUsuario.PROVEEDOR.value,
    },
    {
        "correo": "operador@rutavivamantaro.pe",
        "nombre": "Operador de demostración",
        "rol": RolUsuario.OPERADOR.value,
    },
    {
        "correo": "gestor@rutavivamantaro.pe",
        "nombre": "Gestor municipal de demostración",
        "rol": RolUsuario.GESTOR.value,
    },
    {
        "correo": "administrador@rutavivamantaro.pe",
        "nombre": "Administrador de demostración",
        "rol": RolUsuario.ADMINISTRADOR.value,
    },
]


def crear_usuarios_semilla() -> int:
    """Crea los usuarios que falten. Devuelve cuántos creó.

    Es idempotente: se puede ejecutar las veces que haga falta sin duplicar.
    """
    creados = 0

    with FabricaDeSesiones() as sesion:
        for datos in USUARIOS_SEMILLA:
            if buscar_por_correo(sesion, datos["correo"]) is not None:
                print(f"  ya existía   {datos['correo']:<42} ({datos['rol']})")
                continue

            registrar_usuario(
                sesion,
                correo=datos["correo"],
                contrasena=CONTRASENA_DE_DEMOSTRACION,
                nombre=datos["nombre"],
                rol=datos["rol"],
            )
            creados += 1
            print(f"  creado       {datos['correo']:<42} ({datos['rol']})")

    return creados


def main() -> int:
    configuracion = obtener_configuracion()

    # Salvaguarda: estas credenciales están escritas en el repositorio, así
    # que crear estas cuentas fuera de desarrollo sería abrir cinco puertas.
    if configuracion.entorno != "desarrollo":
        print(
            f"ERROR: el entorno es '{configuracion.entorno}'. Estos usuarios de "
            "demostración solo se crean en desarrollo.",
            file=sys.stderr,
        )
        return 1

    print("=" * 70)
    print("USUARIOS DE DEMOSTRACIÓN")
    print("=" * 70)

    creados = crear_usuarios_semilla()

    print()
    print(f"  Creados en esta ejecución: {creados}")
    print(f"  Contraseña de todos ellos: {CONTRASENA_DE_DEMOSTRACION}")
    print()
    print("  Son credenciales de desarrollo. No usar fuera de una base local.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
