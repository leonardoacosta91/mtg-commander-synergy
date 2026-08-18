"""Tests de cache.py: TTL y política LRU, aislados en una carpeta temporal."""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

from mtg_commander.extraction import cache as cache_local


class TestCacheLocal(unittest.TestCase):
    def setUp(self):
        self._cache_dir_original = cache_local.CACHE_DIR
        self._max_entradas_original = cache_local.MAX_ENTRADAS
        self._temp_dir = tempfile.TemporaryDirectory()
        cache_local.CACHE_DIR = self._temp_dir.name

    def tearDown(self):
        self._temp_dir.cleanup()
        cache_local.CACHE_DIR = self._cache_dir_original
        cache_local.MAX_ENTRADAS = self._max_entradas_original

    def test_guardar_y_leer(self):
        cache_local.guardar("clave1", {"a": 1})
        self.assertEqual(cache_local.leer("clave1"), {"a": 1})

    def test_leer_clave_inexistente_da_none(self):
        self.assertIsNone(cache_local.leer("no_existe"))

    def test_entrada_vencida_da_none(self):
        cache_local.guardar("clave1", {"a": 1})
        ruta = cache_local.ruta_cache("clave1")

        with open(ruta, "r", encoding="utf-8") as archivo:
            cache = json.load(archivo)
        cache["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(cache, archivo)

        self.assertIsNone(cache_local.leer("clave1"))

    def test_entrada_vencida_sin_ttl_se_reutiliza(self):
        cache_local.guardar("clave1", {"oracle_text": "Vuela"})
        ruta = cache_local.ruta_cache("clave1")

        with open(ruta, "r", encoding="utf-8") as archivo:
            cache = json.load(archivo)
        cache["fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(cache, archivo)

        self.assertEqual(
            cache_local.leer("clave1", usar_ttl=False), {"oracle_text": "Vuela"}
        )

    def test_lru_descarta_el_menos_usado_recientemente(self):
        cache_local.MAX_ENTRADAS = 3

        cache_local.guardar("a", 1)
        time.sleep(0.01)
        cache_local.guardar("b", 2)
        time.sleep(0.01)
        cache_local.guardar("c", 3)
        time.sleep(0.01)
        cache_local.guardar("d", 4)  # "a" es el más antiguo sin usar: se descarta

        self.assertIsNone(cache_local.leer("a"))
        self.assertEqual(cache_local.leer("b"), 2)
        self.assertEqual(cache_local.leer("c"), 3)
        self.assertEqual(cache_local.leer("d"), 4)

    def test_leer_protege_de_ser_descartado_por_lru(self):
        cache_local.MAX_ENTRADAS = 3

        cache_local.guardar("a", 1)
        time.sleep(0.01)
        cache_local.guardar("b", 2)
        time.sleep(0.01)
        cache_local.guardar("c", 3)
        time.sleep(0.01)
        cache_local.leer("a")  # "a" vuelve a ser el más usado recientemente
        time.sleep(0.01)
        cache_local.guardar("d", 4)  # ahora "b" es el más antiguo sin usar

        self.assertEqual(cache_local.leer("a"), 1)
        self.assertIsNone(cache_local.leer("b"))


if __name__ == "__main__":
    unittest.main()
