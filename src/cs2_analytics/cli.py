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
from cs2_analytics.vision.build_dataset import build_dataset
from cs2_analytics.vision.frame_extractor import extract_frames
from cs2_analytics.visualization.heatmap import player_heatmap_map


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
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite parsed/<demo-stem>/ if it already exists.",
    )
    p.set_defaults(handler=_handle_parse)


def _handle_parse(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.output_dir)
    demo_id = args.demo.stem
    if repo.demo_exists(demo_id) and not args.force:
        print(
            f"error: {args.output_dir / demo_id}/ already exists. "
            f"Pass --force to overwrite, or delete the directory.",
            file=sys.stderr,
        )
        return 2
    for name, df in parse_demo(str(args.demo)).items():
        getattr(repo, f"save_{name}")(demo_id, df)
        print(f"wrote {args.output_dir / demo_id / (name + '.parquet')}")
    print(f"parsed: {demo_id}")
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
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite parsed/<demo-stem>/ticks.parquet if it already exists.",
    )
    p.set_defaults(handler=_handle_ticks)


def _handle_ticks(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.output_dir)
    demo_id = args.demo.stem
    ticks_path = args.output_dir / demo_id / "ticks.parquet"
    if ticks_path.exists() and not args.force:
        print(
            f"error: {ticks_path} already exists. "
            f"Pass --force to overwrite, or delete the file.",
            file=sys.stderr,
        )
        return 2
    repo.save_ticks(demo_id, generate_tick_dataset(str(args.demo), sample_rate=args.sample_rate))
    print(f"wrote {ticks_path}")
    return 0


def _add_parse_batch(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "parse-batch",
        help="Parse every .dem in a directory; skip demos already in the store.",
    )
    p.add_argument("demos_dir", type=Path, help="Directory containing .dem files")
    p.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("parsed"),
        help="Directory to write parquet files (default: parsed/)",
    )
    p.add_argument(
        "--sample-rate",
        type=int,
        default=16,
        help="Tick sample rate (default: 16). Ignored if --no-ticks.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-parse every demo even if its dir already exists.",
    )
    p.add_argument(
        "--no-ticks",
        action="store_true",
        help="Skip the tick-dataset stage for each demo.",
    )
    p.set_defaults(handler=_handle_parse_batch)


def _handle_parse_batch(args: argparse.Namespace) -> int:
    demos_dir: Path = args.demos_dir
    if not demos_dir.is_dir():
        print(f"error: demos_dir is not a directory: {demos_dir}", file=sys.stderr)
        return 2

    repo = ParsedDataRepository(args.output_dir)
    parsed_count = skipped_count = failed_count = 0

    for demo in sorted(demos_dir.glob("*.dem")):
        demo_id = demo.stem
        if repo.demo_exists(demo_id) and not args.force:
            print(f"skip: {demo_id} (already parsed)")
            skipped_count += 1
            continue
        try:
            for name, df in parse_demo(str(demo)).items():
                getattr(repo, f"save_{name}")(demo_id, df)
            if not args.no_ticks:
                repo.save_ticks(
                    demo_id, generate_tick_dataset(str(demo), sample_rate=args.sample_rate)
                )
            print(f"parse: {demo_id}")
            parsed_count += 1
        except Exception as exc:  # noqa: BLE001 — surface any parser failure per-demo
            print(f"fail: {demo_id} ({exc.__class__.__name__}: {exc})")
            failed_count += 1

    print(f"parse-batch: {parsed_count} parsed, {skipped_count} skipped, {failed_count} failed")
    return 0 if failed_count == 0 else 1


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
    dz.add_argument("--player", required=True, help="Player name as it appears in the demo")
    dz.add_argument(
        "--map",
        dest="map_name",
        required=True,
        help="Source map name (e.g. de_dust2, de_mirage)",
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


def _add_visualize(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("visualize", help="Render visualizations from parsed data")
    p.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path("parsed"),
        help="Directory containing parquet files (default: parsed/)",
    )
    leaf = p.add_subparsers(dest="visualize_command", required=True)

    hm = leaf.add_parser("heatmap", help="Per-player KDE heatmap on a map")
    hm.add_argument("--player", required=True, help="Player name")
    hm.add_argument("--map", dest="map_name", required=True, help="Map name")
    hm.set_defaults(handler=_handle_visualize_heatmap)


def _handle_visualize_heatmap(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    player_heatmap_map(repo, args.player, args.map_name)
    return 0


def _add_vision(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("vision", help="Computer vision pipeline")
    leaf = p.add_subparsers(dest="vision_command", required=True)

    ex = leaf.add_parser("extract", help="Extract frames from clips")
    ex.add_argument("clips_dir", type=Path, help="Directory of input .mp4 clips")
    ex.add_argument(
        "--out", type=Path, default=Path("vision/frames"), help="Output frames dir"
    )
    ex.add_argument("--fps", type=int, default=5, help="Frames per second to extract")
    ex.set_defaults(handler=_handle_vision_extract)

    bd = leaf.add_parser(
        "build-dataset", help="Build the YOLO training dataset from labeled frames"
    )
    bd.set_defaults(handler=_handle_vision_build_dataset)


def _handle_vision_extract(args: argparse.Namespace) -> int:
    clips_dir: Path = args.clips_dir
    out_dir: Path = args.out
    if not clips_dir.is_dir():
        print(f"error: clips_dir is not a directory: {clips_dir}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for clip in sorted(clips_dir.glob("*.mp4")):
        extract_frames(str(clip), str(out_dir / clip.stem), fps=args.fps)
        count += 1
    print(f"extracted frames from {count} clip(s) into {out_dir}")
    return 0


def _handle_vision_build_dataset(args: argparse.Namespace) -> int:
    build_dataset()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs2-analytics",
        description="Counter-Strike 2 demo analytics and computer vision pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    _add_parse(sub)
    _add_parse_batch(sub)
    _add_ticks(sub)
    _add_analyze(sub)
    _add_visualize(sub)
    _add_vision(sub)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
