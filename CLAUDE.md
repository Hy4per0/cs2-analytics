# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two-stage Counter-Strike 2 analytics project:

1. **Demo analysis** — parses `.dem` files into parquet tables, then computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips and trains a YOLOv11 segmentation model to detect players.

Everything is invoked through the `cs2-analytics` console script. There is no `main.py` scratch driver — every operation is a CLI subcommand.

## Single virtual environment

One `uv`-managed venv on **Python 3.11** holds both the analysis stack and the vision stack. `pyproject.toml` declares dependencies; `uv.lock` pins their resolved versions. Running `uv sync --extra dev` from a fresh clone produces a working environment, including CUDA-enabled `torch` from the PyTorch CU121 index.

```powershell
uv sync --extra dev
uv run python -c "import torch; print(torch.cuda.is_available())"  # must print True
```

Older copies of this project had two venvs (`.venv/` Python 3.13 for analysis, `scripts/` Python 3.11 for vision). Both are gone; only one `.venv/` remains, on 3.11.

## Common commands

All operations:

```powershell
uv run cs2-analytics --help                                                      # list subcommands

# Parsing (demo → parquet, per-demo store)
uv run cs2-analytics parse demos/<file>.dem [--output-dir parsed/] [--force]
uv run cs2-analytics ticks demos/<file>.dem [--output-dir parsed/] [--sample-rate 16] [--force]
uv run cs2-analytics parse-batch demos/ [--output-dir parsed/] [--force] [--no-ticks]

# Analysis (over parsed parquet — parse+ticks must run first)
# Defaults to ALL demos in parsed/; --demo <stem> restricts to one.
uv run cs2-analytics analyze [--demo <stem>] rounds
uv run cs2-analytics analyze [--demo <stem>] death-zones --player <name> --map <map>
uv run cs2-analytics analyze [--demo <stem>] entry-kills
uv run cs2-analytics analyze [--demo <stem>] reaction-time --player <name> [--advanced]

# Visualization
uv run cs2-analytics visualize heatmap --player <name> --map <map>

# Vision pipeline
uv run cs2-analytics vision extract <clips-dir> [--out vision/frames/] [--fps 5]
uv run cs2-analytics vision build-dataset
```

YOLO training and inference still go through Ultralytics directly:

```powershell
uv run yolo segment train model=yolo11s-seg.pt data=vision/dataset.yaml epochs=50 imgsz=640 batch=16 device=0
uv run yolo segment predict model=cs2_player_segmentation.pt source=vision/clips/<file>.mp4
```

Trained weights land in `runs/segment/train*/weights/`. `cs2_player_segmentation.pt` (Git-LFS-tracked) is the latest fine-tuned checkpoint; `yolo11s-seg.pt` (gitignored) is the upstream base, re-downloaded by Ultralytics on first use.

## Development

```powershell
uv run pytest          # 10 tests as of foundation merge
uv run ruff check      # lint
uv run ruff format     # auto-format
```

Branch workflow: `main` is the only long-lived branch. Feature work happens on `feature/<name>` branches and merges via PR.

## Package layout

```
src/cs2_analytics/
├── cli.py                    # argparse subcommand dispatcher (entry point: cs2-analytics)
├── data/repository.py        # ParsedDataRepository — sole point of parquet access
├── parser/
│   ├── parse_demo.py         # parse_demo(demo_path) -> dict[str, DataFrame]
│   └── tick_dataset.py       # generate_tick_dataset(demo_path, sample_rate=16) -> DataFrame
├── analysis/
│   ├── death_zones.py        # death_zone_stats(repo, player_name, map_name)
│   ├── entry_kills.py        # entry_kill_stats(repo)
│   ├── reaction_time.py      # reaction_time(repo, player_name)
│   ├── reaction_time_advanced.py  # reaction_time_advanced(repo, player_name)
│   └── round_analyzer.py     # analyze_rounds(repo)
├── visualization/heatmap.py  # player_heatmap_map(repo, player_name, map_name) — awpy adapter (plot)
├── utils/maps.py             # get_zone(map_name, x, y), load_nav(map_name) — awpy adapter (nav)
└── vision/
    ├── frame_extractor.py    # extract_frames(video_path, output_folder, fps=5)
    └── build_dataset.py      # build_dataset() — iterates vision/clips/ with hardcoded paths
```

Tests live in `tests/`. Output / data folders (`parsed/`, `runs/`, `vision/clips/`, `vision/frames/`, `vision/dataset/`, `demos/*.dem`) are gitignored.

## Data flow

