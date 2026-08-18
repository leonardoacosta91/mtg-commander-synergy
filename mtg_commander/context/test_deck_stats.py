"""Tests de estadísticas y sanitización de contexto para LLM."""

import unittest

from mtg_commander.context.deck_stats import calcular_deck_stats, preparar_cartas_para_llm


class TestDeckStats(unittest.TestCase):
    cartas = [
        {
            "name": "Counterspell",
            "cmc": 2,
            "type_line": "Instant",
            "colors": ["U"],
            "keywords": [],
            "produced_mana": [],
            "image_uris": {"normal": "https://img.example/card.jpg"},
        },
        {
            "name": "Temple of Silence",
            "cmc": 0,
            "type_line": "Land",
            "colors": [],
            "keywords": [],
            "produced_mana": ["W", "B"],
        },
        {
            "name": "Angel",
            "cmc": 5,
            "type_line": "Creature — Angel",
            "colors": ["W"],
            "keywords": ["Flying"],
            "produced_mana": [],
            "card_faces": [{"name": "Angel", "image_uris": {"png": "https://img.example/face.png"}}],
        },
    ]

    def test_calcular_estadisticas_deck(self) -> None:
        stats = calcular_deck_stats(self.cartas)

        self.assertEqual(stats.resolved_card_count, 3)
        self.assertEqual(stats.nonland_average_cmc, 3.5)
        self.assertEqual(stats.nonland_curve, {"0-2": 1, "3-4": 0, "5+": 1})
        self.assertEqual(stats.type_counts, {"creature": 1, "instant": 1, "land": 1})
        self.assertEqual(stats.keyword_counts, {"flying": 1})
        self.assertEqual(stats.produced_mana_counts, {"B": 1, "W": 1})

    def test_preparar_contexto_excluye_urls_imagen(self) -> None:
        contexto = preparar_cartas_para_llm(self.cartas)

        self.assertNotIn("image_uris", contexto[0])
        self.assertNotIn("image_uris", contexto[2]["card_faces"][0])
        self.assertEqual(contexto[0]["name"], "Counterspell")


if __name__ == "__main__":
    unittest.main()
