"""Normaliza las rutas de los informes de cobertura para que SonarQube los lea.

    python normalizar_cobertura.py

## Por qué hace falta este paso

El escáner de SonarQube corre dentro de un contenedor Linux con el proyecto
montado en ``/usr/src``, y resuelve las rutas de los informes de cobertura
**relativas a ese directorio**. Los dos informes salen con rutas que ahí no
existen:

- ``backend/coverage.xml`` guarda en ``<source>`` la ruta **absoluta de
  Windows** del directorio ``backend/app`` y los nombres de archivo relativos a
  ella. Dentro del contenedor esa ruta no existe.
- ``frontend/coverage/lcov.info`` guarda ``SF:src\\componentes\\...``: relativo a
  ``frontend/`` y con **barras invertidas**. El escáner buscaría
  ``/usr/src/src/componentes/...``, que tampoco existe.

Resultado sin normalizar, medido: SonarQube informó **13,4 % de cobertura**
mientras pytest declaraba 73,42 % y vitest 74,5 %. No era un desacuerdo de
criterio: era que no había importado casi nada.

## Qué hace

Reescribe las rutas para que sean relativas a la raíz del repositorio y con
barras normales. **No toca ningún número de cobertura**: solo las rutas.
"""

from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent


def normalizar_xml() -> bool:
    """Deja <source> como ruta relativa a la raíz del repositorio."""
    ruta = RAIZ / "backend" / "coverage.xml"

    if not ruta.exists():
        print(f"  FALTA  {ruta.name}: genéralo con pytest --cov-report=xml")
        return False

    texto = ruta.read_text(encoding="utf-8")
    nuevo, cuantos = re.subn(
        r"<source>.*?</source>",
        "<source>backend/app</source>",
        texto,
        flags=re.DOTALL,
    )

    if cuantos == 0:
        print("  AVISO  coverage.xml no tiene <source>; no se toca")
        return False

    ruta.write_text(nuevo, encoding="utf-8")
    print(f"  OK     coverage.xml: {cuantos} <source> -> backend/app")
    return True


def normalizar_lcov() -> bool:
    """Deja cada SF: como frontend/src/... con barras normales."""
    ruta = RAIZ / "frontend" / "coverage" / "lcov.info"

    if not ruta.exists():
        print(f"  FALTA  {ruta.name}: genéralo con vitest --coverage")
        return False

    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cambiadas = 0
    salida = []

    for linea in lineas:
        if linea.startswith("SF:"):
            camino = linea[3:].replace("\\", "/").lstrip("./")

            # Si viniera con ruta absoluta, se recorta a partir de frontend/.
            if "frontend/" in camino:
                camino = camino[camino.index("frontend/") :]
            elif not camino.startswith("frontend/"):
                camino = f"frontend/{camino}"

            salida.append(f"SF:{camino}")
            cambiadas += 1
        else:
            salida.append(linea)

    ruta.write_text("\n".join(salida) + "\n", encoding="utf-8")
    print(f"  OK     lcov.info: {cambiadas} rutas normalizadas")
    return True


def principal() -> int:
    print("Normalizando las rutas de los informes de cobertura para SonarQube:")
    bien = normalizar_xml()
    bien = normalizar_lcov() and bien

    if not bien:
        print("\nFalta algún informe. El escáner correrá, pero sin cobertura.")
        return 1

    print("\nListo. Ahora el escáner puede resolver los archivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
