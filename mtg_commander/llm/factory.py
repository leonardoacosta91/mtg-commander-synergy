"""Fábrica de LLMProvider: resuelve qué provider usar según configuración.

Selección por orden de precedencia: argumento ``name`` → variable de entorno
``LLM_PROVIDER`` → default ``gemini``. El modelo se toma de la variable de
entorno ``LLM_MODEL``; si no está definida, se usa el modelo por defecto del
provider elegido.

Ejemplo de uso::

    provider = create_provider()  # lee LLM_PROVIDER (default gemini)
    respuesta = provider.chat(system="...", prompt="...")
"""

import logging
import os

from dotenv import load_dotenv

from mtg_commander.llm.base import LLMError, LLMProvider
from mtg_commander.llm.providers import AnthropicProvider, GeminiProvider, OpenAIProvider

logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_PROVIDER = "gemini"

PROVIDERS: dict[str, type[LLMProvider]] = {
    provider.name: provider
    for provider in (GeminiProvider, AnthropicProvider, OpenAIProvider)
}

MODELOS_DEFECTO: dict[str, str] = {
    "gemini": "gemini-flash-latest",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
}


def create_provider(name: str | None = None) -> LLMProvider:
    """Crea el LLMProvider configurado a partir de variables de entorno.

    Args:
        name (str | None): nombre del provider (``gemini``, ``anthropic``,
            ``openai``). Si es None, se lee de la variable de entorno
            ``LLM_PROVIDER`` (default: ``gemini``).

    Returns:
        LLMProvider: instancia configurada del provider elegido.

    Raises:
        LLMError: si el nombre no es un provider válido.
    """
    nombre = (name or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)).strip().lower()

    if nombre not in PROVIDERS:
        raise LLMError(
            f"Provider de LLM desconocido: {nombre!r}. "
            f"Válidos: {', '.join(sorted(PROVIDERS))}"
        )

    modelo = os.getenv("LLM_MODEL", "").strip() or MODELOS_DEFECTO[nombre]
    logger.info("LLM provider seleccionado: %s (modelo: %s)", nombre, modelo)
    return PROVIDERS[nombre](model=modelo)
