"""Evaluación de sinergia de cartas nuevas mediante un LLM.

Etapa 4 del pipeline. Aplica prompt chaining: evalúa cada carta de forma
independiente contra el contexto persistente de ``estrategia.md`` y devuelve
una lista de objetos validados, lista para la serialización CSV de T-302.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from mtg_commander.llm import LLMProvider, create_provider

logger = logging.getLogger(__name__)

MAX_TOKENS_EVALUACION = 1200

CAMPOS_EVALUACION = (
    "card_name",
    "include",
    "recommendation_tier",
    "synergy_score",
    "synergy_category",
    "synergy_themes",
    "pros",
    "cons",
    "rationale",
)

CAMPOS_CARTA_LLM = (
    "name",
    "mana_cost",
    "cmc",
    "type_line",
    "oracle_text",
    "colors",
    "color_identity",
    "keywords",
    "produced_mana",
    "power",
    "toughness",
    "loyalty",
    "rarity",
    "set",
    "card_faces",
)

CAMPOS_CARA_LLM = (
    "name",
    "mana_cost",
    "type_line",
    "oracle_text",
    "colors",
    "power",
    "toughness",
    "loyalty",
)

SYSTEM_PROMPT = """You are an expert Magic: The Gathering Commander deck analyst.

Evaluate exactly one candidate card against the supplied persistent deck strategy.
Use only the strategy and the candidate's Scryfall data. Never invent deck cards,
Oracle text, rules interactions, replacement targets, or missing context.

Judge deck-specific contribution, not standalone card strength. Consider:
1. Direct support for the deck's primary plan, win conditions, commander, and key
   packages.
2. The functional role the card would fill and whether it solves a documented gap
   or meaningfully upgrades an existing role.
3. Mana value, color requirements, timing, setup cost, and fit with the curve.
4. Redundancy, replaceability, restrictions, anti-synergies, and the opportunity
   cost of one deck slot.
5. Reliability under the card's exact Oracle wording. Do not conflate casting a
   spell with a permanent entering the battlefield, or card type with effect type.

Merely matching the color identity, mana-value threshold, or a broad theme is not
enough for a high score. Generic Commander value is relevant only when it improves
this deck's stated plan or addresses a documented need.

Use this exact scoring rubric:
- 9-10: "Must-Include" — transformative fit, direct win-condition support, or an
  exceptional upgrade with little opportunity cost.
- 7-8: "Strong Synergy" — clear, repeatable synergy or a meaningful role upgrade.
- 5-6: "Playable" — useful and coherent, but conditional, replaceable, or only a
  modest improvement.
- 3-4: "Low Synergy" — limited or incidental contribution with substantial slot
  pressure.
- 0-2: "Do Not Include" — no meaningful fit, actively conflicts with the plan, or
  is clearly inefficient for the documented role.

Set "include" to true only for scores 5-10, and false for scores 0-4. The score,
tier, and include decision must always follow this mapping exactly.

Return exactly one valid JSON object with these fields and no others:
- "card_name": the exact candidate name.
- "include": a boolean.
- "recommendation_tier": the exact English tier from the rubric.
- "synergy_score": an integer from 0 through 10.
- "synergy_category": a concise primary category in Spanish.
- "synergy_themes": a JSON array of concise Spanish strings.
- "pros": a JSON array of concrete, deck-specific advantages in Spanish.
- "cons": a JSON array of concrete costs, risks, or anti-synergies in Spanish.
- "rationale": a concise technical justification in Spanish that explains the
  decisive deck-specific evidence and opportunity cost.

