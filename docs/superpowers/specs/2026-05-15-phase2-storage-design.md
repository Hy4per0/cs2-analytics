# Phase 2 — Storage layer + batch processing

**Status:** Design approved, ready for implementation plan.
**Date:** 2026-05-15
**Predecessor:** [`2026-05-06-foundation-design.md`](2026-05-06-foundation-design.md) (Phase 0+1, merged in `a1b7f62`)
**Successor:** Phase 3a (Flask UI) depends on this work.

## Problem

Today every `cs2-analytics parse <demo>` writes to a flat `parsed/{kills,damage,rounds,weapon_fire,ticks}.parquet`. Parsing a second demo silently overwrites the first. The downstream goal — a Flask UI that shows accumulated stats across many demos — cannot be built on this layout.

## Goal

Replace the flat layout with a per-demo addressable store, give `ParsedDataRepository` a write side that does not clobber prior demos, let analyses query across the whole corpus, and add a batch-ingest CLI. Minimum scope to unblock the Flask UI; no DuckDB, no manifest, no registry.

## Non-goals

- DuckDB or any new storage dependency.
- Content-hash demo IDs, schema versioning, indices.
- Migrating data from the Phase 0+1 flat layout (users delete `parsed/` and re-parse).
- Cross-demo aggregation helpers beyond a `demo_id` column on every read.
- Flask UI (Phase 3a) and vision integration (Phase 3b).

## Design decisions

### 1. On-disk layout

```
parsed/
├── <demo-stem>/                  # e.g. 13-03-2026_Inf_3Stack/
│   ├── kills.parquet
│   ├── damage.parquet
│   ├── rounds.parquet
│   ├── weapon_fire.parquet
│   └── ticks.parquet
└── <other-demo-stem>/
    └── ...
```

Demo ID = `Path(demo_path).stem`. No hash, no registry file. Collision avoidance is the user's naming convention.

### 2. Idempotency & overwrite policy

`parse` and `ticks` **refuse to overwrite an existing demo directory unless `--force` is passed.** Re-parsing the same file by accident produces a clear error, not silent data loss. Behavior matrix:

| Command | `parsed/<stem>/` state | Without `--force` | With `--force` |
|---|---|---|---|
| `parse` | missing | create, write 4 tables | create, write 4 tables |
| `parse` | exists | exit 2, error message | overwrite, log it |
| `ticks` | `ticks.parquet` missing | write | write |
| `ticks` | `ticks.parquet` exists | exit 2, error message | overwrite, log it |

`parse-batch` skips already-parsed demos by default; `--force` re-parses everything.

### 3. Repository API

```python
class ParsedDataRepository:
    def __init__(self, parsed_dir: Path | str) -> None: ...

    # discovery
    def demo_exists(self, demo_id: str) -> bool: ...
    def list_demos(self) -> list[str]: ...  # sorted

    # write side (per demo)
    def save_kills(self, demo_id: str, df: pd.DataFrame) -> None: ...
    def save_damage(self, demo_id: str, df: pd.DataFrame) -> None: ...
    def save_rounds(self, demo_id: str, df: pd.DataFrame) -> None: ...
    def save_weapon_fire(self, demo_id: str, df: pd.DataFrame) -> None: ...
    def save_ticks(self, demo_id: str, df: pd.DataFrame) -> None: ...

    # read side (aggregating or filtered)
    def get_kills(self, demo_id: str | None = None) -> pd.DataFrame: ...
    def get_damage(self, demo_id: str | None = None) -> pd.DataFrame: ...
    def get_rounds(self, demo_id: str | None = None) -> pd.DataFrame: ...
    def get_weapon_fire(self, demo_id: str | None = None) -> pd.DataFrame: ...
    def get_ticks(self, demo_id: str | None = None) -> pd.DataFrame: ...
```

**Read semantics:**
- `get_X(demo_id=None)` → concat that table across every demo in `list_demos()`, with a `demo_id` column prepended. Empty store returns an empty DataFrame, not an error.
- `get_X(demo_id="X")` → load only `parsed/X/X.parquet`. Raises `FileNotFoundError` if the demo dir or the table is missing.
- The `demo_id` column is **always** present on returned frames, including the filtered case, so consumers don't branch.

**Write semantics:**
- `save_X(demo_id, df)` writes `parsed/<demo_id>/<X>.parquet`, creating the directory as needed.
- `save_X` does **not** check for existing files. The overwrite gate lives in the CLI handler, so the repo stays a thin storage primitive.

### 4. CLI changes

#### `parse <demo> [--output-dir parsed/] [--force]`

