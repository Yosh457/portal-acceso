import unittest
from collections import defaultdict
from unittest.mock import patch

from flask import Flask
from werkzeug.exceptions import ServiceUnavailable, TooManyRequests

from utils.rate_limit import consumir_limite, limitar_autenticacion

class TestRateLimit(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "clave-exclusiva-para-pruebas"

        self.app.add_url_rule(
            "/login",
            endpoint="auth.login",
            methods=["POST"],
            view_func=lambda: "OK",
        )

    def test_error_mysql_devuelve_503(self):
        with self.app.test_request_context("/login", method="POST"):
            with patch("utils.rate_limit.db.session.execute",
                       side_effect=RuntimeError("Fallo simulado")):
                with patch("utils.rate_limit.db.session.rollback") as rollback:
                    with self.assertRaises(ServiceUnavailable) as error:
                        consumir_limite("prueba", "usuario", 5, 60)

                    self.assertEqual(error.exception.code, 503)
                    rollback.assert_called_once()

    def test_limite_general_de_60_solicitudes(self):
        contadores = defaultdict(int)

        def contador_simulado(politica, identificador, maximo, segundos):
            clave = (politica, identificador)
            contadores[clave] += 1
            return contadores[clave] <= maximo, 30

        with patch(
            "utils.rate_limit.consumir_limite",
            side_effect=contador_simulado
        ):
            # Sesenta solicitudes desde la misma IP,
            # utilizando diferentes correos electrónicos.
            for numero in range(60):
                with self.app.test_request_context(
                    "/login",
                    method="POST",
                    data={
                        "email": f"prueba{numero}@example.com",
                        "password": "incorrecta"
                    },
                    environ_base={"REMOTE_ADDR": "127.0.0.1"},
                ):
                    limitar_autenticacion()

            # La solicitud 61 debe superar el límite general.
            with self.app.test_request_context(
                "/login",
                method="POST",
                data={
                    "email": "prueba61@example.com",
                    "password": "incorrecta"
                },
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            ):
                with self.assertRaises(TooManyRequests) as error:
                    limitar_autenticacion()

                self.assertEqual(error.exception.code, 429)
                self.assertEqual(error.exception.retry_after, 30)

        # Comprobar que el contador general acumuló 61 intentos.
        self.assertEqual(
            contadores[("auth_general_ip", "127.0.0.1")],
            61
        )

        # Ninguna cuenta individual debe superar su límite.
        limites_login = [
            cantidad
            for (politica, _), cantidad in contadores.items()
            if politica == "login_cuenta_ip"
        ]

        self.assertEqual(len(limites_login), 60)
        self.assertTrue(all(cantidad == 1 for cantidad in limites_login))

if __name__ == "__main__":
    unittest.main()