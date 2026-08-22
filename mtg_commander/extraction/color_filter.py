"""Filtro defensivo de identidad de color sobre payloads de Scryfall (T-203).

Regla Commander (CR 903.4): toda carta del mazo debe caber dentro de la
identidad de color del comandante. Esa identidad suma costo de maná,
indicadores de color y símbolos de maná del texto en TODAS las caras de la
carta; el campo ``color_identity`` de Scryfall ya viene calculado con todo
incluido (ej.: Garruk Relentless vale [G, B] por los pips negros del reverso).

La búsqueda de /cards/search ya filtra del lado del servidor (``id<=wub``);
este módulo re-verifica la regla localmente antes de enviar cartas a la
evaluación LLM, para no depender de la query o la cache usada al descargar.
"""

import logging

logger = logging.getLogger(__name__)


def filtrar_por_identidad(
    cartas: list[dict], color_identity: list[str]
) -> list[dict]:
    """Devuelve solo las cartas que caben en la identidad del comandante.

    Una carta cabe si su ``color_identity`` es subconjunto de la identidad
    recibida. Las cartas incoloras siempre caben; las que no traigan el
    campo ``color_identity`` se excluyen con warning por ser payload
    sospechoso.

    Args:
        cartas (list[dict]): cartas crudas de Scryfall (ej. salida de
            ``set_cards.obtener_cartas_del_set()``), en cualquier orden.
        color_identity (list[str]): identidad del comandante, ej.
            ["W", "U", "B"], tal como la devuelve
            ``commander.obtener_color_identity()``. Vacía significa
            comandante incoloro: solo pasan cartas sin colores.

    Returns:
        list[dict]: sublista de ``cartas`` compatible con la identidad,
            preservando el orden original.
    """
    permitidos = {color.upper() for color in color_identity}
    aceptadas: list[dict] = []

    for carta in cartas:
        identidad = carta.get("color_identity")
        if identidad is None:
            logger.warning(
                "Carta sin campo color_identity; se excluye: %s",
                carta.get("name", "<sin nombre>"),
            )
            continue
        if {color.upper() for color in identidad} <= permitidos:
            aceptadas.append(carta)

    logger.info(
        "Filtro Commander: %d/%d cartas aceptadas para identidad %s",
        len(aceptadas),
        len(cartas),
        sorted(permitidos) or "incoloro",
    )
    return aceptadas
