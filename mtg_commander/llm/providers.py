"""Implementaciones concretas de LLMProvider.

Cada provider importa su SDK de forma perezosa (dentro del método) para que
instalar un SDK no sea requisito para usar los demás: el paquete base solo
depende de la stdlib.

Variables de entorno por provider (configurar en el archivo .env):
- ``GEMINI_API_KEY`` para Google Gemini.
- ``ANTHROPIC_API_KEY`` para Anthropic (Claude).
- ``OPENAI_API_KEY`` para OpenAI (ChatGPT).
"""

import importlib
import logging
import os
from typing import Any

import requests

from mtg_commander.llm.base import LLMError, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

MAX_TOKENS_DEFECTO = 4096
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
LLM_HTTP_TIMEOUT = 60.0


def _importar_sdk(nombre_sdk: str) -> Any:
    """Importa un SDK de forma perezosa convirtiendo ImportError en LLMError.

    Args:
        nombre_sdk (str): nombre del módulo a importar, ej. ``google.generativeai``.

    Returns:
        Any: el módulo importado.

    Raises:
        LLMError: si el SDK no está instalado.
    """
    try:
        return importlib.import_module(nombre_sdk)
    except ImportError as exc:
        raise LLMError(
            f"SDK {nombre_sdk!r} no instalado. Agregalo a requirements.txt "
            "y ejecutá pip install -r requirements.txt."
        ) from exc


def _api_key(var: str) -> str:
    """Lee una API key de entorno o lanza LLMError con mensaje claro.

    Args:
        var (str): nombre de la variable de entorno, ej. ``GEMINI_API_KEY``.

    Returns:
        str: el valor de la variable, sin espacios al inicio/final.

    Raises:
        LLMError: si la variable no está definida o está vacía.
    """
    key = os.getenv(var, "").strip()
    if not key:
        raise LLMError(f"Falta la API key: configurá {var} en tu archivo .env")
    return key


class GeminiProvider(LLMProvider):
    """Proveedor de Google Gemini mediante su API REST oficial."""

    name = "gemini"

    def chat(self, system: str, prompt: str, **kwargs: Any) -> LLMResponse:
        """Ver `LLMProvider.chat`."""
        config_generacion: dict[str, Any] = {"temperature": self.temperature}
        if "max_tokens" in kwargs:
            config_generacion["maxOutputTokens"] = int(kwargs["max_tokens"])
        if kwargs.get("json_mode"):
            config_generacion["responseMimeType"] = "application/json"

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config_generacion,
        }
        url = f"{GEMINI_BASE_URL}/{self.model}:generateContent"

        try:
            respuesta = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": _api_key("GEMINI_API_KEY"),
                },
                json=payload,
                timeout=float(kwargs.get("timeout", LLM_HTTP_TIMEOUT)),
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto = datos["candidates"][0]["content"]["parts"][0]["text"]
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error("Error llamando a Gemini: %s", exc)
            raise LLMError(f"Gemini API falló: {exc}") from exc

        if not isinstance(texto, str) or not texto.strip():
            raise LLMError("Gemini API devolvió una respuesta sin texto")

        return LLMResponse(text=texto, provider=self.name, model=self.model)


class AnthropicProvider(LLMProvider):
    """Proveedor de Anthropic (Claude)."""

    name = "anthropic"

    def chat(self, system: str, prompt: str, **kwargs: Any) -> LLMResponse:
        """Ver `LLMProvider.chat`."""
        anthropic = _importar_sdk("anthropic")
        client = anthropic.Anthropic(api_key=_api_key("ANTHROPIC_API_KEY"))

        try:
            mensaje = client.messages.create(
                model=self.model,
                max_tokens=int(kwargs.get("max_tokens", MAX_TOKENS_DEFECTO)),
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            logger.error("Error llamando a Anthropic: %s", exc)
            raise LLMError(f"Anthropic API falló: {exc}") from exc

        return LLMResponse(
            text=mensaje.content[0].text, provider=self.name, model=self.model
        )


class OpenAIProvider(LLMProvider):
    """Proveedor de OpenAI (ChatGPT)."""

    name = "openai"

    def _parametro_limite_salida(self, max_tokens: int) -> dict[str, int]:
        """Devuelve el parámetro de límite compatible con el modelo configurado.

        Los modelos GPT-5 y posteriores de Chat Completions reemplazaron el
        parámetro legado ``max_tokens`` por ``max_completion_tokens``. Los
        modelos anteriores mantienen el nombre legado, por lo que la elección
        se resuelve aquí sin alterar el contrato público de ``LLMProvider``.

        Args:
            max_tokens: límite de tokens de salida solicitado por el pipeline.

        Returns:
            Diccionario listo para expandir en ``chat.completions.create``.
        """
        if self.model.lower().startswith("gpt-5"):
            return {"max_completion_tokens": max_tokens}
        return {"max_tokens": max_tokens}

    def _parametros_modelo(self, max_tokens: int) -> dict[str, Any]:
        """Construye parámetros de generación compatibles con cada familia.

        GPT-5 no admite una temperatura distinta de su valor por defecto en
        Chat Completions. En esos modelos se omite el parámetro; las familias
        anteriores conservan la temperatura configurable de ``LLMProvider``.

        Args:
            max_tokens: límite de tokens de salida solicitado por el pipeline.

        Returns:
            Parámetros específicos del modelo para la llamada al SDK.
        """
        parametros: dict[str, Any] = self._parametro_limite_salida(max_tokens)
        if not self.model.lower().startswith("gpt-5"):
            parametros["temperature"] = self.temperature
        return parametros

    def chat(self, system: str, prompt: str, **kwargs: Any) -> LLMResponse:
        """Ver `LLMProvider.chat`."""
        max_tokens = int(kwargs.get("max_tokens", MAX_TOKENS_DEFECTO))
        openai = _importar_sdk("openai")
        client = openai.OpenAI(api_key=_api_key("OPENAI_API_KEY"))

        parametros: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        parametros.update(self._parametros_modelo(max_tokens))
        if kwargs.get("json_mode"):
            parametros["response_format"] = {"type": "json_object"}

        try:
            respuesta = client.chat.completions.create(**parametros)
        except Exception as exc:
            logger.error("Error llamando a OpenAI: %s", exc)
            raise LLMError(f"OpenAI API falló: {exc}") from exc

        return LLMResponse(
            text=respuesta.choices[0].message.content,
            provider=self.name,
            model=self.model,
        )
