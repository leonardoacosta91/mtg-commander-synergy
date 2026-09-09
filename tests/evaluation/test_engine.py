"""Tests del motor de evaluación sin consumir APIs externas."""

import json
import tempfile
import unittest
from pathlib import Path

from mtg_commander.evaluation.engine import (
    EvaluationError,
    SYSTEM_PROMPT,
    construir_prompt,
    evaluar_cartas,
    parsear_evaluacion,
    preparar_carta_para_llm,
)
from mtg_commander.llm.base import LLMProvider, LLMResponse


def _evaluacion(nombre: str, score: int = 8) -> dict[str, object]:
    """Construye una respuesta válida reutilizable en los casos de prueba."""
    return {
        "card_name": nombre,
        "include": True,
        "recommendation_tier": "Strong Synergy",
        "synergy_score": score,
        "synergy_category": "Lifegain",
        "synergy_themes": ["Lifegain", "Card draw"],
        "pros": ["Activa el plan del comandante"],
        "cons": ["Compite por un slot"],
        "rationale": "Refuerza una condición estratégica ya presente.",
    }


class FakeProvider(LLMProvider):
    """Provider determinista que devuelve una respuesta por llamada."""

    name = "fake"

    def __init__(self, respuestas: list[str]) -> None:
        super().__init__(model="fake-model")
        self.respuestas = iter(respuestas)
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def chat(self, system: str, prompt: str, **kwargs: object) -> LLMResponse:
        self.calls.append((system, prompt, kwargs))
        return LLMResponse(next(self.respuestas), self.name, self.model)


class TestEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.carta = {
            "name": "Zoraline, Cosmos Hierophant",
            "mana_cost": "{1}{W}{B}",
            "cmc": 3.0,
            "type_line": "Legendary Creature — Bat Cleric",
            "oracle_text": "Flying, vigilance, lifelink",
            "colors": ["W", "B"],
            "color_identity": ["W", "B"],
            "keywords": ["Flying", "Vigilance", "Lifelink"],
            "rarity": "rare",
            "image_uris": {"normal": "https://example.test/card.jpg"},
            "prices": {"usd": "1.00"},
        }

    def test_preparar_carta_elimina_datos_no_relevantes(self) -> None:
        resultado = preparar_carta_para_llm(self.carta)

        self.assertEqual(resultado["name"], self.carta["name"])
        self.assertNotIn("image_uris", resultado)
        self.assertNotIn("prices", resultado)

    def test_construir_prompt_delimita_estrategia_y_carta(self) -> None:
        prompt = construir_prompt(self.carta, "# Estrategia\nPlan lifegain")

        self.assertIn("<deck_strategy>", prompt)
        self.assertIn("Plan lifegain", prompt)
        self.assertIn("<candidate_card>", prompt)
        self.assertIn("Zoraline, Cosmos Hierophant", prompt)
        self.assertNotIn("https://example.test/card.jpg", prompt)

    def test_system_prompt_fija_rubrica_y_coherencia(self) -> None:
        self.assertIn('9-10: "Must-Include"', SYSTEM_PROMPT)
        self.assertIn('5-6: "Playable"', SYSTEM_PROMPT)
        self.assertIn('Set "include" to true only for scores 5-10', SYSTEM_PROMPT)
        self.assertIn("deck-specific advantages in Spanish", SYSTEM_PROMPT)

    def test_preparar_carta_acepta_texto_oracle_en_caras(self) -> None:
        carta_doble = {
            "name": "Carta Doble",
            "type_line": "Creature // Sorcery",
            "card_faces": [
                {
                    "name": "Frente",
                    "oracle_text": "Flying",
                    "image_uris": {"normal": "https://example.test/front.jpg"},
                },
                {"name": "Dorso", "oracle_text": "Draw a card."},
            ],
        }

        resultado = preparar_carta_para_llm(carta_doble)
        self.assertEqual(len(resultado["card_faces"]), 2)
        self.assertNotIn("image_uris", resultado["card_faces"][0])

    def test_parsear_evaluacion_normaliza_textos_y_listas(self) -> None:
        datos = _evaluacion(self.carta["name"])
        datos["synergy_themes"] = [" Lifegain ", "Lifegain"]

        resultado = parsear_evaluacion(json.dumps(datos), self.carta["name"])

        self.assertEqual(resultado["synergy_themes"], ["Lifegain"])
        self.assertIs(resultado["include"], True)
        self.assertEqual(resultado["synergy_score"], 8)

    def test_parsear_evaluacion_rechaza_json_o_contrato_invalidos(self) -> None:
        with self.assertRaisesRegex(EvaluationError, "no es JSON válido"):
            parsear_evaluacion("no-json", self.carta["name"])

        datos = _evaluacion(self.carta["name"])
        del datos["rationale"]
        with self.assertRaisesRegex(EvaluationError, "Faltan campos"):
            parsear_evaluacion(json.dumps(datos), self.carta["name"])

    def test_parsear_evaluacion_rechaza_nombre_y_score_incorrectos(self) -> None:
        with self.assertRaisesRegex(EvaluationError, "se esperaba"):
            parsear_evaluacion(json.dumps(_evaluacion("Otra Carta")), self.carta["name"])

        datos = _evaluacion(self.carta["name"], score=11)
        with self.assertRaisesRegex(EvaluationError, "entre 0 y 10"):
            parsear_evaluacion(json.dumps(datos), self.carta["name"])

    def test_evaluar_cartas_hace_una_llamada_por_carta(self) -> None:
        segunda = dict(self.carta, name="Segunda Carta")
        provider = FakeProvider(
            [
                json.dumps(_evaluacion(self.carta["name"])),
                json.dumps(_evaluacion(segunda["name"])),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            strategy_path = Path(temp_dir) / "estrategia.md"
            strategy_path.write_text("# Estrategia\nPlan lifegain", encoding="utf-8")
            resultado = evaluar_cartas(
                [self.carta, segunda], strategy_path=strategy_path, provider=provider
            )

        self.assertEqual(
            [fila["card_name"] for fila in resultado],
            [self.carta["name"], segunda["name"]],
        )
        self.assertEqual(len(provider.calls), 2)
        self.assertTrue(all(call[2]["json_mode"] for call in provider.calls))

    def test_evaluar_cartas_registra_progreso_y_resumen(self) -> None:
        provider = FakeProvider([json.dumps(_evaluacion(self.carta["name"]))])

        with tempfile.TemporaryDirectory() as temp_dir:
            strategy_path = Path(temp_dir) / "estrategia.md"
            strategy_path.write_text("# Estrategia\nPlan lifegain", encoding="utf-8")
            with self.assertLogs("mtg_commander.evaluation.engine", level="INFO") as logs:
                evaluar_cartas(
                    [self.carta], strategy_path=strategy_path, provider=provider
                )

        mensajes = "\n".join(logs.output)
        self.assertIn("Inicio evaluación de sinergia: 1 cartas", mensajes)
        self.assertIn("[1/1] Inicio evaluación: Zoraline, Cosmos Hierophant", mensajes)
        self.assertIn("[1/1] Fin evaluación: Zoraline, Cosmos Hierophant", mensajes)
        self.assertIn("include=True", mensajes)
        self.assertIn("score=8", mensajes)
        self.assertIn("Fin evaluación de sinergia: 1/1 cartas", mensajes)

    def test_evaluar_cartas_rechaza_entradas_vacias(self) -> None:
        with self.assertRaisesRegex(ValueError, "no puede estar vacía"):
            evaluar_cartas([])


if __name__ == "__main__":
    unittest.main()
