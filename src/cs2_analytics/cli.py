import argparse
import sys
from pathlib import Path

from cs2_analytics.analysis.death_zones import death_zone_stats
from cs2_analytics.analysis.entry_kills import entry_kill_stats
from cs2_analytics.analysis.reaction_time import reaction_time
from cs2_analytics.analysis.reaction_time_advanced import reaction_time_advanced
from cs2_analytics.analysis.round_analyzer import analyze_rounds
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


def _add_analyze(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("analyze", help="Run analysis on parsed data")
    p.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path("parsed"),
        help="Directory containing parquet files (default: parsed/)",
    )
    leaf = p.add_subparsers(dest="analyze_command", required=True)

    rounds = leaf.add_parser("rounds", help="Round-by-round summary stats")
    rounds.set_defaults(handler=_handle_analyze_rounds)

    dz = leaf.add_parser("death-zones", help="Where a player dies most often")
    dz.add_argument("--player", required=True, help="Player name (e.g. AngelsHy4per)")
    dz.add_argument(
        "--map", dest="map_name", required=True, help="Map name (e.g. de_inferno)"
    )
    dz.set_defaults(handler=_handle_analyze_death_zones)

    ek = leaf.add_parser("entry-kills", help="Entry kill statistics")
    ek.set_defaults(handler=_handle_analyze_entry_kills)

    rt = leaf.add_parser("reaction-time", help="Player reaction time")
    rt.add_argument("--player", required=True, help="Player name")
    rt.add_argument(
        "--advanced",
        action="store_true",
        help="Use the advanced reaction-time calculation",
    )
    rt.set_defaults(handler=_handle_analyze_reaction_time)


def _handle_analyze_rounds(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    analyze_rounds(repo)
    return 0


def _handle_analyze_death_zones(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    death_zone_stats(repo, args.player, args.map_name)
    return 0


def _handle_analyze_entry_kills(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    entry_kill_stats(repo)
    return 0


def _handle_analyze_reaction_time(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    if args.advanced:
        reaction_time_advanced(repo, args.player)
    else:
        reaction_time(repo, args.player)
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
    _add_analyze(sub)
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
