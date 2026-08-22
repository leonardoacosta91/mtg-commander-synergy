"""Tests de commander: no golpean la red, mockean ScryfallClient.get."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

import requests

from mtg_commander.ingestion.commander import (
    PerfilComandante,
    detectar_comandante,
    obtener_color_identity,
)


def _http_error(status_code: int) -> requests.HTTPError:
    """Construye un HTTPError con una respuesta simulada del status dado."""
    respuesta = MagicMock()
    respuesta.status_code = status_code
    return requests.HTTPError(response=respuesta)


class TestObtenerColorIdentity(unittest.TestCase):
    def test_coincidencia_exacta_devuelve_colores_en_wubrg(self):
        cliente = MagicMock()
        cliente.get.return_value = {"color_identity": ["U", "B", "W"]}

        resultado = obtener_color_identity(cliente, "Y'shtola, Night's Blessed")

        self.assertEqual(resultado, ["W", "U", "B"])
        cliente.get.assert_called_once_with(
            "/cards/named", params={"exact": "Y'shtola, Night's Blessed"}
        )

    def test_sin_coincidencia_exacta_hace_fallback_a_fuzzy(self):
        cliente = MagicMock()
        cliente.get.side_effect = [
            _http_error(404),  # exact: no encontrada
            {"color_identity": ["G", "W"]},  # fuzzy: encontrada
        ]

        resultado = obtener_color_identity(cliente, "Yshola Nights Blessed")

        self.assertEqual(resultado, ["W", "G"])
        self.assertEqual(
            [llamada.kwargs["params"] for llamada in cliente.get.call_args_list],
            [{"exact": "Yshola Nights Blessed"}, {"fuzzy": "Yshola Nights Blessed"}],
        )

    def test_falla_exact_y_fuzzy_lanza_value_error(self):
        cliente = MagicMock()
        cliente.get.side_effect = [_http_error(404), _http_error(404)]

        with self.assertRaises(ValueError):
            obtener_color_identity(cliente, "Carta Inexistente XYZ")
        self.assertEqual(cliente.get.call_count, 2)

    def test_error_de_servidor_no_reintenta_con_fuzzy(self):
        cliente = MagicMock()
        cliente.get.side_effect = _http_error(500)

        with self.assertRaises(requests.HTTPError):
            obtener_color_identity(cliente, "Y'shtola, Night's Blessed")
        self.assertEqual(cliente.get.call_count, 1)


class TestDetectarComandante(unittest.TestCase):
    def test_detecta_comandante_y_consulta_su_identidad(self):
        cliente = MagicMock()
        cliente.get.return_value = {"color_identity": ["W", "U", "B"]}

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta = os.path.join(carpeta_temporal, "deck.txt")
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write("Commander\n1 Y'shtola, Night's Blessed\n\nDeck\n1 Sol Ring\n")

            perfil = detectar_comandante(ruta, cliente)

        self.assertIsInstance(perfil, PerfilComandante)
        self.assertEqual(perfil.nombre, "Y'shtola, Night's Blessed")
        self.assertEqual(perfil.color_identity, ["W", "U", "B"])
        cliente.get.assert_called_once_with(
            "/cards/named", params={"exact": "Y'shtola, Night's Blessed"}
        )


if __name__ == "__main__":
    unittest.main()
