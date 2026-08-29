"""Conexion a PostgreSQL y sesiones de SQLAlchemy.

Aqui se crean dos cosas que el resto del backend reutiliza:

- el *motor*: el objeto que mantiene el grupo de conexiones abiertas a
  PostgreSQL. Se crea una sola vez al arrancar la aplicacion, porque abrir
  una conexion es caro.
- la *sesion*: la unidad de trabajo de una peticion. Se abre al empezar a
  atender una peticion HTTP y se cierra al terminar, pase lo que pase.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.configuracion import obtener_configuracion

configuracion = obtener_configuracion()

# pool_pre_ping comprueba que la conexion siga viva antes de usarla. Sin esto,
# si el contenedor de Postgres se reinicia, la aplicacion arrastra conexiones
# muertas y falla la siguiente peticion.
motor = create_engine(
    configuracion.url_base_datos,
    pool_pre_ping=True,
    echo=False,
)

FabricaDeSesiones = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base de la que heredan todas las tablas del proyecto.

    SQLAlchemy usa esta clase para llevar el registro de las tablas definidas,
    y Alembic lo lee para generar las migraciones automaticamente.
    """


def obtener_sesion() -> Generator[Session, None, None]:
    """Entrega una sesion de base de datos a un endpoint y la cierra al final.

    FastAPI llama a esta funcion por cada peticion que la declare como
    dependencia. El bloque try/finally garantiza que la sesion se cierre
    aunque el endpoint lance una excepcion.
    """
    sesion = FabricaDeSesiones()
    try:
        yield sesion
    finally:
        sesion.close()
