"""Tests de naming.py: no dependen de la red ni de hora exacta."""

import shutil
import unittest

from mtg_commander.serialization.naming import CARPETA_SALIDA, generar_nombre_csv


class TestGenerarNombreCsv(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(CARPETA_SALIDA, ignore_errors=True)

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
        import os

        shutil.rmtree(CARPETA_SALIDA, ignore_errors=True)
        self.assertFalse(os.path.isdir(CARPETA_SALIDA))

        generar_nombre_csv("Test")

        self.assertTrue(os.path.isdir(CARPETA_SALIDA))


if __name__ == "__main__":
    unittest.main()
