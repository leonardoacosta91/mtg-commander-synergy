"""Síntesis del perfil estratégico del mazo mediante un LLM.

Etapa 2c del flujo de Context Generation. Consume las cartas enriquecidas por
Scryfall (2a) y el research trazable (2b), y persiste ``estrategia.md`` para
reutilizarlo como contexto del evaluador de sinergias.
"""

import json
from pathlib import Path
from typing import Any

from mtg_commander.context.deck_profiler import DeckProfile
from mtg_commander.context.deck_stats import DeckStats, calcular_deck_stats, preparar_cartas_para_llm
from mtg_commander.llm import LLMProvider, create_provider

ESTRATEGIA_MD_PATH = Path("estrategia.md")
# El presupuesto incluye razonamiento y texto visible en modelos GPT-5+.
# 24k deja margen suficiente para sintetizar research trazable extenso.
MAX_TOKENS_ESTRATEGIA = 24_000

SYSTEM_PROMPT = """You are an expert Magic: The Gathering Commander deck analyst.

Produce a reusable strategic profile for evaluating future card inclusions. Base
every claim on the supplied deck statistics, Scryfall Oracle data, preliminary
profile, and sourced community research.

Evidence policy:
- Treat deck statistics and Oracle data as the source of truth for card facts,
  rules text, color identity, mana curve, and observable deck composition.
- Treat the preliminary profile as a hypothesis to confirm, refine, or reject.
- Attribute community findings with their existing [F#] references. Never create
  a citation or apply one to a claim that its source does not support.
- Separate observable deck facts from community opinions. If sources disagree,
  describe the disagreement instead of silently choosing a side.
- Never invent cards, interactions, combos, replacement targets, or metagame
  claims. State material uncertainty explicitly.

Focus on how the deck plays: its primary and secondary plans, sequencing, win
conditions, functional packages, constraints, failure modes, and opportunity
costs. For each important package, explain its purpose and how its pieces work
together. Make the inclusion criteria concrete enough to judge a new card against
an existing role or likely cut, rather than merely listing desirable mechanics.

Return Markdown in Spanish, without a code fence, using exactly these headings:
# Estrategia — <comandante o nombre del mazo>
## Resumen estratégico
## Identidad de color y restricciones
## Perfil de mana y curva
## Plan de juego por etapas
## Win conditions
## Sinergias y paquetes clave
## Criterios para evaluar nuevas cartas
## Cartas debatidas y anti-sinergias
## Incertidumbres y contradicciones

Write every card name in square brackets. Preserve [F#] references next to the
claims they support. Prefer precise, decision-useful statements over generic
Commander advice."""


def construir_prompt(
    cartas: list[dict[str, Any]],
    research: str,
    stats: DeckStats | None = None,
    profile: DeckProfile | None = None,
) -> str:
    """Construye el input determinista para la síntesis estratégica.

    Args:
        cartas: decklist enriquecido con datos normalizados de Scryfall.
        research: contenido completo y trazable de ``research.md``.

    Returns:
        Prompt que delimita estadísticas, perfil, cartas y research.

    Raises:
        ValueError: si falta alguna de las dos fuentes requeridas.
    """
    if not cartas:
        raise ValueError("El decklist enriquecido no puede estar vacío")
    if not research.strip():
        raise ValueError("El contenido de research.md no puede estar vacío")

    stats = stats or calcular_deck_stats(cartas)
    cartas_json = json.dumps(preparar_cartas_para_llm(cartas), ensure_ascii=False, indent=2)
    profile_json = json.dumps(
        {
            "archetypes": profile.archetypes,
            "themes": profile.themes,
            "summary": profile.summary,
        }
        if profile is not None
        else {"status": "not_available"},
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Synthesize the strategic profile from the following evidence.\n\n"
        "<deck_stats>\n"
        f"{json.dumps(stats.to_dict(), ensure_ascii=False, indent=2)}\n"
        "</deck_stats>\n\n"
        "<preliminary_deck_profile>\n"
        f"{profile_json}\n"
        "</preliminary_deck_profile>\n\n"
        "<enriched_decklist>\n"
        f"{cartas_json}\n"
        "</enriched_decklist>\n\n"
        "<community_research>\n"
        f"{research.strip()}\n"
        "</community_research>"
    )


def generar_estrategia(
    cartas: list[dict[str, Any]],
    research_path: Path,
    output_path: Path = ESTRATEGIA_MD_PATH,
    provider: LLMProvider | None = None,
    stats: DeckStats | None = None,
    profile: DeckProfile | None = None,
) -> Path:
    """Genera y persiste ``estrategia.md`` a partir de las etapas 2a y 2b.

    Args:
        cartas: cartas del deck enriquecidas mediante ``obtener_info_cartas``.
        research_path: archivo ``research.md`` generado en la etapa 2b.
        output_path: destino del perfil estratégico persistente.
        provider: provider inyectable; si es ``None`` usa ``create_provider()``.
        stats: estadísticas deterministas del deck; si es ``None`` se calculan.
        profile: arquetipos y temas inferidos para la búsqueda de research.

    Returns:
        Ruta absoluta del archivo generado.

    Raises:
        FileNotFoundError: si ``research_path`` no existe.
        ValueError: si una entrada o la respuesta del LLM están vacías.
        LLMError: propagado si el provider falla.
    """
    research = research_path.read_text(encoding="utf-8")
    prompt = construir_prompt(cartas, research, stats, profile)
    llm = provider or create_provider()
    respuesta = llm.chat(
        system=SYSTEM_PROMPT,
        prompt=prompt,
        max_tokens=MAX_TOKENS_ESTRATEGIA,
    )
    contenido = respuesta.text.strip()
    if not contenido:
        raise ValueError("El LLM devolvió una estrategia vacía")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{contenido}\n", encoding="utf-8")
    return output_path.resolve()
