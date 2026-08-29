"""Pruebas del hasheo de contraseñas y de los tokens de sesión.

Es el módulo más delicado del proyecto: un fallo aquí no rompe una pantalla,
expone las cuentas de todo el mundo. Se prueba sin base de datos, porque es
lógica pura.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.servicios.seguridad import (
    crear_token_de_acceso,
    hashear_contrasena,
    leer_token_de_acceso,
    verificar_contrasena,
)

CONTRASENA = "unaClaveSegura1"


class TestHasheoDeContrasenas:
    def test_el_hash_no_contiene_la_contrasena(self):
        """Lo primero que hay que poder afirmar: la contraseña no se guarda."""
        hash_generado = hashear_contrasena(CONTRASENA)

        assert CONTRASENA not in hash_generado

    def test_usa_argon2id(self):
        # El prefijo del hash declara el algoritmo. argon2id es la variante
        # recomendada por OWASP: resiste tanto ataques con GPU como los que
        # explotan los tiempos de acceso a memoria.
        assert hashear_contrasena(CONTRASENA).startswith("$argon2id$")

    def test_la_misma_contrasena_da_hashes_distintos(self):
        """Cada hash lleva su propia sal aleatoria.

        Si dos usuarios con la misma contraseña tuvieran el mismo hash, una
        tabla de hashes precalculados los rompería a los dos de golpe.
        """
        assert hashear_contrasena(CONTRASENA) != hashear_contrasena(CONTRASENA)

    def test_verifica_la_contrasena_correcta(self):
        assert verificar_contrasena(CONTRASENA, hashear_contrasena(CONTRASENA)) is True

    def test_rechaza_la_contrasena_incorrecta(self):
        assert verificar_contrasena("otra_cosa", hashear_contrasena(CONTRASENA)) is False

    def test_distingue_mayusculas_y_minusculas(self):
        assert verificar_contrasena(CONTRASENA.upper(), hashear_contrasena(CONTRASENA)) is False

    def test_devuelve_false_ante_un_hash_corrupto(self):
        """Caso borde: un registro dañado no debe tumbar el inicio de sesión.

        Si esta función lanzara una excepción, una sola fila corrupta en la
        base devolvería un error 500 a quien intentara entrar.
        """
        assert verificar_contrasena(CONTRASENA, "esto no es un hash") is False
        assert verificar_contrasena(CONTRASENA, "") is False

    def test_admite_contrasenas_con_tildes_y_emojis(self):
        # Caso borde real: la gente usa acentos y la Ñ en sus contraseñas.
        rara = "contraseñaÁrbol🦙2026"
        assert verificar_contrasena(rara, hashear_contrasena(rara)) is True


class TestTokensDeSesion:
    def test_el_token_lleva_el_usuario_y_el_rol(self):
        contenido = leer_token_de_acceso(crear_token_de_acceso(42, "gestor"))

        assert contenido is not None
        # "sub" va como texto: lo exige la especificación de JWT.
        assert contenido["sub"] == "42"
        assert contenido["rol"] == "gestor"

    def test_el_token_no_contiene_la_contrasena_ni_el_hash(self):
        """Recordatorio importante: un JWT está firmado, NO cifrado.

        Cualquiera puede leer su contenido. Por eso no puede llevar nada
        sensible dentro.
        """
        token = crear_token_de_acceso(42, "gestor")
        contenido = leer_token_de_acceso(token)

        assert set(contenido or {}) == {"sub", "rol", "iat", "exp"}

    def test_rechaza_un_token_manipulado(self):
        token = crear_token_de_acceso(42, "visitante")

        # Se cambia un carácter del contenido: la firma deja de cuadrar.
        cabecera, cuerpo, firma = token.split(".")
        alterado = f"{cabecera}.{cuerpo[:-4]}XXXX.{firma}"

        assert leer_token_de_acceso(alterado) is None

    def test_rechaza_un_token_con_otra_firma(self):
        """Nadie puede fabricarse un token de administrador sin la clave."""
        from jose import jwt

        falsificado = jwt.encode(
            {"sub": "1", "rol": "administrador"}, "clave_del_atacante", algorithm="HS256"
        )

        assert leer_token_de_acceso(falsificado) is None

    def test_rechaza_un_token_caducado(self):
        # Se emite con validez negativa: nace ya expirado.
        caducado = crear_token_de_acceso(42, "visitante", minutos_de_validez=-1)

        assert leer_token_de_acceso(caducado) is None

    def test_rechaza_texto_que_no_es_un_token(self):
        assert leer_token_de_acceso("cualquier cosa") is None
        assert leer_token_de_acceso("") is None

    def test_la_expiracion_es_la_esperada(self):
        contenido = leer_token_de_acceso(crear_token_de_acceso(1, "visitante", 60))

        assert contenido is not None
        expira = datetime.fromtimestamp(contenido["exp"], UTC)
        esperado = datetime.now(UTC) + timedelta(minutes=60)

        # Un minuto de margen para el tiempo que tarda la prueba en correr.
        assert abs((expira - esperado).total_seconds()) < 60
