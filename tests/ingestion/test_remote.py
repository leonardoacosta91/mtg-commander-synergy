"""Tests de remote.py: no golpean la red, mockean requests.get."""

import unittest
from unittest.mock import MagicMock, patch

from mtg_commander.ingestion.remote import (
    DecklistRemoto,
    _extraer_id_archidekt,
    _extraer_id_moxfield,
    leer_decklist_remoto,
    obtener_decklist_remoto,
)

MOXFIELD_URL = "https://moxfield.com/decks/DjuDSYNPCU-YzvsmATpDMQ"
ARCHIDEKT_URL = "https://archidekt.com/decks/6096281/print_list"


def _mock_respuesta(payload: dict) -> MagicMock:
    respuesta = MagicMock()
    respuesta.json.return_value = payload
    respuesta.raise_for_status.return_value = None
    return respuesta


class TestExtraerId(unittest.TestCase):
    def test_extraer_id_moxfield_de_url_valida(self):
        self.assertEqual(_extraer_id_moxfield(MOXFIELD_URL), "DjuDSYNPCU-YzvsmATpDMQ")

    def test_extraer_id_moxfield_url_invalida_lanza_error(self):
        with self.assertRaises(ValueError):
            _extraer_id_moxfield("https://moxfield.com/lists/algo")

    def test_extraer_id_archidekt_de_url_con_slug(self):
        self.assertEqual(_extraer_id_archidekt(ARCHIDEKT_URL), "6096281")


class TestObtenerDecklistMoxfield(unittest.TestCase):
    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_arma_las_5_secciones_con_cantidades(self, mock_get):
        mock_get.return_value = _mock_respuesta(
            {
                "commanders": {"Iroh, Grand Lotus": {"quantity": 1}},
                "mainboard": {"Sol Ring": {"quantity": 1}, "Island": {"quantity": 1}},
                "sideboard": {},
                "maybeboard": {"Manamorphose": {"quantity": 1}},
                "tokens": [{"name": "Ally"}, {"name": "Clue"}],
            }
        )

        decklist = obtener_decklist_remoto(MOXFIELD_URL)

        self.assertEqual(decklist.commanders, {"Iroh, Grand Lotus": 1})
        self.assertEqual(decklist.mainboard, {"Sol Ring": 1, "Island": 1})
        self.assertEqual(decklist.sideboard, {})
        self.assertEqual(decklist.considering, {"Manamorphose": 1})
        self.assertEqual(decklist.tokens, {"Ally": 1, "Clue": 1})

    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_url_con_query_string_extrae_bien_el_id(self, mock_get):
        mock_get.return_value = _mock_respuesta(
            {"commanders": {}, "mainboard": {"Sol Ring": {"quantity": 1}}}
        )

        obtener_decklist_remoto("https://moxfield.com/decks/abc123?foo=bar")

        url_llamada = mock_get.call_args[0][0]
        self.assertIn("abc123", url_llamada)


class TestObtenerDecklistArchidekt(unittest.TestCase):
    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_clasifica_por_categoria(self, mock_get):
        def carta(nombre, quantity, categorias):
            return {
                "quantity": quantity,
                "categories": categorias,
                "card": {"oracleCard": {"name": nombre}},
            }

        mock_get.return_value = _mock_respuesta(
            {
                "cards": [
                    carta("Iroh, Grand Lotus", 1, ["Commander"]),
                    carta("Sol Ring", 1, ["Artifact", "Ramp"]),
                    carta("Manamorphose", 1, ["Maybeboard"]),
                    carta("Pithing Needle", 1, ["Sideboard"]),
                    carta("Ally", 1, ["Tokens"]),
                ]
            }
        )

        decklist = obtener_decklist_remoto(ARCHIDEKT_URL)

        self.assertEqual(decklist.commanders, {"Iroh, Grand Lotus": 1})
        self.assertEqual(decklist.mainboard, {"Sol Ring": 1})
        self.assertEqual(decklist.considering, {"Manamorphose": 1})
        self.assertEqual(decklist.sideboard, {"Pithing Needle": 1})
        self.assertEqual(decklist.tokens, {"Ally": 1})

    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_suma_cantidades_de_printings_duplicados_en_la_misma_seccion(self, mock_get):
        def carta(nombre, quantity):
            return {
                "quantity": quantity,
                "categories": ["Land"],
                "card": {"oracleCard": {"name": nombre}},
            }

        mock_get.return_value = _mock_respuesta(
            {"cards": [carta("Breeding Pool", 2), carta("Breeding Pool", 1)]}
        )

        decklist = obtener_decklist_remoto(ARCHIDEKT_URL)

        self.assertEqual(decklist.mainboard, {"Breeding Pool": 3})

    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_categorias_ausentes_no_crashea(self, mock_get):
        mock_get.return_value = _mock_respuesta(
            {
                "cards": [
                    {
                        "quantity": 1,
                        "categories": None,
                        "card": {"oracleCard": {"name": "Alhammarret's Archive"}},
                    }
                ]
            }
        )

        decklist = obtener_decklist_remoto(ARCHIDEKT_URL)

        self.assertEqual(decklist.mainboard, {"Alhammarret's Archive": 1})


class TestLeerDecklistRemotoCompatV1(unittest.TestCase):
    @patch("mtg_commander.ingestion.remote.requests.get")
    def test_devuelve_solo_nombres_comandante_mas_mainboard(self, mock_get):
        mock_get.return_value = _mock_respuesta(
            {
                "commanders": {"Iroh, Grand Lotus": {"quantity": 1}},
                "mainboard": {"Sol Ring": {"quantity": 1}, "Island": {"quantity": 1}},
                "sideboard": {"Pithing Needle": {"quantity": 1}},
                "maybeboard": {"Manamorphose": {"quantity": 1}},
                "tokens": [],
            }
        )

        nombres = leer_decklist_remoto(MOXFIELD_URL)

        self.assertEqual(sorted(nombres), sorted(["Iroh, Grand Lotus", "Sol Ring", "Island"]))


class TestUrlNoSoportada(unittest.TestCase):
    def test_url_de_otro_sitio_lanza_value_error(self):
        with self.assertRaises(ValueError):
            obtener_decklist_remoto("https://tappedout.net/mtg-decks/algo/")


if __name__ == "__main__":
    unittest.main()
