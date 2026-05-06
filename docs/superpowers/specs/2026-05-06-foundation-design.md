# Foundation Design — CS2 Analytics

**Date:** 2026-05-06
**Status:** Draft, awaiting user review
**Phase:** Phase 0 + Phase 1 (combined as "Foundation")

## 1. Context

The project today is two CS2 analytics pipelines glued together by `main.py`:

1. **Demo analysis** — `demoparser2` parses `.dem` files into parquet tables; `analysis/` modules compute heatmaps, death zones, entry kills, reaction time on those tables.
2. **Computer vision** — `vision/` extracts frames from gameplay clips and trains a YOLOv11 segmentation model (`cs2_player_segmentation.pt`).

The current state has accumulated debt that blocks future work:

- **Two virtual environments** (`.venv/` Python 3.13 for analysis, `scripts/` Python 3.11 for vision/torch) — historical, not actually required by the libraries
- **No dependency manifest** at the project root — `requirements.txt`, `pyproject.toml`, lockfiles all absent
- **Not a git repository** — no version control, no remote
- **`main.py` is a scratch driver** — comment-in/out lines toggle which analyses run; hardcoded demo path, output dir, player name
- **Hardcoded `de_inferno`** in `analysis/death_zones.py`
- **Namespace packages without `__init__.py`** — imports only resolve when CWD is the project root
- **No tests, no linter, no build system**

This spec covers Phase 0 (repo + reproducibility floor) and Phase 1 (architecture refactor) as a combined foundation. Later phases — storage/batch pipeline, Flask UI, vision integration — are scoped separately and depend on this foundation.

## 2. Goals & non-goals

### Goals
- Single Python 3.11 virtual environment, managed by `uv`, fully reproducible from a committed lockfile
- Public GitHub repository, MIT-licensed, with `cs2_player_segmentation.pt` (58.4 MB) tracked via Git LFS
- Proper Python package layout (`src/cs2_analytics/`) replacing the namespace-package quirks
- Real CLI (`cs2-analytics <command>`) replacing `main.py`'s comment-toggling pattern
- All hardcoded values (demo path, output dir, player name, map name) become CLI arguments
- `awpy` usage isolated to adapter modules; the rest of the code never imports `awpy.*` directly
- Repository pattern for parsed-data access; analyses no longer call `pd.read_parquet(...)` directly
- SOLID applied where it pays off (SRP, OCP, DIP); LSP/ISP not chased in procedural code
- Minimum quality floor: `ruff` lint/format + one smoke test

### Non-goals (explicit deferrals)
- GitHub Actions CI — Phase 2+
- `mypy` type checking — Phase 2+
- Pre-commit hooks — Phase 2+
- Real test suite (only smoke test in foundation)
- Player identity by SteamID instead of name string — separate concern
- Batch processing of multiple demos — Phase 2
- Flask web UI — Phase 3
- Persistent storage layer (DuckDB / accumulated stats) — Phase 2
- Any new analysis features

## 3. Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Python version | **3.11** | `torch 2.5.1+cu121` has no 3.13 wheels; awpy requires ≥3.11 |
| Package manager | **`uv`** | Fast, real lockfile (`uv.lock`), single tool for venv+deps |
| Dependency manifest | **`pyproject.toml`** with `hatchling` build backend | Standard, supports console scripts, ruff config |
| Package layout | **`src/` layout** under `src/cs2_analytics/` | Modern Python default; avoids "works in dev but not when installed" bugs |
| CLI framework | **stdlib `argparse`** | No extra dependency; sufficient for subcommand structure |
| Linter/formatter | **`ruff`** | Single tool replaces black + isort + flake8 |
| `.pt` model storage | **Git LFS** for `cs2_player_segmentation.pt`; `yolo11s-seg.pt` gitignored (re-downloadable upstream) | 58.4 MB exceeds GitHub's 50 MB warn threshold |
| Repo visibility | **Public**, **MIT** license | User preference |
| Branch workflow | `main` + `feature/<name>` branches via PR | Trunk-based with feature branches |
| `awpy` strategy | **Keep with adapter layer** (Option 3 from brainstorm) | Parsing already uses `demoparser2` directly; awpy only used in two narrow spots; isolating it costs ~zero extra during the refactor and future-proofs against awpy issues |
| `dataset/` source folder | **Merge into `parser/`** | Both are demo-parsing stages; eliminates `dataset/` ambiguity (currently overloaded as both code and output dir) |
| Architecture patterns | **Pipeline + Repository + Adapter** | Pipeline names what already exists; Repository abstracts parquet access so Phase 2 can swap storage; Adapter isolates `awpy`. Strategy/Command rejected as overkill for current scale. |

