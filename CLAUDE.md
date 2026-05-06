# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two-stage Counter-Strike 2 analytics project:

1. **Demo analysis** — parses `.dem` files into parquet tables, then computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips and trains a YOLOv11 segmentation model to detect players.

`main.py` is the orchestrator for the demo-analysis pipeline. Lines are commented in/out to toggle which steps run; treat it as a scratch driver, not a CLI.

## Two virtual environments (important)

The project uses **two separate venvs** because the analysis stack and the vision stack have incompatible Python versions:

| Venv | Python | Purpose | Key packages |
|------|--------|---------|--------------|
| `.venv/` | 3.13 | Demo parsing & analysis | `awpy`, `demoparser2`, `pandas`, `matplotlib`, `polars`, `pyarrow` |
| `scripts/` | 3.11 | YOLO training / inference | `torch+cu121`, `torchvision`, `ultralytics`, `opencv-python` |

`scripts/` looks like a source directory but is actually a venv (it has `pyvenv.cfg`, `Scripts/python.exe`, `Lib/site-packages`). Do **not** put project code in it.

Activation (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1       # for main.py and analysis/
.\scripts\Scripts\Activate.ps1     # for vision/ training/inference
```

When running anything that imports `awpy`/`demoparser2`/`pandas`, use `.venv`. When running anything that imports `ultralytics`/`torch`/`cv2`, use `scripts`.

## Common commands

Run the analysis pipeline (uses `.venv`):
```powershell
python main.py
```

Build the vision dataset (frames from clips; uses `scripts` venv):
```powershell
cd vision; python build_dataset.py
```

Train the YOLO segmentation model (uses `scripts` venv):
```powershell
yolo segment train model=yolo11s-seg.pt data=vision/dataset.yaml epochs=50 imgsz=640 batch=16 device=0
```
Trained weights land in `runs/segment/train*/weights/`. The repo's `cs2_player_segmentation.pt` is the latest fine-tuned checkpoint; `yolo11s-seg.pt` is the upstream base. Training args from the most recent run are preserved in `runs/segment/train/args.yaml`.

Run inference:
```powershell
yolo segment predict model=cs2_player_segmentation.pt source=vision/clips/<file>.mp4
```

There are no tests, linter config, or build system.

## Data flow

```
demos/*.dem ──► parser.parse_demo ─────► parsed/{kills,damage,rounds,weapon_fire}.parquet
            ╲
             ╲► dataset.tick_dataset ──► parsed/ticks.parquet  (downsampled: tick % 16 == 0)

parsed/*.parquet ──► analysis/*           (console stats)
                 ╲
                  ╲► visualization.heatmap (matplotlib over awpy map render)

vision/clips/*.mp4 ──► frame_extractor ──► vision/frames/<clip>/*.jpg
                                       ──► (manual YOLO labels) ──► vision/dataset/{images,labels}/train
                                       ──► YOLO training ──► cs2_player_segmentation.pt
```

The analysis modules (`analysis/`, `visualization/`, `utils/map_zones_awpy.py`) read parquet files directly from `parsed/`. They do not take the demo as input — `parse_demo` and `tick_dataset` must run first. Paths are relative, so always run scripts from the project root.

## Module conventions

- **Module folders have no `__init__.py`.** They rely on Python 3 namespace packages — adding empty `__init__.py` files is unnecessary, but be aware that imports like `from parser.parse_demo import parse_demo` only work when CWD is the project root.
- **Player identity is matched by name string** (e.g. `"AngelsHy4per"`) across `kills.user_name`, `kills.attacker_name`, `ticks.name`, `weapon_fire.user_name`. There's no steam-id join.
- **Tick alignment** between events and `ticks.parquet` is approximate — events fire on every tick, but `ticks.parquet` only stores every 16th tick. `analysis/death_zones.py` handles this by finding the closest tick; `analysis/reaction_time_advanced.py` does an exact match and silently drops events that fall on unsampled ticks.
- **Map names** follow Source convention (`de_inferno`, `de_dust2`, `de_mirage`, `de_overpass`). `awpy` resolves these to nav meshes via `NAVS_DIR`. `analysis/death_zones.py` has `de_inferno` hardcoded — change it there if analyzing other maps.
- **Demo path is hardcoded** in `main.py`. To analyze a different demo, edit `demo_path` directly.

## Vision dataset layout

`vision/dataset.yaml` points to `vision/dataset/{images,labels}/train` (val == train, i.e. no held-out split — trained metrics are training metrics, not validation). Single class: `0: player`. Frames are extracted at 5 fps from `vision/clips/`. Clip filenames encode the round outcome (e.g. `clip3_dust2_wonandmiss.mp4`) for human reference; this is not parsed anywhere.

## Info

Just so you know `cs2_player_segmentation.pt` is a model that is trained on different skins and models disponible in cs2. It was trained with Source Viewer or something like that.

## Architecture

Apply SOLID principles, with these three design patterns as the project's structural backbone:

- **Pipeline (Pipes-and-Filters)** — overall data flow shape: parse → tick dataset → analysis → visualization. Each stage takes well-defined input, produces well-defined output, and doesn't know about other stages.
- **Repository** — data access for parsed parquet files goes through `cs2_analytics.data.repository.ParsedDataRepository`. Analysis and visualization modules never call `pd.read_parquet(...)` directly. This lets Phase 2 swap the storage backend (e.g. DuckDB) without touching analysis code.
- **Adapter** — `awpy` is only imported in two adapter modules: `cs2_analytics.utils.maps` (nav meshes) and `cs2_analytics.visualization.heatmap` (map rendering). The rest of the codebase imports from these adapters, never `awpy.*` directly.

SOLID applied concretely: parsers parse only (SRP — persistence is the repository's job); new analyses live in new files registered in the CLI dispatch table (OCP — no modification to existing analyses); analyses depend on the repository interface and the awpy adapters (DIP — not on filesystem paths or `awpy.*` internals). LSP/ISP are not artificially chased in mostly-procedural code.