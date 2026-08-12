"""Tests de latest_set.py: no golpean la red, controlan el cache en disco."""

import json
import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from mtg_commander.extraction import latest_set

SETS_DE_PRUEBA = [
    {"code": "eve", "name": "Eventide", "set_type": "expansion", "released_at": "2008-07-25"},
    {"code": "trk", "name": "Star Trek", "set_type": "expansion", "released_at": "2026-11-13"},
    {"code": "pzen", "name": "Zendikar Promos", "set_type": "promo", "released_at": "2099-01-01"},
    {"code": "m10", "name": "Magic 2010", "set_type": "core", "released_at": "2009-07-17"},
]


class TestLatestSet(unittest.TestCase):
    def setUp(self):
        # Aislamos el cache de cada test en una carpeta temporal propia.
        self._cache_path_original = latest_set.CACHE_PATH
        latest_set.CACHE_PATH = os.path.join("outputs", "cache", "test_sets_cache.json")

    def tearDown(self):
        shutil.rmtree("outputs", ignore_errors=True)
        latest_set.CACHE_PATH = self._cache_path_original

    def test_sin_cache_descarga_filtra_y_guarda(self):
        cliente = MagicMock()
        cliente.get.return_value = {"data": SETS_DE_PRUEBA}

        resultado = latest_set.obtener_ultimo_set(cliente)

        # "pzen" es más reciente pero es tipo "promo": no debe ganar.
        self.assertEqual(resultado.code, "trk")
        self.assertEqual(resultado.name, "Star Trek")
        cliente.get.assert_called_once_with("/sets")
        self.assertTrue(os.path.exists(latest_set.CACHE_PATH))

    def test_con_cache_vigente_no_llama_a_la_api(self):
        cache = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sets": SETS_DE_PRUEBA,
        }
        os.makedirs(os.path.dirname(latest_set.CACHE_PATH), exist_ok=True)
        with open(latest_set.CACHE_PATH, "w", encoding="utf-8") as archivo:
            json.dump(cache, archivo)

        cliente = MagicMock()
        resultado = latest_set.obtener_ultimo_set(cliente)

        self.assertEqual(resultado.code, "trk")
        cliente.get.assert_not_called()

    def test_cache_vencido_vuelve_a_descargar(self):
        cache_viejo = {
            "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
            "sets": SETS_DE_PRUEBA,
        }
        os.makedirs(os.path.dirname(latest_set.CACHE_PATH), exist_ok=True)
        with open(latest_set.CACHE_PATH, "w", encoding="utf-8") as archivo:
            json.dump(cache_viejo, archivo)

        cliente = MagicMock()
        cliente.get.return_value = {"data": SETS_DE_PRUEBA}

        latest_set.obtener_ultimo_set(cliente)

        cliente.get.assert_called_once_with("/sets")

    def test_override_pide_set_directo_y_no_toca_cache(self):
        cliente = MagicMock()
        cliente.get.return_value = {"code": "eve", "name": "Eventide"}

        resultado = latest_set.obtener_ultimo_set(cliente, set_override="eve")

        self.assertEqual(resultado, latest_set.SetInfo(code="eve", name="Eventide"))
        cliente.get.assert_called_once_with("/sets/eve")
        self.assertFalse(os.path.exists(latest_set.CACHE_PATH))

    def test_sin_sets_validos_lanza_value_error(self):
        cliente = MagicMock()
        cliente.get.return_value = {"data": [SETS_DE_PRUEBA[2]]}  # solo el "promo"

        with self.assertRaises(ValueError):
            latest_set.obtener_ultimo_set(cliente)


if __name__ == "__main__":
    unittest.main()