Compute `demo_id = Path(demo).stem`. If `repo.demo_exists(demo_id)` and not `--force` → print `error: parsed/<stem>/ already exists. Pass --force to overwrite, or delete the directory.` and exit 2. Else run `parse_demo`, save each of the four event tables under `demo_id`, log one line per table, end with `parsed: <demo_id>`.

#### `ticks <demo> [--output-dir parsed/] [--sample-rate 16] [--force]`

Same identity rule. Existence check is scoped to `parsed/<demo_id>/ticks.parquet` so `ticks` can run after `parse` without `--force`.

#### `parse-batch <demos-dir> [--output-dir parsed/] [--sample-rate 16] [--force] [--no-ticks]` *(new)*

Iterate `*.dem` in `<demos-dir>` (non-recursive, sorted). For each:
- If `parsed/<stem>/` exists and not `--force`: print `skip: <stem> (already parsed)`.
- Else: run `parse` then (unless `--no-ticks`) `ticks` for that demo.
- On exception: print `fail: <stem> (<short reason>)` and continue.

End with `parse-batch: N parsed, M skipped, K failed`. Exit 0 if `K == 0`, else 1.

#### `analyze <subcommand> [--parsed-dir parsed/] [--demo <stem>]` *(new flag)*

`--demo X` restricts the repo's reads to a single demo; absent, analyses run over the full store. Applies to all current analyses (`rounds`, `death-zones`, `entry-kills`, `reaction-time`).

#### `visualize heatmap [--demo <stem>]`

Same treatment as `analyze`.

Vision subcommands and the global CLI shape are unchanged.

### 5. Error handling

- `parse` / `ticks` overwrite without `--force` → exit 2 with the message above.
- `analyze --demo X` where `parsed/X/` is missing → `FileNotFoundError` from the repo, surfaces as exit 1 with the missing path.
- `analyze` on an empty store → analyses receive empty DataFrames. Each analysis must handle "no data" without crashing (most already print zero-row summaries; verify and patch any that don't during implementation).
- `parse-batch` swallows per-demo exceptions, logs them, returns nonzero only at the end.

## Tests

Extend the existing files (`tests/test_repository.py`, `tests/test_cli.py`, `tests/test_smoke.py`):

- **Repository:**
  - `save_kills(demo_id, df)` writes to nested path; round-trips via `get_kills(demo_id)`.
  - `get_kills()` across two demos concatenates and tags `demo_id` correctly.
  - `get_kills()` on an empty store returns an empty frame, no error.
  - `list_demos()` returns sorted IDs and ignores non-directory entries (e.g. a stray file).
  - `demo_exists()` true after save, false otherwise.
- **CLI:**
  - `parse` refuses when `parsed/<stem>/` exists; succeeds with `--force`.
  - `analyze --demo <missing>` errors clearly.
  - `parse-batch` happy path with mocked per-demo step (unit, not end-to-end — no second `.dem` fixture available).
- **Smoke:** extend the existing end-to-end smoke to parse one demo, assert `parsed/<stem>/kills.parquet` exists, then re-parse without `--force` and assert exit 2.

## Migration from Phase 0+1

The new layout is incompatible with the old `parsed/*.parquet`. Upgrade procedure for a developer pulling Phase 2:

```powershell
Remove-Item -Recurse -Force parsed
uv run cs2-analytics parse demos/<file>.dem
uv run cs2-analytics ticks demos/<file>.dem
```

This will be documented in `STATUS.md` and the Phase 2 PR description.

## Architecture impact

- **Repository pattern earns its keep:** every change is inside `ParsedDataRepository` plus the CLI handlers. No analysis module changes signature; they just get a `demo_id` column they can ignore or use.
- **DIP preserved:** analyses still depend on the repo interface, not on paths.
- **OCP preserved:** adding `parse-batch` is a new file + one entry in the CLI dispatch.
- **No leakage of `pd.read_parquet` outside the repo.**

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `get_X()` concats become slow with many demos | Out of scope; current corpus is small. The repo internals can swap to DuckDB later without API change. |
| Two demos with the same filename stem | User-side naming convention. Could be revisited with content-hash IDs in a later phase. |
| Empty parquet read with mismatched dtypes when store is empty | Return empty DataFrame with no columns — analyses must tolerate this. Tested. |
| Analyses that hardcoded "one match's worth of data" semantics break under concat | Audited during implementation; each analysis runs against a two-demo fixture in tests. |

## Out of scope (deferred)

- DuckDB, content-hash IDs, registry/manifest, schema versioning.
- Auto-migration of the flat layout.
- Cross-demo aggregation primitives.
- Flask UI (Phase 3a), vision integration (Phase 3b).
- GitHub Actions CI, mypy, pre-commit hooks.