```
demos/*.dem ──► parse_demo  ─────► (DataFrames) ──► repo.save_kills(demo_id, ...)
            ╲                                        repo.save_damage(...)
             ╲                                       repo.save_rounds(...)
             ╲                                       repo.save_weapon_fire(...)
             ╲► tick_dataset ─────► (DataFrame) ──► repo.save_ticks(demo_id, ...)
                                                          │
                              parsed/<demo-stem>/*.parquet
                                                          │
                                                          ▼
                                  repo.get_kills(demo_id=None|"X")  → DataFrame w/ demo_id col
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
              analysis/*       visualization     (future: storage,
            (console stats)      (matplotlib       Flask UI, batch)
                                + awpy plot)

vision/clips/*.mp4 ──► extract_frames ──► vision/frames/<clip>/*.jpg
                                      ──► (manual YOLO labels) ──► vision/dataset/{images,labels}/train
                                      ──► YOLO training ──► cs2_player_segmentation.pt
```

Analysis and visualization modules **never** call `pd.read_parquet` or construct parquet paths. They take a `ParsedDataRepository` instance and use its `get_*` methods. The repository is the only module that knows the on-disk layout, which makes the storage backend swappable later.

## Module conventions

- **Real packages with `__init__.py` files.** No more namespace-package quirks; imports work from anywhere.
- **Storage is per-demo.** `parsed/<demo-stem>/<table>.parquet`. Every `repo.save_*` takes a `demo_id` argument; every `repo.get_*` accepts an optional `demo_id` (defaults to aggregating across all demos and adding a `demo_id` column).
- **All analyses take `(repo, ...)` as their first argument.** Adding a new analysis means adding a new file under `cs2_analytics/analysis/` and registering one entry in `cli.py`'s analyze dispatch (OCP).
- **Player identity is matched by name string** (e.g. `"AngelsHy4per"`) across `kills.user_name`, `kills.attacker_name`, `ticks.name`, `weapon_fire.user_name`. There is no steam-id join. Migrating to SteamID is a known future concern (not on the foundation).
- **Tick alignment** between events and `ticks.parquet` is approximate — events fire on every tick, but `ticks.parquet` only stores every 16th tick by default. `analysis/death_zones.py` handles this by finding the closest tick; `analysis/reaction_time_advanced.py` does an exact match and silently drops events that fall on unsampled ticks.
- **Map names** follow Source convention (`de_inferno`, `de_dust2`, `de_mirage`, `de_overpass`). The `awpy` adapter (`cs2_analytics/utils/maps.py`) resolves them to nav meshes via `NAVS_DIR`.
- **`demoparser2 0.41.x` field names**: player view-angle fields are `yaw` / `pitch`, not `view_angle_yaw` / `view_angle_pitch`. Older releases used the longer names; if you upgrade beyond 0.41.x, double-check the field names in `parser/tick_dataset.py` and `analysis/reaction_time_advanced.py`.

## Vision dataset layout

`vision/dataset.yaml` points to `vision/dataset/{images,labels}/train` (val == train, i.e. no held-out split — trained metrics are training metrics, not validation). Single class: `0: player`. Frames are extracted at 5 fps from `vision/clips/`. Clip filenames encode the round outcome (e.g. `clip3_dust2_wonandmiss.mp4`) for human reference; this is not parsed anywhere.

## Info

`cs2_player_segmentation.pt` is a fine-tuned YOLOv11 segmentation checkpoint trained on CS2 player models / skins (built initially with Source Viewer). It is **Git-LFS-tracked** (~58 MB); a fresh clone with `git lfs install` configured will pull it automatically.

## Architecture

Apply SOLID principles, with these three design patterns as the project's structural backbone:

- **Pipeline (Pipes-and-Filters)** — overall data flow shape: parse → tick dataset → analysis → visualization. Each stage takes well-defined input, produces well-defined output, and doesn't know about other stages.
- **Repository** — data access for parsed parquet files goes through `cs2_analytics.data.repository.ParsedDataRepository`. Analysis and visualization modules never call `pd.read_parquet(...)` directly. This lets Phase 2 swap the storage backend (e.g. DuckDB) without touching analysis code.
- **Adapter** — `awpy` is only imported in two adapter modules: `cs2_analytics.utils.maps` (nav meshes) and `cs2_analytics.visualization.heatmap` (map rendering). The rest of the codebase imports from these adapters, never `awpy.*` directly.

SOLID applied concretely: parsers parse only (SRP — persistence is the repository's job); new analyses live in new files registered in the CLI dispatch table (OCP — no modification to existing analyses); analyses depend on the repository interface and the awpy adapters (DIP — not on filesystem paths or `awpy.*` internals). LSP/ISP are not artificially chased in mostly-procedural code.

## Where to look first

- **Roadmap & current state**: `STATUS.md` (project root)
- **Foundation spec**: `docs/superpowers/specs/2026-05-06-foundation-design.md`
- **Foundation execution plan**: `docs/superpowers/plans/2026-05-06-foundation.md`
- **Tests**: `tests/test_repository.py`, `tests/test_cli.py`, `tests/test_smoke.py`
