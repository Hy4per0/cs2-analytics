import argparse
import sys
from pathlib import Path

from cs2_analytics.data.repository import ParsedDataRepository
from cs2_analytics.parser.parse_demo import parse_demo
from cs2_analytics.parser.tick_dataset import generate_tick_dataset


def _add_parse(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("parse", help="Parse a .dem file into event parquet tables")
    p.add_argument("demo", type=Path, help="Path to the .dem file")
    p.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("parsed"),
        help="Directory to write parquet files (default: parsed/)",
    )
    p.set_defaults(handler=_handle_parse)


def _handle_parse(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.output_dir)
    for name, df in parse_demo(str(args.demo)).items():
        getattr(repo, f"save_{name}")(df)
    return 0


def _add_ticks(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("ticks", help="Generate downsampled tick dataset from a .dem file")
    p.add_argument("demo", type=Path, help="Path to the .dem file")
    p.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("parsed"),
        help="Directory to write ticks.parquet (default: parsed/)",
    )
    p.add_argument(
        "--sample-rate",
        type=int,
        default=16,
        help="Keep every Nth tick (default: 16)",
    )
    p.set_defaults(handler=_handle_ticks)


def _handle_ticks(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.output_dir)
    repo.save_ticks(generate_tick_dataset(str(args.demo), sample_rate=args.sample_rate))
    return 0


def _stub(name: str):
    def handler(args: argparse.Namespace) -> int:
        print(f"{name} subcommand not yet wired")
        return 0

    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs2-analytics",
        description="Counter-Strike 2 demo analytics and computer vision pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    _add_parse(sub)
    _add_ticks(sub)
    sub.add_parser("analyze", help="Run analysis on parsed data").set_defaults(
        handler=_stub("analyze")
    )
    sub.add_parser("visualize", help="Render visualizations from parsed data").set_defaults(
        handler=_stub("visualize")
    )
    sub.add_parser("vision", help="Computer vision pipeline").set_defaults(handler=_stub("vision"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
