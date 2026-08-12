"""Cache local en disco para respuestas de Scryfall, con política LRU.

Antes de este módulo, `latest_set.py` y `set_cards.py` tenían cada uno
su propia lógica de leer/guardar cache (casi idéntica, duplicada) —
esto la centraliza en un solo lugar, siguiendo la regla del proyecto
de reutilizar en vez de duplicar (ver AGENTS.md, "Coherencia con el
proyecto y reutilización").

Cada entrada vive en su propio archivo JSON dentro de `outputs/cache/`,
con dos políticas independientes:

- **TTL (24h):** una entrada vencida se trata como si no existiera,
  aunque siga en disco (hay que volver a descargarla).
- **LRU (tope de archivos):** si hay `MAX_ENTRADAS` o más archivos de
  cache, se descarta el que hace más tiempo no se usa (por fecha de
  modificación del archivo) antes de guardar uno nuevo. Evita que el
  cache crezca sin límite si se evalúan muchos sets/mazos distintos.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

CACHE_DIR = os.path.join("outputs", "cache")
CACHE_TTL = timedelta(hours=24)
MAX_ENTRADAS = 50

logger = logging.getLogger(__name__)


def ruta_cache(clave: str) -> str:
    """Ruta del archivo de cache correspondiente a una clave (ej. "sets_cache")."""
    return os.path.join(CACHE_DIR, f"{clave}.json")


def leer(clave: str) -> Any | None:
    """Devuelve el valor cacheado bajo `clave` si existe y sigue vigente (<24h).

    Si lo devuelve, marca el archivo como usado recientemente (protege
    a esta entrada de ser la próxima descartada por la política LRU).

    Returns:
        El valor guardado con `guardar()`, o ``None`` si no hay cache
        para esa clave o si ya venció.
    """
    ruta = ruta_cache(clave)
    if not os.path.exists(ruta):
        return None

    with open(ruta, "r", encoding="utf-8") as archivo:
        cache = json.load(archivo)

    fetched_at = datetime.fromisoformat(cache["fetched_at"])
    if datetime.now(timezone.utc) - fetched_at >= CACHE_TTL:
        return None

    os.utime(ruta, None)  # actualiza el "último uso" para la política LRU
    return cache["valor"]


def guardar(clave: str, valor: Any) -> None:
    """Guarda `valor` bajo `clave`, sobrescribiendo si ya existía.

    Antes de escribir, aplica la política LRU: si ya hay `MAX_ENTRADAS`
    archivos de cache, descarta el menos usado recientemente.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    _aplicar_lru()

    cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "valor": valor,
    }
    with open(ruta_cache(clave), "w", encoding="utf-8") as archivo:
        json.dump(cache, archivo, indent=2, ensure_ascii=False)


def _aplicar_lru() -> None:
    """Si el cache está en el tope, descarta el archivo menos usado recientemente."""
    if not os.path.isdir(CACHE_DIR):
        return

    archivos = [
        os.path.join(CACHE_DIR, nombre)
        for nombre in os.listdir(CACHE_DIR)
        if nombre.endswith(".json")
    ]
    if len(archivos) < MAX_ENTRADAS:
        return

    mas_antiguo = min(archivos, key=os.path.getmtime)
    logger.info("Cache lleno (%d entradas): descartando %s (LRU)", len(archivos), mas_antiguo)
    os.remove(mas_antiguo)
