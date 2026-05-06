# CS2 Analytics

Two-stage Counter-Strike 2 analytics pipeline.

1. **Demo analysis** — parses `.dem` files into parquet tables, computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips, trains a YOLOv11 segmentation model to detect players.

## Setup

Requires Python 3.11, [uv](https://github.com/astral-sh/uv), and Git LFS.

```powershell
# 1. Clone (LFS pulls the trained model automatically)
git clone https://github.com/Hy4per0/cs2-analytics.git
cd cs2-analytics

# 2. Sync dependencies (creates .venv on Python 3.11 with CUDA-enabled torch)
uv sync --extra dev

# 3. Verify CUDA is available
uv run python -c "import torch; print(torch.cuda.is_available())"
```

## CLI usage

All operations go through the `cs2-analytics` console script.

```powershell
# Parse a demo into kills/damage/rounds/weapon_fire parquet tables
uv run cs2-analytics parse demos/<your-demo>.dem

# Generate a downsampled tick dataset (every 16th tick by default)
uv run cs2-analytics ticks demos/<your-demo>.dem

# Run analysis (parsed/*.parquet must exist first)
uv run cs2-analytics analyze rounds
uv run cs2-analytics analyze death-zones --player <player-name> --map de_inferno
uv run cs2-analytics analyze entry-kills
uv run cs2-analytics analyze reaction-time --player <player-name> --advanced

# Visualize
uv run cs2-analytics visualize heatmap --player <player-name> --map de_inferno

# Vision pipeline
uv run cs2-analytics vision extract vision/clips/ --fps 5
uv run cs2-analytics vision build-dataset

# Train YOLO (uses ultralytics CLI directly, not cs2-analytics)
uv run yolo segment train model=yolo11s-seg.pt data=vision/dataset.yaml epochs=50 imgsz=640 batch=16 device=0
```

## Architecture

See `CLAUDE.md` and `docs/superpowers/specs/2026-05-06-foundation-design.md`.

Three patterns:

- **Pipeline** — data flows demo → parse → ticks → analysis/visualization
- **Repository** (`cs2_analytics.data.repository.ParsedDataRepository`) — single point of parquet access; analysis modules never read parquet by path
- **Adapter** — `awpy` is only imported in `cs2_analytics.utils.maps` and `cs2_analytics.visualization.heatmap`; everything else uses these adapters

SOLID applied to SRP / OCP / DIP. New analyses go in `src/cs2_analytics/analysis/<name>.py` and are registered in `src/cs2_analytics/cli.py`.

## Development

```powershell
uv run pytest          # run tests (10 currently)
uv run ruff check      # lint
uv run ruff format     # auto-format
```

Branch workflow: `main` is the only long-lived branch. Feature work happens on `feature/<name>` branches and merges via PR.

## License

MIT — see `LICENSE`.
