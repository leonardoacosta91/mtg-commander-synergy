"""CLI de ``python -m mtg_commander.context``."""

import argparse
import logging
from pathlib import Path

from mtg_commander.context.orchestrator import generar_contexto


def construir_parser() -> argparse.ArgumentParser:
    """Construye el parser público del flujo Context."""
    parser = argparse.ArgumentParser(
        description="Genera estrategia.md a partir de un decklist local.",
    )
    parser.add_argument("--deck", required=True, type=Path, help="Decklist .txt")
    parser.add_argument(
        "--output", type=Path, default=Path("estrategia.md"), help="Estrategia de salida"
    )
    parser.add_argument(
        "--research-output",
        type=Path,
        default=Path("research.md"),
        help="Research intermedio de salida",
    )
    parser.add_argument(
        "--provider", choices=("gemini", "openai", "anthropic"), help="Provider LLM"
    )
    parser.add_argument("--force", action="store_true", help="Forzar regeneración")
    parser.add_argument("--verbose", action="store_true", help="Activar logs de debug")
    return parser


def main() -> int:
    """Ejecuta el CLI y devuelve un código de salida de proceso."""
    args = construir_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )
    try:
        resultado = generar_contexto(
            deck_path=args.deck,
            strategy_path=args.output,
            research_path=args.research_output,
            force=args.force,
            provider_name=args.provider,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        logging.error("No se pudo generar el contexto: %s", exc)
        return 1

    if resultado.regenerated:
        print(f"Contexto generado: {resultado.strategy_path}")
    else:
        print(f"Deck sin cambios; contexto reutilizado: {resultado.strategy_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
