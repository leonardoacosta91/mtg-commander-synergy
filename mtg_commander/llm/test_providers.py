"""Tests de los providers concretos sin llamadas externas."""

import unittest
from unittest import mock

import requests

from mtg_commander.llm.base import LLMError
from mtg_commander.llm.providers import GeminiProvider, OpenAIProvider


class TestGeminiProvider(unittest.TestCase):
    @mock.patch("mtg_commander.llm.providers.requests.post")
    def test_chat_normaliza_respuesta_rest(self, post: mock.Mock) -> None:
        respuesta = post.return_value
        respuesta.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "estrategia"}]}}]
        }

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "secret"}):
            resultado = GeminiProvider("gemini-flash-latest").chat(
                system="sistema", prompt="mazo", max_tokens=100
            )

        self.assertEqual(resultado.text, "estrategia")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "secret")
        self.assertEqual(
            kwargs["json"]["generationConfig"]["maxOutputTokens"], 100
        )
        respuesta.raise_for_status.assert_called_once_with()

    @mock.patch("mtg_commander.llm.providers.requests.post")
    def test_chat_traduce_error_http(self, post: mock.Mock) -> None:
        post.side_effect = requests.Timeout("timeout")

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "secret"}):
            with self.assertRaisesRegex(LLMError, "Gemini API falló"):
                GeminiProvider("gemini-flash-latest").chat("sistema", "mazo")

    @mock.patch("mtg_commander.llm.providers.requests.post")
    def test_chat_rechaza_payload_sin_candidatos(self, post: mock.Mock) -> None:
        post.return_value.json.return_value = {"candidates": []}

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "secret"}):
            with self.assertRaisesRegex(LLMError, "Gemini API falló"):
                GeminiProvider("gemini-flash-latest").chat("sistema", "mazo")


class TestOpenAIProvider(unittest.TestCase):
    @mock.patch("mtg_commander.llm.providers._importar_sdk")
    def test_chat_normaliza_respuesta_sdk(self, importar_sdk: mock.Mock) -> None:
        sdk = importar_sdk.return_value
        client = sdk.OpenAI.return_value
        mensaje = client.chat.completions.create.return_value.choices[0].message
        mensaje.content = "estrategia"

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "secret"}):
            resultado = OpenAIProvider("gpt-4o-mini").chat(
                system="sistema", prompt="mazo", max_tokens=100
            )

        self.assertEqual(resultado.text, "estrategia")
        sdk.OpenAI.assert_called_once_with(api_key="secret")
        parametros = client.chat.completions.create.call_args.kwargs
        self.assertEqual(parametros["model"], "gpt-4o-mini")
        self.assertEqual(parametros["max_tokens"], 100)
        self.assertEqual(parametros["messages"][0]["role"], "system")

    @mock.patch("mtg_commander.llm.providers._importar_sdk")
    def test_chat_traduce_error_sdk(self, importar_sdk: mock.Mock) -> None:
        sdk = importar_sdk.return_value
        sdk.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError(
            "falló"
        )

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "secret"}):
            with self.assertRaisesRegex(LLMError, "OpenAI API falló"):
                OpenAIProvider("gpt-4o-mini").chat("sistema", "mazo")

if __name__ == "__main__":
    unittest.main()
