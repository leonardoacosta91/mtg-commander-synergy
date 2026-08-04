"""Detección del comandante y cálculo de su identidad de color.

En Commander, la identidad de color del mazo es la identidad de color
de su comandante: toda carta del mazo debe caber dentro de esos colores.
"""

import json
from dataclasses import dataclass

import requests

from mtg_commander.ingestion.local import leer_comandante

URL_SCRYFALL_CARTA = "https://api.scryfall.com/cards/named"
ENCABEZADOS = {
    "User-Agent": (
        "mtg-commander-synergy/0.1 (proyecto educativo; contacto: antony@example.com)"
    ),
}
# Orden oficial de colores del formato: Blanco, Azul, Negro, Rojo, Verde.
ORDEN_WUBRG = "WUBRG"


@dataclass
class PerfilComandante:
    """Comandante detectado y su identidad de color."""

    nombre: str
    color_identity: list[str]


def obtener_color_identity(nombre_carta: str) -> list[str]:
    """Consulta en Scryfall la identidad de color de una carta.

    Primero intenta una búsqueda exacta y, si no hay coincidencia,
    una aproximada (tolerante a errores de tipeo en el decklist).

    Args:
        nombre_carta (str): Nombre de la carta a consultar.

    Returns:
        list[str]: Colores en orden WUBRG, ej. ["W", "U", "B"].

    Raises:
        ValueError: Si la carta no se encuentra en Scryfall o la
            respuesta no es un JSON válido.
        requests.HTTPError: Si la API responde con un error de servidor.
    """
    for modo in ("exact", "fuzzy"):
        respuesta = requests.get(
            URL_SCRYFALL_CARTA,
            params={modo: nombre_carta},
            headers=ENCABEZADOS,
            timeout=10,
        )
        if respuesta.status_code == 200:
            try:
                datos = respuesta.json()
            except json.JSONDecodeError:
                raise ValueError(
                    f"Respuesta inválida de Scryfall para: {nombre_carta}"
                )
            # Se devuelve en el orden oficial WUBRG (Scryfall varía el orden).
            return sorted(datos["color_identity"], key=ORDEN_WUBRG.index)
        if respuesta.status_code >= 500:
            respuesta.raise_for_status()

    raise ValueError(f"No se encontró la carta en Scryfall: {nombre_carta}")


def detectar_comandante(ruta_archivo: str) -> PerfilComandante:
    """Detecta el comandante del decklist y calcula su identidad de color.

    Args:
        ruta_archivo (str): Ruta al decklist .txt.

    Returns:
        PerfilComandante: Nombre del comandante y su identidad de color.

    Raises:
        ValueError: Si no hay comandante o la carta no existe en Scryfall.
        requests.HTTPError: Si la API responde con un error de servidor.
    """
    nombre = leer_comandante(ruta_archivo)
    color_identity = obtener_color_identity(nombre)
    return PerfilComandante(nombre=nombre, color_identity=color_identity)
