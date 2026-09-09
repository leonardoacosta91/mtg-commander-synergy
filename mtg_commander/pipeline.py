"""Orquestación del pipeline completo de recomendaciones Commander.

Conecta las etapas ya implementadas sin duplicar la lógica de cada módulo:
contexto persistente, extracción desde Scryfall, filtro Commander, evaluación
LLM y serialización CSV.
"""

from dataclasses import dataclass
from pathlib import Path

from mtg_commander.context.orchestrator import ContextResult, generar_contexto
from mtg_commander.evaluation import evaluar_cartas
from mtg_commander.extraction.client import ScryfallClient
from mtg_commander.extraction.color_filter import filtrar_por_identidad
from mtg_commander.extraction.latest_set import SetInfo, obtener_ultimo_set
from mtg_commander.extraction.set_cards import obtener_cartas_del_set
from mtg_commander.ingestion.commander import PerfilComandante, detectar_comandante
from mtg_commander.llm import LLMProvider, create_provider
from mtg_commander.serialization.csv_export import exportar_evaluacion_csv

DATA_DIR = Path("data")


@dataclass(frozen=True)
class PipelineResult:
    """Resultado observable de una corrida completa del pipeline."""

    deck_path: Path
    context: ContextResult
    commander: PerfilComandante
    set_info: SetInfo
    candidate_count: int
    csv_path: Path


def resolver_deck(deck: str | Path) -> Path:
    """Resuelve un decklist local, aceptando nombres cortos dentro de ``data/``.

    Una ruta explícita existente tiene prioridad. Si no existe, se prueba el
    mismo nombre relativo a ``data/``; así ``--deck mi_mazo.txt`` equivale a
    ``--deck data/mi_mazo.txt`` desde la raíz del repositorio.

    Args:
        deck: ruta explícita o nombre de un archivo dentro de ``data/``.

    Returns:
        Ruta absoluta del decklist encontrado.

    Raises:
        FileNotFoundError: si ninguna de las rutas candidatas existe.
    """
    ruta = Path(deck).expanduser()
    candidatas = [ruta]
    if not ruta.is_absolute():
        candidatas.append(DATA_DIR / ruta)

    for candidata in candidatas:
        if candidata.is_file():
            return candidata.resolve()

    rutas_probadas = ", ".join(str(candidata) for candidata in candidatas)
    raise FileNotFoundError(f"No se encontró el decklist. Rutas probadas: {rutas_probadas}")


def generar_contexto_del_deck(
    deck: str | Path,
    strategy_path: Path = Path("estrategia.md"),
    research_path: Path = Path("research.md"),
    force: bool = False,
    client: ScryfallClient | None = None,
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> ContextResult:
    """Genera o reutiliza el contexto para un deck pasado por nombre o ruta.

    Args:
        deck: ruta explícita o nombre de archivo dentro de ``data/``.
        strategy_path: destino local de ``estrategia.md``.
        research_path: destino local de ``research.md``.
        force: fuerza regenerar el contexto aunque el deck no haya cambiado.
        client: cliente Scryfall inyectable.
        provider: provider LLM inyectable.
        provider_name: nombre del provider si no se inyecta una instancia.

    Returns:
        Resultado del orquestador de contexto.
    """
    return generar_contexto(
        deck_path=resolver_deck(deck),
        strategy_path=strategy_path,
        research_path=research_path,
        force=force,
        client=client,
        provider=provider,
        provider_name=provider_name,
    )


def ejecutar_pipeline(
    deck: str | Path,
    set_override: str | None = None,
    strategy_path: Path = Path("estrategia.md"),
    research_path: Path = Path("research.md"),
    force_context: bool = False,
    client: ScryfallClient | None = None,
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> PipelineResult:
    """Ejecuta las cinco etapas para un deck y exporta sus recomendaciones.

    Se comparte una sola instancia de ``ScryfallClient`` y de ``LLMProvider``
    por corrida. Esto conserva sesión, rate limiting y configuración entre el
    Pass 1 y Pass 2, y evita que cada etapa configure dependencias por separado.

    Args:
        deck: ruta explícita o nombre de archivo dentro de ``data/``.
        set_override: código de set opcional para omitir la detección automática.
        strategy_path: ubicación de la estrategia persistente.
        research_path: ubicación del research intermedio.
        force_context: fuerza regenerar el contexto del deck.
        client: cliente Scryfall inyectable para pruebas o reutilización.
        provider: provider LLM inyectable para pruebas o reutilización.
        provider_name: nombre del provider a crear si no se inyectó uno.

    Returns:
        Resumen con las rutas y datos relevantes de la corrida.

    Raises:
        ValueError: si no quedan cartas candidatas tras el filtro Commander.
    """
    deck_path = resolver_deck(deck)
    scryfall = client or ScryfallClient()
    llm = provider or create_provider(provider_name)
    context = generar_contexto(
        deck_path=deck_path,
        strategy_path=strategy_path,
        research_path=research_path,
        force=force_context,
        client=scryfall,
        provider=llm,
    )
    commander = detectar_comandante(str(deck_path), scryfall)
    set_info = obtener_ultimo_set(scryfall, set_override=set_override)
    cartas_set = obtener_cartas_del_set(scryfall, set_info.code, commander.color_identity)
    candidatas = filtrar_por_identidad(cartas_set, commander.color_identity)
    if not candidatas:
        raise ValueError(
            f"No hay cartas candidatas compatibles en el set {set_info.code.upper()}"
        )

    evaluaciones = evaluar_cartas(candidatas, context.strategy_path, provider=llm)
    ruta_csv = Path(exportar_evaluacion_csv(evaluaciones, set_name=set_info.code))
    return PipelineResult(
        deck_path=deck_path,
        context=context,
        commander=commander,
        set_info=set_info,
        candidate_count=len(candidatas),
        csv_path=ruta_csv,
    )
