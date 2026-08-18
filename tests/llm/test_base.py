"""Tests del contrato base de LLM: abstracción no instanciable y respuesta inmutable."""

import unittest
from dataclasses import FrozenInstanceError

from mtg_commander.llm.base import LLMProvider, LLMResponse


class TestLLMBase(unittest.TestCase):
    def test_llm_provider_es_abstracto(self):
        with self.assertRaises(TypeError):
            LLMProvider(model="gemini-2.0-flash")

    def test_llm_response_normaliza_provider_y_modelo(self):
        respuesta = LLMResponse(text="hola", provider="gemini", model="gemini-2.0-flash")
        self.assertEqual(respuesta.text, "hola")
        self.assertEqual(respuesta.provider, "gemini")
        self.assertEqual(respuesta.model, "gemini-2.0-flash")

    def test_llm_response_es_inmutable(self):
        respuesta = LLMResponse(text="hola", provider="gemini", model="m")
        with self.assertRaises(FrozenInstanceError):
            respuesta.text = "otro"


if __name__ == "__main__":
    unittest.main()
