"""Extracción de cartas nuevas de un set, filtradas por color identity.

Etapa 3 del pipeline (Data Extraction): una vez detectado el último set
(T-201), se bajan sus cartas no-tierra que caben en la identidad de
color del comandante, siguiendo la paginación de /cards/search y
cacheando el resultado localmente (≥24h) para no repetir la búsqueda.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from mtg_commander.extraction.client import ScryfallClient

CACHE_DIR = os.path.join("outputs", "cache")
CACHE_TTL = timedelta(hours=24)
ENDPOINT_SEARCH = "/cards/search"

logger = logging.getLogger(__name__)


def _ruta_cache(set_code: str, color_identity: list[str]) -> str:
    """Ruta del archivo de cache para un set + identidad de color puntual."""
    identidad = "".join(color_identity).lower() or "incoloro"
    return os.path.join(CACHE_DIR, f"cards_{set_code}_{identidad}.json")


def _leer_cache(ruta: str) -> list[dict] | None:
    """Devuelve las cartas cacheadas si el archivo existe y sigue vigente (<24h)."""
    if not os.path.exists(ruta):
        return None

    with open(ruta, "r", encoding="utf-8") as archivo:
        cache = json.load(archivo)

    fetched_at = datetime.fromisoformat(cache["fetched_at"])
    if datetime.now(timezone.utc) - fetched_at >= CACHE_TTL:
        return None

    return cache["cards"]


def _guardar_cache(ruta: str, cartas: list[dict]) -> None:
    """Sobrescribe el cache local con las cartas recién descargadas."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cards": cartas,
    }
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(cache, archivo, indent=2, ensure_ascii=False)


def _armar_query(set_code: str, color_identity: list[str]) -> str:
    """Arma la query de Scryfall: set puntual + identidad de color + sin tierras.

    ``id<=wub`` filtra cartas cuya identidad de color cabe dentro de la
    identidad del comandante (regla Commander). Con identidad vacía
    (comandante incoloro) se usa ``id:c``.
    """
    identidad = "".join(color_identity).lower()
    filtro_identidad = f"id<={identidad}" if identidad else "id:c"
    return f"set:{set_code} {filtro_identidad} -type:land"


def obtener_cartas_del_set(
    client: ScryfallClient, set_code: str, color_identity: list[str]
) -> list[dict]:
    """Trae todas las cartas no-tierra de un set que caben en una identidad de color.

    Sigue la paginación de `/cards/search` (parámetro `page`) hasta
    agotar los resultados, y cachea el resultado combinado en disco
    (válido 24h) para no repetir la búsqueda completa en corridas
    seguidas del mismo set + identidad.

    Args:
        client (ScryfallClient): cliente ya configurado.
        set_code (str): código del set a consultar (ej. "eve").
        color_identity (list[str]): colores en orden WUBRG (ej. ["W", "U", "B"]),
            tal como los devuelve `commander.obtener_color_identity()`. Una
            lista vacía busca cartas de identidad incolora.

    Returns:
        list[dict]: cartas del set que matchean, en el formato crudo de
            Scryfall (sin normalizar). Lista vacía si no hay matches.
    """
    ruta_cache = _ruta_cache(set_code, color_identity)
    cartas_cacheadas = _leer_cache(ruta_cache)
    if cartas_cacheadas is not None:
        logger.info("Usando cache local para set=%s identity=%s", set_code, color_identity)
        return cartas_cacheadas

    query = _armar_query(set_code, color_identity)
    cartas: list[dict] = []
    pagina = 1

    while True:
        try:
            respuesta = client.get(ENDPOINT_SEARCH, params={"q": query, "page": pagina})
        except requests.exceptions.HTTPError as error:
            # Scryfall responde 404 cuando la búsqueda no tiene resultados:
            # no es un error, es "cero cartas" (ej. identidad muy restrictiva).
            if error.response is not None and error.response.status_code == 404:
                break
            raise

        cartas.extend(respuesta.get("data", []))

        if not respuesta.get("has_more"):
            break
        pagina += 1

    _guardar_cache(ruta_cache, cartas)
    return cartas