Return JSON only. Do not include Markdown, commentary, or analysis outside it."""


class EvaluationError(ValueError):
    """Respuesta de evaluación inválida para una carta candidata."""


def _texto_no_vacio(datos: dict[str, Any], campo: str) -> str:
    """Valida y normaliza un campo textual requerido."""
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise EvaluationError(f"El campo {campo!r} debe ser texto no vacío")
    return " ".join(valor.split())


def _lista_de_textos(datos: dict[str, Any], campo: str) -> list[str]:
    """Valida y normaliza una lista de textos del contrato."""
    valor = datos.get(campo)
    if not isinstance(valor, list):
        raise EvaluationError(f"El campo {campo!r} debe ser una lista")

    resultado: list[str] = []
    for elemento in valor:
        if not isinstance(elemento, str) or not elemento.strip():
            raise EvaluationError(
                f"El campo {campo!r} debe contener solo textos no vacíos"
            )
        texto = " ".join(elemento.split())
        if texto not in resultado:
            resultado.append(texto)
    return resultado


def preparar_carta_para_llm(carta: dict[str, Any]) -> dict[str, Any]:
    """Reduce un payload de Scryfall a metadatos útiles para la evaluación.

    Args:
        carta: carta cruda o normalizada obtenida desde Scryfall.

    Returns:
        Copia saneada sin imágenes, precios, URLs ni metadatos editoriales.

    Raises:
        ValueError: si faltan nombre, tipo o texto Oracle utilizable.
    """
    nombre = carta.get("name")
    tipo = carta.get("type_line")
    texto_oracle = carta.get("oracle_text")
    caras = carta.get("card_faces")

    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("La carta candidata debe incluir un nombre")
    if not isinstance(tipo, str) or not tipo.strip():
        raise ValueError(f"La carta {nombre!r} debe incluir type_line")
    if not isinstance(texto_oracle, str) or not texto_oracle.strip():
        tiene_texto_en_caras = isinstance(caras, list) and any(
            isinstance(cara, dict)
            and isinstance(cara.get("oracle_text"), str)
            and bool(cara["oracle_text"].strip())
            for cara in caras
        )
        if not tiene_texto_en_caras:
            raise ValueError(f"La carta {nombre!r} no tiene texto Oracle utilizable")

    resultado = {campo: carta[campo] for campo in CAMPOS_CARTA_LLM if campo in carta}
    if isinstance(caras, list):
        resultado["card_faces"] = [
            {campo: cara[campo] for campo in CAMPOS_CARA_LLM if campo in cara}
            for cara in caras
            if isinstance(cara, dict)
        ]
    return resultado


def construir_prompt(carta: dict[str, Any], estrategia: str) -> str:
    """Construye el turno de evaluación para una carta candidata.

    Args:
        carta: payload de Scryfall de una única carta.
        estrategia: contenido persistente de ``estrategia.md``.

    Returns:
        Prompt delimitado con estrategia y carta serializada.

    Raises:
        ValueError: si la estrategia o la carta no son utilizables.
    """
    if not estrategia.strip():
        raise ValueError("El contenido de estrategia.md no puede estar vacío")
    carta_llm = preparar_carta_para_llm(carta)
    return (
        "Evaluate the candidate card against the deck strategy below.\n\n"
        "<deck_strategy>\n"
        f"{estrategia.strip()}\n"
        "</deck_strategy>\n\n"
        "<candidate_card>\n"
        f"{json.dumps(carta_llm, ensure_ascii=False, indent=2)}\n"
        "</candidate_card>"
    )


def parsear_evaluacion(texto: str, card_name: str) -> dict[str, Any]:
    """Parsea y valida el JSON generado para una carta.

    Args:
        texto: respuesta textual del provider.
        card_name: nombre esperado según el payload de entrada.

    Returns:
        Evaluación normalizada con el contrato completo de T-301.

    Raises:
        EvaluationError: si el JSON o alguno de sus campos es inválido.
    """
    if not isinstance(texto, str) or not texto.strip():
        raise EvaluationError("El LLM devolvió una evaluación vacía")

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise EvaluationError("El LLM devolvió una evaluación que no es JSON válido") from exc

    if not isinstance(datos, dict):
        raise EvaluationError("La evaluación debe ser un objeto JSON")

    faltantes = [campo for campo in CAMPOS_EVALUACION if campo not in datos]
    extras = [campo for campo in datos if campo not in CAMPOS_EVALUACION]
    if faltantes:
        raise EvaluationError(f"Faltan campos requeridos: {faltantes}")
    if extras:
        raise EvaluationError(f"La evaluación contiene campos no permitidos: {extras}")

    nombre = _texto_no_vacio(datos, "card_name")
    if nombre != card_name:
        raise EvaluationError(
            f"El LLM evaluó {nombre!r}, pero se esperaba {card_name!r}"
        )

    incluir = datos["include"]
    if not isinstance(incluir, bool):
        raise EvaluationError("El campo 'include' debe ser booleano")

    score = datos["synergy_score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 10:
        raise EvaluationError("El campo 'synergy_score' debe ser un entero entre 0 y 10")

    return {
        "card_name": nombre,
        "include": incluir,
        "recommendation_tier": _texto_no_vacio(datos, "recommendation_tier"),
        "synergy_score": score,
        "synergy_category": _texto_no_vacio(datos, "synergy_category"),
        "synergy_themes": _lista_de_textos(datos, "synergy_themes"),
        "pros": _lista_de_textos(datos, "pros"),
        "cons": _lista_de_textos(datos, "cons"),
        "rationale": _texto_no_vacio(datos, "rationale"),
    }


def evaluar_carta(
    carta: dict[str, Any],
    estrategia: str,
    provider: LLMProvider,
) -> dict[str, Any]:
    """Evalúa y valida una carta usando un provider ya configurado.

    Args:
        carta: payload de la carta candidata.
        estrategia: perfil estratégico persistente del mazo.
        provider: provider LLM compartido por la corrida.

    Returns:
        Evaluación validada según el contrato de T-301.
    """
    prompt = construir_prompt(carta, estrategia)
    nombre = str(carta["name"]).strip()
    respuesta = provider.chat(
        system=SYSTEM_PROMPT,
        prompt=prompt,
        max_tokens=MAX_TOKENS_EVALUACION,
        json_mode=True,
    )
    try:
        return parsear_evaluacion(respuesta.text, nombre)
    except EvaluationError as exc:
        raise EvaluationError(f"Evaluación inválida para {nombre!r}: {exc}") from exc


def evaluar_cartas(
    cartas: list[dict[str, Any]],
    strategy_path: Path = Path("estrategia.md"),
    provider: LLMProvider | None = None,
) -> list[dict[str, Any]]:
    """Ejecuta el prompt chaining para todas las cartas candidatas.

    Args:
        cartas: payload filtrado por identidad de color en la Etapa 3.
        strategy_path: ruta del ``estrategia.md`` generado por la Etapa 2.
        provider: provider inyectable; si es ``None`` usa ``create_provider()``.

    Returns:
        Una evaluación validada por carta, preservando el orden de entrada.

    Raises:
        FileNotFoundError: si no existe el archivo de estrategia.
        ValueError: si no hay cartas o la estrategia está vacía.
        EvaluationError: si una respuesta del LLM incumple el contrato.
        LLMError: propagado si falla el provider.
    """
    if not cartas:
        raise ValueError("La lista de cartas candidatas no puede estar vacía")

    estrategia = strategy_path.read_text(encoding="utf-8")
    if not estrategia.strip():
        raise ValueError("El contenido de estrategia.md no puede estar vacío")

    llm = provider or create_provider()
    total = len(cartas)
    inicio_total = time.perf_counter()
    logger.info(
        "Inicio evaluación de sinergia: %d cartas | provider=%s | modelo=%s",
        total,
        llm.name,
        llm.model,
    )

    resultados: list[dict[str, Any]] = []
    for posicion, carta in enumerate(cartas, start=1):
        nombre = str(carta.get("name", "<sin nombre>")).strip()
        inicio_carta = time.perf_counter()
        logger.info("[%d/%d] Inicio evaluación: %s", posicion, total, nombre)
        try:
            resultado = evaluar_carta(carta, estrategia, llm)
        except Exception:
            duracion = time.perf_counter() - inicio_carta
            logger.exception(
                "[%d/%d] Error evaluación: %s (%.2fs)",
                posicion,
                total,
                nombre,
                duracion,
            )
            raise

        duracion = time.perf_counter() - inicio_carta
        resultados.append(resultado)
        logger.info(
            "[%d/%d] Fin evaluación: %s | include=%s | tier=%s | score=%s | %.2fs",
            posicion,
            total,
            nombre,
            resultado["include"],
            resultado["recommendation_tier"],
            resultado["synergy_score"],
            duracion,
        )

    logger.info(
        "Fin evaluación de sinergia: %d/%d cartas | %.2fs",
        len(resultados),
        total,
        time.perf_counter() - inicio_total,
    )
    return resultados
