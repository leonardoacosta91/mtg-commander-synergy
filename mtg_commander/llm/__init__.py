"""Abstracción de proveedores LLM: contrato común, implementaciones y fábrica.

El pipeline habla solo contra ``LLMProvider`` (ver `mtg_commander.llm.base`) y
construye la instancia correcta vía `mtg_commander.llm.factory.create_provider`,
sin importar qué provider (Gemini, Claude, ChatGPT) esté configurado.
"""

from mtg_commander.llm.base import LLMError, LLMProvider, LLMResponse
from mtg_commander.llm.factory import create_provider

__all__ = ["LLMError", "LLMProvider", "LLMResponse", "create_provider"]
