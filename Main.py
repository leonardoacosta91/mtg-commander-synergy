"""CLI del pipeline completo de MTG Commander Synergy."""

import argparse
import logging

import requests

from mtg_commander.llm import LLMError
from mtg_commander.pipeline import ejecutar_pipeline, generar_contexto_del_deck


def construir_parser() -> argparse.ArgumentParser:
    """Construye el parser del CLI principal."""
    parser = argparse.ArgumentParser(
        description="Evalúa cartas de un set nuevo para un mazo Commander local.",
    )
    parser.add_argument(
        "--deck",
        required=True,
        help="Nombre de un .txt dentro de data/ o ruta explícita al decklist.",
    )
    parser.add_argument(
        "--set",
        dest="set_override",
        help="Código de set opcional; por defecto detecta el último expansion/core.",
    )
    parser.add_argument(
        "--provider",
        choices=("gemini", "openai", "anthropic"),
        help="Provider LLM; por defecto usa LLM_PROVIDER o gemini.",
    )
    parser.add_argument(
        "--force-context",
        action="store_true",
        help="Regenera estrategia.md aunque el deck no haya cambiado.",
    )
    parser.add_argument(
        "--context-only",
        action="store_true",
        help="Genera o reutiliza estrategia.md sin evaluar cartas ni crear CSV.",
    )
    parser.add_argument("--verbose", action="store_true", help="Activa logs de debug.")
    return parser


def main() -> int:
    """Ejecuta el CLI y devuelve un código de salida de proceso."""
    args = construir_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )

    try:
        if args.context_only:
            context = generar_contexto_del_deck(
                deck=args.deck,
                force=args.force_context,
                provider_name=args.provider,
            )
            accion = "generado" if context.regenerated else "reutilizado"
            print(f"Contexto {accion}: {context.strategy_path}")
            return 0

        resultado = ejecutar_pipeline(
            deck=args.deck,
            set_override=args.set_override,
            force_context=args.force_context,
            provider_name=args.provider,
        )
    except (OSError, requests.RequestException, LLMError, RuntimeError, ValueError) as exc:
        logging.error("No se pudo completar el pipeline: %s", exc)
        return 1

    contexto = "generado" if resultado.context.regenerated else "reutilizado"
    print(f"Deck: {resultado.deck_path}")
    print(
        "Comandante: "
        f"{resultado.commander.nombre} ({'/'.join(resultado.commander.color_identity)})"
    )
    print(f"Contexto {contexto}: {resultado.context.strategy_path}")
    print(f"Set evaluado: {resultado.set_info.name} ({resultado.set_info.code.upper()})")
    print(f"Cartas candidatas: {resultado.candidate_count}")
    print(f"Reporte CSV: {resultado.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