## 4. Repo & infrastructure

### Files created at the project root

| File | Purpose |
|---|---|
| `.git/` | `git init`, push to `github.com/<user>/<repo>` (public) |
| `.gitignore` | Excludes venvs, build artifacts, gitignored data dirs (see below) |
| `.gitattributes` | `cs2_player_segmentation.pt filter=lfs diff=lfs merge=lfs -text` |
| `LICENSE` | MIT |
| `README.md` | Project description, setup, CLI usage, branching note |
| `.python-version` | `3.11` (uv reads this) |
| `pyproject.toml` | Dependencies, ruff config, console script entry point |
| `uv.lock` | Generated by `uv sync`, committed |

### `.gitignore` rules

```
# Virtual environments
.venv/
scripts/        # legacy 3.11 venv, removed during refactor

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
dist/

# Project data (regenerable)
parsed/
runs/
vision/clips/
vision/frames/
vision/dataset/

# Demo files (large, may contain personal data)
demos/*.dem

# Models
yolo11s-seg.pt    # upstream base, re-downloaded by ultralytics

# IDE / editor
.idea/
.vscode/
.env
```

### Files deleted

- `scripts/` — legacy 3.11 venv
- `.venv/` — recreated by uv on first sync
- `features/`, `models/` — empty directories
- `main.py` — replaced by the CLI

### Branch workflow

- `main` is the only long-lived branch
- This refactor lives on `phase-0-1-foundation`, merges to `main` via PR
- All future feature work follows the same `feature/<name>` → PR → `main` pattern

## 4a. Architecture patterns

The project uses three patterns as its structural backbone. They're complementary, not competing.

### Pipeline (Pipes-and-Filters)

The data flow already is a pipeline; this just names it.

```
demos/*.dem
    │
    ▼
[parser]  ──► DataFrames (kills, damage, rounds, weapon_fire, ticks)
    │
    ▼
[ParsedDataRepository.save_*]  ──► parsed/*.parquet
    │
    ▼
[ParsedDataRepository.get_*]   ──► DataFrames
    │
    ▼
[analysis]  ──► console stats / structured results
[visualization]  ──► matplotlib figures
```

Each stage has a well-defined input/output shape and does not reach across stages.

### Repository

`cs2_analytics.data.repository.ParsedDataRepository` is the **only** module that knows the parquet file layout. Analysis and visualization modules receive a repository instance and call `get_kills()`, `get_ticks(map_name=...)`, etc. — they never see a path.

Foundation-phase interface:

```python
class ParsedDataRepository:
    def __init__(self, parsed_dir: Path | str): ...

    # Read side (used by analysis, visualization)
    def get_kills(self) -> pd.DataFrame: ...
    def get_damage(self) -> pd.DataFrame: ...
    def get_rounds(self) -> pd.DataFrame: ...
    def get_weapon_fire(self) -> pd.DataFrame: ...
    def get_ticks(self) -> pd.DataFrame: ...

    # Write side (used by parser CLI subcommands)
    def save_kills(self, df: pd.DataFrame) -> None: ...
    def save_damage(self, df: pd.DataFrame) -> None: ...
    def save_rounds(self, df: pd.DataFrame) -> None: ...
    def save_weapon_fire(self, df: pd.DataFrame) -> None: ...
    def save_ticks(self, df: pd.DataFrame) -> None: ...
```

Phase 2 can replace this class with a DuckDB-backed implementation; nothing downstream changes.

### Adapter (`awpy` isolation)

Only two modules may import from `awpy`:

- `cs2_analytics.utils.maps` — nav meshes, zone detection (`awpy.data`, `awpy.nav`)
- `cs2_analytics.visualization.heatmap` — KDE map rendering (`awpy.plot`)

Everything else imports from these adapters. A future awpy replacement touches two files, not the whole codebase.

### SOLID — concrete application

| Principle | How it shows up |
|---|---|
| **S**ingle Responsibility | Parser modules parse and return DataFrames. Persistence is the repository's job. Today's `parse_demo.py` mixes these — split during refactor. |
| **O**pen/Closed | New analyses go in new files under `analysis/` and get a new dispatch entry in `cli.py`. Existing analyses are not modified to add a new one. |
| **D**ependency Inversion | Analysis depends on `ParsedDataRepository` (interface-shaped) and the `maps` / `heatmap` adapters. Not on filesystem paths or `awpy.*` internals. |
| **L**iskov Substitution | Not artificially pursued. If multiple repository implementations land in Phase 2, they share the method signatures above; that's enough. |
| **I**nterface Segregation | Read and write methods on `ParsedDataRepository` could be split into `ParsedDataReader` / `ParsedDataWriter` if the surface grows. Not split now — premature. |

