"""Pruebas de la importación del catálogo desde el inventario del MINCETUR."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select

from app.modelos.catalogo import RecursoTuristico
from app.servicios.catalogo import (
    convertir_a_numero,
    convertir_fecha_de_corte,
    detectar_codificacion,
    detectar_orden_de_coordenadas,
    importar_inventario,
    normalizar_cabecera,
    normalizar_texto,
)

# ---------------------------------------------------------------------------
# Normalización de texto
# ---------------------------------------------------------------------------


class TestNormalizarTexto:
    """La normalización es lo que permite comparar nombres de distrito.

    Sin ella, "CONCEPCIÓN" y "Concepcion" contarían como dos provincias
    distintas y los filtros no encontrarían la mitad de los recursos.
    """

    def test_quita_tildes_y_pasa_a_mayusculas(self):
        assert normalizar_texto("Concepción") == "CONCEPCION"
        assert normalizar_texto("junín") == "JUNIN"

    def test_quita_los_espacios_sobrantes(self):
        assert normalizar_texto("  Jauja  ") == "JAUJA"

    def test_devuelve_cadena_vacia_para_valores_ausentes(self):
        # Caso borde: pandas representa las celdas vacías como NaN, que es un
        # float. Si no se contempla, str(NaN) daría el texto "nan".
        assert normalizar_texto(None) == ""
        assert normalizar_texto(float("nan")) == ""

    def test_conserva_la_ene(self):
        # La Ñ no es una N con tilde: es una letra propia y debe sobrevivir.
        assert normalizar_texto("Ñuñoa") == "ÑUÑOA"


# ---------------------------------------------------------------------------
# Conversión de valores
# ---------------------------------------------------------------------------


class TestConvertirValores:
    def test_acepta_el_punto_decimal(self):
        assert convertir_a_numero("-12.0687") == pytest.approx(-12.0687)

    def test_acepta_la_coma_decimal(self):
        # Caso borde: algunos archivos oficiales usan coma. Descartar esas
        # filas perdería coordenadas válidas por un detalle de formato.
        assert convertir_a_numero("-12,0687") == pytest.approx(-12.0687)

    def test_devuelve_none_si_no_es_un_numero(self):
        assert convertir_a_numero("") is None
        assert convertir_a_numero("s/d") is None
        assert convertir_a_numero(None) is None

    def test_interpreta_la_fecha_de_corte_en_formato_aaaammdd(self):
        assert convertir_fecha_de_corte("20260827") == date(2026, 8, 27)

    def test_interpreta_otros_formatos_de_fecha_habituales(self):
        assert convertir_fecha_de_corte("27/08/2026") == date(2026, 8, 27)
        assert convertir_fecha_de_corte("2026-08-27") == date(2026, 8, 27)

    def test_devuelve_none_si_la_fecha_es_ilegible(self):
        assert convertir_fecha_de_corte("no es fecha") is None
        assert convertir_fecha_de_corte("") is None


# ---------------------------------------------------------------------------
# Lectura del archivo
# ---------------------------------------------------------------------------


class TestDetectarCodificacion:
    def test_detecta_cp1252(self, csv_de_ejemplo: Path):
        # El inventario real del MINCETUR viene en cp1252. Leerlo como UTF-8
        # rompería todos los nombres con tilde.
        assert detectar_codificacion(csv_de_ejemplo) in {"cp1252", "latin-1"}

    def test_detecta_utf8(self, tmp_path: Path):
        ruta = tmp_path / "utf8.csv"
        ruta.write_bytes("REGIÓN;PROVINCIA\nJunín;Huancayo\n".encode())
        # utf-8-sig acepta también los archivos sin marca de orden de bytes,
        # así que es la primera candidata que responde. Da igual cuál de las
        # dos etiquetas devuelva: el texto se lee idéntico.
        assert detectar_codificacion(ruta) in {"utf-8", "utf-8-sig"}


class TestDetectarOrdenDeCoordenadas:
    """La comprobación más importante del importador.

    El archivo oficial trae los rótulos LATITUD y LONGITUD intercambiados. El
    código no lo da por hecho: lo decide mirando los datos. Estas pruebas
    fijan los dos casos.
    """

    @staticmethod
    def _marco(latitudes: list[str], longitudes: list[str]) -> tuple:
        marco = pd.DataFrame({"LATITUD": latitudes, "LONGITUD": longitudes})
        return marco, normalizar_cabecera(list(marco.columns))

    def test_detecta_que_estan_intercambiadas(self):
        # Como viene el archivo real: en LATITUD hay longitudes (-75.x).
        marco, cabecera = self._marco(["-75.21", "-75.31"], ["-12.07", "-11.92"])
        assert detectar_orden_de_coordenadas(marco, cabecera) is True

    def test_detecta_que_estan_bien(self):
        # Si el MINCETUR corrige el archivo, el importador no debe romperlo.
        marco, cabecera = self._marco(["-12.07", "-11.92"], ["-75.21", "-75.31"])
        assert detectar_orden_de_coordenadas(marco, cabecera) is False

    def test_ignora_las_filas_sin_coordenadas(self):
        # Caso borde: filas vacías mezcladas no deben confundir la decisión.
        marco, cabecera = self._marco(["-75.21", "", None], ["-12.07", "", None])
        assert detectar_orden_de_coordenadas(marco, cabecera) is True


# ---------------------------------------------------------------------------
# Importación completa (necesita base de datos)
# ---------------------------------------------------------------------------


class TestImportarInventario:
    def test_importa_solo_los_recursos_de_la_ruta(self, sesion, csv_de_ejemplo: Path):
        """De las 5 filas del CSV, solo 3 son de las provincias de la ruta."""
        resultado = importar_inventario(sesion, csv_de_ejemplo)

        assert resultado.filas_en_el_archivo == 5
        assert resultado.filas_de_junin == 4  # 3 de la ruta + Tarma
        assert resultado.filas_de_la_ruta == 3
        assert resultado.insertados == 3

    def test_corrige_las_coordenadas_intercambiadas(self, sesion, csv_de_ejemplo: Path):
        """La coordenada debe quedar guardada en el orden correcto.

        En el CSV, la Plaza de la Constitución trae LATITUD=-75.21 y
        LONGITUD=-12.068. Tras importar debe estar en latitud -12.068 y
        longitud -75.21, que es donde de verdad está Huancayo.
        """
        resultado = importar_inventario(sesion, csv_de_ejemplo)
        assert resultado.coordenadas_estaban_intercambiadas is True

        punto = cast(RecursoTuristico.ubicacion, Geometry)
        latitud, longitud = sesion.execute(
            select(func.ST_Y(punto), func.ST_X(punto)).where(
                RecursoTuristico.codigo_mincetur == "900001"
            )
        ).one()

        assert latitud == pytest.approx(-12.068)
        assert longitud == pytest.approx(-75.21)

    def test_guarda_sin_ubicacion_los_recursos_sin_coordenadas(self, sesion, csv_de_ejemplo: Path):
        """Regla de honestidad: no se inventa una coordenada, se deja nula."""
        resultado = importar_inventario(sesion, csv_de_ejemplo)

        assert resultado.sin_coordenadas == 1

        recurso = sesion.scalars(
            select(RecursoTuristico).where(RecursoTuristico.codigo_mincetur == "900003")
        ).one()
        assert recurso.ubicacion is None

    def test_descarta_los_recursos_de_otras_regiones_y_provincias(
        self, sesion, csv_de_ejemplo: Path
    ):
        importar_inventario(sesion, csv_de_ejemplo)

        codigos = set(sesion.scalars(select(RecursoTuristico.codigo_mincetur)).all())

        assert "900004" not in codigos, "no debe importarse un recurso de Cusco"
        assert "900005" not in codigos, "no debe importarse un recurso de Tarma"

    def test_es_idempotente(self, sesion, csv_de_ejemplo: Path):
        """Importar dos veces no debe duplicar recursos.

        Es lo que permite volver a cargar el inventario cuando el MINCETUR
        publique una versión nueva, sin tener que vaciar la tabla.
        """
        primera = importar_inventario(sesion, csv_de_ejemplo)
        segunda = importar_inventario(sesion, csv_de_ejemplo)

        assert primera.insertados == 3
        assert segunda.insertados == 0
        assert segunda.actualizados == 3

        total = sesion.scalar(select(func.count()).select_from(RecursoTuristico))
        assert total == 3

    def test_normaliza_provincia_y_distrito(self, sesion, csv_de_ejemplo: Path):
        importar_inventario(sesion, csv_de_ejemplo)

        recurso = sesion.scalars(
            select(RecursoTuristico).where(RecursoTuristico.codigo_mincetur == "900002")
        ).one()

        # En el CSV viene "Concepción" con tilde y minúsculas.
        assert recurso.provincia == "CONCEPCION"
        assert recurso.distrito == "SANTA ROSA DE OCOPA"

    def test_guarda_la_fecha_de_corte(self, sesion, csv_de_ejemplo: Path):
        importar_inventario(sesion, csv_de_ejemplo)

        recurso = sesion.scalars(
            select(RecursoTuristico).where(RecursoTuristico.codigo_mincetur == "900001")
        ).one()

        assert recurso.fecha_corte == date(2026, 8, 27)

    def test_falla_con_mensaje_claro_si_faltan_columnas(self, sesion, tmp_path: Path):
        """Caso borde: si el MINCETUR cambia la cabecera, hay que enterarse."""
        ruta = tmp_path / "mal.csv"
        ruta.write_text("COLUMNA_A;COLUMNA_B\n1;2\n", encoding="utf-8")

        with pytest.raises(ValueError, match="no tiene las columnas esperadas"):
            importar_inventario(sesion, ruta)
