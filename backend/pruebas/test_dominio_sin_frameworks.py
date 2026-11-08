"""El dominio no conoce ningun framework, y esto lo comprueba una maquina.

El criterio de la asignatura pide *«cero acoplamiento de frameworks en el
Dominio»*. Esa frase, escrita en un informe, es una afirmacion que nadie puede
verificar sin leer 68 archivos. Escrita como prueba automatica, es un hecho que
se comprueba en cada envio al repositorio.

## Por que con `ast` y no buscando texto

Buscar la palabra ``sqlalchemy`` con una expresion regular da falsos positivos
(un comentario que explica *por que* el dominio no usa SQLAlchemy contiene la
palabra) y falsos negativos (``__import__("sqla" + "lchemy")``). Leyendo el
arbol sintactico solo se ven importaciones de verdad: las que el interprete
ejecutaria.

## Que NO prohibe, y por que

OR-Tools, scikit-learn, NumPy, OSMnx, NetworkX y pysentimiento **si** pueden
aparecer en el dominio. Son librerias de calculo: no hablan con la red, ni con
el disco, ni con la base de datos. Un puerto delante de OR-Tools no
desacoplaria nada real, solo anadiria una capa que mantener. La decision esta
firmada en el ADR-017.

Lo que se prohibe es lo que ata el dominio a *como* se guardan o se entregan
los datos: el ORM, el driver, las migraciones, el marco web, el validador de
entrada y los clientes HTTP.
"""

import ast
from pathlib import Path

import pytest

#: Raiz del paquete. Este archivo vive en ``backend/pruebas/``.
RAIZ_DEL_PAQUETE = Path(__file__).resolve().parent.parent / "src"

DOMINIO = RAIZ_DEL_PAQUETE / "domain"

#: Los paquetes de nivel superior que el dominio no puede importar.
#:
#: Se compara contra la RAIZ del modulo importado, asi que ``sqlalchemy.orm``
#: cuenta como ``sqlalchemy`` sin tener que enumerar cada submodulo.
FRAMEWORKS_PROHIBIDOS = frozenset(
    {
        "fastapi",  # marco web: es un adaptador de entrada
        "starlette",  # lo que hay debajo de FastAPI
        "sqlalchemy",  # ORM: es un adaptador de salida
        "geoalchemy2",  # las extensiones geoespaciales del ORM
        "psycopg",  # el driver de PostgreSQL
        "alembic",  # las migraciones
        "pydantic",  # validacion de entrada y salida
        "httpx",  # cliente HTTP
        "requests",  # cliente HTTP
        "urllib3",  # cliente HTTP
    }
)


def _raices_importadas(archivo: Path) -> set[str]:
    """Devuelve el primer segmento de cada modulo que ``archivo`` importa."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    raices: set[str] = set()

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                raices.add(alias.name.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom):
            # `from . import x` tiene module None: es relativo, nunca externo.
            if nodo.level == 0 and nodo.module:
                raices.add(nodo.module.split(".")[0])

    return raices


def _modulos_del_dominio() -> list[Path]:
    return sorted(p for p in DOMINIO.rglob("*.py") if "__pycache__" not in p.parts)


def test_la_carpeta_del_dominio_existe_y_no_esta_vacia():
    """Una carpeta vacia pasaria todas las demas pruebas de este archivo.

    Sin esta comprobacion, borrar el dominio entero dejaria la suite en verde
    y el criterio «cero acoplamiento» se cumpliria por no tener nada que
    acoplar. Eso seria exactamente la trampa que este archivo existe para
    impedir.
    """
    assert DOMINIO.is_dir(), f"No existe {DOMINIO}"
    assert _modulos_del_dominio(), "El dominio no tiene ningun modulo"


@pytest.mark.parametrize("archivo", _modulos_del_dominio(), ids=lambda p: p.stem)
def test_el_modulo_del_dominio_no_importa_frameworks(archivo: Path):
    prohibidos = _raices_importadas(archivo) & FRAMEWORKS_PROHIBIDOS

    assert not prohibidos, (
        f"{archivo.relative_to(RAIZ_DEL_PAQUETE.parent)} importa "
        f"{sorted(prohibidos)}, que es infraestructura.\n"
        "El dominio pide los datos por un puerto; no va a buscarlos."
    )


#: Paquetes propios que el dominio tampoco puede importar.
#:
#: No basta con prohibir SQLAlchemy: importar ``src.modelos`` lo arrastra de
#: todos modos, y el acoplamiento seria el mismo con una capa de por medio.
#: ``src.servicios``, ``src.rutas`` y ``src.esquemas`` siguen siendo
#: infraestructura mientras no terminen las fases 3 a 6 de la migracion.
PAQUETES_DE_FUERA = (
    "src.adapters",
    "src.modelos",
    "src.rutas",
    "src.esquemas",
    "src.servicios",
    "src.ia",
    "src.base_datos",
)


def test_el_dominio_no_importa_hacia_afuera():
    """La dependencia apunta hacia adentro, nunca hacia afuera.

    Un modulo del dominio que importa `src.adapters` esta saltandose su
    propio puerto, aunque no toque SQLAlchemy directamente.
    """
    culpables: list[str] = []

    for archivo in _modulos_del_dominio():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            modulos = []
            if isinstance(nodo, ast.Import):
                modulos = [a.name for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                modulos = [nodo.module]

            for modulo in modulos:
                if modulo.startswith(PAQUETES_DE_FUERA):
                    culpables.append(f"{archivo.name} -> {modulo}")

    assert not culpables, "El dominio mira hacia afuera:\n" + "\n".join(culpables)
