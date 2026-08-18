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
MAX_TOKENS_ESTRATEGIA = 4096

SYSTEM_PROMPT = """Sos un analista experto en Commander de Magic: The Gathering.
Sintetizá únicamente la evidencia recibida: texto Oracle del deck y research con
fuentes. No inventes cartas, interacciones ni citas. Priorizá patrones que sirvan
para evaluar futuras inclusiones y explicá el para qué de cada paquete.

Devolvé Markdown en español, sin bloque de código, con exactamente estas secciones:
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

Conservá las referencias [F#] cuando una afirmación provenga del research y escribí
todos los nombres de cartas entre corchetes. Separá hechos observables del deck de
opiniones de la comunidad. Si falta evidencia, declaralo explícitamente."""


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
        "Sintetizá el perfil estratégico del siguiente mazo.\n\n"
        "<deck_stats>\n"
        f"{json.dumps(stats.to_dict(), ensure_ascii=False, indent=2)}\n"
        "</deck_stats>\n\n"
        "<deck_profile>\n"
        f"{profile_json}\n"
        "</deck_profile>\n\n"
        "<decklist_enriquecido>\n"
        f"{cartas_json}\n"
        "</decklist_enriquecido>\n\n"
        "<research>\n"
        f"{research.strip()}\n"
        "</research>"
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
