"""Contrato común para proveedores de LLM.

El pipeline (etapas 2c y 4) habla solo contra la abstracción ``LLMProvider``,
de modo que cambiar de proveedor (Gemini, Anthropic, OpenAI) no requiera tocar
los módulos que consumen el LLM. Cada implementación concreta traduce este
contrato a la API de su SDK.

El contrato es deliberadamente mínimo: un solo método ``chat`` con semántica
system + user, porque es la operación que todos los SDKs de LLM comparten.
El output estructurado (JSON) se parsea en el pipeline, no en el provider.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Error controlado de un proveedor de LLM (SDK ausente, key faltante, API)."""


@dataclass(frozen=True)
class LLMResponse:
    """Respuesta normalizada de un proveedor de LLM.

    Attributes:
        text (str): contenido de texto generado.
        provider (str): nombre del provider, ej. ``"gemini"``.
        model (str): identificador del modelo usado.
    """

    text: str
    provider: str
    model: str


class LLMProvider(ABC):
    """Interfaz común de chat entre proveedores de LLM.

    Attributes:
        name (str): identificador del provider (``gemini``, ``anthropic``, ``openai``).
        model (str): identificador del modelo, ej. ``gemini-2.0-flash``.
        temperature (float): temperatura de muestreo (0.0 determinista → 1.0 creativo).
    """

    name: str = ""

    def __init__(self, model: str, temperature: float = 0.3) -> None:
        """Inicializa el provider con el modelo y la temperatura a usar.

        Args:
            model (str): identificador del modelo.
            temperature (float): temperatura de muestreo.
        """
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def chat(self, system: str, prompt: str, **kwargs: Any) -> LLMResponse:
        """Envía un turno de chat (system + usuario) y devuelve la respuesta.

        Args:
            system (str): contexto de sistema (ej. contenido de estrategia.md
                o instrucciones de formato estructurado).
            prompt (str): mensaje del usuario.
            **kwargs: parámetros adicionales específicos del provider. Soportados:
                ``max_tokens`` (int): límite de tokens de la respuesta.
                ``json_mode`` (bool): pedir output JSON nativo cuando el SDK lo
                soporte (Gemini/OpenAI). El parseo real ocurre en el pipeline.

        Returns:
            LLMResponse: texto de respuesta con metadatos del provider y modelo.

        Raises:
            LLMError: si el SDK no está instalado, falta la API key o la API
                rechaza la petición.
        """
        raise NotImplementedError