## 5. Package structure

```
Project_Cs2_Game_Analyses/
├── src/
│   └── cs2_analytics/
│       ├── __init__.py
│       ├── cli.py                      # argparse subcommand dispatcher
│       ├── data/
│       │   ├── __init__.py
│       │   └── repository.py           # ParsedDataRepository (only module that touches parquet paths)
│       ├── parser/
│       │   ├── __init__.py
│       │   ├── parse_demo.py           # parses demo, returns dict of DataFrames; no persistence
│       │   └── tick_dataset.py         # parses ticks, returns DataFrame; no persistence
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── death_zones.py
│       │   ├── entry_kills.py
│       │   ├── reaction_time.py
│       │   ├── reaction_time_advanced.py
│       │   └── round_analyzer.py
│       ├── visualization/
│       │   ├── __init__.py
│       │   └── heatmap.py              # awpy adapter (visualization side)
│       ├── utils/
│       │   ├── __init__.py
│       │   └── maps.py                 # was utils/map_zones_awpy.py — awpy adapter (nav side)
│       └── vision/
│           ├── __init__.py
│           ├── frame_extractor.py
│           └── build_dataset.py
├── tests/
│   └── test_smoke.py                   # imports + CLI --help
├── demos/                              # gitignored
├── parsed/                             # gitignored
├── runs/                               # gitignored
├── vision/
│   ├── clips/                          # gitignored
│   ├── frames/                         # gitignored
│   ├── dataset/                        # gitignored
│   └── dataset.yaml                    # COMMITTED — config, not data
├── cs2_player_segmentation.pt          # LFS-tracked
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── .gitignore
├── .gitattributes
└── .python-version
```

### Module changes

| Old path | New path | Notes |
|---|---|---|
| `parser/parse_demo.py` | `src/cs2_analytics/parser/parse_demo.py` | **Behavior change (SRP):** returns a dict of DataFrames; no longer writes parquet itself. The CLI calls the repository to persist. |
| `dataset/tick_dataset.py` | `src/cs2_analytics/parser/tick_dataset.py` | **Behavior change (SRP):** returns a DataFrame; no longer writes parquet. Merged into `parser/`. |
| `analysis/*.py` | `src/cs2_analytics/analysis/*.py` | **Behavior change (DIP):** each analysis takes a `ParsedDataRepository` instead of reading parquet files by path. Existing logic unchanged. |
| `utils/map_zones_awpy.py` | `src/cs2_analytics/utils/maps.py` | Renamed; this is the awpy nav adapter |
| `visualization/heatmap.py` | `src/cs2_analytics/visualization/heatmap.py` | **Behavior change (DIP):** takes a `ParsedDataRepository` for tick data; map render still through awpy adapter |
| `vision/*.py` | `src/cs2_analytics/vision/*.py` | No behavior change |
| `main.py` | (deleted) | Replaced by CLI |
| (new) | `src/cs2_analytics/data/repository.py` | New: `ParsedDataRepository` |

### awpy adapter discipline

- `cs2_analytics/utils/maps.py` is the **only** module that imports from `awpy.data` / `awpy.nav`
- `cs2_analytics/visualization/heatmap.py` is the **only** module that imports from `awpy.plot`
- `cs2_analytics/analysis/death_zones.py` calls `from cs2_analytics.utils.maps import get_zone, load_nav` — never `awpy.*` directly
- Future modules must follow this rule. If awpy gets abandoned, replacing it means rewriting two files, not searching the entire codebase.

## 6. Dependencies — `pyproject.toml`

