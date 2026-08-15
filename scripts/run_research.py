"""CLI para ejecutar el research de Reddit manualmente (Etapa 2b).

Uso:
    python scripts/run_research.py \\
        --commander "Y'shtola, Night's Blessed" \\
        --color-identity W U B \\
        --deck data/yshtola_esper.txt

El archivo research.md se genera en el directorio de trabajo actual.
"""

import argparse
import logging
import sys
from pathlib import Path

# Asegura que el proyecto esté en el path cuando se corre como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mtg_commander.context.reddit_research import generar_research


def main() -> None:
    """Punto de entrada del CLI."""
    parser = argparse.ArgumentParser(
        description="Genera research.md buscando info del comandante en Reddit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/run_research.py \\
      --commander "Y'shtola, Night's Blessed" \\
      --color-identity W U B \\
      --deck data/yshtola_esper.txt
        """,
    )
    parser.add_argument(
        "--commander",
        required=True,
        help='Nombre completo del comandante, ej: "Y\'shtola, Night\'s Blessed"',
    )
    parser.add_argument(
        "--color-identity",
        nargs="+",
        default=[],
        metavar="COLOR",
        help="Identidad de color del mazo, ej: W U B",
    )
    parser.add_argument(
        "--deck",
        required=True,
        help="Ruta al archivo .txt del decklist",
    )
    parser.add_argument(
        "--output",
        default="research.md",
        help="Ruta de salida para research.md (default: research.md)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar logs de debug",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )

    print(f"\n🔍 Buscando research para: {args.commander}")
    print(f"   Color identity : {' '.join(args.color_identity) or 'no especificada'}")
    print(f"   Decklist       : {args.deck}")
    print(f"   Output         : {args.output}\n")

    try:
        output_path = generar_research(
            commander=args.commander,
            color_identity=args.color_identity,
            decklist_path=args.deck,
            output_path=Path(args.output),
        )
        print(f"\n✅ research.md generado en: {output_path}")

    except EnvironmentError as e:
        print(f"\n❌ Error de configuración: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
