"""Tests del orquestador Context sin consumir servicios externos."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mtg_commander.context.deck_profiler import DeckProfile
from mtg_commander.context.orchestrator import (
    calcular_fingerprint_deck,
    generar_contexto,
)
from mtg_commander.llm.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    """Provider mínimo para verificar la inyección del orquestador."""

    name = "fake"

    def __init__(self) -> None:
        super().__init__(model="fake")

    def chat(self, system: str, prompt: str, **kwargs: object) -> LLMResponse:
        return LLMResponse("{}", self.name, self.model)


class TestContextOrchestrator(unittest.TestCase):
    """Cubre regeneración y reutilización por fingerprint."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.deck = self.base / "deck.txt"
        self.deck.write_text(
            "Commander\n1 Test Commander\n\nDeck\n1 Arcane Signet\n",
            encoding="utf-8",
        )
        self.strategy = self.base / "estrategia.md"
        self.research = self.base / "research.md"
        self.state = self.base / "context_state.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("mtg_commander.context.orchestrator.generar_estrategia")
    @patch("mtg_commander.context.orchestrator.generar_research")
    @patch("mtg_commander.context.orchestrator.perfilar_deck")
    @patch("mtg_commander.context.orchestrator.obtener_info_cartas")
    def test_genera_pipeline_y_persiste_estado(
        self,
        obtener_info: Mock,
        perfilar: Mock,
        research: Mock,
        estrategia: Mock,
    ) -> None:
        obtener_info.return_value = [
            {
                "name": "Test Commander",
                "color_identity": ["U"],
                "cmc": 2,
                "type_line": "Legendary Creature",
                "oracle_text": "Draw a card.",
            },
            {
                "name": "Arcane Signet",
                "color_identity": [],
                "cmc": 2,
                "type_line": "Artifact",
                "oracle_text": "Add one mana.",
            },
        ]
        perfilar.return_value = DeckProfile(["control"], ["card draw"], "Test")
        research.side_effect = lambda **kwargs: self.research.write_text(
            "research", encoding="utf-8"
        )
        estrategia.side_effect = lambda *args, **kwargs: self.strategy.write_text(
            "strategy", encoding="utf-8"
        )

        resultado = generar_contexto(
            self.deck,
            self.strategy,
            self.research,
            self.state,
            client=Mock(),
            provider=FakeProvider(),
        )

        self.assertTrue(resultado.regenerated)
        self.assertTrue(self.state.exists())
        research.assert_called_once()
        estrategia.assert_called_once()

    def test_reutiliza_estrategia_si_el_deck_no_cambio(self) -> None:
        self.strategy.write_text("strategy", encoding="utf-8")
        fingerprint = calcular_fingerprint_deck(["Test Commander", "Arcane Signet"])
        self.state.write_text(
            '{"deck_fingerprint": "' + fingerprint + '"}', encoding="utf-8"
        )

        resultado = generar_contexto(
            self.deck,
            self.strategy,
            self.research,
            self.state,
        )

        self.assertFalse(resultado.regenerated)
        self.assertEqual(resultado.strategy_path, self.strategy.resolve())

    def test_deck_modificado_invalida_estado(self) -> None:
        self.strategy.write_text("strategy", encoding="utf-8")
        self.state.write_text('{"deck_fingerprint": "anterior"}', encoding="utf-8")

        with patch(
            "mtg_commander.context.orchestrator.obtener_info_cartas",
            side_effect=RuntimeError("pipeline ejecutado"),
        ):
            with self.assertRaisesRegex(RuntimeError, "pipeline ejecutado"):
                generar_contexto(
                    self.deck,
                    self.strategy,
                    self.research,
                    self.state,
                    client=Mock(),
                    provider=FakeProvider(),
                )


if __name__ == "__main__":
    unittest.main()
