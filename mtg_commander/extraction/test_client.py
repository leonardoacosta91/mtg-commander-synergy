"""Tests del cliente de Scryfall: no golpean la red, mockean session.request."""

import unittest
from unittest.mock import MagicMock

from mtg_commander.extraction.client import ScryfallClient


class TestScryfallClient429(unittest.TestCase):
    def test_429_reintenta_y_termina_devolviendo_datos(self):
        cliente = ScryfallClient(max_retries=3, backoff_factor=0)

        respuesta_429 = MagicMock(status_code=429)
        respuesta_200 = MagicMock(status_code=200)
        respuesta_200.json.return_value = {"object": "list", "data": []}

        # Primera llamada devuelve 429, la segunda ya devuelve 200.
        cliente.session.request = MagicMock(side_effect=[respuesta_429, respuesta_200])

        resultado = cliente.get("/sets")

        self.assertEqual(resultado, {"object": "list", "data": []})
        self.assertEqual(cliente.session.request.call_count, 2)

    def test_429_persistente_no_crashea_lanza_error_controlado(self):
        cliente = ScryfallClient(max_retries=3, backoff_factor=0)

        respuesta_429 = MagicMock(status_code=429)
        cliente.session.request = MagicMock(return_value=respuesta_429)

        with self.assertRaises(RuntimeError):
            cliente.get("/sets")

        self.assertEqual(cliente.session.request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
