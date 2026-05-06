# Project status — CS2 Analytics

> **Purpose:** Hand-off document. The previous chat session ended after merging the foundation refactor. A new Claude Code session can pick up from here without needing the prior conversation.

**Last updated:** 2026-05-06
**Repo:** https://github.com/Hy4per0/cs2-analytics (public, MIT)
**Default branch:** `main`

---

## Where we are

**Phase 0 + 1 (Foundation) — ✅ MERGED.**

Squash commit: [`a1b7f62`](https://github.com/Hy4per0/cs2-analytics/commit/a1b7f6227247fa33edb7c6f4ebc52578f10cb92f) — "Phase 0+1: Foundation refactor (#1)" merged 2026-05-06.

What this delivered:

| Area | State |
|---|---|
| Python venv | Single `uv`-managed `.venv/` on Python 3.11 (replaces dual `.venv/` 3.13 + `scripts/` 3.11) |
| Dependency manifest | `pyproject.toml` + committed `uv.lock` |
| Package layout | `src/cs2_analytics/` with `parser/`, `analysis/`, `visualization/`, `utils/`, `vision/`, `data/` subpackages |
| Entry point | `cs2-analytics` console script (replaces deleted `main.py`) |
| Architecture | **Pipeline + Repository + Adapter** patterns; SOLID applied to SRP/OCP/DIP |
| `awpy` isolation | Only in `utils/maps.py` and `visualization/heatmap.py` |
| Repository | `cs2_analytics.data.repository.ParsedDataRepository` is the sole point of parquet access |
| Hardcoded values | Eliminated (`de_inferno`, `AngelsHy4per`, demo path) — all CLI args now |
| Quality floor | `ruff` lint + 10 pytest tests, all green |
| Git LFS | `cs2_player_segmentation.pt` (58 MB) tracked under LFS |
| GitHub | Public repo, MIT license, branch workflow established |

**End-to-end smoke baseline (preserved through every refactor):**
```
parse demos/13-03-2026_Inf_3Stack.dem  → kills/damage/rounds/weapon_fire parquet
ticks <same demo>                      → 89870 rows in ticks.parquet
analyze reaction-time --advanced       → 40 reaction events
```

## Quirks discovered along the way

1. **`demoparser2 0.41.x` renamed view-angle fields** to `yaw` / `pitch` (was `view_angle_yaw` / `view_angle_pitch`). The codebase now uses the new names. If you upgrade beyond `0.41.x`, double-check the field names in `parser/tick_dataset.py` and `analysis/reaction_time_advanced.py`.

2. **`pandas 3.x` × `awpy 2.x`** resolved cleanly with `numpy 2.4`. The risk flagged in the foundation spec did not materialize; no version pinning needed.

3. **Git LFS quirk on Windows**: when the `.gitattributes` LFS rule was committed early, the `.pt` file got routed through LFS automatically the first time it was added, even before the formal "set up LFS" task. Result: the model is correctly an LFS pointer in the tree, with the actual blob in LFS storage.

4. **CRLF warnings** are normal on Windows + Git for Windows. Auto-conversion to LF on commit is fine; don't try to "fix" them.

## Next phases (in dependency order)

These were scoped during the original brainstorm. Each gets its own spec → plan → implementation cycle.

### Phase 2 — Storage layer + batch processing

**Goal:** Make the analytics pipeline accumulate stats across many demos. Today, every `cs2-analytics parse` overwrites `parsed/*.parquet`. We need a persistent store that aggregates.

**Likely scope:**
- Replace single-demo parquet output with a per-demo addressable store (DuckDB, or a `parsed/<demo-id>/*.parquet` layout, or both)
- `ParsedDataRepository` gains a write-side that doesn't clobber prior demos
- A "match registry" so analyses can ask "all of player X's deaths across all parsed demos on de_inferno"
- Idempotent re-runs (parse a demo twice → second run is a no-op)
- `cs2-analytics parse-batch <dir>` for ingesting many demos at once

**Why now:** the user's original goal is a Flask UI showing accumulated stats. That UI needs Phase 2's storage to render anything interesting beyond a single match.

### Phase 3a — Flask web UI

**Goal:** Browser-based interface over Phase 2's accumulated storage.

**Depends on:** Phase 2 (no UI without data to render).

**Likely scope (TBD in its own brainstorm):** routes, views, auth?, deployment story.

### Phase 3b — Vision pipeline integration

**Goal:** Bring the vision side into the unified workflow. Today, `vision extract` and `vision build-dataset` exist as CLI subcommands but are isolated from the demo pipeline. Future: surface CV results in the Flask UI, link CV detections to specific demo ticks, etc.

**Depends on:** foundation (already done). Can run in parallel with Phase 2 or 3a.

### Future (deferred indefinitely until needed)

- GitHub Actions CI (lint + test on push)
- `mypy` / type checking
- Pre-commit hooks
- Real test suite (only smoke + repository unit tests today)
- Player-by-SteamID instead of name-string matching

## How to start the next chat

In a new Claude Code session, opening this repo:

1. Claude will read `CLAUDE.md` automatically — it has the up-to-date architecture, layout, and commands.
2. Point Claude at this file (`STATUS.md`) to bring it up to speed on what's been shipped vs. what's next.
3. To start Phase 2: say something like "let's brainstorm Phase 2 — the storage layer." That triggers the `superpowers:brainstorming` skill, which produces a spec, then a plan, then implementation. The same flow that built the foundation.
4. The foundation spec and plan are checked in at `docs/superpowers/specs/` and `docs/superpowers/plans/` — useful as a template for Phase 2's docs.

## Quick verification commands

To confirm the project is in the documented state:

```powershell
git log --oneline -3                          # most recent merge commit on main
uv sync --extra dev                           # sync deps
uv run pytest -q                              # 10 passed
uv run ruff check                             # All checks passed!
uv run cs2-analytics --help                   # 5 subcommands listed
git lfs ls-files                              # cs2_player_segmentation.pt tracked
```

If any of these fail in a fresh clone, something is inconsistent with this status doc — report it before continuing.
