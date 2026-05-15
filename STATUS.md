# Project status — CS2 Analytics

> **Purpose:** Hand-off document. The previous chat session ended after merging the foundation refactor. A new Claude Code session can pick up from here without needing the prior conversation.

**Last updated:** 2026-05-15
**Repo:** https://github.com/Hy4per0/cs2-analytics (public, MIT)
**Default branch:** `main`

---

## Where we are

**Phase 2 (Storage layer + batch processing) — ✅ MERGED.**

Per-demo parquet layout: `parsed/<demo-stem>/{kills,damage,rounds,weapon_fire,ticks}.parquet`. `ParsedDataRepository` aggregates across demos on read and tags rows with `demo_id`. New CLI: `parse-batch` for bulk ingest, `--force` on `parse`/`ticks`, `--demo <stem>` filter on `analyze`/`visualize`.

**Upgrade from Phase 0+1:** delete `parsed/` and re-run `parse` + `ticks`. The old flat layout is not auto-migrated.

What this delivered (in addition to Phase 0+1):

| Area | State |
|---|---|
| Storage | Per-demo `parsed/<stem>/*.parquet`; previous flat layout is incompatible |
| Repository | Write side takes `demo_id`; read side aggregates with a `demo_id` column; supports single-demo filter |
| CLI | `parse-batch` subcommand; `--force` on `parse` / `ticks`; `--demo` on `analyze` / `visualize` |
| Idempotency | `parse` / `ticks` refuse to overwrite without `--force`; `parse-batch` skips already-parsed demos |
| Tests | 24 pytest, all green; ruff clean |

**End-to-end smoke baseline (preserved):**
```
parse demos/13-03-2026_Inf_3Stack.dem  → parsed/13-03-2026_Inf_3Stack/{kills,damage,rounds,weapon_fire}.parquet
ticks <same demo>                      → 89870 rows in parsed/13-03-2026_Inf_3Stack/ticks.parquet
analyze rounds                         → Total kills: 171, headshots 72
analyze reaction-time --advanced       → 40 reaction events
```

## Quirks discovered along the way

1. **`demoparser2 0.41.x` renamed view-angle fields** to `yaw` / `pitch` (was `view_angle_yaw` / `view_angle_pitch`). The codebase now uses the new names. If you upgrade beyond `0.41.x`, double-check the field names in `parser/tick_dataset.py` and `analysis/reaction_time_advanced.py`.

2. **`pandas 3.x` × `awpy 2.x`** resolved cleanly with `numpy 2.4`. The risk flagged in the foundation spec did not materialize; no version pinning needed.

3. **Git LFS quirk on Windows**: when the `.gitattributes` LFS rule was committed early, the `.pt` file got routed through LFS automatically the first time it was added, even before the formal "set up LFS" task. Result: the model is correctly an LFS pointer in the tree, with the actual blob in LFS storage.

4. **CRLF warnings** are normal on Windows + Git for Windows. Auto-conversion to LF on commit is fine; don't try to "fix" them.

## Next phases (in dependency order)

These were scoped during the original brainstorm. Each gets its own spec → plan → implementation cycle.

### Phase 3a — Flask web UI

**Goal:** Browser-based interface over Phase 2's accumulated storage.

**Depends on:** Phase 2 (done).

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
