"""Preparación común de las pruebas del backend.

Aquí viven las *fixtures*: piezas que varias pruebas necesitan y que pytest
inyecta automáticamente cuando una prueba las pide por nombre.

La decisión importante de este archivo: las pruebas que necesitan base de
datos **no la simulan**. Usan PostgreSQL con PostGIS de verdad, porque el
proyecto se apoya en funciones geográficas (ST_X, ST_Y, índices GIST) que
ninguna base simulada implementa. Simularlas daría pruebas que pasan mientras
el código real falla.

A cambio, cada prueba corre dentro de una transacción que se deshace al
terminar, así que nunca alteran el catálogo real. Y si la base no está
levantada, esas pruebas se saltan con un aviso claro en vez de fallar.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.base_datos import motor


def hay_base_de_datos() -> bool:
    """Comprueba si PostgreSQL responde y tiene PostGIS."""
    try:
        with motor.connect() as conexion:
            conexion.execute(text("SELECT postgis_version()"))
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo significa "no disponible"
        return False


#: Marca para las pruebas que necesitan la base de datos levantada.
necesita_base_de_datos = pytest.mark.skipif(
    not hay_base_de_datos(),
    reason="Requiere PostgreSQL con PostGIS. Levántalo con: docker compose up -d",
)


@pytest.fixture
def sesion(request: pytest.FixtureRequest) -> Generator[Session, None, None]:
    """Sesión de base de datos que deshace todos sus cambios al terminar.

    Cómo funciona: se abre una transacción externa antes de entregar la
    sesión y se anula al final. Todo lo que la prueba inserte, actualice o
    borre desaparece, aunque la prueba llame a ``commit()`` — porque ese
    commit ocurre dentro de la transacción externa, que nunca se confirma.
    """
    if not hay_base_de_datos():
        pytest.skip("Requiere PostgreSQL con PostGIS levantado")

    conexion = motor.connect()
    transaccion = conexion.begin()
    sesion_de_prueba = Session(bind=conexion, join_transaction_mode="create_savepoint")

    # Se parte de un catálogo vacío para que las pruebas puedan afirmar
    # totales exactos ("deben quedar 3 recursos") sin que los 295 recursos
    # reales del inventario las estropeen. Este borrado también se deshace al
    # terminar, así que los datos reales no corren ningún peligro.
    sesion_de_prueba.execute(
        text("TRUNCATE recurso_turistico, horario_atencion, registro_validacion CASCADE")
    )

    try:
        yield sesion_de_prueba
    finally:
        sesion_de_prueba.close()
        transaccion.rollback()
        conexion.close()


@pytest.fixture
def csv_de_ejemplo(tmp_path: Path) -> Path:
    """Crea un CSV pequeño con la misma estructura que el archivo del MINCETUR.

    Contiene a propósito los mismos defectos que el archivo real, para que las
    pruebas ejerciten el código que los corrige:

    - Codificación cp1252 (con tildes en bytes de un solo byte).
    - Columnas LATITUD y LONGITUD **intercambiadas**.
    - Una fila sin coordenadas.
    - Una fila de otra región, que debe descartarse.
    - Una fila de Junín pero de una provincia fuera de la ruta.
    """
    contenido = (
        "REGIÓN;PROVINCIA;DISTRITO;CODIGO DEL RECURSO;NOMBRE DEL RECURSO;"
        "CATEGORÍA;TIPO DE CATEGORÍA;SUB TIPO CATEGORÍA;URL;LATITUD;LONGITUD;FECHA_DE_CORTE\n"
        # Válido, con coordenadas intercambiadas como en el archivo real.
        "Junín;Huancayo;HUANCAYO;900001;Plaza de la Constitución;"
        "2. MANIFESTACIONES CULTURALES;Plazas;Plaza;https://ejemplo.pe/1;"
        "-75.21;-12.068;20260827\n"
        # Válido, en Concepción.
        "Junín;Concepción;SANTA ROSA DE OCOPA;900002;Convento de Santa Rosa de Ocopa;"
        "2. MANIFESTACIONES CULTURALES;Museos;Convento;https://ejemplo.pe/2;"
        "-75.3103;-11.9169;20260827\n"
        # Sin coordenadas: debe importarse igual, pero sin ubicación.
        "Junín;Jauja;JAUJA;900003;Recurso sin coordenadas;"
        "3. FOLCLORE;Ferias;Feria;;;;20260827\n"
        # Otra región: debe descartarse.
        "Cusco;Cusco;CUSCO;900004;Recurso de otra región;"
        "1. SITIOS NATURALES;Lagunas;Laguna;;-71.97;-13.53;20260827\n"
        # Junín pero provincia fuera de la ruta: debe descartarse.
        "Junín;Tarma;TARMA;900005;Recurso fuera de la ruta;"
        "1. SITIOS NATURALES;Valles;Valle;;-75.69;-11.42;20260827\n"
    )

    ruta = tmp_path / "inventario_de_prueba.csv"
    ruta.write_bytes(contenido.encode("cp1252"))
    return ruta
