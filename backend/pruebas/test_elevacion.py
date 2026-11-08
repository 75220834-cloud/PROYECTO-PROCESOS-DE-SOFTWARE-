"""Pruebas del muestreo de altitudes sobre el modelo Copernicus GLO-30.

## Por qué estas pruebas no bajan nada de internet

El módulo descarga teselas de AWS Open Data. Una prueba que descargara de
verdad tardaría minutos, fallaría sin conexión y le pegaría a un servicio
público por nada. Lo que se comprueba aquí es lo que el proyecto escribió:

- **la geometría de las teselas**, que es aritmética pura y donde un error de
  signo manda a buscar la tesela equivocada al otro lado del mundo;
- **la idempotencia de la descarga**, que es lo que evita bajar 100 MB dos
  veces;
- **el cuidado con el archivo a medias**, que evita que una descarga
  interrumpida deje una tesela corrupta con pinta de completa;
- **la diferencia entre «cero metros» y «no lo sé»**, que es la decisión más
  importante del módulo.

La red se sustituye por un doble; el formato GeoTIFF, también. Lo que se
comprueba es el código del proyecto, no la biblioteca que lee rásteres.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.adapters.outbound import elevacion_copernicus as elevacion
from src.adapters.outbound.elevacion_copernicus import (
    MuestreadorDeAltitud,
    descargar_tesela,
    nombre_de_tesela,
    ruta_local_de_tesela,
    teselas_necesarias,
)


class TestNombreDeTesela:
    def test_el_ejemplo_documentado_en_el_propio_modulo(self):
        """El docstring dice que (−12,5, −75,5) está en S13/W076. Se comprueba."""
        assert nombre_de_tesela(-12.5, -75.5) == ("S13", "W076")

    def test_usa_el_suelo_y_no_el_redondeo(self):
        """Las teselas se nombran por su esquina SUROESTE.

        Con redondeo, −12,5 daría −12 y se pediría la tesela de al lado. Es un
        error que no rompe nada visiblemente: devuelve altitudes de otro sitio.
        """
        assert nombre_de_tesela(-12.9, -75.1)[0] == "S13"
        assert nombre_de_tesela(-12.1, -75.9)[0] == "S13"

    @pytest.mark.parametrize(
        ("latitud", "longitud", "esperado"),
        [
            (-12.07, -75.21, ("S13", "W076")),  # Huancayo
            (0.5, 0.5, ("N00", "E000")),  # el origen, los dos positivos
            (-0.5, -0.5, ("S01", "W001")),  # justo al otro lado del origen
            (45.3, 120.8, ("N45", "E120")),  # hemisferio norte y este
            (-33.9, -70.6, ("S34", "W071")),  # Santiago de Chile
        ],
    )
    def test_hemisferios_y_signos(self, latitud, longitud, esperado):
        assert nombre_de_tesela(latitud, longitud) == esperado

    def test_la_longitud_lleva_tres_digitos_y_la_latitud_dos(self):
        """Es el formato del nombre de archivo de Copernicus, no un capricho."""
        lat, lon = nombre_de_tesela(-9.0, -5.0)

        assert len(lat) == 3  # S09
        assert len(lon) == 4  # W005


class TestRutaLocalDeTesela:
    def test_compone_el_nombre_de_archivo_de_copernicus(self):
        ruta = ruta_local_de_tesela(-12.07, -75.21)

        assert ruta.name == "Copernicus_DSM_COG_10_S13_00_W076_00_DEM.tif"

    def test_cuelga_de_la_carpeta_de_teselas(self, monkeypatch, tmp_path):
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)

        assert ruta_local_de_tesela(-12.07, -75.21).parent == tmp_path


class _RespuestaFalsa:
    """Doble de la respuesta de httpx.stream, sin red."""

    def __init__(self, bloques: list[bytes], error: Exception | None = None):
        self._bloques = bloques
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        if self._error is not None:
            raise self._error

    def iter_bytes(self, chunk_size: int = 0):
        yield from self._bloques


class TestDescargarTesela:
    def test_no_vuelve_a_descargar_si_la_tesela_ya_esta(self, monkeypatch, tmp_path):
        """Idempotencia: una tesela pesa decenas de megas."""
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        destino = ruta_local_de_tesela(-12.07, -75.21)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"tesela ya descargada")

        def no_debe_llamarse(*_, **__):
            raise AssertionError("intentó descargar una tesela que ya estaba")

        monkeypatch.setattr(elevacion.httpx, "stream", no_debe_llamarse)

        assert descargar_tesela(-12.07, -75.21) == destino

    def test_un_archivo_vacio_no_cuenta_como_descargado(self, monkeypatch, tmp_path):
        """Un archivo de 0 bytes es una descarga fallida, no una tesela."""
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        destino = ruta_local_de_tesela(-12.07, -75.21)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"")

        monkeypatch.setattr(
            elevacion.httpx, "stream", lambda *a, **k: _RespuestaFalsa([b"datos buenos"])
        )

        assert descargar_tesela(-12.07, -75.21).read_bytes() == b"datos buenos"

    def test_descarga_y_junta_los_bloques_en_orden(self, monkeypatch, tmp_path):
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        monkeypatch.setattr(
            elevacion.httpx,
            "stream",
            lambda *a, **k: _RespuestaFalsa([b"uno", b"dos", b"tres"]),
        )

        destino = descargar_tesela(-12.07, -75.21)

        assert destino.read_bytes() == b"unodostres"

    def test_pide_la_url_de_la_tesela_que_corresponde(self, monkeypatch, tmp_path):
        """Un error de signo aquí descargaría la tesela del hemisferio opuesto."""
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        pedidas: list[str] = []

        def espiar(metodo, url, **_):
            pedidas.append(url)
            return _RespuestaFalsa([b"x"])

        monkeypatch.setattr(elevacion.httpx, "stream", espiar)

        descargar_tesela(-12.07, -75.21)

        assert len(pedidas) == 1
        assert "S13_00_W076" in pedidas[0]

    def test_una_descarga_fallida_no_deja_una_tesela_a_medias(self, monkeypatch, tmp_path):
        """Lo que protege el archivo temporal.

        Si el servidor responde con error, no debe quedar ningún archivo con el
        nombre definitivo: la siguiente ejecución lo daría por bueno y el
        cálculo de pendientes usaría datos truncados sin avisar.
        """
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        monkeypatch.setattr(
            elevacion.httpx,
            "stream",
            lambda *a, **k: _RespuestaFalsa([], error=RuntimeError("503 del servidor")),
        )

        with pytest.raises(RuntimeError):
            descargar_tesela(-12.07, -75.21)

        assert not ruta_local_de_tesela(-12.07, -75.21).exists()

    def test_crea_la_carpeta_si_no_existia(self, monkeypatch, tmp_path):
        carpeta = tmp_path / "ni" / "existe" / "todavia"
        monkeypatch.setattr(elevacion, "CARPETA_DEM", carpeta)
        monkeypatch.setattr(elevacion.httpx, "stream", lambda *a, **k: _RespuestaFalsa([b"x"]))

        assert descargar_tesela(-12.07, -75.21).exists()


#: Marca que la tesela no devuelve ninguna muestra para ese punto.
#:
#: No se simula lanzando StopIteration: desde PEP 479, lanzarlo DENTRO de un
#: generador lo convierte en RuntimeError, que no es lo que el codigo captura.
#: Lo que de verdad ocurre es que `sample` no produce nada y el `next()` de
#: `altitud` es el que levanta StopIteration.
SIN_MUESTRA = object()


class _TeselaFalsa:
    """Doble de un GeoTIFF abierto con rasterio."""

    def __init__(self, valor, nodata=None):
        self._valor = valor
        self.nodata = nodata
        self.cerrada = False

    def sample(self, _puntos):
        if self._valor is SIN_MUESTRA:
            return
        if isinstance(self._valor, Exception):
            raise self._valor
        yield [self._valor]

    def close(self):
        self.cerrada = True


class TestMuestreadorDeAltitud:
    def test_sin_tesela_descargada_devuelve_desconocido(self, monkeypatch, tmp_path):
        """No hay archivo: la respuesta es «no lo sé», no un cero."""
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)

        with MuestreadorDeAltitud() as muestreador:
            assert muestreador.altitud(-12.07, -75.21) is None

    def test_devuelve_la_altitud_cuando_la_tesela_tiene_dato(self):
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(3250.0)

        assert muestreador.altitud(-12.07, -75.21) == 3250.0

    def test_el_valor_de_sin_dato_del_archivo_se_traduce_a_desconocido(self):
        """Se compara con el nodata declarado en el archivo, no con un número fijo."""
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(
            -32768.0, nodata=-32768.0
        )

        assert muestreador.altitud(-12.07, -75.21) is None

    @pytest.mark.parametrize("valor", [-500.0, -9999.0])
    def test_los_valores_muy_negativos_son_mar_o_hueco(self, valor):
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(valor)

        assert muestreador.altitud(-12.07, -75.21) is None

    def test_cero_metros_es_una_altitud_valida_y_no_un_hueco(self):
        """La decisión que explica el módulo: en la costa, cero es un dato.

        Confundirlo con «no lo sé» haría que un tramo pareciera una bajada de
        3 250 metros.
        """
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(0.0)

        assert muestreador.altitud(-12.07, -75.21) == 0.0

    @pytest.mark.parametrize(
        "fallo", [SIN_MUESTRA, IndexError(), ValueError("fuera de los límites")]
    )
    def test_un_fallo_al_muestrear_devuelve_desconocido_y_no_revienta(self, fallo):
        """Un punto fuera de la tesela no puede tumbar el cálculo entero.

        Los tres casos del código: que la tesela no devuelva ninguna muestra
        (StopIteration en el `next`), que el resultado venga vacío (IndexError)
        y que el punto caiga fuera de los límites del ráster (ValueError).
        """
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(fallo)

        assert muestreador.altitud(-12.07, -75.21) is None

    def test_muestrea_varios_puntos_de_una_vez(self):
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[nombre_de_tesela(-12.07, -75.21)] = _TeselaFalsa(3250.0)

        alturas = muestreador.altitudes([(-12.07, -75.21), (-12.08, -75.22)])

        assert alturas == [3250.0, 3250.0]

    def test_reutiliza_la_tesela_abierta_en_vez_de_abrirla_cada_vez(self, monkeypatch, tmp_path):
        """Es la razón de ser de la clase: abrir el GeoTIFF por consulta sería lentísimo."""
        monkeypatch.setattr(elevacion, "CARPETA_DEM", tmp_path)
        muestreador = MuestreadorDeAltitud()

        muestreador.altitud(-12.07, -75.21)
        muestreador.altitud(-12.08, -75.22)

        # Los dos puntos caen en la misma tesela: solo debe haber una entrada.
        assert len(muestreador._teselas) == 1

    def test_al_cerrar_cierra_las_teselas_abiertas(self):
        tesela = _TeselaFalsa(3250.0)
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[("S13", "W076")] = tesela

        muestreador.cerrar()

        assert tesela.cerrada is True
        assert muestreador._teselas == {}

    def test_cerrar_no_se_atraganta_con_las_teselas_que_faltaban(self):
        """Las ausentes se guardan como None; cerrarlas no debe reventar."""
        muestreador = MuestreadorDeAltitud()
        muestreador._teselas[("S13", "W076")] = None

        muestreador.cerrar()

        assert muestreador._teselas == {}

    def test_sirve_como_gestor_de_contexto(self):
        tesela = _TeselaFalsa(3250.0)

        with MuestreadorDeAltitud() as muestreador:
            muestreador._teselas[("S13", "W076")] = tesela

        assert tesela.cerrada is True


class TestTeselasNecesarias:
    def test_un_rectangulo_dentro_de_una_sola_tesela_da_un_punto(self):
        # El Valle del Mantaro cabe holgadamente en una tesela de un grado.
        puntos = teselas_necesarias((-75.4, -12.3, -75.1, -12.1))

        assert len(puntos) == 1
        assert nombre_de_tesela(*puntos[0]) == ("S13", "W076")

    def test_un_borde_exacto_arrastra_la_tesela_siguiente(self):
        """Comportamiento de borde, documentado porque sorprende.

        Un rectángulo que termina justo en el grado −12,0 toca ya la tesela que
        empieza ahí, porque floor(−12,0) es −12. Pedir una tesela de más es
        inofensivo —se descarga y no se usa—; pedir una de menos dejaría puntos
        sin altitud.
        """
        puntos = teselas_necesarias((-75.4, -12.3, -75.1, -12.0))

        assert len(puntos) == 2

    def test_un_rectangulo_a_caballo_entre_teselas_las_da_todas(self):
        puntos = teselas_necesarias((-76.5, -13.5, -74.5, -11.5))

        # De −14 a −12 son 3 grados de latitud; de −77 a −75, 3 de longitud.
        assert len(puntos) == 9

    def test_devuelve_el_centro_de_cada_tesela(self):
        """Un punto del borde podría caer en la tesela de al lado."""
        puntos = teselas_necesarias((-75.9, -12.9, -75.1, -12.1))

        for latitud, longitud in puntos:
            assert math.isclose(latitud % 1, 0.5)
            assert math.isclose(longitud % 1, 0.5)

    def test_los_puntos_que_devuelve_sirven_para_nombrar_teselas(self):
        """Comprueba que las dos funciones encajan entre sí."""
        puntos = teselas_necesarias((-76.5, -13.5, -75.5, -12.5))
        nombres = {nombre_de_tesela(lat, lon) for lat, lon in puntos}

        assert ("S13", "W076") in nombres
        assert len(nombres) == len(puntos)  # ninguna repetida


def test_la_carpeta_de_teselas_cuelga_del_backend():
    """CARPETA_DEM se calcula con parents[2]; un cambio de ubicación lo rompe."""
    assert elevacion.CARPETA_DEM.name == "dem"
    assert elevacion.CARPETA_DEM.parent.name == "datos"
    assert isinstance(elevacion.CARPETA_DEM, Path)