```toml
[project]
name = "cs2-analytics"
version = "0.1.0"
description = "CS2 demo analytics and computer vision pipeline"
requires-python = ">=3.11,<3.12"
license = { text = "MIT" }
dependencies = [
    "awpy>=2.0.2",
    "demoparser2>=0.41.1",
    "pandas",
    "polars",
    "pyarrow",
    "matplotlib",
    "seaborn",
    "scipy",
    "numpy",
    "torch==2.5.1",
    "torchvision==0.20.1",
    "ultralytics>=8.4.22",
    "opencv-python",
]

[project.optional-dependencies]
dev = ["ruff", "pytest"]

[project.scripts]
cs2-analytics = "cs2_analytics.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
torch = { index = "pytorch-cu121" }
torchvision = { index = "pytorch-cu121" }

[[tool.uv.index]]
name = "pytorch-cu121"
url = "https://download.pytorch.org/whl/cu121"
explicit = true

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

`torch` and `torchvision` are explicitly version-pinned because they must come from the PyTorch CUDA 12.1 index — minor version drift can break CUDA compatibility. All other packages (`pandas`, `numpy`, `awpy`, etc.) are left unconstrained or use floor-only constraints. The lockfile (`uv.lock`) captures the exact resolved versions for full reproducibility; additional pins are only added if `uv sync` produces a conflict (see risks in Section 9).

## 7. CLI design

`main.py` becomes `cs2-analytics` with subcommands. Each line of today's `main.py` maps to one subcommand invocation.

| Today's `main.py` | New CLI invocation |
|---|---|
| `parse_demo(demo_path, output_dir)` | `cs2-analytics parse <demo> [--output-dir parsed/]` |
| `generate_tick_dataset(demo_path, output_dir)` | `cs2-analytics ticks <demo> [--output-dir parsed/] [--sample-rate 16]` |
| `analyze_rounds()` | `cs2-analytics analyze rounds [--parsed-dir parsed/]` |
| `death_zone_stats("AngelsHy4per")` | `cs2-analytics analyze death-zones --player <name> --map <map>` |
| `entry_kill_stats()` | `cs2-analytics analyze entry-kills` |
| `reaction_time("AngelsHy4per")` | `cs2-analytics analyze reaction-time --player <name>` |
| `reaction_time_advanced("AngelsHy4per")` | `cs2-analytics analyze reaction-time --player <name> --advanced` |
| `player_heatmap_map("AngelsHy4per", "de_inferno")` | `cs2-analytics visualize heatmap --player <name> --map <map>` |
| (vision frame extract) | `cs2-analytics vision extract <clips-dir> [--out vision/frames/] [--fps 5]` |
| (vision dataset build) | `cs2-analytics vision build-dataset` |

### Hardcoded values being eliminated

| Hardcoded today | New source |
|---|---|
| `demo_path = "demos/13-03-2026_Inf_3Stack.dem"` (main.py) | CLI positional argument |
| `output_dir = "parsed"` (main.py) | `--output-dir`, default `parsed/` |
| `de_inferno` (analysis/death_zones.py) | `--map` argument, no default |
| `"AngelsHy4per"` (everywhere) | `--player` argument, no default |

### CLI implementation details

- `cli.py` uses stdlib `argparse` with subparsers; no Click/Typer dependency
- Each subcommand handler:
  1. Constructs a `ParsedDataRepository(parsed_dir)` from the `--parsed-dir` flag (default `parsed/`)
  2. For parser subcommands: calls the parser function to get DataFrames, then calls `repo.save_*` methods
  3. For analysis/visualization subcommands: passes the repository instance into the analysis/visualization function
- `--help` works at every level (`cs2-analytics --help`, `cs2-analytics analyze --help`, `cs2-analytics analyze death-zones --help`)
- New analyses are added by writing a new module under `analysis/` and adding one entry to the dispatch table in `cli.py` — no modification of existing analysis files (OCP)
- No config file in this phase; if config grows unwieldy in Phase 2, a TOML config file gets added then

## 8. Migration order

This order is deliberately cautious — single-venv consolidation and `awpy + torch + pandas` co-installation are the only steps with unknown risk, and they go before any structural code changes so that compatibility issues surface early.

| # | Step | Notes |
|---|---|---|
| 1 | `git init`, write minimal `.gitignore` and `README.md`, push initial commit to GitHub `main` | Safety net before any code changes |
| 2 | Create branch `phase-0-1-foundation` for everything below | Reviewable as one PR |
| 3 | Install `uv`, write `pyproject.toml` with `[tool.uv.sources]` for PyTorch CUDA, run `uv sync` | **Highest-risk step.** Validate before touching code. |
| 4 | Validate env: `uv run python -c "import awpy, demoparser2, torch, ultralytics; print(torch.cuda.is_available())"` | Must print `True`. If `False`, PyTorch index misconfigured — fix before proceeding. |
| 5 | Smoke-test existing code in the new env: `uv run python main.py` against the existing demo | Confirms behavior intact before structural changes. **Once green, delete `scripts/` and the old `.venv/`.** |
| 6 | Add `[tool.ruff]` config, run `uv run ruff check`. Auto-fix or `noqa` egregious issues — do not restyle everything | Get linter green; future diffs stay clean |
| 7 | Restructure to `src/cs2_analytics/`: move files, add `__init__.py` files, update imports module-by-module | Mechanical; rerun smoke test after each module |
| 8 | Rename `utils/map_zones_awpy.py` → `utils/maps.py`; verify no other module imports `awpy.*` directly | Enforces adapter discipline |
| 9 | Add `cs2_analytics/data/repository.py` with `ParsedDataRepository`. Refactor parser modules to return DataFrames (drop their persistence calls). | Introduces the repository pattern. Repository is the only path-aware module from here on. |
| 10 | Refactor each analysis module and `visualization/heatmap.py` to take a `ParsedDataRepository` parameter instead of reading parquet by path. Run `python main.py` again to verify behavior. | DIP applied. Smoke-test after each module to keep regressions narrow. |
| 11 | Build `cli.py` subcommand-by-subcommand. Each handler constructs a repository, calls parser/analysis/visualization functions, persists via repository where applicable. Delete `main.py` last. | Each subcommand independently testable |
| 12 | Replace hardcoded `de_inferno` and player-name defaults with CLI args | Done after restructure so we edit one place, not two |
| 13 | Add `tests/test_smoke.py` (imports + CLI `--help`), run `uv run pytest` | Codifies "didn't break the imports" |
| 14 | `git lfs install`, `git lfs track "cs2_player_segmentation.pt"`, commit `.gitattributes`, re-add the model as LFS | Done late so we don't push 58 MB blob non-LFS during exploration |
| 15 | Finalize `README.md` with full setup + CLI usage; commit `LICENSE` (MIT); open PR `phase-0-1-foundation` → `main`; merge | Foundation done |

## 9. Risks

| Risk | Likelihood | Response |
|---|---|---|
| `awpy 2.0.2` requires `pandas<3` | Medium-high | Pin `pandas<3` in `pyproject.toml`, downgrade |
| `torch 2.5` and `awpy` have conflicting `numpy` bounds | Medium | `uv sync` will fail with a resolution error; pin `numpy<2.X` per stricter side |
| `uv` can't resolve `torch+cu121` correctly | Low | Fall back to `uv pip install torch --index-url ...` and document; not a phase blocker |
| Module imports break after restructure (circular import that worked at the old top level) | Low | Smoke test catches it; fix imports |
| Git LFS bandwidth limits on free GitHub plan | Very low for solo use | Free tier: 1 GB storage / 1 GB monthly bandwidth; ample for one 58 MB model |
| awpy known issues (.nav v36, polars on old demos) bite this project | Very low | User parses modern personal demos on standard maps; neither known issue applies. Adapter layer makes future replacement cheap if needed. |

## 10. Acceptance criteria

The foundation is done when:

- [ ] Repo is on GitHub, public, MIT-licensed
- [ ] `git lfs ls-files` shows `cs2_player_segmentation.pt` tracked
- [ ] Single venv on Python 3.11; `scripts/` deleted
- [ ] `uv sync` from a fresh clone produces a working environment
- [ ] `uv run python -c "import torch; print(torch.cuda.is_available())"` prints `True`
- [ ] `uv run pytest` passes (smoke test green)
- [ ] `uv run ruff check` passes
- [ ] `uv run cs2-analytics --help` lists all subcommands
- [ ] Every operation that today's `main.py` performs is reachable via a CLI subcommand
- [ ] No source file imports `awpy.*` except `cs2_analytics/utils/maps.py` and `cs2_analytics/visualization/heatmap.py`
- [ ] No source file outside `cs2_analytics/data/repository.py` calls `pd.read_parquet`, `pd.DataFrame.to_parquet`, or constructs parquet file paths
- [ ] No source file contains hardcoded `de_inferno`, `AngelsHy4per`, or `13-03-2026_Inf_3Stack.dem`
- [ ] PR `phase-0-1-foundation` is merged to `main`

## 11. Out of scope (deferred phases)

| Phase | Scope |
|---|---|
| Phase 2 | Storage layer (DuckDB or accumulated parquet store), batch demo processing, idempotent re-runs |
| Phase 3a | Flask web UI over Phase 2 storage |
| Phase 3b | Vision pipeline integration into the CLI / UI |
| Future | GitHub Actions CI, mypy, pre-commit hooks, real test suite, SteamID-based player identity, multi-map analysis |

Each deferred phase gets its own spec → plan → implementation cycle. They depend on this foundation but not on each other in tightly-coupled ways (3a and 3b can run in parallel).
