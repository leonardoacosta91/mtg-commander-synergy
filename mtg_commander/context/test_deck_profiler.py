"""Tests del perfilador de deck sin llamadas a Scryfall ni al LLM."""

import unittest

from mtg_commander.context.deck_profiler import (
    DeckProfile,
    construir_prompt,
    parsear_perfil,
    perfilar_deck,
)
from mtg_commander.llm.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    """Provider determinista para verificar el contrato de perfilado."""

    name = "fake"

    def __init__(self, text: str) -> None:
        super().__init__("fake")
        self.text = text
        self.kwargs: dict[str, object] = {}

    def chat(self, system: str, prompt: str, **kwargs: object) -> LLMResponse:
        self.kwargs = kwargs
        return LLMResponse(text=self.text, provider=self.name, model=self.model)


class TestDeckProfiler(unittest.TestCase):
    cartas = [{"name": "Carta", "oracle_text": "Draw a card."}]

    def test_parsear_perfil_normaliza_y_acota_tags(self) -> None:
        perfil = parsear_perfil(
            '{"archetypes": [" Control ", "control", "Midrange", "Combo"], '
            '"themes": ["Life Drain", "life drain", "spellslinger"], '
            '"summary": "  Plan   de  control.  "}'
        )

        self.assertEqual(perfil.archetypes, ["control", "midrange", "combo"])
        self.assertEqual(perfil.themes, ["life drain", "spellslinger"])
        self.assertEqual(perfil.summary, "Plan de control.")

    def test_parsear_perfil_rechaza_json_invalido(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON válido"):
            parsear_perfil("no es json")

    def test_construir_prompt_requiere_cartas(self) -> None:
        with self.assertRaisesRegex(ValueError, "no puede estar vacío"):
            construir_prompt([])

    def test_perfilar_deck_pide_json_mode(self) -> None:
        provider = FakeProvider(
            '{"archetypes": ["control"], "themes": ["spellslinger"], '
            '"summary": "Control de hechizos."}'
        )

        perfil = perfilar_deck(self.cartas, provider)

        self.assertEqual(perfil, DeckProfile(["control"], ["spellslinger"], "Control de hechizos."))
        self.assertTrue(provider.kwargs["json_mode"])
        self.assertEqual(provider.kwargs["max_tokens"], 700)

    def test_prompt_excluye_urls_de_imagen(self) -> None:
        cartas = [{"name": "Carta", "image_uris": {"normal": "https://img.example/card.jpg"}}]

        prompt = construir_prompt(cartas)

        self.assertIn("<deck_stats>", prompt)
        self.assertNotIn("https://img.example/card.jpg", prompt)


if __name__ == "__main__":
    unittest.main()
