"""Tests de la fábrica de providers: selección, defaults y manejo de errores."""

import unittest
from unittest import mock

from mtg_commander.llm import create_provider
from mtg_commander.llm.base import LLMError
from mtg_commander.llm.providers import AnthropicProvider, GeminiProvider, OpenAIProvider


class TestCreateProvider(unittest.TestCase):
    def test_nombre_explicito_devuelve_provider_correcto(self):
        self.assertIsInstance(create_provider("gemini"), GeminiProvider)
        self.assertIsInstance(create_provider("anthropic"), AnthropicProvider)
        self.assertIsInstance(create_provider("openai"), OpenAIProvider)

    def test_nombre_case_insensitive(self):
        self.assertIsInstance(create_provider("GEMINI"), GeminiProvider)
        self.assertIsInstance(create_provider("  Anthropic "), AnthropicProvider)

    def test_default_gemini_sin_entorno(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            provider = create_provider()
            self.assertIsInstance(provider, GeminiProvider)
            self.assertEqual(provider.model, "gemini-flash-latest")

    def test_provider_desde_llm_provider_env(self):
        with mock.patch.dict("os.environ", {"LLM_PROVIDER": "anthropic"}, clear=True):
            self.assertIsInstance(create_provider(), AnthropicProvider)

    def test_modelo_desde_llm_model_env(self):
        with mock.patch.dict("os.environ", {"LLM_MODEL": "gemini-3-pro"}, clear=True):
            provider = create_provider("gemini")
            self.assertEqual(provider.model, "gemini-3-pro")

    def test_provider_desconocido_lanza_llm_error(self):
        with self.assertRaises(LLMError):
            create_provider("palm")


if __name__ == "__main__":
    unittest.main()
