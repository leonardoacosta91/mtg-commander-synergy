"""Tests de set_cards.py: no golpean la red, controlan el cache en disco."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import requests

from mtg_commander.extraction import cache as cache_local
from mtg_commander.extraction import set_cards


def _carta(nombre: str) -> dict:
    return {"name": nombre, "type_line": "Instant"}


class TestSetCards(unittest.TestCase):
    def setUp(self):
        self._cache_dir_original = cache_local.CACHE_DIR
        self._temp_dir = tempfile.TemporaryDirectory()
        cache_local.CACHE_DIR = self._temp_dir.name

    def tearDown(self):
        self._temp_dir.cleanup()
        cache_local.CACHE_DIR = self._cache_dir_original

    def test_armar_query_con_identidad(self):
        query = set_cards._armar_query("eve", ["W", "U", "B"])
        self.assertEqual(query, "set:eve id<=wub -type:land")

    def test_armar_query_incolora(self):
        query = set_cards._armar_query("eve", [])
        self.assertEqual(query, "set:eve id:c -type:land")

    def test_pagina_unica_sin_paginacion(self):
        cliente = MagicMock()
        cliente.get.return_value = {
            "data": [_carta("Sol Ring"), _carta("Swords to Plowshares")],
            "has_more": False,
        }

        resultado = set_cards.obtener_cartas_del_set(cliente, "eve", ["W", "U", "B"])

        self.assertEqual(len(resultado), 2)
        cliente.get.assert_called_once_with(
            "/cards/search", params={"q": "set:eve id<=wub -type:land", "page": 1}
        )

    def test_multiples_paginas_se_concatenan(self):
        cliente = MagicMock()
        cliente.get.side_effect = [
            {"data": [_carta("Carta A")], "has_more": True},
            {"data": [_carta("Carta B")], "has_more": False},
        ]

        resultado = set_cards.obtener_cartas_del_set(cliente, "eve", ["W"])

        self.assertEqual([c["name"] for c in resultado], ["Carta A", "Carta B"])
        self.assertEqual(cliente.get.call_count, 2)
        segunda_llamada_params = cliente.get.call_args_list[1].kwargs["params"]
        self.assertEqual(segunda_llamada_params["page"], 2)

    def test_cache_vigente_no_llama_a_la_api(self):
        clave = set_cards._clave_cache("eve", ["W", "U", "B"])
        ruta = cache_local.ruta_cache(clave)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        cache = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "valor": [_carta("Sol Ring")],
        }
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(cache, archivo)

        cliente = MagicMock()
        resultado = set_cards.obtener_cartas_del_set(cliente, "eve", ["W", "U", "B"])

        self.assertEqual(resultado, [_carta("Sol Ring")])
        cliente.get.assert_not_called()

    def test_cache_vencido_vuelve_a_descargar(self):
        clave = set_cards._clave_cache("eve", ["W"])
        ruta = cache_local.ruta_cache(clave)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        cache_viejo = {
            "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
            "valor": [_carta("Carta Vieja")],
        }
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(cache_viejo, archivo)

        cliente = MagicMock()
        cliente.get.return_value = {"data": [_carta("Carta Nueva")], "has_more": False}

        resultado = set_cards.obtener_cartas_del_set(cliente, "eve", ["W"])

        self.assertEqual(resultado, [_carta("Carta Nueva")])
        cliente.get.assert_called_once()

    def test_404_sin_resultados_no_crashea_y_cachea_lista_vacia(self):
        respuesta_fake = MagicMock(status_code=404)
        error = requests.exceptions.HTTPError(response=respuesta_fake)

        cliente = MagicMock()
        cliente.get.side_effect = error

        resultado = set_cards.obtener_cartas_del_set(cliente, "eve", ["W", "U", "B", "R", "G"])

        self.assertEqual(resultado, [])
        clave = set_cards._clave_cache("eve", ["W", "U", "B", "R", "G"])
        self.assertTrue(os.path.exists(cache_local.ruta_cache(clave)))


if __name__ == "__main__":
    unittest.main()
