"""Estadísticas deterministas y contexto seguro para LLM de un deck enriquecido."""

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

TIPOS_RELEVANTES = ("artifact", "battle", "creature", "enchantment", "instant", "land", "planeswalker", "sorcery")
CAMPOS_LLM = (
    "name",
    "oracle_text",
    "mana_cost",
    "cmc",
    "type_line",
    "colors",
    "color_identity",
    "rarity",
    "keywords",
    "produced_mana",
    "power",
    "toughness",
    "loyalty",
    "layout",
)
CAMPOS_LLM_CARA = (
    "name",
    "oracle_text",
    "mana_cost",
    "type_line",
    "colors",
    "color_identity",
    "power",
    "toughness",
    "loyalty",
)


@dataclass(frozen=True)
class DeckStats:
    """Resumen cuantitativo calculado sin inferencia de LLM."""

    resolved_card_count: int
    nonland_average_cmc: float | None
    nonland_curve: dict[str, int]
    type_counts: dict[str, int]
    color_counts: dict[str, int]
    keyword_counts: dict[str, int]
    produced_mana_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convierte las estadísticas en un objeto apto para serializar a JSON."""
        return asdict(self)


def _es_tierra(carta: dict[str, Any]) -> bool:
    """Determina si una carta contiene el tipo Land."""
    return "land" in str(carta.get("type_line") or "").lower()


def calcular_deck_stats(cartas: list[dict[str, Any]]) -> DeckStats:
    """Calcula curva, tipos, colores, keywords y mana producido del deck.

    Args:
        cartas: payload normalizado de Scryfall, una entrada por carta resuelta.

    Returns:
        Estadísticas reproducibles basadas exclusivamente en los datos de carta.
    """
    tipos: Counter[str] = Counter()
    colores: Counter[str] = Counter()
    keywords: Counter[str] = Counter()
    mana_producido: Counter[str] = Counter()
    curva: Counter[str] = Counter({"0-2": 0, "3-4": 0, "5+": 0})
    cmcs_no_tierra: list[float] = []

    for carta in cartas:
        type_line = str(carta.get("type_line") or "").lower()
        for tipo in TIPOS_RELEVANTES:
            if tipo in type_line:
                tipos[tipo] += 1
        colores.update(carta.get("colors") or [])
        keywords.update(str(keyword).lower() for keyword in carta.get("keywords") or [])
        mana_producido.update(carta.get("produced_mana") or [])

        cmc = carta.get("cmc")
        if _es_tierra(carta) or not isinstance(cmc, (int, float)):
            continue
        cmc_float = float(cmc)
        cmcs_no_tierra.append(cmc_float)
        if cmc_float <= 2:
            curva["0-2"] += 1
        elif cmc_float <= 4:
            curva["3-4"] += 1
        else:
            curva["5+"] += 1

    promedio = round(sum(cmcs_no_tierra) / len(cmcs_no_tierra), 2) if cmcs_no_tierra else None
    return DeckStats(
        resolved_card_count=len(cartas),
        nonland_average_cmc=promedio,
        nonland_curve=dict(curva),
        type_counts=dict(sorted(tipos.items())),
        color_counts=dict(sorted(colores.items())),
        keyword_counts=dict(sorted(keywords.items())),
        produced_mana_counts=dict(sorted(mana_producido.items())),
    )


def preparar_cartas_para_llm(cartas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Elimina datos visuales y conserva solo el contexto útil para estrategia.

    Args:
        cartas: payload enriquecido y cacheado de Scryfall.

    Returns:
        Copia reducida sin ``image_uris`` ni URLs de imagen de las caras.
    """
    resultado: list[dict[str, Any]] = []
    for carta in cartas:
        contexto = {campo: carta.get(campo) for campo in CAMPOS_LLM}
        contexto["card_faces"] = [
            {campo: cara.get(campo) for campo in CAMPOS_LLM_CARA}
            for cara in carta.get("card_faces") or []
        ]
        resultado.append(contexto)
    return resultado
