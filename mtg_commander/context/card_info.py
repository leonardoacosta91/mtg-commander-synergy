"""Enriquecimiento de cartas del decklist vía Scryfall /cards/collection.

Etapa 2a del flujo de Deck Context: resuelve cada carta del decklist
normalizado (T-002) contra Scryfall en batches, y se queda solo con los
campos que el resto del pipeline necesita.
"""

import logging

from mtg_commander.extraction.client import ScryfallClient

ENDPOINT_COLLECTION = "/cards/collection"
TAMANO_BATCH = 75  # límite duro de identificadores por pedido a /cards/collection
CAMPOS_NORMALIZADOS = (
    "oracle_text",
    "mana_cost",
    "type_line",
    "colors",
    "color_identity",
    "rarity",
)

logger = logging.getLogger(__name__)


def partir_en_batches(nombres: list[str], tamano: int = TAMANO_BATCH) -> list[list[str]]:
    """Parte una lista en sublistas de a lo sumo `tamano` elementos.

    Args:
        nombres (list[str]): lista completa a partir.
        tamano (int): tamaño máximo de cada sublista.

    Returns:
        list[list[str]]: sublistas consecutivas que reconstruyen la lista original.
    """
    return [nombres[i : i + tamano] for i in range(0, len(nombres), tamano)]


def normalizar_carta(carta: dict) -> dict:
    """Se queda solo con los campos mínimos que usa el proyecto.

    Args:
        carta (dict): objeto "card" tal como lo devuelve Scryfall.

    Returns:
        dict: `name` + los campos de `CAMPOS_NORMALIZADOS`.
    """
    normalizada = {"name": carta.get("name")}
    for campo in CAMPOS_NORMALIZADOS:
        normalizada[campo] = carta.get(campo)
    return normalizada


def obtener_info_cartas(client: ScryfallClient, nombres: list[str]) -> list[dict]:
    """Resuelve cada carta del decklist contra /cards/collection y normaliza el payload.

    Args:
        client (ScryfallClient): cliente ya configurado (headers, rate limit, retry).
        nombres (list[str]): nombres de cartas tal como los devuelve `leer_decklist()`.
            Puede tener duplicados (ej. tierras básicas repetidas); se deduplican
            antes de consultar para no gastar pedidos de más.

    Returns:
        list[dict]: una entrada normalizada por cada nombre de `nombres` que Scryfall
            pudo resolver, en el mismo orden que la lista de entrada. Las cartas no
            encontradas se loguean como warning y se excluyen del resultado.
    """
    nombres_unicos = list(dict.fromkeys(nombres))  # dedup preservando el orden
    info_por_nombre: dict[str, dict] = {}

    for batch in partir_en_batches(nombres_unicos):
        identificadores = [{"name": nombre} for nombre in batch]
        respuesta = client.post(ENDPOINT_COLLECTION, {"identifiers": identificadores})

        for carta in respuesta.get("data", []):
            info_por_nombre[carta["name"]] = normalizar_carta(carta)

        for no_encontrada in respuesta.get("not_found", []):
            logger.warning(
                "Scryfall no encontró la carta: %s", no_encontrada.get("name", "<sin nombre>")
            )

    return [info_por_nombre[nombre] for nombre in nombres if nombre in info_por_nombre]
