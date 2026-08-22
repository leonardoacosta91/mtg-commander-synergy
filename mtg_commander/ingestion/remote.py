"""Ingesta remota de decklists desde Moxfield y Archidekt (V2 de Etapa 1, T-401).

Alternativa a la ingesta local (T-002, `local.py`): en vez de leer un
archivo `.txt`, recibe la URL de un mazo público y devuelve sus
cartas, separadas por sección y **con cantidades**: comandante(s),
mainboard, sideboard, considering (así le dice Moxfield en la
interfaz a lo que la API llama `maybeboard`) y tokens.

Además expone `leer_decklist_remoto()`, que devuelve solo la lista
plana de nombres (comandante(s) + mainboard) para mantener el mismo
contrato que `leer_decklist()` y poder enchufarse al resto del
pipeline sin cambios.

Limitación conocida: en mazos de Archidekt, el comandante se identifica
por la categoría "Commander" tageada en la carta. Si el dueño del mazo
no la tageó así (pasa en la práctica), esa carta cae en `mainboard` en
vez de `commanders` — no hay otra forma confiable de distinguirla en
la API pública.
"""

import re
from dataclasses import dataclass, field

import requests

TIMEOUT = 10
HEADERS = {"User-Agent": "MTGCommanderApp/1.0"}

CATEGORIA_COMANDANTE = "Commander"
CATEGORIA_SIDEBOARD = "Sideboard"
CATEGORIA_MAYBEBOARD = "Maybeboard"
CATEGORIA_TOKENS = "Tokens"


@dataclass
class DecklistRemoto:
    """Decklist completo de un mazo remoto, con cantidades por sección.

    `considering` corresponde al `maybeboard` de la API de Moxfield
    ("Considering" es como lo llama la interfaz).
    """

    commanders: dict[str, int] = field(default_factory=dict)
    mainboard: dict[str, int] = field(default_factory=dict)
    sideboard: dict[str, int] = field(default_factory=dict)
    considering: dict[str, int] = field(default_factory=dict)
    tokens: dict[str, int] = field(default_factory=dict)


def _extraer_id_moxfield(url: str) -> str:
    """Extrae el ID de mazo de una URL de Moxfield (ej. .../decks/{id})."""
    match = re.search(r"moxfield\.com/decks/([^/?#]+)", url)
    if not match:
        raise ValueError(f"No se pudo extraer el ID de mazo de la URL de Moxfield: {url}")
    return match.group(1)


def _extraer_id_archidekt(url: str) -> str:
    """Extrae el ID de mazo de una URL de Archidekt (ej. .../decks/{id}/...)."""
    match = re.search(r"archidekt\.com/decks/(\d+)", url)
    if not match:
        raise ValueError(f"No se pudo extraer el ID de mazo de la URL de Archidekt: {url}")
    return match.group(1)


def _seccion_a_cantidades(datos: dict, clave: str) -> dict[str, int]:
    """Convierte una sección de Moxfield (`{nombre: {quantity, ...}}`) a `{nombre: cantidad}`."""
    return {nombre: entrada.get("quantity", 1) for nombre, entrada in datos.get(clave, {}).items()}


def _obtener_decklist_moxfield(deck_id: str) -> DecklistRemoto:
    """Consulta el mazo en la API de Moxfield y arma el `DecklistRemoto`."""
    url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"
    respuesta = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    respuesta.raise_for_status()
    datos = respuesta.json()

    # A diferencia del resto, "tokens" es una lista de definiciones de
    # carta (no un dict con "quantity"): un token no tiene "cantidad"
    # real, así que se cuenta como 1 por tipo de token distinto.
    tokens = {token["name"]: 1 for token in datos.get("tokens", []) if token.get("name")}

    return DecklistRemoto(
        commanders=_seccion_a_cantidades(datos, "commanders"),
        mainboard=_seccion_a_cantidades(datos, "mainboard"),
        sideboard=_seccion_a_cantidades(datos, "sideboard"),
        considering=_seccion_a_cantidades(datos, "maybeboard"),
        tokens=tokens,
    )


def _obtener_decklist_archidekt(deck_id: str) -> DecklistRemoto:
    """Consulta el mazo en la API de Archidekt y arma el `DecklistRemoto`.

    Cada carta vive en una única lista (`cards`) con `categories`
    (etiquetas). Se la clasifica en la primera sección que matchea,
    en este orden de prioridad: Comandante → Sideboard → Maybeboard
    (Considering) → Tokens → Mainboard (default si no matchea ninguna).
    El nombre real vive en `card.oracleCard.name`, no en el nivel
    superior de cada entrada.

    Un mismo nombre puede aparecer en más de una entrada de `cards`
    (ediciones/printings distintas de la misma carta) — las cantidades
    se **suman**, no se pisan.
    """
    url = f"https://archidekt.com/api/decks/{deck_id}/"
    respuesta = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    respuesta.raise_for_status()
    datos = respuesta.json()

    resultado = DecklistRemoto()

    for entrada in datos.get("cards", []):
        nombre = entrada["card"]["oracleCard"]["name"]
        cantidad = entrada.get("quantity", 1)
        categorias = set(entrada.get("categories") or [])

        if CATEGORIA_COMANDANTE in categorias:
            seccion = resultado.commanders
        elif CATEGORIA_SIDEBOARD in categorias:
            seccion = resultado.sideboard
        elif CATEGORIA_MAYBEBOARD in categorias:
            seccion = resultado.considering
        elif CATEGORIA_TOKENS in categorias:
            seccion = resultado.tokens
        else:
            seccion = resultado.mainboard

        seccion[nombre] = seccion.get(nombre, 0) + cantidad

    return resultado


def obtener_decklist_remoto(url: str) -> DecklistRemoto:
    """Lee un mazo público de Moxfield o Archidekt con todas sus secciones y cantidades.

    Args:
        url (str): URL de un mazo público (ej.
            `https://moxfield.com/decks/{id}` o
            `https://archidekt.com/decks/{id}/...`).

    Returns:
        DecklistRemoto: comandante(s), mainboard, sideboard,
            considering y tokens, cada uno como `{nombre: cantidad}`.

    Raises:
        ValueError: si la URL no es de un sitio soportado, o no se
            pudo extraer el ID de mazo.
        requests.HTTPError: si la API del sitio responde con error
            (ej. mazo privado, inexistente, o caído el servicio).
    """
    if "moxfield.com" in url:
        return _obtener_decklist_moxfield(_extraer_id_moxfield(url))
    if "archidekt.com" in url:
        return _obtener_decklist_archidekt(_extraer_id_archidekt(url))
    raise ValueError(f"URL no soportada (solo Moxfield/Archidekt): {url}")


def leer_decklist_remoto(url: str) -> list[str]:
    """Versión compatible con el contrato de `leer_decklist()` (T-002).

    Devuelve solo los nombres de comandante(s) + mainboard, sin
    cantidades ni el resto de las secciones — para que el resto del
    pipeline (T-102, T-103, etc.) pueda consumir un mazo remoto sin
    cambios.

    Args:
        url (str): ver `obtener_decklist_remoto`.

    Returns:
        list[str]: nombres de cartas del mazo (comandante(s) + mainboard).
    """
    decklist = obtener_decklist_remoto(url)
    return list(decklist.commanders.keys()) + list(decklist.mainboard.keys())
