"""Configuración de Alembic, la herramienta de migraciones.

Una *migración* es un archivo que describe un cambio del esquema de la base de
datos (crear una tabla, añadir una columna) y cómo deshacerlo. Se versionan en
el repositorio, de modo que cualquier persona del equipo puede poner su base
de datos exactamente en el mismo estado ejecutando un solo comando.

Este archivo hace tres cosas:
1. Toma la URL de conexión de la configuración de la aplicación, no de
   alembic.ini, para que no haya contraseñas escritas en el repositorio.
2. Le da a Alembic el catálogo de tablas del proyecto, para que pueda
   comparar el código con la base de datos real y generar las migraciones.
3. Le indica que solo mire las tablas declaradas en el código: sin ese
   filtro intentaría borrar las tablas que instalan las extensiones de
   PostgreSQL.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.base_datos import Base
from app.configuracion import obtener_configuracion

# Importar los módulos de modelos es lo que registra las tablas en Base.
# Sin este import, Alembic no vería ninguna tabla y generaría migraciones vacías.
from app.modelos import catalogo  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La contraseña vive en el .env, nunca en alembic.ini.
config.set_main_option("sqlalchemy.url", obtener_configuracion().url_base_datos)

target_metadata = Base.metadata


def incluir_objeto(objeto, nombre, tipo, reflejado, objeto_comparado) -> bool:
    """Decide si Alembic debe tener en cuenta un objeto de la base de datos.

    En lugar de mantener una lista negra de lo que hay que excluir, se usa una
    lista blanca: solo se consideran las tablas que el proyecto declara en sus
    modelos. Es mucho más robusto, porque cualquier tabla que aparezca en la
    base sin estar en el código —las que instala una extensión, una tabla de
    pruebas olvidada— se ignora sola, sin tener que preverla.

    De los índices se excluyen los que empiezan por ``idx_``: así nombra
    GeoAlchemy2 los índices espaciales que crea y elimina por su cuenta al
    gestionar la columna geográfica. Si no se excluyeran, cada migración
    intentaría borrarlos y volverlos a crear.
    """
    if tipo == "table":
        return nombre in target_metadata.tables

    if tipo == "index" and nombre is not None and nombre.startswith("idx_"):
        return False

    return True


def ejecutar_migraciones_sin_conexion() -> None:
    """Genera el SQL de las migraciones sin conectarse a la base de datos.

    Útil para revisar qué se va a ejecutar antes de tocar una base real.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=incluir_objeto,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones_con_conexion() -> None:
    """Aplica las migraciones contra la base de datos configurada."""
    motor = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            include_object=incluir_objeto,
            # Detecta también los cambios de tipo de una columna, no solo que
            # la columna exista.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_migraciones_sin_conexion()
else:
    ejecutar_migraciones_con_conexion()
