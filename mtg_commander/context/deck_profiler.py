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

SYSTEM_PROMPT = """You are an expert Magic: The Gathering Commander deck analyst.

Your task is to infer a preliminary strategic profile from the supplied deck
statistics and Scryfall Oracle data. This profile will be used to build focused
community-research queries; it is not the final deck strategy.

Evidence rules:
- Use only the supplied data. Never invent cards, rules text, interactions, or
  metagame context.
- Treat repeated deck-wide patterns as stronger evidence than isolated cards.
- Do not assume that the commander alone defines the deck's strategy.
- Distinguish the primary game plan from incidental subthemes and generic value.
- When the evidence supports multiple plans, capture the overlap and state the
  uncertainty in the summary.

Return exactly one valid JSON object with these fields and no others:
- "archetypes": 1 to 3 concise, lowercase archetype labels.
- "themes": 1 to 6 concise, lowercase English mechanics or patterns suitable
  for Reddit searches, such as "spellslinger", "life drain", or
  "artifact tokens".
- "summary": a brief Spanish explanation of the deck evidence supporting the
  selected archetypes and themes.

Do not use Markdown. Do not put card names, commander names, or generic staples
in "themes". Do not make unsupported claims about power level or metagame."""


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
        "Infer a preliminary strategic profile from the following deck evidence.\n\n"
        "<deck_stats>\n"
        f"{json.dumps(stats.to_dict(), ensure_ascii=False)}\n"
        "</deck_stats>\n\n"
        "<enriched_decklist>\n"
        f"{json.dumps(preparar_cartas_para_llm(cartas), ensure_ascii=False)}\n"
        "</enriched_decklist>"
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
