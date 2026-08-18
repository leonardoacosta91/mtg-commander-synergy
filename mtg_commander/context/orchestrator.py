"""Orquestación completa del flujo de generación de contexto del mazo."""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from mtg_commander.context.card_info import obtener_info_cartas
from mtg_commander.context.deck_profiler import perfilar_deck
from mtg_commander.context.deck_stats import calcular_deck_stats
from mtg_commander.context.generator import generar_estrategia
from mtg_commander.context.reddit_research import generar_research
from mtg_commander.extraction.client import ScryfallClient
from mtg_commander.ingestion.local import leer_comandante, leer_decklist
from mtg_commander.llm import LLMProvider, create_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextResult:
    """Resultado observable de una ejecución del flujo Context."""

    strategy_path: Path
    research_path: Path
    regenerated: bool


def calcular_fingerprint_deck(cartas: list[str]) -> str:
    """Calcula una huella estable a partir del decklist normalizado.

    Args:
        cartas: nombres normalizados, conservando orden y duplicados.

    Returns:
        Hash SHA-256 hexadecimal del contrato normalizado.
    """
    payload = json.dumps(cartas, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ruta_estado_para(output_path: Path) -> Path:
    """Resuelve el archivo de estado local asociado a una estrategia.

    Args:
        output_path: destino configurado para ``estrategia.md``.

    Returns:
        Ruta dentro de ``outputs/cache`` que no colisiona entre destinos.
    """
    destino = str(output_path.resolve())
    clave = hashlib.sha256(destino.encode("utf-8")).hexdigest()[:16]
    return Path("outputs/cache") / f"context_state_{clave}.json"


def _estado_vigente(output_path: Path, state_path: Path, fingerprint: str) -> bool:
    """Indica si la estrategia existente corresponde al deck actual."""
    if not output_path.is_file() or not state_path.is_file():
        return False
    try:
        estado = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return estado.get("deck_fingerprint") == fingerprint


def _guardar_estado(state_path: Path, fingerprint: str, deck_path: Path) -> None:
    """Persiste atómicamente la huella del último contexto generado."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporal = state_path.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(
            {
                "deck_fingerprint": fingerprint,
                "deck_path": str(deck_path.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporal.replace(state_path)


def _identidad_del_comandante(
    commander: str, cartas_enriquecidas: list[dict[str, object]]
) -> list[str]:
    """Obtiene la identidad del comandante desde el payload de Scryfall."""
    nombre_objetivo = commander.casefold()
    for carta in cartas_enriquecidas:
        nombre = carta.get("name")
        if isinstance(nombre, str) and nombre.casefold() == nombre_objetivo:
            identidad = carta.get("color_identity")
            if isinstance(identidad, list) and all(
                isinstance(color, str) for color in identidad
            ):
                return identidad
    raise ValueError(f"No se pudo resolver la identidad de color de {commander!r}")


def generar_contexto(
    deck_path: Path,
    strategy_path: Path = Path("estrategia.md"),
    research_path: Path = Path("research.md"),
    state_path: Path | None = None,
    force: bool = False,
    client: ScryfallClient | None = None,
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> ContextResult:
    """Ejecuta ingesta → Scryfall → perfil → research → estrategia.

    Args:
        deck_path: archivo local con el decklist.
        strategy_path: destino de ``estrategia.md``.
        research_path: destino intermedio de ``research.md``.
        state_path: estado de fingerprint; por defecto vive en ``outputs/cache``.
        force: regenera aunque el deck no haya cambiado.
        client: cliente Scryfall inyectable.
        provider: proveedor LLM inyectable y compartido entre ambos pasos LLM.
        provider_name: provider a crear si no se inyectó una instancia.

    Returns:
        Rutas generadas y bandera que indica si hubo regeneración.

    Raises:
        FileNotFoundError: si no existe el decklist.
        ValueError: si el deck está vacío o no se resuelve el comandante.
    """
    deck_path = deck_path.resolve()
    cartas = leer_decklist(str(deck_path))
    if not cartas:
        raise ValueError("El decklist normalizado no contiene cartas")

    fingerprint = calcular_fingerprint_deck(cartas)
    estado = state_path or ruta_estado_para(strategy_path)
    if not force and _estado_vigente(strategy_path, estado, fingerprint):
        logger.info("El deck no cambió; se reutiliza %s", strategy_path)
        return ContextResult(strategy_path.resolve(), research_path.resolve(), False)

    commander = leer_comandante(str(deck_path))
    scryfall = client or ScryfallClient()
    llm = provider or create_provider(provider_name)
    enriquecidas = obtener_info_cartas(scryfall, cartas)
    color_identity = _identidad_del_comandante(commander, enriquecidas)
    stats = calcular_deck_stats(enriquecidas)
    profile = perfilar_deck(enriquecidas, provider=llm, stats=stats)

    research_path.parent.mkdir(parents=True, exist_ok=True)
    generar_research(
        commander=commander,
        color_identity=color_identity,
        decklist_path=str(deck_path),
        output_path=research_path,
        profile=profile,
    )
    generar_estrategia(
        enriquecidas,
        research_path,
        strategy_path,
        provider=llm,
        stats=stats,
        profile=profile,
    )
    _guardar_estado(estado, fingerprint, deck_path)
    return ContextResult(strategy_path.resolve(), research_path.resolve(), True)
