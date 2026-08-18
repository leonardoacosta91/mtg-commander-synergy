"""Tests del armado de queries de Reddit sin acceso a la API."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mtg_commander.context.deck_profiler import DeckProfile
from mtg_commander.context.reddit_research import construir_queries, construir_research_md


class TestConstruirQueries(unittest.TestCase):
    commander = "Y'shtola, Night's Blessed"

    def test_sin_perfil_usa_queries_generales(self) -> None:
        queries = construir_queries(self.commander)

        self.assertEqual(
            queries,
            [
                "Y'shtola, Night's Blessed win conditions",
                "Y'shtola, Night's Blessed synergies deck",
                "Y'shtola, Night's Blessed how to win",
            ],
        )

    def test_perfil_agrega_tags_y_deduplica(self) -> None:
        profile = DeckProfile(
            archetypes=["control", "spellslinger"],
            themes=["spellslinger", "life drain"],
            summary="Plan de control.",
        )

        queries = construir_queries(self.commander, profile)

        self.assertEqual(queries[-3:], [
            "Y'shtola, Night's Blessed control",
            "Y'shtola, Night's Blessed spellslinger",
            "Y'shtola, Night's Blessed life drain",
        ])
        self.assertEqual(len(queries), 6)

    def test_metadata_cuenta_entradas_normalizadas(self) -> None:
        with TemporaryDirectory() as temp_dir:
            deck_path = Path(temp_dir) / "deck.txt"
            deck_path.write_text(
                "Commander\n1 Commander\n\nDeck\n1 Carta A\n2 Island\n",
                encoding="utf-8",
            )

            research = construir_research_md(
                "Commander", ["U"], str(deck_path), []
            )

        self.assertIn("· 3 entradas normalizadas", research)


if __name__ == "__main__":
    unittest.main()
