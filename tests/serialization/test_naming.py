"""Tests de naming.py: no dependen de la red ni de hora exacta."""

import os
import tempfile
import unittest
from unittest import mock

from mtg_commander.serialization import naming
from mtg_commander.serialization.naming import generar_nombre_csv


class TestGenerarNombreCsv(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.salida = os.path.join(self.temp_dir.name, "outputs")
        self.salida_patched = mock.patch.object(
            naming, "CARPETA_SALIDA", self.salida
        )
        self.salida_patched.start()

    def tearDown(self):
        self.salida_patched.stop()
        self.temp_dir.cleanup()

    def test_llamadas_consecutivas_dan_nombres_distintos(self):
        # Caso que rompía la versión con timestamp de resolución de segundos:
        # llamadas tan seguidas que el reloj del sistema no llega a avanzar.
        nombres = [generar_nombre_csv("Test") for _ in range(100)]
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_incluye_set_name_y_extension_csv(self):
        nombre = generar_nombre_csv("Esper")
        self.assertIn("Esper", nombre)
        self.assertTrue(nombre.endswith(".csv"))

    def test_crea_carpeta_outputs(self):
        self.assertFalse(os.path.isdir(naming.CARPETA_SALIDA))

        generar_nombre_csv("Test")

        self.assertTrue(os.path.isdir(naming.CARPETA_SALIDA))


if __name__ == "__main__":
    unittest.main()
