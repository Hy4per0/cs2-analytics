# CS2 Analytics — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current two-venv, scratch-driver, ungoverned project into a single-venv, src-layout, repository+adapter-pattern Python package with a real CLI, published as a public GitHub repo.

**Architecture:** Pipeline (data flow) + Repository (parquet abstraction) + Adapter (`awpy` isolation), per spec section 4a. SOLID applied to SRP/OCP/DIP. The migration is incremental — existing `main.py` keeps working at every checkpoint until step 26 deletes it.

**Tech Stack:** Python 3.11, `uv` (package manager), `pyproject.toml` (manifest), stdlib `argparse` (CLI), `ruff` (lint/format), `pytest` (smoke tests), Git LFS (large model file), GitHub (`main` + feature branches).

**Spec:** `docs/superpowers/specs/2026-05-06-foundation-design.md`

**Working directory:** `C:\Users\Hy4per\Documents\Project_Cs2_Game_Analyses` (Windows + PowerShell, but Bash also available via the Bash tool).

---

## Pre-flight checks (operator setup, one-time)

Before Task 1, the operator must have these tools installed:

- **`git`** — verify with `git --version`
- **`git-lfs`** — already verified present (`git-lfs/3.7.1`); skip if your machine differs
- **`uv`** — install with PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` then restart shell
- **`gh`** (GitHub CLI) — `winget install --id GitHub.cli` then `gh auth login`. If you prefer not to install `gh`, every Task that uses it has a web-UI fallback noted.
- **Python 3.11** — already present at `C:\Users\Hy4per\AppData\Local\Programs\Python\Python311` per pre-existing `scripts/` venv config.

---

## Phase A — Repository setup (Tasks 1–3)

### Task 1: Initial commit on local main

**Files:**
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `LICENSE`
- Create: `README.md` (minimal initial version)
- Create: `.python-version`

- [ ] **Step 1: Verify not already a git repo**

```powershell
git status
```
Expected: `fatal: not a git repository (or any of the parent directories): .git`

- [ ] **Step 2: Create `.gitignore`**

Write to `.gitignore`:

```gitignore
# Virtual environments
.venv/
scripts/
.uv-cache/

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
dist/
.pytest_cache/
.ruff_cache/

# Project data (regenerable)
parsed/
runs/
vision/clips/
vision/frames/
vision/dataset/

