"""Tests del orquestador completo sin consumir servicios externos."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mtg_commander.context.orchestrator import ContextResult
from mtg_commander.extraction.latest_set import SetInfo
from mtg_commander.ingestion.commander import PerfilComandante
from mtg_commander.llm.base import LLMProvider, LLMResponse
from mtg_commander.pipeline import ejecutar_pipeline, resolver_deck


class FakeProvider(LLMProvider):
    """Provider mínimo para comprobar que el pipeline comparte una instancia."""

    name = "fake"

    def __init__(self) -> None:
        super().__init__(model="fake-model")

    def chat(self, system: str, prompt: str, **kwargs: object) -> LLMResponse:
        return LLMResponse("{}", self.name, self.model)


class TestPipeline(unittest.TestCase):
    """Cubre coordinación entre módulos y resolución de decklists."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.deck = self.base / "deck.txt"
        self.deck.write_text("Commander\n1 Test Commander\n", encoding="utf-8")
        self.strategy = self.base / "estrategia.md"
        self.research = self.base / "research.md"
        self.csv = self.base / "evaluation_tst.csv"
        self.client = Mock()
        self.provider = FakeProvider()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolver_deck_acepta_nombre_corto_en_data(self) -> None:
        data_dir = self.base / "data"
        data_dir.mkdir()
        esperado = data_dir / "mi_mazo.txt"
        esperado.write_text("Deck\n1 Sol Ring\n", encoding="utf-8")

        with patch("mtg_commander.pipeline.DATA_DIR", data_dir):
            resultado = resolver_deck("mi_mazo.txt")

        self.assertEqual(resultado, esperado.resolve())

    @patch("mtg_commander.pipeline.exportar_evaluacion_csv")
    @patch("mtg_commander.pipeline.evaluar_cartas")
    @patch("mtg_commander.pipeline.filtrar_por_identidad")
    @patch("mtg_commander.pipeline.obtener_cartas_del_set")
    @patch("mtg_commander.pipeline.obtener_ultimo_set")
    @patch("mtg_commander.pipeline.detectar_comandante")
    @patch("mtg_commander.pipeline.generar_contexto")
    def test_ejecuta_etapas_y_reutiliza_client_y_provider(
        self,
        generar_contexto: Mock,
        detectar: Mock,
        ultimo_set: Mock,
        cartas_set: Mock,
        filtrar: Mock,
        evaluar: Mock,
        exportar: Mock,
    ) -> None:
        generar_contexto.return_value = ContextResult(
            self.strategy, self.research, regenerated=False
        )
        detectar.return_value = PerfilComandante("Test Commander", ["U"])
        ultimo_set.return_value = SetInfo("tst", "Test Set")
        cartas = [{"name": "Carta de Prueba", "color_identity": ["U"]}]
        cartas_set.return_value = cartas
        filtrar.return_value = cartas
        evaluar.return_value = [{"card_name": "Carta de Prueba"}]
        exportar.return_value = str(self.csv)

        resultado = ejecutar_pipeline(
            self.deck,
            set_override="tst",
            client=self.client,
            provider=self.provider,
        )

        generar_contexto.assert_called_once_with(
            deck_path=self.deck.resolve(),
            strategy_path=Path("estrategia.md"),
            research_path=Path("research.md"),
            force=False,
            client=self.client,
            provider=self.provider,
        )
        detectar.assert_called_once_with(str(self.deck.resolve()), self.client)
        ultimo_set.assert_called_once_with(self.client, set_override="tst")
        cartas_set.assert_called_once_with(self.client, "tst", ["U"])
        filtrar.assert_called_once_with(cartas, ["U"])
        evaluar.assert_called_once_with(cartas, self.strategy, provider=self.provider)
        exportar.assert_called_once_with(evaluar.return_value, set_name="tst")
        self.assertEqual(resultado.csv_path, self.csv)
        self.assertEqual(resultado.candidate_count, 1)

    @patch("mtg_commander.pipeline.filtrar_por_identidad", return_value=[])
    @patch("mtg_commander.pipeline.obtener_cartas_del_set", return_value=[])
    @patch(
        "mtg_commander.pipeline.obtener_ultimo_set",
        return_value=SetInfo("tst", "Test Set"),
    )
    @patch(
        "mtg_commander.pipeline.detectar_comandante",
        return_value=PerfilComandante("Test Commander", ["U"]),
    )
    @patch(
        "mtg_commander.pipeline.generar_contexto",
        return_value=ContextResult(Path("estrategia.md"), Path("research.md"), False),
    )
    def test_falla_con_mensaje_claro_si_no_hay_candidatas(self, *_: Mock) -> None:
        with self.assertRaisesRegex(ValueError, "No hay cartas candidatas compatibles"):
            ejecutar_pipeline(self.deck, client=self.client, provider=self.provider)


if __name__ == "__main__":
    unittest.main()
