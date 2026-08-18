"""Tests del generador de estrategia sin consumir APIs externas."""

import tempfile
import unittest
from pathlib import Path

from mtg_commander.context.deck_profiler import DeckProfile
from mtg_commander.context.generator import construir_prompt, generar_estrategia
from mtg_commander.context.deck_stats import calcular_deck_stats
from mtg_commander.llm.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, text: str) -> None:
        super().__init__(model="fake-model")
        self.text = text
        self.last_system = ""
        self.last_prompt = ""

    def chat(self, system: str, prompt: str, **kwargs: object) -> LLMResponse:
        self.last_system = system
        self.last_prompt = prompt
        return LLMResponse(text=self.text, provider=self.name, model=self.model)


class TestGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.cartas = [
            {
                "name": "Y'shtola, Night's Blessed",
                "mana_cost": "{1}{W}{U}{B}",
                "type_line": "Legendary Creature",
                "oracle_text": "Vigilance",
                "colors": ["W", "U", "B"],
                "color_identity": ["W", "U", "B"],
                "rarity": "mythic",
                "image_uris": {"normal": "https://img.example/yshtola.jpg"},
            }
        ]

    def test_construir_prompt_delimita_fuentes(self) -> None:
        prompt = construir_prompt(self.cartas, "# Research\nDato [F1]")
        self.assertIn("<decklist_enriquecido>", prompt)
        self.assertIn("Y'shtola, Night's Blessed", prompt)
        self.assertIn("<research>", prompt)
        self.assertIn("Dato [F1]", prompt)

    def test_construir_prompt_rechaza_entradas_vacias(self) -> None:
        with self.assertRaises(ValueError):
            construir_prompt([], "research")
        with self.assertRaises(ValueError):
            construir_prompt(self.cartas, "  ")

    def test_construir_prompt_pasa_stats_y_perfil_sin_imagenes(self) -> None:
        profile = DeckProfile(["control"], ["life drain"], "Plan de control.")
        prompt = construir_prompt(
            self.cartas,
            "research",
            calcular_deck_stats(self.cartas),
            profile,
        )

        self.assertIn("<deck_stats>", prompt)
        self.assertIn("<deck_profile>", prompt)
        self.assertIn('"control"', prompt)
        self.assertNotIn("https://img.example/yshtola.jpg", prompt)

    def test_generar_estrategia_persiste_respuesta(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            research_path = base / "research.md"
            output_path = base / "estrategia.md"
            research_path.write_text("# Research\nEvidencia [F1]", encoding="utf-8")
            provider = FakeProvider("# Estrategia — Y'shtola\n\n## Resumen estratégico")

            resultado = generar_estrategia(
                self.cartas, research_path, output_path, provider
            )

            self.assertEqual(resultado, output_path.resolve())
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "# Estrategia — Y'shtola\n\n## Resumen estratégico\n",
            )
            self.assertIn("exactamente estas secciones", provider.last_system)
            self.assertIn("Evidencia [F1]", provider.last_prompt)

    def test_generar_estrategia_rechaza_respuesta_vacia(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            research_path = base / "research.md"
            research_path.write_text("research", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "estrategia vacía"):
                generar_estrategia(
                    self.cartas,
                    research_path,
                    base / "estrategia.md",
                    FakeProvider("  "),
                )


if __name__ == "__main__":
    unittest.main()