# Demo files (large; may contain personal data)
demos/*.dem

# Models
yolo11s-seg.pt

# IDE / editor
.idea/
.vscode/
.env
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create `.gitattributes` (LFS rule for the trained model)**

Write to `.gitattributes`:

```gitattributes
cs2_player_segmentation.pt filter=lfs diff=lfs merge=lfs -text
```

- [ ] **Step 4: Create `LICENSE` (MIT)**

Write to `LICENSE`:

```
MIT License

Copyright (c) 2026 Patrick Thiais

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: Create minimal `README.md` (will be expanded in Task 30)**

Write to `README.md`:

```markdown
# CS2 Analytics

Two-stage Counter-Strike 2 analytics pipeline:

1. **Demo analysis** — parses `.dem` files into parquet tables, computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips, trains a YOLOv11 segmentation model to detect players.

Setup, CLI usage, and architecture details: TBD (added in final task of foundation refactor).
```

- [ ] **Step 6: Create `.python-version`**

Write to `.python-version`:

```
3.11
```

- [ ] **Step 7: Initialize git, configure LFS hooks, stage and commit**

```powershell
git init -b main
git lfs install
git add .gitignore .gitattributes LICENSE README.md .python-version CLAUDE.md docs/
git commit -m "chore: initialize repo with gitignore, LFS, license, readme, spec"
```

Expected: commit succeeds. `git log --oneline` shows one commit.

---

### Task 2: Push to GitHub

**Files:** none (remote setup only)

- [ ] **Step 1: Create the GitHub repo**

If `gh` is installed:

```powershell
gh repo create cs2-analytics --public --source=. --remote=origin --description "Counter-Strike 2 demo analytics and computer vision pipeline"
```

Expected: Output ends with `https://github.com/<your-username>/cs2-analytics`

If `gh` is NOT installed (fallback): Open https://github.com/new in a browser, create `cs2-analytics` as a public repo with no README/license/.gitignore (we have those locally), then run:

```powershell
git remote add origin https://github.com/<your-username>/cs2-analytics.git
```

- [ ] **Step 2: Push initial commit**

```powershell
git push -u origin main
```

Expected: `* [new branch]      main -> main` and `branch 'main' set up to track 'origin/main'`.

- [ ] **Step 3: Verify on GitHub**

Open the repo URL in a browser. Confirm `.gitignore`, `LICENSE`, `README.md`, and `docs/superpowers/specs/2026-05-06-foundation-design.md` are visible.

---

### Task 3: Create the working branch

- [ ] **Step 1: Branch off main**

```powershell
git checkout -b phase-0-1-foundation
```

Expected: `Switched to a new branch 'phase-0-1-foundation'`

- [ ] **Step 2: Push branch to GitHub (so it's visible / draft-PR-able)**

```powershell
git push -u origin phase-0-1-foundation
```

Expected: `* [new branch]      phase-0-1-foundation -> phase-0-1-foundation`

---

## Phase B — Single venv migration (Tasks 4–7)

### Task 4: Write pyproject.toml and create the uv-managed venv

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "cs2-analytics"
version = "0.1.0"
description = "CS2 demo analytics and computer vision pipeline"
requires-python = ">=3.11,<3.12"
license = { text = "MIT" }
authors = [
    { name = "Patrick Thiais", email = "patrickthiais@gmail.com" },
]
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

[tool.hatch.build.targets.wheel]
packages = ["src/cs2_analytics"]

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

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create the `src/cs2_analytics/` skeleton (required for hatchling to find a package)**

```powershell
New-Item -ItemType Directory -Force -Path "src\cs2_analytics" | Out-Null
New-Item -ItemType File -Force -Path "src\cs2_analytics\__init__.py" | Out-Null
```

The `__init__.py` is intentionally empty for now.

- [ ] **Step 3: Run `uv sync`**

```powershell
uv sync --extra dev
```

Expected: `uv` resolves dependencies, downloads wheels (CUDA-enabled torch from the pytorch-cu121 index), installs the project in editable mode, and writes `uv.lock`. May take 2–5 minutes on first run.

If `uv sync` fails with a dependency conflict (e.g. `pandas 3.x` vs `awpy 2.x`):
- Read the resolver's error
- Add a pin to `pyproject.toml` (e.g. `"pandas<3"`) per the risk table in spec section 9
- Re-run `uv sync`

- [ ] **Step 4: Commit the manifest and lockfile**

```powershell
git add pyproject.toml uv.lock src/cs2_analytics/__init__.py
git commit -m "build: add pyproject.toml + uv.lock for single 3.11 venv"
```

---

### Task 5: Validate the consolidated environment

- [ ] **Step 1: Test all critical imports resolve**

```powershell
uv run python -c "import awpy, demoparser2, torch, ultralytics, pandas, polars, pyarrow, matplotlib, seaborn, scipy, numpy, cv2; print('all imports ok')"
```

Expected: `all imports ok`

If any import fails, fix the corresponding dependency in `pyproject.toml` and rerun `uv sync` before continuing.

- [ ] **Step 2: Test CUDA is available**

```powershell
uv run python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Expected: `CUDA available: True` and a device name (e.g. `NVIDIA GeForce RTX ...`).

If `CUDA available: False`:
- The torch wheel came from PyPI instead of the pytorch-cu121 index.
- Verify `[tool.uv.sources]` and `[[tool.uv.index]]` blocks in `pyproject.toml` are correct.
- Run `uv pip uninstall torch torchvision`, then `uv pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121`
- Re-run the CUDA check. If it still fails, update `pyproject.toml` per `uv` documentation for explicit indexes and re-sync.

- [ ] **Step 3: No commit needed (verification only)**

---

### Task 6: Smoke-test existing main.py in the new env, then delete legacy venvs

- [ ] **Step 1: Run main.py end-to-end against the existing test demo**

```powershell
uv run python main.py
```

Expected: prints `Parsing demo: demos/13-03-2026_Inf_3Stack.dem`, then `Parsing complete`, then `Generating tick dataset...`, then `Tick dataset saved` and `Rows: <some number>`, then reaction-time analysis output.

If this fails with `ModuleNotFoundError` for any of `awpy`/`demoparser2`/`pandas`/etc., go back to Task 5.

If this fails with an `awpy`+`pandas` API error (e.g. polars problem on parsing), pin `pandas<3` in `pyproject.toml`, re-run `uv sync`, retry.

- [ ] **Step 2: Verify parquet outputs were produced**

```powershell
Get-ChildItem parsed\*.parquet | Select-Object Name, @{N="MB";E={[math]::Round($_.Length/1MB, 2)}}
```

Expected: at least `kills.parquet`, `damage.parquet`, `rounds.parquet`, `weapon_fire.parquet`, `ticks.parquet` exist with non-zero sizes.

This is the **baseline behavior** that all subsequent refactor tasks must preserve.

- [ ] **Step 3: Delete legacy venvs**

```powershell
Remove-Item -Recurse -Force scripts
Remove-Item -Recurse -Force .venv
```

Wait — the new uv-managed venv was created at `.venv/` by `uv sync`. **Do not delete `.venv/`** if `uv sync` put it there. Only delete the OLD `.venv/` (Python 3.13). To check which Python a `.venv/` is on:

```powershell
Get-Content .venv\pyvenv.cfg | Select-String "version"
```

If it says `3.13.x`, it's the old venv — delete it AND re-run `uv sync` to recreate on 3.11. If it says `3.11.x`, it's the new uv-managed one — keep it and only delete `scripts/`.

```powershell
# Always safe to delete:
Remove-Item -Recurse -Force scripts
# Conditional: delete .venv only if it's the old 3.13 one
$cfg = Get-Content .venv\pyvenv.cfg -ErrorAction SilentlyContinue
if ($cfg -match "version = 3\.13") { Remove-Item -Recurse -Force .venv; uv sync --extra dev }
```

- [ ] **Step 4: Commit (no source changes — just record that legacy venvs are gone)**

The venvs were already in `.gitignore` so there's nothing to stage. This step is a no-op for git, but verify cleanliness:

```powershell
git status
```

Expected: `nothing to commit, working tree clean` (apart from untracked output dirs `parsed/`, which are gitignored).

---

### Task 7: Configure ruff, fix lint issues on existing code

- [ ] **Step 1: Run ruff against the existing code**

```powershell
uv run ruff check .
```

Expected: some number of warnings (likely import ordering, unused imports). Note the count.

- [ ] **Step 2: Auto-fix what ruff can fix**

```powershell
uv run ruff check --fix .
uv run ruff format .
```

- [ ] **Step 3: Re-run check; manually fix anything left**

```powershell
uv run ruff check .
```

For any remaining issues:
- If genuine, fix them (e.g. unused variable, undefined name)
- If false-positive, add `# noqa: <RULE>` on the offending line with a brief comment

- [ ] **Step 4: Verify main.py still runs after ruff changes**

```powershell
uv run python main.py
```

Expected: same baseline behavior as Task 6 step 1.

- [ ] **Step 5: Commit**

```powershell
git add .
git commit -m "style: apply ruff auto-fixes to existing code"
```

---

## Phase C — Package restructure (Tasks 8–14)

The order: move modules one folder at a time, update imports in every file that references the moved module (most importantly `main.py`), and run a smoke test after each move. After each task, `uv run python main.py` should produce identical output to the Task 6 baseline.

### Task 8: Create the `cs2_analytics` package skeleton (subfolders only)

**Files:**
- Create: `src/cs2_analytics/parser/__init__.py`
- Create: `src/cs2_analytics/analysis/__init__.py`
- Create: `src/cs2_analytics/visualization/__init__.py`
- Create: `src/cs2_analytics/utils/__init__.py`
- Create: `src/cs2_analytics/vision/__init__.py`
- Create: `src/cs2_analytics/data/__init__.py`

- [ ] **Step 1: Create directories and `__init__.py` files**

```powershell
$subdirs = @("parser","analysis","visualization","utils","vision","data")
foreach ($d in $subdirs) {
    New-Item -ItemType Directory -Force -Path "src\cs2_analytics\$d" | Out-Null
    New-Item -ItemType File -Force -Path "src\cs2_analytics\$d\__init__.py" | Out-Null
}
```

- [ ] **Step 2: Verify the package is importable**

```powershell
uv run python -c "import cs2_analytics, cs2_analytics.parser, cs2_analytics.analysis, cs2_analytics.visualization, cs2_analytics.utils, cs2_analytics.vision, cs2_analytics.data; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```powershell
git add src/cs2_analytics
git commit -m "refactor: scaffold src/cs2_analytics/ package skeleton"
```

---

### Task 9: Move `parser/parse_demo.py` and `dataset/tick_dataset.py` into the new layout

**Files:**
- Move: `parser/parse_demo.py` → `src/cs2_analytics/parser/parse_demo.py`
- Move: `dataset/tick_dataset.py` → `src/cs2_analytics/parser/tick_dataset.py`
- Modify: `main.py:1` and `main.py:3`

- [ ] **Step 1: Move files with `git mv` to preserve history**

```powershell
git mv parser/parse_demo.py src/cs2_analytics/parser/parse_demo.py
git mv dataset/tick_dataset.py src/cs2_analytics/parser/tick_dataset.py
Remove-Item -Recurse -Force parser, dataset
```

- [ ] **Step 2: Update `main.py` imports**

In `main.py`, change line 1 from:

```python
from parser.parse_demo import parse_demo
```

to:

```python
from cs2_analytics.parser.parse_demo import parse_demo
```

And change line 3 from:

```python
from dataset.tick_dataset import generate_tick_dataset
```

to:

```python
from cs2_analytics.parser.tick_dataset import generate_tick_dataset
```

- [ ] **Step 3: Smoke test**

```powershell
uv run python main.py
```

Expected: same output as Task 6 baseline.

- [ ] **Step 4: Commit**

```powershell
git add main.py src/cs2_analytics/parser
git commit -m "refactor: move parser/ and dataset/tick_dataset.py into src/cs2_analytics/parser/"
```

---

### Task 10: Move `analysis/` into the new layout

**Files:**
- Move: `analysis/death_zones.py` → `src/cs2_analytics/analysis/death_zones.py`
- Move: `analysis/entry_kills.py` → `src/cs2_analytics/analysis/entry_kills.py`
- Move: `analysis/reaction_time.py` → `src/cs2_analytics/analysis/reaction_time.py`
- Move: `analysis/reaction_time_advanced.py` → `src/cs2_analytics/analysis/reaction_time_advanced.py`
- Move: `analysis/round_analyzer.py` → `src/cs2_analytics/analysis/round_analyzer.py`
- Modify: `main.py` lines 2, 5, 6, 7, 8

- [ ] **Step 1: Move files**

```powershell
$files = @("death_zones.py","entry_kills.py","reaction_time.py","reaction_time_advanced.py","round_analyzer.py")
foreach ($f in $files) { git mv "analysis/$f" "src/cs2_analytics/analysis/$f" }
Remove-Item -Recurse -Force analysis
```

- [ ] **Step 2: Update `main.py` imports**

In `main.py`, replace:

```python
from analysis.round_analyzer import analyze_rounds
from analysis.death_zones import death_zone_stats
from analysis.entry_kills import entry_kill_stats
from analysis.reaction_time import reaction_time
from analysis.reaction_time_advanced import reaction_time_advanced
```

with:

```python
from cs2_analytics.analysis.round_analyzer import analyze_rounds
from cs2_analytics.analysis.death_zones import death_zone_stats
from cs2_analytics.analysis.entry_kills import entry_kill_stats
from cs2_analytics.analysis.reaction_time import reaction_time
from cs2_analytics.analysis.reaction_time_advanced import reaction_time_advanced
```

- [ ] **Step 3: Smoke test (will fail — death_zones.py still imports `from utils.map_zones_awpy`, which we haven't moved yet)**

```powershell
uv run python main.py
```

Expected: ImportError on `from utils.map_zones_awpy import get_zone`. **This is the intentional failure that Task 11 fixes.** Don't try to fix it now.

- [ ] **Step 4: Stage but don't commit yet — bundle with Task 11**

```powershell
git add main.py src/cs2_analytics/analysis
```

(Commit happens at the end of Task 11 once `death_zones.py`'s `utils` import is also fixed. This keeps `main` runnable at every commit.)

---

### Task 11: Move `utils/map_zones_awpy.py` and rename to `utils/maps.py`

**Files:**
- Move + rename: `utils/map_zones_awpy.py` → `src/cs2_analytics/utils/maps.py`
- Modify: `src/cs2_analytics/analysis/death_zones.py:2` (the only intra-package import of utils)

- [ ] **Step 1: Move + rename**

```powershell
git mv utils/map_zones_awpy.py src/cs2_analytics/utils/maps.py
Remove-Item -Recurse -Force utils
```

- [ ] **Step 2: Update import in `death_zones.py`**

In `src/cs2_analytics/analysis/death_zones.py`, change line 2 from:

```python
from utils.map_zones_awpy import get_zone
```

to:

```python
from cs2_analytics.utils.maps import get_zone
```

- [ ] **Step 3: Clean up the duplicate import block in `maps.py`** (the original file has lines 26–28 duplicating lines 1–4)

Open `src/cs2_analytics/utils/maps.py`. Delete lines 26–28 (the duplicate `from pathlib import Path / from awpy.data import NAVS_DIR / from awpy.nav import Nav` block).

The file should start with:

```python
from pathlib import Path

from awpy.data import NAVS_DIR
from awpy.nav import Nav


def _point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Return True if point (x, y) is inside the polygon using ray casting."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    for i in range(n):
        x_i, y_i = polygon[i]
        x_j, y_j = polygon[(i + 1) % n]
        intersect = ((y_i > y) != (y_j > y)) and (
            x < (x_j - x_i) * (y - y_i) / (y_j - y_i + 1e-12) + x_i
        )
        if intersect:
            inside = not inside

    return inside


nav_cache = {}


def load_nav(map_name):
    if map_name not in nav_cache:
        nav_path = Path(NAVS_DIR) / f"{map_name}.json"
        nav_cache[map_name] = Nav.from_json(nav_path)

    return nav_cache[map_name]


def get_zone(map_name: str, x: float, y: float) -> str:
    nav = load_nav(map_name)

    for area in nav.areas.values():
        xs = [corner.x for corner in area.corners]
        ys = [corner.y for corner in area.corners]

        if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys):
            return str(area.area_id)

    return "unknown"
```

- [ ] **Step 4: Smoke test**

```powershell
uv run python main.py
```

Expected: same output as Task 6 baseline.

- [ ] **Step 5: Commit (combined with the staged Task 10 changes)**

```powershell
git add src/cs2_analytics
git commit -m "refactor: move analysis/ and utils/ into src/cs2_analytics/, rename map_zones_awpy -> maps"
```

---

### Task 12: Move `visualization/heatmap.py`

**Files:**
- Move: `visualization/heatmap.py` → `src/cs2_analytics/visualization/heatmap.py`
- Modify: `main.py:4`

- [ ] **Step 1: Move file**

```powershell
git mv visualization/heatmap.py src/cs2_analytics/visualization/heatmap.py
Remove-Item -Recurse -Force visualization
```

- [ ] **Step 2: Update `main.py` import**

Change line 4 of `main.py` from:

```python
from visualization.heatmap import player_heatmap_map 
```

to:

```python
from cs2_analytics.visualization.heatmap import player_heatmap_map
```

- [ ] **Step 3: Smoke test**

```powershell
uv run python main.py
```

Expected: same baseline. (Note: `player_heatmap_map` is imported but the call is commented out in main.py, so the import is the only thing being verified.)

- [ ] **Step 4: Commit**

```powershell
git add main.py src/cs2_analytics/visualization
git commit -m "refactor: move visualization/ into src/cs2_analytics/visualization/"
```

---

### Task 13: Move `vision/` Python sources (keep `vision/dataset.yaml` and ignored data dirs in place)

**Files:**
- Move: `vision/frame_extractor.py` → `src/cs2_analytics/vision/frame_extractor.py`
- Move: `vision/build_dataset.py` → `src/cs2_analytics/vision/build_dataset.py`
- Keep in place: `vision/dataset.yaml` (YOLO config, referenced by training command)
- Keep in place (gitignored): `vision/clips/`, `vision/frames/`, `vision/dataset/`

- [ ] **Step 1: Move only the .py files; leave `dataset.yaml` and the data dirs alone**

```powershell
git mv vision/frame_extractor.py src/cs2_analytics/vision/frame_extractor.py
git mv vision/build_dataset.py src/cs2_analytics/vision/build_dataset.py
```

`vision/dataset.yaml`, `vision/clips/`, `vision/frames/`, `vision/dataset/` stay where they are (referenced by `yolo segment train ...` invocations in CLAUDE.md).

- [ ] **Step 2: Fix `build_dataset.py`'s top-level import**

The original line 2 of `build_dataset.py` is `from frame_extractor import extract_frames` — a CWD-relative import that breaks after the move. In `src/cs2_analytics/vision/build_dataset.py`, change line 2 from:

```python
from frame_extractor import extract_frames
```

to:

```python
from cs2_analytics.vision.frame_extractor import extract_frames
```

- [ ] **Step 3: Smoke test imports**

```powershell
uv run python -c "from cs2_analytics.vision import frame_extractor, build_dataset; from cs2_analytics.vision.frame_extractor import extract_frames; from cs2_analytics.vision.build_dataset import build_dataset; print('ok')"
```

Expected: `ok`. (`main.py` doesn't import vision, so end-to-end smoke isn't affected here.)

- [ ] **Step 4: Commit**

```powershell
git add src/cs2_analytics/vision vision
git commit -m "refactor: move vision/*.py into src/cs2_analytics/vision/, fix build_dataset import"
```

---

### Task 14: Verify adapter discipline (no direct `awpy.*` imports outside the two adapter files)

- [ ] **Step 1: Grep for `awpy` imports across `src/`**

```powershell
uv run python -c "
import re, pathlib
violations = []
for p in pathlib.Path('src').rglob('*.py'):
    text = p.read_text(encoding='utf-8')
    for m in re.finditer(r'(?m)^(from|import)\s+awpy\b.*$', text):
        rel = str(p).replace('\\', '/')
        if rel not in ('src/cs2_analytics/utils/maps.py', 'src/cs2_analytics/visualization/heatmap.py'):
            violations.append((rel, m.group(0)))
print('VIOLATIONS:', violations if violations else 'none')
"
```

Expected: `VIOLATIONS: none`

If violations exist, refactor the offending file to import from `cs2_analytics.utils.maps` or `cs2_analytics.visualization.heatmap` instead, then rerun.

- [ ] **Step 2: No commit needed (verification only).**

---

## Phase D — Repository pattern (Tasks 15–17)

### Task 15: Add `ParsedDataRepository` (TDD)

**Files:**
- Create: `src/cs2_analytics/data/repository.py`
- Create: `tests/__init__.py`
- Create: `tests/test_repository.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty file):

```powershell
New-Item -ItemType Directory -Force -Path "tests" | Out-Null
New-Item -ItemType File -Force -Path "tests\__init__.py" | Out-Null
```

Write `tests/test_repository.py`:

```python
from pathlib import Path

import pandas as pd
import pytest

from cs2_analytics.data.repository import ParsedDataRepository


def test_save_and_get_kills_roundtrip(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    df = pd.DataFrame({"tick": [1, 2], "user_name": ["a", "b"]})
    repo.save_kills(df)
    loaded = repo.get_kills()
    pd.testing.assert_frame_equal(loaded, df)


def test_get_kills_when_missing_raises(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.get_kills()


def test_save_creates_parsed_dir(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "parsed"
    repo = ParsedDataRepository(target)
    df = pd.DataFrame({"tick": [1]})
    repo.save_ticks(df)
    assert (target / "ticks.parquet").exists()


def test_all_table_methods_roundtrip(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    sample = pd.DataFrame({"col": [1, 2, 3]})
    for name in ("kills", "damage", "rounds", "weapon_fire", "ticks"):
        getattr(repo, f"save_{name}")(sample)
        pd.testing.assert_frame_equal(getattr(repo, f"get_{name}")(), sample)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
uv run pytest tests/test_repository.py -v
```

Expected: All 4 tests fail with `ModuleNotFoundError: No module named 'cs2_analytics.data.repository'`.

- [ ] **Step 3: Write the minimal implementation**

Write `src/cs2_analytics/data/repository.py`:

```python
from pathlib import Path

import pandas as pd


class ParsedDataRepository:
    """Parquet-backed access for parsed demo data.

    This is the only module that knows the parquet file layout. Analysis,
    visualization, and CLI code accept a ParsedDataRepository instance and
    call its methods rather than reading parquet files by path.
    """

    _TABLES = ("kills", "damage", "rounds", "weapon_fire", "ticks")

    def __init__(self, parsed_dir: Path | str) -> None:
        self.parsed_dir = Path(parsed_dir)

    def _path(self, table: str) -> Path:
        return self.parsed_dir / f"{table}.parquet"

    def _save(self, table: str, df: pd.DataFrame) -> None:
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self._path(table))

    def _get(self, table: str) -> pd.DataFrame:
        path = self._path(table)
        if not path.exists():
            raise FileNotFoundError(
                f"{table}.parquet not found in {self.parsed_dir}. "
                f"Did you run `cs2-analytics parse <demo>` first?"
            )
        return pd.read_parquet(path)

    def save_kills(self, df: pd.DataFrame) -> None: self._save("kills", df)
    def save_damage(self, df: pd.DataFrame) -> None: self._save("damage", df)
    def save_rounds(self, df: pd.DataFrame) -> None: self._save("rounds", df)
    def save_weapon_fire(self, df: pd.DataFrame) -> None: self._save("weapon_fire", df)
    def save_ticks(self, df: pd.DataFrame) -> None: self._save("ticks", df)

    def get_kills(self) -> pd.DataFrame: return self._get("kills")
    def get_damage(self) -> pd.DataFrame: return self._get("damage")
    def get_rounds(self) -> pd.DataFrame: return self._get("rounds")
    def get_weapon_fire(self) -> pd.DataFrame: return self._get("weapon_fire")
    def get_ticks(self) -> pd.DataFrame: return self._get("ticks")
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
uv run pytest tests/test_repository.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/cs2_analytics/data/repository.py tests/__init__.py tests/test_repository.py
git commit -m "feat: add ParsedDataRepository (Repository pattern, TDD)"
```

---

### Task 16: Refactor `parse_demo` to return DataFrames (SRP)

**Files:**
- Modify: `src/cs2_analytics/parser/parse_demo.py`
- Modify: `main.py:13`

- [ ] **Step 1: Replace `parse_demo` body with a returning version**

Overwrite `src/cs2_analytics/parser/parse_demo.py` with:

```python
import pandas as pd
from demoparser2 import DemoParser


def parse_demo(demo_path: str) -> dict[str, pd.DataFrame]:
    """Parse a CS2 .dem file into event tables.

    Returns a dict mapping table name to DataFrame. Persistence is the
    caller's responsibility (typically via ParsedDataRepository.save_*).
    """
    print(f"Parsing demo: {demo_path}")

    parser = DemoParser(demo_path)
    tables = {
        "kills": pd.DataFrame(parser.parse_event("player_death")),
        "damage": pd.DataFrame(parser.parse_event("player_hurt")),
        "rounds": pd.DataFrame(parser.parse_event("round_start")),
        "weapon_fire": pd.DataFrame(parser.parse_event("weapon_fire")),
    }

    print("Parsing complete")
    return tables
```

- [ ] **Step 2: Update `main.py` to use the repository**

In `main.py`, after the existing imports, add:

```python
from cs2_analytics.data.repository import ParsedDataRepository
```

Replace the line `parse_demo(demo_path, output_dir)` with:

```python
repo = ParsedDataRepository(output_dir)
for name, df in parse_demo(demo_path).items():
    getattr(repo, f"save_{name}")(df)
```

- [ ] **Step 3: Smoke test**

```powershell
uv run python main.py
```

Expected: same output as Task 6 baseline; `parsed/kills.parquet`, `parsed/damage.parquet`, `parsed/rounds.parquet`, `parsed/weapon_fire.parquet` regenerated with same row counts.

- [ ] **Step 4: Commit**

```powershell
git add src/cs2_analytics/parser/parse_demo.py main.py
git commit -m "refactor: parse_demo returns DataFrames; persistence via Repository (SRP)"
```

---

### Task 17: Refactor `tick_dataset` to return a DataFrame (SRP)

**Files:**
- Modify: `src/cs2_analytics/parser/tick_dataset.py`
- Modify: `main.py:19`

- [ ] **Step 1: Replace `generate_tick_dataset` body with a returning version**

Overwrite `src/cs2_analytics/parser/tick_dataset.py` with:

```python
import pandas as pd
from demoparser2 import DemoParser


def generate_tick_dataset(demo_path: str, sample_rate: int = 16) -> pd.DataFrame:
    """Parse player tick data, downsampled to every Nth tick.

    Returns the DataFrame. Persistence is the caller's responsibility
    (typically via ParsedDataRepository.save_ticks).
    """
    print("Generating tick dataset...")

    parser = DemoParser(demo_path)
    df = pd.DataFrame(
        parser.parse_ticks(
            [
                "tick",
                "name",
                "team_name",
                "X",
                "Y",
                "Z",
                "health",
                "armor_value",
                "active_weapon_name",
                "velocity_X",
                "velocity_Y",
                "yaw",
                "pitch",
            ]
        )
    )

    df = df[df["tick"] % sample_rate == 0]

    print(f"Tick dataset generated. Rows: {len(df)}")
    return df
```

- [ ] **Step 2: Update `main.py` tick generation call**

Replace:

```python
generate_tick_dataset(demo_path, output_dir)
```

with:

```python
repo.save_ticks(generate_tick_dataset(demo_path))
```

- [ ] **Step 3: Smoke test**

```powershell
uv run python main.py
```

Expected: same baseline; `parsed/ticks.parquet` regenerated.

- [ ] **Step 4: Commit**

```powershell
git add src/cs2_analytics/parser/tick_dataset.py main.py
git commit -m "refactor: generate_tick_dataset returns DataFrame; persistence via Repository (SRP)"
```

---

## Phase E — Analysis & visualization refactor (Tasks 18–22)

Each analysis function currently accepts a player name (and possibly a hardcoded map) and reads parquet files by path. We change each to accept a `ParsedDataRepository` (and explicit `map_name` where applicable), then update `main.py` accordingly.

### Task 18: Refactor `death_zones.py` to take a Repository + explicit map name

**Files:**
- Modify: `src/cs2_analytics/analysis/death_zones.py`
- Modify: `main.py` (the `death_zone_stats(...)` call site, currently commented out)

- [ ] **Step 1: Open `src/cs2_analytics/analysis/death_zones.py` and identify the function signature and its uses of `pd.read_parquet` and the hardcoded `de_inferno`**

Read the current file. The function signature is `def death_zone_stats(player_name): ...`.

- [ ] **Step 2: Change the signature and replace `pd.read_parquet(...)` calls with `repo.get_*()` calls**

Replace the function definition. The new signature is:

```python
def death_zone_stats(repo: ParsedDataRepository, player_name: str, map_name: str) -> None:
```

At the top of the file, replace:

```python
import pandas as pd
from utils.map_zones_awpy import get_zone
```

with:

```python
from cs2_analytics.data.repository import ParsedDataRepository
from cs2_analytics.utils.maps import get_zone
```

(`pandas` import removed if it's no longer directly used in the file; keep it if the function references `pd.*` internally — verify by running `uv run ruff check src/cs2_analytics/analysis/death_zones.py` after editing.)

Replace any line of the form `kills = pd.read_parquet("parsed/kills.parquet")` with `kills = repo.get_kills()`. Same for `ticks`, `damage`, etc.

Replace any literal `"de_inferno"` inside the function body with the `map_name` parameter.

- [ ] **Step 3: Update `main.py`**

Replace the (currently commented-out) line:

```python
# # Analyze death zones for a specific player
# death_zone_stats("AngelsHy4per")
```

with (still commented to match current run state — uncomment to test):

```python
# # Analyze death zones for a specific player
# death_zone_stats(repo, "AngelsHy4per", "de_inferno")
```

- [ ] **Step 4: Verify the function still imports and runs**

Uncomment the call temporarily, run `uv run python main.py`, confirm same behavior as if it had been uncommented in the Task 6 baseline (you may need to capture that baseline first by uncommenting the old version). Re-comment when done.

If you don't want to verify by running it (the behavior baseline for commented-out calls is not in Task 6's smoke test), at minimum verify it imports:

```powershell
uv run python -c "from cs2_analytics.analysis.death_zones import death_zone_stats; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```powershell
git add src/cs2_analytics/analysis/death_zones.py main.py
git commit -m "refactor: death_zone_stats takes Repository + map_name (DIP, kill hardcoded de_inferno)"
```

---

### Task 19: Refactor `entry_kills.py` to take a Repository

**Files:**
- Modify: `src/cs2_analytics/analysis/entry_kills.py`
- Modify: `main.py` (the `entry_kill_stats()` call site)

- [ ] **Step 1: Read the current file and identify `pd.read_parquet` calls**

Open `src/cs2_analytics/analysis/entry_kills.py`. Note every `pd.read_parquet("parsed/<table>.parquet")` call.

- [ ] **Step 2: Change the signature and replace path reads with repo reads**

Change the function signature from `def entry_kill_stats(): ...` to:

```python
def entry_kill_stats(repo: ParsedDataRepository) -> None:
```

Add to the top of the file:

```python
from cs2_analytics.data.repository import ParsedDataRepository
```

Replace each `pd.read_parquet("parsed/X.parquet")` with the corresponding `repo.get_X()` call.

- [ ] **Step 3: Update `main.py`**

Replace:

```python
# # Analyze entry kills
# entry_kill_stats()
```

with:

```python
# # Analyze entry kills
# entry_kill_stats(repo)
```

- [ ] **Step 4: Verify import**

```powershell
uv run python -c "from cs2_analytics.analysis.entry_kills import entry_kill_stats; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```powershell
git add src/cs2_analytics/analysis/entry_kills.py main.py
git commit -m "refactor: entry_kill_stats takes Repository (DIP)"
```

---

### Task 20: Refactor `reaction_time.py` and `reaction_time_advanced.py` to take a Repository

**Files:**
- Modify: `src/cs2_analytics/analysis/reaction_time.py`
- Modify: `src/cs2_analytics/analysis/reaction_time_advanced.py`
- Modify: `main.py` (lines 30 and 32)

- [ ] **Step 1: Read both files and identify path reads**

Open both. Note every `pd.read_parquet` call.

- [ ] **Step 2: Update `reaction_time.py`**

Change `def reaction_time(player_name): ...` to:

```python
def reaction_time(repo: ParsedDataRepository, player_name: str) -> None:
```

Add `from cs2_analytics.data.repository import ParsedDataRepository`. Replace path reads with repo calls.

- [ ] **Step 3: Update `reaction_time_advanced.py`**

Change `def reaction_time_advanced(player_name): ...` to:

```python
def reaction_time_advanced(repo: ParsedDataRepository, player_name: str) -> None:
```

Same pattern.

- [ ] **Step 4: Update `main.py` call sites**

Replace:

```python
# reaction_time("AngelsHy4per")
```

with:

```python
# reaction_time(repo, "AngelsHy4per")
```

Replace:

```python
reaction_time_advanced("AngelsHy4per")
```

with:

```python
reaction_time_advanced(repo, "AngelsHy4per")
```

(Note: `reaction_time_advanced` is the only analysis line currently uncommented in main.py per spec; this preserves that behavior.)

- [ ] **Step 5: Smoke test**

```powershell
uv run python main.py
```

Expected: same Task 6 baseline output (reaction time advanced still runs and prints results).

- [ ] **Step 6: Commit**

```powershell
git add src/cs2_analytics/analysis/reaction_time.py src/cs2_analytics/analysis/reaction_time_advanced.py main.py
git commit -m "refactor: reaction_time + reaction_time_advanced take Repository (DIP)"
```

---

### Task 21: Refactor `round_analyzer.py` to take a Repository

**Files:**
- Modify: `src/cs2_analytics/analysis/round_analyzer.py`
- Modify: `main.py` (the `analyze_rounds()` call)

- [ ] **Step 1: Read the file, identify path reads**

- [ ] **Step 2: Update signature**

Change `def analyze_rounds(): ...` to:

```python
def analyze_rounds(repo: ParsedDataRepository) -> None:
```

Add `from cs2_analytics.data.repository import ParsedDataRepository`. Replace path reads with repo calls.

- [ ] **Step 3: Update `main.py`**

Replace:

```python
# # Analyze rounds and print stats
# analyze_rounds()
```

with:

```python
# # Analyze rounds and print stats
# analyze_rounds(repo)
```

- [ ] **Step 4: Verify import**

```powershell
uv run python -c "from cs2_analytics.analysis.round_analyzer import analyze_rounds; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```powershell
git add src/cs2_analytics/analysis/round_analyzer.py main.py
git commit -m "refactor: analyze_rounds takes Repository (DIP)"
```

---

### Task 22: Refactor `visualization/heatmap.py` to take a Repository

**Files:**
- Modify: `src/cs2_analytics/visualization/heatmap.py`
- Modify: `main.py` (the heatmap call site, currently commented)

- [ ] **Step 1: Update signature and replace `pd.read_parquet` with `repo.get_ticks()`**

Overwrite `src/cs2_analytics/visualization/heatmap.py` with:

```python
import matplotlib.pyplot as plt
from awpy.plot import heatmap

from cs2_analytics.data.repository import ParsedDataRepository


def player_heatmap_map(repo: ParsedDataRepository, player_name: str, map_name: str) -> None:
    """Render a KDE heatmap of a player's positions on a given map."""
    ticks = repo.get_ticks()
    player_data = ticks[ticks["name"] == player_name].copy()
    points = list(player_data[["X", "Y", "Z"]].itertuples(index=False, name=None))

    fig, ax = heatmap(
        map_name=map_name,
        points=points,
        method="kde",
        cmap="inferno",
        alpha=0.6,
        kde_lower_bound=0.01,
    )

    plt.title(f"Heatmap - {player_name}")
    plt.show()
```

- [ ] **Step 2: Update `main.py`**

Replace:

```python
# # Example usage of heatmap and death zone analysis
# player_heatmap_map("AngelsHy4per", "de_inferno")
```

with:

```python
# # Example usage of heatmap and death zone analysis
# player_heatmap_map(repo, "AngelsHy4per", "de_inferno")
```

- [ ] **Step 3: Verify import**

```powershell
uv run python -c "from cs2_analytics.visualization.heatmap import player_heatmap_map; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Final integration smoke test (now that all modules are repository-based)**

```powershell
uv run python main.py
```

Expected: same Task 6 baseline (parses demo, generates ticks, runs reaction_time_advanced).

- [ ] **Step 5: Commit**

```powershell
git add src/cs2_analytics/visualization/heatmap.py main.py
git commit -m "refactor: player_heatmap_map takes Repository (DIP)"
```

---

## Phase F — CLI (Tasks 23–26)

### Task 23: Build the CLI skeleton (TDD: `--help` works)

**Files:**
- Create: `src/cs2_analytics/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Write `tests/test_cli.py`:

```python
import pytest

from cs2_analytics.cli import main


def test_cli_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_no_args_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code != 0


def test_cli_lists_subcommands_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for cmd in ("parse", "ticks", "analyze", "visualize", "vision"):
        assert cmd in out
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
uv run pytest tests/test_cli.py -v
```

Expected: 3 tests fail with `ModuleNotFoundError: No module named 'cs2_analytics.cli'`.

- [ ] **Step 3: Write the minimal CLI**

Write `src/cs2_analytics/cli.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
uv run pytest tests/test_cli.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Verify the installed console script works**

```powershell
uv run cs2-analytics --help
```

Expected: prints the help text including the 5 subcommands.

If `cs2-analytics` is not found as a command, run `uv sync --extra dev` again to refresh the editable install.

- [ ] **Step 6: Commit**

```powershell
git add src/cs2_analytics/cli.py tests/test_cli.py
git commit -m "feat: add CLI skeleton with parse/ticks/analyze/visualize/vision subcommand stubs"
```

---

### Task 24: Wire `parse` and `ticks` subcommands

**Files:**
- Modify: `src/cs2_analytics/cli.py`

- [ ] **Step 1: Add argument parsing and handlers for `parse` and `ticks`**

Replace the current `build_parser()` and `main()` in `src/cs2_analytics/cli.py` with:

```python
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
        "--output-dir", "-o", type=Path, default=Path("parsed"),
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
        "--output-dir", "-o", type=Path, default=Path("parsed"),
        help="Directory to write ticks.parquet (default: parsed/)",
    )
    p.add_argument(
        "--sample-rate", type=int, default=16,
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
    sub.add_parser("analyze", help="Run analysis on parsed data").set_defaults(handler=_stub("analyze"))
    sub.add_parser("visualize", help="Render visualizations from parsed data").set_defaults(handler=_stub("visualize"))
    sub.add_parser("vision", help="Computer vision pipeline").set_defaults(handler=_stub("vision"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify CLI tests still pass**

```powershell
uv run pytest tests/test_cli.py -v
```

Expected: 3 tests still pass.

- [ ] **Step 3: Smoke test `parse` and `ticks` subcommands against the test demo**

```powershell
uv run cs2-analytics parse demos/13-03-2026_Inf_3Stack.dem
uv run cs2-analytics ticks demos/13-03-2026_Inf_3Stack.dem
```

Expected: same behavior as `python main.py` produced for those two operations.

- [ ] **Step 4: Commit**

```powershell
git add src/cs2_analytics/cli.py
git commit -m "feat: wire parse and ticks CLI subcommands"
```

---

### Task 25: Wire `analyze` subcommands (rounds, death-zones, entry-kills, reaction-time)

**Files:**
- Modify: `src/cs2_analytics/cli.py`

- [ ] **Step 1: Add the `analyze` group with four leaf subcommands**

In `src/cs2_analytics/cli.py`, add these imports at the top:

```python
from cs2_analytics.analysis.death_zones import death_zone_stats
from cs2_analytics.analysis.entry_kills import entry_kill_stats
from cs2_analytics.analysis.reaction_time import reaction_time
from cs2_analytics.analysis.reaction_time_advanced import reaction_time_advanced
from cs2_analytics.analysis.round_analyzer import analyze_rounds
```

Add this helper near the other `_add_*` functions:

```python
def _add_analyze(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("analyze", help="Run analysis on parsed data")
    p.add_argument(
        "--parsed-dir", type=Path, default=Path("parsed"),
        help="Directory containing parquet files (default: parsed/)",
    )
    leaf = p.add_subparsers(dest="analyze_command", required=True)

    rounds = leaf.add_parser("rounds", help="Round-by-round summary stats")
    rounds.set_defaults(handler=_handle_analyze_rounds)

    dz = leaf.add_parser("death-zones", help="Where a player dies most often")
    dz.add_argument("--player", required=True, help="Player name (e.g. AngelsHy4per)")
    dz.add_argument("--map", dest="map_name", required=True, help="Map name (e.g. de_inferno)")
    dz.set_defaults(handler=_handle_analyze_death_zones)

    ek = leaf.add_parser("entry-kills", help="Entry kill statistics")
    ek.set_defaults(handler=_handle_analyze_entry_kills)

    rt = leaf.add_parser("reaction-time", help="Player reaction time")
    rt.add_argument("--player", required=True, help="Player name")
    rt.add_argument("--advanced", action="store_true", help="Use the advanced reaction-time calculation")
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
```

In `build_parser()`, replace the line:

```python
    sub.add_parser("analyze", help="Run analysis on parsed data").set_defaults(handler=_stub("analyze"))
```

with:

```python
    _add_analyze(sub)
```

- [ ] **Step 2: Verify CLI tests still pass**

```powershell
uv run pytest tests/test_cli.py -v
```

Expected: 3 tests still pass.

- [ ] **Step 3: Smoke test each analyze subcommand**

(Assumes `parsed/*.parquet` is fresh from Task 24.)

```powershell
uv run cs2-analytics analyze reaction-time --player AngelsHy4per --advanced
```

Expected: same output as the `reaction_time_advanced` line in Task 6's baseline.

The other three (`rounds`, `death-zones`, `entry-kills`) were not run in the Task 6 baseline (commented out in main.py), so just verify they don't crash:

```powershell
uv run cs2-analytics analyze rounds
uv run cs2-analytics analyze entry-kills
uv run cs2-analytics analyze death-zones --player AngelsHy4per --map de_inferno
```

Expected: no ImportError, no AttributeError. Functional output may vary.

- [ ] **Step 4: Commit**

```powershell
git add src/cs2_analytics/cli.py
git commit -m "feat: wire analyze {rounds,death-zones,entry-kills,reaction-time} CLI subcommands"
```

---

### Task 26: Wire `visualize` and `vision` subcommands; delete `main.py`

**Files:**
- Modify: `src/cs2_analytics/cli.py`
- Delete: `main.py`

- [ ] **Step 1: Add `visualize heatmap` and `vision extract` / `vision build-dataset` subcommands**

In `src/cs2_analytics/cli.py`, add these imports:

```python
from cs2_analytics.visualization.heatmap import player_heatmap_map
from cs2_analytics.vision.frame_extractor import extract_frames
from cs2_analytics.vision.build_dataset import build_dataset
```

The function signatures (verified during plan authoring):
- `extract_frames(video_path: str, output_folder: str, fps: int = 5)` — operates on a single video
- `build_dataset()` — iterates `vision/clips/` (hardcoded), calls `extract_frames` for each `.mp4`

Add helpers near the others:

```python
def _add_visualize(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("visualize", help="Render visualizations from parsed data")
    p.add_argument(
        "--parsed-dir", type=Path, default=Path("parsed"),
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
    ex.add_argument("--out", type=Path, default=Path("vision/frames"), help="Output frames dir")
    ex.add_argument("--fps", type=int, default=5, help="Frames per second to extract")
    ex.set_defaults(handler=_handle_vision_extract)

    bd = leaf.add_parser("build-dataset", help="Build the YOLO training dataset from labeled frames")
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
```

> **Note on overlapping behavior:** `vision extract <clips-dir>` (with configurable `--out` and `--fps`) and `vision build-dataset` (which calls the existing hardcoded-paths `build_dataset()`) currently do similar things. We keep both for foundation phase to preserve existing behavior. Phase 3b will reconcile this — `build-dataset` is reserved for a future "compose YOLO training set from labeled frames" workflow.

In `build_parser()`, replace the two stub lines:

```python
    sub.add_parser("visualize", help="Render visualizations from parsed data").set_defaults(handler=_stub("visualize"))
    sub.add_parser("vision", help="Computer vision pipeline").set_defaults(handler=_stub("vision"))
```

with:

```python
    _add_visualize(sub)
    _add_vision(sub)
```

You can also remove the `_stub` helper if no other subcommand uses it.

- [ ] **Step 2: Verify CLI tests still pass**

```powershell
uv run pytest tests/test_cli.py -v
```

Expected: 3 tests still pass.

- [ ] **Step 3: Smoke test (just `--help`, since heatmap and vision subcommands have side effects)**

```powershell
uv run cs2-analytics visualize --help
uv run cs2-analytics vision --help
uv run cs2-analytics visualize heatmap --help
uv run cs2-analytics vision extract --help
uv run cs2-analytics vision build-dataset --help
```

Expected: each `--help` exits with code 0 and prints relevant help text.

- [ ] **Step 4: Delete `main.py`**

```powershell
git rm main.py
```

- [ ] **Step 5: Final end-to-end smoke**

```powershell
uv run cs2-analytics parse demos/13-03-2026_Inf_3Stack.dem
uv run cs2-analytics ticks demos/13-03-2026_Inf_3Stack.dem
uv run cs2-analytics analyze reaction-time --player AngelsHy4per --advanced
```

Expected: equivalent output to Task 6's baseline (across the three steps that main.py performed).

- [ ] **Step 6: Commit**

```powershell
git add src/cs2_analytics/cli.py
git commit -m "feat: wire visualize and vision subcommands; delete main.py"
```

---

## Phase G — Verification & finalization (Tasks 27–30)

### Task 27: Add the smoke test (full module-import + CLI `--help`)

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the smoke test**

Write `tests/test_smoke.py`:

```python
import pytest


def test_all_modules_import() -> None:
    import cs2_analytics  # noqa: F401
    import cs2_analytics.cli  # noqa: F401
    import cs2_analytics.data.repository  # noqa: F401
    import cs2_analytics.parser.parse_demo  # noqa: F401
    import cs2_analytics.parser.tick_dataset  # noqa: F401
    import cs2_analytics.analysis.death_zones  # noqa: F401
    import cs2_analytics.analysis.entry_kills  # noqa: F401
    import cs2_analytics.analysis.reaction_time  # noqa: F401
    import cs2_analytics.analysis.reaction_time_advanced  # noqa: F401
    import cs2_analytics.analysis.round_analyzer  # noqa: F401
    import cs2_analytics.visualization.heatmap  # noqa: F401
    import cs2_analytics.utils.maps  # noqa: F401
    import cs2_analytics.vision.frame_extractor  # noqa: F401
    import cs2_analytics.vision.build_dataset  # noqa: F401


def test_cli_top_level_help_exits_zero() -> None:
    from cs2_analytics.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_every_subcommand_help_exits_zero() -> None:
    from cs2_analytics.cli import main
    for argv in (
        ["parse", "--help"],
        ["ticks", "--help"],
        ["analyze", "rounds", "--help"],
        ["analyze", "death-zones", "--help"],
        ["analyze", "entry-kills", "--help"],
        ["analyze", "reaction-time", "--help"],
        ["visualize", "heatmap", "--help"],
        ["vision", "extract", "--help"],
        ["vision", "build-dataset", "--help"],
    ):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 0, f"failed for argv={argv}"
```

- [ ] **Step 2: Run the full test suite**

```powershell
uv run pytest -v
```

Expected: all tests across `test_repository.py`, `test_cli.py`, and `test_smoke.py` pass.

- [ ] **Step 3: Commit**

```powershell
git add tests/test_smoke.py
git commit -m "test: add smoke test (module imports + CLI subcommand --help)"
```

---

### Task 28: Verify acceptance criteria

This task is verification only — no code changes. Walk through the spec's section 10 acceptance criteria.

- [ ] **Step 1: All criteria from spec section 10**

Run each check; mark each as ✓ or fix the gap before proceeding:

```powershell
# Repo on GitHub, public, MIT-licensed — verify in browser at the repo URL

# git lfs ls-files shows the model (will be empty until Task 29)
git lfs ls-files

# Single venv on Python 3.11
Get-Content .venv/pyvenv.cfg | Select-String "version"
# Expected: version = 3.11.x

# scripts/ deleted
Test-Path scripts
# Expected: False

# uv sync from a fresh clone produces a working environment — try in a temp dir if you want; otherwise trust uv.lock
git ls-files | Select-String "uv.lock|pyproject.toml"
# Expected: both present

# CUDA available
uv run python -c "import torch; print(torch.cuda.is_available())"
# Expected: True

# pytest passes
uv run pytest -v
# Expected: all green

# ruff passes
uv run ruff check .
# Expected: no errors

# CLI lists all subcommands
uv run cs2-analytics --help

# Every operation reachable via CLI subcommand — verify visually against spec section 7

# No source file imports awpy.* outside the two adapters (re-run Task 14's check)
uv run python -c "
import re, pathlib
v=[]
for p in pathlib.Path('src').rglob('*.py'):
    for m in re.finditer(r'(?m)^(from|import)\s+awpy\b.*$', p.read_text(encoding='utf-8')):
        rel=str(p).replace('\\','/')
        if rel not in ('src/cs2_analytics/utils/maps.py','src/cs2_analytics/visualization/heatmap.py'):
            v.append((rel,m.group(0)))
print('VIOLATIONS:', v if v else 'none')
"
# Expected: VIOLATIONS: none

# No module outside data/repository.py reads/writes parquet directly
uv run python -c "
import re, pathlib
v=[]
for p in pathlib.Path('src').rglob('*.py'):
    rel=str(p).replace('\\','/')
    if rel == 'src/cs2_analytics/data/repository.py':
        continue
    text = p.read_text(encoding='utf-8')
    if re.search(r'pd\.read_parquet|\.to_parquet', text):
        v.append(rel)
print('VIOLATIONS:', v if v else 'none')
"
# Expected: VIOLATIONS: none

# No hardcoded values
uv run python -c "
import re, pathlib
v=[]
for p in pathlib.Path('src').rglob('*.py'):
    text = p.read_text(encoding='utf-8')
    for needle in ('AngelsHy4per','de_inferno','13-03-2026_Inf_3Stack'):
        if needle in text:
            v.append((str(p), needle))
print('VIOLATIONS:', v if v else 'none')
"
# Expected: VIOLATIONS: none
```

- [ ] **Step 2: Fix any failures inline before continuing**

If any check returns violations, fix them, commit, and re-run.

---

### Task 29: Set up Git LFS for the trained model

**Files:**
- Modify: `cs2_player_segmentation.pt` (re-tracked under LFS)

- [ ] **Step 1: Verify LFS hooks installed**

```powershell
git lfs install
```

Expected: `Updated git hooks.` (or `Hooks already installed.`)

- [ ] **Step 2: Track the model file (already in `.gitattributes` from Task 1, but make sure)**

```powershell
git lfs track "cs2_player_segmentation.pt"
git add .gitattributes
```

- [ ] **Step 3: Re-add the model file under LFS**

The model has not been added to git yet (it was excluded from the initial `git add` in Task 1 step 7). Add it now:

```powershell
git add cs2_player_segmentation.pt
git status
```

Expected output: `cs2_player_segmentation.pt` shows as a new file. Run:

```powershell
git lfs ls-files
```

Expected: shows `cs2_player_segmentation.pt` (with an OID prefix) — this confirms it's tracked under LFS, not as a regular blob.

If `git lfs ls-files` is empty, run `git rm --cached cs2_player_segmentation.pt; git add cs2_player_segmentation.pt` to force re-staging through the LFS filter.

- [ ] **Step 4: Commit**

```powershell
git commit -m "feat: track cs2_player_segmentation.pt via Git LFS"
```

- [ ] **Step 5: Push to remote (will upload LFS object)**

```powershell
git push
```

Expected: `Uploading LFS objects: 100% (1/1), 58 MB ...`

If you hit GitHub LFS quota issues on a free account, see https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage. The free tier allows 1 GB storage and 1 GB monthly bandwidth — well within bounds for one 58 MB file.

---

### Task 30: Finalize README, open and merge PR

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the minimal README with a real one**

Overwrite `README.md`:

```markdown
# CS2 Analytics

Two-stage Counter-Strike 2 analytics pipeline.

1. **Demo analysis** — parses `.dem` files into parquet tables, computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips, trains a YOLOv11 segmentation model to detect players.

## Setup

Requires Python 3.11, [uv](https://github.com/astral-sh/uv), and Git LFS.

```powershell
# 1. Clone (LFS pulls the trained model automatically)
git clone https://github.com/<your-username>/cs2-analytics.git
cd cs2-analytics

# 2. Sync dependencies (creates .venv on Python 3.11 with CUDA-enabled torch)
uv sync --extra dev

# 3. Verify CUDA
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
uv run cs2-analytics analyze death-zones --player AngelsHy4per --map de_inferno
uv run cs2-analytics analyze entry-kills
uv run cs2-analytics analyze reaction-time --player AngelsHy4per --advanced

# Visualize
uv run cs2-analytics visualize heatmap --player AngelsHy4per --map de_inferno

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
uv run pytest          # run tests
uv run ruff check      # lint
uv run ruff format     # auto-format
```

## License

MIT — see `LICENSE`.
```

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "docs: finalize README with setup, CLI usage, and architecture overview"
```

- [ ] **Step 3: Push the branch**

```powershell
git push
```

- [ ] **Step 4: Open the PR**

If `gh` is installed:

```powershell
gh pr create --base main --head phase-0-1-foundation --title "Phase 0+1: Foundation refactor" --body "Implements docs/superpowers/specs/2026-05-06-foundation-design.md.

## Summary
- Single Python 3.11 venv via uv (replaces dual .venv/ + scripts/ setup)
- src/cs2_analytics/ package layout with Pipeline + Repository + Adapter patterns
- CLI (cs2-analytics) replacing main.py scratch driver
- All hardcoded values (demo path, player name, map name, de_inferno) become CLI args
- awpy isolated to two adapter modules
- Git LFS tracking for cs2_player_segmentation.pt
- ruff lint floor + smoke tests

## Test plan
- [x] uv sync produces working env on Python 3.11
- [x] CUDA available
- [x] uv run pytest passes
- [x] uv run ruff check passes
- [x] cs2-analytics --help lists all subcommands
- [x] parse + ticks + analyze reaction-time --advanced match prior main.py output"
```

If `gh` is not installed: open `https://github.com/<your-username>/cs2-analytics/pull/new/phase-0-1-foundation` in a browser and paste the title and body above.

- [ ] **Step 5: Merge the PR**

After self-review (or external review if applicable):

```powershell
gh pr merge --squash --delete-branch
```

Or via the GitHub UI: select "Squash and merge" → confirm → delete branch.

- [ ] **Step 6: Update local main**

```powershell
git checkout main
git pull
git branch -d phase-0-1-foundation  # already deleted on remote
```

Expected: `main` now contains the foundation refactor; the phase branch is gone locally and on remote.

---

## Done

The foundation is complete when:
- The PR is merged.
- All section 10 acceptance criteria from the spec verify clean.
- `uv run cs2-analytics parse demos/<demo>.dem && uv run cs2-analytics ticks demos/<demo>.dem && uv run cs2-analytics analyze reaction-time --player <name> --advanced` produces the same output the old `main.py` did.

Phase 2 (storage layer / batch pipeline), Phase 3a (Flask UI), and Phase 3b (vision pipeline integration) get their own specs and plans.
