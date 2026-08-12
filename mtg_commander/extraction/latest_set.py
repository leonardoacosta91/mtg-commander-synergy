"""Detección del set de Magic más reciente, con cache local.

Etapa 3 del pipeline (Data Extraction): antes de bajar cartas nuevas
hay que saber cuál es el último set de expansión/núcleo. El listado
completo de /sets cambia poco, así que se cachea en disco para no
golpear la API en cada corrida (AGENTS.md recomienda cachear ≥24h).
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from mtg_commander.extraction.client import ScryfallClient

CACHE_PATH = os.path.join("outputs", "cache", "sets_cache.json")
CACHE_TTL = timedelta(hours=24)
TIPOS_VALIDOS = {"expansion", "core"}

logger = logging.getLogger(__name__)


@dataclass
class SetInfo:
    """Set de Magic identificado: código y nombre."""

    code: str
    name: str


def _leer_cache() -> list[dict] | None:
    """Devuelve la lista de sets cacheada si el archivo existe y sigue vigente.

    Returns:
        list[dict] | None: los sets cacheados, o ``None`` si no hay cache
            o si ya venció la ventana de 24h (hay que volver a descargar).
    """
    if not os.path.exists(CACHE_PATH):
        return None

    with open(CACHE_PATH, "r", encoding="utf-8") as archivo:
        cache = json.load(archivo)

    fetched_at = datetime.fromisoformat(cache["fetched_at"])
    if datetime.now(timezone.utc) - fetched_at >= CACHE_TTL:
        return None

    return cache["sets"]


def _guardar_cache(sets: list[dict]) -> None:
    """Sobrescribe el cache local con la lista de sets recién descargada."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sets": sets,
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as archivo:
        json.dump(cache, archivo, indent=2, ensure_ascii=False)


def _obtener_lista_sets(client: ScryfallClient) -> list[dict]:
    """Devuelve el listado completo de sets: del cache si está vigente, si no lo descarga."""
    sets_cacheados = _leer_cache()
    if sets_cacheados is not None:
        logger.info("Usando cache local de /sets (vigente <24h)")
        return sets_cacheados

    respuesta = client.get("/sets")
    sets = respuesta["data"]
    _guardar_cache(sets)
    return sets


def obtener_ultimo_set(client: ScryfallClient, set_override: str | None = None) -> SetInfo:
    """Determina el set de Magic a evaluar: el más reciente, o uno forzado.

    Args:
        client (ScryfallClient): cliente ya configurado.
        set_override (str | None): código de set a forzar (ej. "eve"),
            salteando la detección automática. Si se pasa, se resuelve con
            un pedido directo a `/sets/{code}` (más barato que traer el
            listado completo) y no toca el cache.

    Returns:
        SetInfo: código y nombre del set elegido.

    Raises:
        ValueError: si no hay ningún set de tipo expansion/core disponible.
    """
    if set_override is not None:
        datos = client.get(f"/sets/{set_override}")
        return SetInfo(code=datos["code"], name=datos["name"])

    sets = _obtener_lista_sets(client)
    candidatos = [s for s in sets if s.get("set_type") in TIPOS_VALIDOS]

    if not candidatos:
        raise ValueError("No se encontró ningún set de tipo expansion/core")

    # Los released_at son fechas ISO (YYYY-MM-DD): comparan bien como texto.
    mas_reciente = max(candidatos, key=lambda s: s["released_at"])
    return SetInfo(code=mas_reciente["code"], name=mas_reciente["name"])
