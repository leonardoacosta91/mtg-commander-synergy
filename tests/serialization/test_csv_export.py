"""Tests de csv_export.py: usan el mock real de T-301 y casos de error."""

import csv
import json
import os
import shutil
import unittest

from mtg_commander.serialization.csv_export import (
    CAMPOS_CSV,
    cargar_evaluaciones,
    exportar_evaluacion_csv,
)

RUTA_MOCK = os.path.join("data", "evaluation_mock.json")


def _leer_filas_csv(ruta: str) -> list[dict]:
    with open(ruta, "r", encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


class TestCsvExport(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree("outputs", ignore_errors=True)

    def test_cargar_evaluaciones_del_mock_real(self):
        evaluaciones = cargar_evaluaciones(RUTA_MOCK)
        self.assertEqual(len(evaluaciones), 2)
        self.assertEqual(evaluaciones[0]["card_name"], "Zoraline, Cosmos Hierophant")

    def test_cargar_evaluaciones_json_invalido_lanza_error(self):
        ruta_rota = os.path.join("outputs", "roto.json")
        os.makedirs("outputs", exist_ok=True)
        with open(ruta_rota, "w", encoding="utf-8") as archivo:
            archivo.write("{ esto no es JSON valido")

        with self.assertRaises(json.JSONDecodeError):
            cargar_evaluaciones(ruta_rota)

    def test_exporta_todas_las_filas_del_mock_con_header_completo(self):
        evaluaciones = cargar_evaluaciones(RUTA_MOCK)
        ruta_csv = exportar_evaluacion_csv(evaluaciones, set_name="Test")

        self.assertTrue(os.path.exists(ruta_csv))
        filas = _leer_filas_csv(ruta_csv)
        self.assertEqual(len(filas), 2)
        self.assertEqual(set(filas[0].keys()), set(CAMPOS_CSV))

    def test_serializa_listas_como_texto_separado_por_punto_y_coma(self):
        evaluaciones = cargar_evaluaciones(RUTA_MOCK)
        ruta_csv = exportar_evaluacion_csv(evaluaciones, set_name="Test")

        filas = _leer_filas_csv(ruta_csv)
        sol_ring = next(f for f in filas if f["card_name"] == "Sol Ring")
        self.assertEqual(sol_ring["synergy_themes"], "Generic Utility")

        zoraline = next(f for f in filas if f["card_name"] == "Zoraline, Cosmos Hierophant")
        self.assertEqual(
            zoraline["pros"],
            "Permite recuperar permanentes pequeños del cementerio al atacar; "
            "Aporta ganancia de vida (Vínculo vital) para activar habilidades de Y'shtola",
        )

    def test_fila_invalida_se_excluye_sin_crashear(self):
        evaluaciones = [
            {
                "card_name": "Carta Completa",
                "include": True,
                "recommendation_tier": "Strong Synergy",
                "synergy_score": 7,
                "synergy_category": "Ramp",
                "synergy_themes": ["Ramp"],
                "pros": ["Buena"],
                "cons": [],
                "rationale": "Porque sí.",
            },
            {
                "card_name": "Carta Incompleta",
                "include": True,
                # faltan el resto de los campos del contrato
            },
        ]

        ruta_csv = exportar_evaluacion_csv(evaluaciones, set_name="Test")
        filas = _leer_filas_csv(ruta_csv)

        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["card_name"], "Carta Completa")

    def test_dos_llamadas_no_se_pisan(self):
        evaluaciones = cargar_evaluaciones(RUTA_MOCK)

        ruta1 = exportar_evaluacion_csv(evaluaciones, set_name="Test")
        ruta2 = exportar_evaluacion_csv(evaluaciones, set_name="Test")

        self.assertNotEqual(ruta1, ruta2)
        self.assertTrue(os.path.exists(ruta1))
        self.assertTrue(os.path.exists(ruta2))


if __name__ == "__main__":
    unittest.main()
