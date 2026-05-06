import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs2-analytics",
        description="Counter-Strike 2 demo analytics and computer vision pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("parse", help="Parse a .dem file into event parquet tables")
    sub.add_parser("ticks", help="Generate downsampled tick dataset from a .dem file")
    sub.add_parser("analyze", help="Run analysis on parsed data")
    sub.add_parser("visualize", help="Render visualizations from parsed data")
    sub.add_parser("vision", help="Computer vision pipeline (frame extraction, dataset build)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    print(f"command={args.command} (not yet implemented)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
