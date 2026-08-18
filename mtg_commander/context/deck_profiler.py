"""Perfilado estratégico preliminar del deck para orientar el research web.

Esta etapa transforma el payload enriquecido por Scryfall en tags de arquetipo y
mecánicas. El perfil no sustituye ``estrategia.md``: solamente determina qué
consultar en Reddit antes de la síntesis final.
"""

import json
from dataclasses import dataclass
from typing import Any

from mtg_commander.context.deck_stats import DeckStats, calcular_deck_stats, preparar_cartas_para_llm
from mtg_commander.llm import LLMProvider, create_provider

MAX_TOKENS_PERFIL = 700
MAX_ARCHETYPES = 3
MAX_THEMES = 6

SYSTEM_PROMPT = """Sos un analista de Commander de Magic: The Gathering.
Analizá exclusivamente las cartas y su texto Oracle provistos. Identificá el
plan predominante del deck sin inventar cartas ni asumir que el comandante
define por sí solo la estrategia. Devolvé únicamente un objeto JSON válido con:
- "archetypes": entre 1 y 3 arquetipos en minúscula;
- "themes": entre 1 y 6 mecánicas o patrones buscables en Reddit, en inglés y
  minúscula (ej. "spellslinger", "life drain", "artifact tokens");
- "summary": resumen breve en español de la evidencia del deck.

Evitá nombres de cartas y staples genéricos en "themes". No incluyas Markdown."""


@dataclass(frozen=True)
class DeckProfile:
    """Tags estratégicos inferidos desde la lista enriquecida de un mazo."""

    archetypes: list[str]
    themes: list[str]
    summary: str


def _lista_de_textos(datos: object, campo: str, limite: int) -> list[str]:
    """Valida y normaliza una lista de tags devuelta por el LLM."""
    if not isinstance(datos, list):
        raise ValueError(f"El campo {campo!r} debe ser una lista")

    resultado: list[str] = []
    for valor in datos:
        if not isinstance(valor, str):
            raise ValueError(f"El campo {campo!r} debe contener solo texto")
        tag = " ".join(valor.split()).strip().lower()
        if tag and tag not in resultado:
            resultado.append(tag)

    if not resultado:
        raise ValueError(f"El campo {campo!r} no puede estar vacío")
    return resultado[:limite]


def parsear_perfil(texto: str) -> DeckProfile:
    """Parsea y valida el JSON estructurado devuelto por el provider.

    Args:
        texto: respuesta JSON del LLM.

    Returns:
        Perfil estratégico normalizado y acotado.

    Raises:
        ValueError: si el JSON no cumple el contrato esperado.
    """
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError("El LLM devolvió un perfil que no es JSON válido") from exc

    if not isinstance(datos, dict):
        raise ValueError("El perfil del deck debe ser un objeto JSON")

    resumen = datos.get("summary")
    if not isinstance(resumen, str) or not resumen.strip():
        raise ValueError("El campo 'summary' debe ser texto no vacío")

    return DeckProfile(
        archetypes=_lista_de_textos(datos.get("archetypes"), "archetypes", MAX_ARCHETYPES),
        themes=_lista_de_textos(datos.get("themes"), "themes", MAX_THEMES),
        summary=" ".join(resumen.split()),
    )


def construir_prompt(cartas: list[dict[str, Any]], stats: DeckStats | None = None) -> str:
    """Serializa el deck enriquecido para el perfilador.

    Args:
        cartas: payload normalizado de ``obtener_info_cartas``.

    Returns:
        Prompt con estadísticas y deck delimitados en JSON, sin URLs de imagen.

    Raises:
        ValueError: si no hay cartas para analizar.
    """
    if not cartas:
        raise ValueError("El decklist enriquecido no puede estar vacío")
    stats = stats or calcular_deck_stats(cartas)
    return (
        "Identificá el perfil estratégico preliminar de este deck.\n\n"
        "<deck_stats>\n"
        f"{json.dumps(stats.to_dict(), ensure_ascii=False)}\n"
        "</deck_stats>\n\n"
        "<decklist_enriquecido>\n"
        f"{json.dumps(preparar_cartas_para_llm(cartas), ensure_ascii=False)}\n"
        "</decklist_enriquecido>"
    )


def perfilar_deck(
    cartas: list[dict[str, Any]],
    provider: LLMProvider | None = None,
    stats: DeckStats | None = None,
) -> DeckProfile:
    """Infiere tags de investigación a partir de las cartas enriquecidas.

    Args:
        cartas: cartas obtenidas por la etapa 2a de Scryfall.
        provider: provider inyectable; si es ``None`` usa ``create_provider()``.
        stats: estadísticas deterministas; si es ``None`` se calculan.

    Returns:
        Perfil validado para alimentar las búsquedas de Reddit.
    """
    llm = provider or create_provider()
    respuesta = llm.chat(
        system=SYSTEM_PROMPT,
        prompt=construir_prompt(cartas, stats),
        max_tokens=MAX_TOKENS_PERFIL,
        json_mode=True,
    )
    return parsear_perfil(respuesta.text)
