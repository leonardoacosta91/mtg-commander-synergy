"""Detección del comandante y cálculo de su identidad de color.

En Commander, la identidad de color del mazo es la identidad de color
de su comandante: toda carta del mazo debe caber dentro de esos colores.
"""

from dataclasses import dataclass

import requests

from mtg_commander.extraction.client import ScryfallClient
from mtg_commander.ingestion.local import leer_comandante

ENDPOINT_NOMBRE = "/cards/named"
# Orden oficial de colores del formato: Blanco, Azul, Negro, Rojo, Verde.
ORDEN_WUBRG = "WUBRG"


@dataclass
class PerfilComandante:
    """Comandante detectado y su identidad de color."""

    nombre: str
    color_identity: list[str]


def obtener_color_identity(client: ScryfallClient, nombre_carta: str) -> list[str]:
    """Consulta en Scryfall la identidad de color de una carta.

    Primero intenta una búsqueda exacta y, si no hay coincidencia (HTTP 404),
    una aproximada (tolerante a errores de tipeo en el decklist). Todo el
    pedido HTTP se delega en el ``ScryfallClient`` inyectado, que centraliza
    los headers obligatorios, el rate limiting y el manejo del HTTP 429.

    Args:
        client (ScryfallClient): cliente ya configurado, inyectado como
            parámetro según el patrón del proyecto (card_info.py).
        nombre_carta (str): Nombre de la carta a consultar.

    Returns:
        list[str]: Colores en orden WUBRG, ej. ["W", "U", "B"].

    Raises:
        ValueError: Si la carta no se encuentra en Scryfall.
        requests.HTTPError: Si la API responde con un error distinto de 404
            (por ejemplo, un error de servidor).
    """
    for modo in ("exact", "fuzzy"):
        try:
            datos = client.get(ENDPOINT_NOMBRE, params={modo: nombre_carta})
        except requests.HTTPError as error:
            respuesta = error.response
            if respuesta is None or respuesta.status_code != 404:
                raise
            continue  # sin coincidencia exacta -> probamos fuzzy

        # Se devuelve en el orden oficial WUBRG (Scryfall varía el orden).
        return sorted(datos["color_identity"], key=ORDEN_WUBRG.index)

    raise ValueError(f"No se encontró la carta en Scryfall: {nombre_carta}")


def detectar_comandante(ruta_archivo: str, client: ScryfallClient) -> PerfilComandante:
    """Detecta el comandante del decklist y calcula su identidad de color.

    Args:
        ruta_archivo (str): Ruta al decklist .txt.
        client (ScryfallClient): cliente de Scryfall inyectado como parámetro.

    Returns:
        PerfilComandante: Nombre del comandante y su identidad de color.

    Raises:
        ValueError: Si no hay comandante o la carta no existe en Scryfall.
        requests.HTTPError: Si la API responde con un error distinto de 404.
    """
    nombre = leer_comandante(ruta_archivo)
    color_identity = obtener_color_identity(client, nombre)
    return PerfilComandante(nombre=nombre, color_identity=color_identity)
