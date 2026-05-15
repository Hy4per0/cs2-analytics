# Phase 2 — Storage Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat single-demo `parsed/*.parquet` layout with a per-demo addressable store (`parsed/<demo-stem>/*.parquet`), add a multi-demo read side to `ParsedDataRepository`, add a `parse-batch` CLI command, and add a `--demo` filter to all analyses.

**Architecture:** Pipeline + Repository + Adapter (unchanged). All storage knowledge stays inside `ParsedDataRepository`. The CLI handlers own the overwrite-protection gate (`--force`). Analyses keep their `(repo, ...)` signature and gain an ignorable `demo_id` column on every read.

**Tech Stack:** Python 3.11, `uv`, pandas/pyarrow (already vendored), stdlib `argparse`, `pytest`, `ruff`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-15-phase2-storage-design.md`

**Working directory:** `C:\Users\Hy4per\Documents\Project_Cs2_Game_Analyses` (Windows + PowerShell; `Bash` tool also available).

**Branch:** create `feature/phase2-storage` from `main` before Task 1. Merge via PR at the end.

---

## File Structure

Files this plan creates or modifies. Each has one responsibility.

| Path | Role | Action |
|---|---|---|
| `src/cs2_analytics/data/repository.py` | Per-demo write side + aggregating read side | Rewrite |
| `src/cs2_analytics/cli.py` | `--force` on `parse`/`ticks`, new `parse-batch`, `--demo` on `analyze`/`visualize` | Modify |
| `src/cs2_analytics/analysis/round_analyzer.py` | Tolerate empty kills | Modify |
| `tests/test_repository.py` | Cover new repo surface | Rewrite |
| `tests/test_cli.py` | Cover `--force`, `parse-batch` skip logic, `--demo` errors | Modify |
| `tests/test_smoke.py` | Extend end-to-end to assert nested layout + `--force` gate | Modify |
| `STATUS.md` | Note Phase 2 merged, upgrade procedure | Modify |
| `CLAUDE.md` | Update commands and on-disk layout doc | Modify |

---

## Pre-flight

- [ ] **Step 0.1: Branch off main**

```powershell
git switch main
git pull
git switch -c feature/phase2-storage
```

- [ ] **Step 0.2: Confirm baseline is green**

```powershell
uv run pytest -q
uv run ruff check
```

Expected: 10 tests pass, ruff clean.

---

## Task 1: Repository — write side per demo

**Files:**
- Modify: `src/cs2_analytics/data/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1.1: Write failing tests for the new write/discovery surface**

Replace `tests/test_repository.py` entirely with:

```python
from pathlib import Path

import pandas as pd
import pytest

from cs2_analytics.data.repository import ParsedDataRepository


def test_save_kills_writes_to_demo_subdir(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    df = pd.DataFrame({"tick": [1, 2], "user_name": ["a", "b"]})
    repo.save_kills("match1", df)
    assert (tmp_path / "match1" / "kills.parquet").exists()


def test_save_and_get_single_demo_roundtrip(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    df = pd.DataFrame({"tick": [1, 2], "user_name": ["a", "b"]})
    repo.save_kills("match1", df)
    loaded = repo.get_kills(demo_id="match1")
    assert list(loaded["user_name"]) == ["a", "b"]
    assert (loaded["demo_id"] == "match1").all()


def test_get_kills_aggregates_across_demos(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    repo.save_kills("a", pd.DataFrame({"tick": [1], "user_name": ["x"]}))
    repo.save_kills("b", pd.DataFrame({"tick": [2], "user_name": ["y"]}))
    loaded = repo.get_kills()
    assert len(loaded) == 2
    assert set(loaded["demo_id"]) == {"a", "b"}


def test_get_kills_on_empty_store_returns_empty_frame(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    loaded = repo.get_kills()
    assert isinstance(loaded, pd.DataFrame)
    assert loaded.empty


def test_get_kills_missing_demo_raises(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.get_kills(demo_id="nope")


def test_demo_exists(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    assert not repo.demo_exists("m")
    repo.save_kills("m", pd.DataFrame({"x": [1]}))
    assert repo.demo_exists("m")


def test_list_demos_sorted_and_ignores_files(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    repo.save_kills("b", pd.DataFrame({"x": [1]}))
    repo.save_kills("a", pd.DataFrame({"x": [1]}))
    (tmp_path / "stray.txt").write_text("ignore me")
    assert repo.list_demos() == ["a", "b"]


def test_all_table_methods_roundtrip(tmp_path: Path) -> None:
    repo = ParsedDataRepository(tmp_path)
    sample = pd.DataFrame({"col": [1, 2, 3]})
    for name in ("kills", "damage", "rounds", "weapon_fire", "ticks"):
        getattr(repo, f"save_{name}")("d1", sample)
        loaded = getattr(repo, f"get_{name}")(demo_id="d1")
        assert list(loaded["col"]) == [1, 2, 3]
        assert (loaded["demo_id"] == "d1").all()
```

- [ ] **Step 1.2: Run tests, confirm they fail**

Run: `uv run pytest tests/test_repository.py -v`
Expected: all fail with `TypeError` (missing demo_id arg) or `AttributeError` (no `list_demos`/`demo_exists`).

- [ ] **Step 1.3: Rewrite `src/cs2_analytics/data/repository.py`**

Replace the entire file with:

```python
from pathlib import Path

import pandas as pd


class ParsedDataRepository:
    """Per-demo parquet store.

    Layout: <parsed_dir>/<demo_id>/<table>.parquet for table in TABLES.
    Reads can target one demo (demo_id="X") or aggregate across the whole
    store (demo_id=None). Aggregated reads tag rows with their demo_id.
    """

    _TABLES = ("kills", "damage", "rounds", "weapon_fire", "ticks")

    def __init__(self, parsed_dir: Path | str) -> None:
        self.parsed_dir = Path(parsed_dir)

    def _demo_dir(self, demo_id: str) -> Path:
        return self.parsed_dir / demo_id

    def _path(self, demo_id: str, table: str) -> Path:
        return self._demo_dir(demo_id) / f"{table}.parquet"

    def demo_exists(self, demo_id: str) -> bool:
        return self._demo_dir(demo_id).is_dir()

    def list_demos(self) -> list[str]:
        if not self.parsed_dir.is_dir():
            return []
        return sorted(p.name for p in self.parsed_dir.iterdir() if p.is_dir())

    def _save(self, table: str, demo_id: str, df: pd.DataFrame) -> None:
        self._demo_dir(demo_id).mkdir(parents=True, exist_ok=True)
        df.to_parquet(self._path(demo_id, table))

    def _get(self, table: str, demo_id: str | None) -> pd.DataFrame:
        if demo_id is not None:
            path = self._path(demo_id, table)
            if not path.exists():
                raise FileNotFoundError(
                    f"{table}.parquet not found for demo '{demo_id}' "
                    f"(looked in {path}). Did you run "
                    f"`cs2-analytics parse <demo>` for that demo?"
                )
            df = pd.read_parquet(path)
            df.insert(0, "demo_id", demo_id)
            return df

        frames: list[pd.DataFrame] = []
        for did in self.list_demos():
            path = self._path(did, table)
            if not path.exists():
                continue
            part = pd.read_parquet(path)
            part.insert(0, "demo_id", did)
            frames.append(part)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    # write side
    def save_kills(self, demo_id: str, df: pd.DataFrame) -> None:
        self._save("kills", demo_id, df)

    def save_damage(self, demo_id: str, df: pd.DataFrame) -> None:
        self._save("damage", demo_id, df)

    def save_rounds(self, demo_id: str, df: pd.DataFrame) -> None:
        self._save("rounds", demo_id, df)

    def save_weapon_fire(self, demo_id: str, df: pd.DataFrame) -> None:
        self._save("weapon_fire", demo_id, df)

    def save_ticks(self, demo_id: str, df: pd.DataFrame) -> None:
        self._save("ticks", demo_id, df)

    # read side
    def get_kills(self, demo_id: str | None = None) -> pd.DataFrame:
        return self._get("kills", demo_id)

    def get_damage(self, demo_id: str | None = None) -> pd.DataFrame:
        return self._get("damage", demo_id)

    def get_rounds(self, demo_id: str | None = None) -> pd.DataFrame:
        return self._get("rounds", demo_id)

    def get_weapon_fire(self, demo_id: str | None = None) -> pd.DataFrame:
        return self._get("weapon_fire", demo_id)

    def get_ticks(self, demo_id: str | None = None) -> pd.DataFrame:
        return self._get("ticks", demo_id)
```

- [ ] **Step 1.4: Run tests, confirm they pass**

Run: `uv run pytest tests/test_repository.py -v`
Expected: 8 passed.

- [ ] **Step 1.5: Commit**

```powershell
git add src/cs2_analytics/data/repository.py tests/test_repository.py
git commit -m "feat(repository): per-demo layout with aggregating reads"
```

---

## Task 2: Harden `analyze_rounds` against empty store

`analyze_rounds` does `headshots / len(kills)` which divides by zero on an empty store. Patch.

**Files:**
- Modify: `src/cs2_analytics/analysis/round_analyzer.py`
- Modify: `tests/test_repository.py` (add an analysis-level smoke)

- [ ] **Step 2.1: Add failing test**

Append to `tests/test_repository.py`:

```python
def test_analyze_rounds_handles_empty_store(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from cs2_analytics.analysis.round_analyzer import analyze_rounds

    repo = ParsedDataRepository(tmp_path)
    analyze_rounds(repo)  # must not raise
    out = capsys.readouterr().out
    assert "Total kills: 0" in out
```

- [ ] **Step 2.2: Run, confirm it fails**

Run: `uv run pytest tests/test_repository.py::test_analyze_rounds_handles_empty_store -v`
Expected: FAIL with `ZeroDivisionError` or `KeyError: 'headshot'`.

- [ ] **Step 2.3: Patch `round_analyzer.py`**

Replace `src/cs2_analytics/analysis/round_analyzer.py` with:

```python
from cs2_analytics.data.repository import ParsedDataRepository


def analyze_rounds(repo: ParsedDataRepository) -> None:
    kills = repo.get_kills()
    total = len(kills)
    print("Total kills:", total)
    if total == 0:
        print("Headshots: 0")
        print("Headshot rate: n/a")
        return
    headshots = int(kills["headshot"].sum())
    print("Headshots:", headshots)
    print("Headshot rate:", headshots / total)
```

- [ ] **Step 2.4: Run, confirm pass**

Run: `uv run pytest tests/test_repository.py -v`
Expected: 9 passed.

- [ ] **Step 2.5: Commit**

```powershell
git add src/cs2_analytics/analysis/round_analyzer.py tests/test_repository.py
git commit -m "fix(analysis): analyze_rounds handles empty store"
```

---

## Task 3: CLI — `parse` with `--force` and per-demo IDs

**Files:**
- Modify: `src/cs2_analytics/cli.py` (`_add_parse`, `_handle_parse`)
- Modify: `tests/test_cli.py`

- [ ] **Step 3.1: Add failing test**

Append to `tests/test_cli.py`:

```python
from pathlib import Path


def test_parse_refuses_when_demo_dir_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    from cs2_analytics import cli as cli_mod

    (tmp_path / "parsed" / "fake").mkdir(parents=True)
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"not a real demo")

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {})

    rc = cli_mod.main(["parse", str(demo), "--output-dir", str(tmp_path / "parsed")])
    assert rc == 2
    assert "already exists" in capsys.readouterr().err


def test_parse_force_overwrites(
    tmp_path: Path, monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"not a real demo")

    sample = {"kills": pd.DataFrame({"x": [1]})}
    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: sample)

    rc = cli_mod.main(["parse", str(demo), "--output-dir", str(parsed), "--force"])
    assert rc == 0
    assert (parsed / "fake" / "kills.parquet").exists()
```

- [ ] **Step 3.2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py::test_parse_refuses_when_demo_dir_exists tests/test_cli.py::test_parse_force_overwrites -v`
Expected: both fail.

- [ ] **Step 3.3: Patch `_add_parse` and `_handle_parse` in `src/cs2_analytics/cli.py`**

Replace the existing `_add_parse` and `_handle_parse` functions with:

```python
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
```

- [ ] **Step 3.4: Run, confirm pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all green.

- [ ] **Step 3.5: Commit**

```powershell
git add src/cs2_analytics/cli.py tests/test_cli.py
git commit -m "feat(cli): parse uses per-demo dirs with --force gate"
```

---

## Task 4: CLI — `ticks` with `--force` scoped to `ticks.parquet`

**Files:**
- Modify: `src/cs2_analytics/cli.py` (`_add_ticks`, `_handle_ticks`)
- Modify: `tests/test_cli.py`

- [ ] **Step 4.1: Add failing test**

Append to `tests/test_cli.py`:

```python
def test_ticks_refuses_when_ticks_parquet_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)
    (parsed / "fake" / "ticks.parquet").write_bytes(b"x")
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"x")

    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["ticks", str(demo), "--output-dir", str(parsed)])
    assert rc == 2
    assert "ticks.parquet" in capsys.readouterr().err


def test_ticks_runs_when_demo_dir_exists_but_no_ticks_yet(
    tmp_path: Path, monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    parsed = tmp_path / "parsed"
    (parsed / "fake").mkdir(parents=True)  # dir exists, but no ticks.parquet
    demo = tmp_path / "fake.dem"
    demo.write_bytes(b"x")

    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["ticks", str(demo), "--output-dir", str(parsed)])
    assert rc == 0
    assert (parsed / "fake" / "ticks.parquet").exists()
```

- [ ] **Step 4.2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py -v -k ticks`
Expected: both new ones fail.

- [ ] **Step 4.3: Patch `_add_ticks` and `_handle_ticks`**

Replace the existing functions with:

```python
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
```

- [ ] **Step 4.4: Run, confirm pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all green.

- [ ] **Step 4.5: Commit**

```powershell
git add src/cs2_analytics/cli.py tests/test_cli.py
git commit -m "feat(cli): ticks uses per-demo dirs with --force gate"
```

---

## Task 5: CLI — `parse-batch`

**Files:**
- Modify: `src/cs2_analytics/cli.py` (add `_add_parse_batch`, `_handle_parse_batch`, register in `build_parser`)
- Modify: `tests/test_cli.py`
- Modify: `tests/test_smoke.py` (add `parse-batch` to the every-subcommand-help test)

- [ ] **Step 5.1: Add failing tests**

Append to `tests/test_cli.py`:

```python
def test_parse_batch_skips_existing_and_parses_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    (demos_dir / "b.dem").write_bytes(b"x")

    parsed = tmp_path / "parsed"
    (parsed / "a").mkdir(parents=True)  # 'a' already parsed
    (parsed / "a" / "ticks.parquet").write_bytes(b"x")  # has ticks too

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {"kills": pd.DataFrame({"x": [1]})})
    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["parse-batch", str(demos_dir), "--output-dir", str(parsed)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "skip: a" in out
    assert "parse: b" in out
    assert "1 parsed, 1 skipped, 0 failed" in out
    assert (parsed / "b" / "kills.parquet").exists()
    assert (parsed / "b" / "ticks.parquet").exists()


def test_parse_batch_no_ticks_flag(tmp_path: Path, monkeypatch) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    parsed = tmp_path / "parsed"

    monkeypatch.setattr(cli_mod, "parse_demo", lambda _p: {"kills": pd.DataFrame({"x": [1]})})
    called = {"ticks": False}

    def fake_ticks(_p, sample_rate=16):
        called["ticks"] = True
        return pd.DataFrame({"t": [1]})

    monkeypatch.setattr(cli_mod, "generate_tick_dataset", fake_ticks)

    rc = cli_mod.main(
        ["parse-batch", str(demos_dir), "--output-dir", str(parsed), "--no-ticks"]
    )
    assert rc == 0
    assert called["ticks"] is False


def test_parse_batch_continues_after_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    import pandas as pd
    from cs2_analytics import cli as cli_mod

    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    (demos_dir / "a.dem").write_bytes(b"x")
    (demos_dir / "b.dem").write_bytes(b"x")
    parsed = tmp_path / "parsed"

    def flaky_parse(p):
        if "a.dem" in p:
            raise RuntimeError("boom")
        return {"kills": pd.DataFrame({"x": [1]})}

    monkeypatch.setattr(cli_mod, "parse_demo", flaky_parse)
    monkeypatch.setattr(
        cli_mod, "generate_tick_dataset", lambda _p, sample_rate=16: pd.DataFrame({"t": [1]})
    )

    rc = cli_mod.main(["parse-batch", str(demos_dir), "--output-dir", str(parsed)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "fail: a" in out
    assert "parse: b" in out
    assert "1 parsed, 0 skipped, 1 failed" in out
```

Update `tests/test_smoke.py`'s `test_every_subcommand_help_exits_zero` to include `["parse-batch", "--help"]`:

```python
def test_every_subcommand_help_exits_zero() -> None:
    from cs2_analytics.cli import main

    for argv in (
        ["parse", "--help"],
        ["parse-batch", "--help"],
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

- [ ] **Step 5.2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py tests/test_smoke.py -v -k batch`
Expected: 3 fails (no `parse-batch` registered).

- [ ] **Step 5.3: Add `_add_parse_batch` and `_handle_parse_batch` to `src/cs2_analytics/cli.py`**

Add these functions (place them just below `_handle_ticks`):

```python
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
```

Register the new subcommand in `build_parser` — add the line so it reads:

```python
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
```

- [ ] **Step 5.4: Run, confirm pass**

Run: `uv run pytest tests/test_cli.py tests/test_smoke.py -v`
Expected: all green.

- [ ] **Step 5.5: Commit**

```powershell
git add src/cs2_analytics/cli.py tests/test_cli.py tests/test_smoke.py
git commit -m "feat(cli): add parse-batch subcommand"
```

---

## Task 6: CLI — `--demo` filter on `analyze` and `visualize`

**Files:**
- Modify: `src/cs2_analytics/cli.py` (analyze + visualize subparsers and handlers)
- Modify: `src/cs2_analytics/analysis/round_analyzer.py` and other analyses to accept the optional demo_id
- Modify: `tests/test_cli.py`

The analysis functions today call `repo.get_kills()` with no demo. To make `--demo` work end-to-end without changing every call site individually, the CLI handler will pass `demo_id` into a thin per-analysis wrapper. Simpler: the analysis functions accept an optional `demo_id: str | None = None` kwarg and forward it to `repo.get_*`.

- [ ] **Step 6.1: Add failing test**

Append to `tests/test_cli.py`:

```python
def test_analyze_demo_missing_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from cs2_analytics import cli as cli_mod

    rc = cli_mod.main(
        [
            "analyze",
            "--parsed-dir",
            str(tmp_path / "parsed"),
            "--demo",
            "nope",
            "rounds",
        ]
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "nope" in err
```

- [ ] **Step 6.2: Run, confirm fail**

Run: `uv run pytest tests/test_cli.py::test_analyze_demo_missing_returns_nonzero -v`
Expected: FAIL (argument `--demo` not recognized or no error surfaced).

- [ ] **Step 6.3: Patch the four analysis modules**

Edit each of:

- `src/cs2_analytics/analysis/round_analyzer.py`
- `src/cs2_analytics/analysis/death_zones.py`
- `src/cs2_analytics/analysis/entry_kills.py`
- `src/cs2_analytics/analysis/reaction_time.py`
- `src/cs2_analytics/analysis/reaction_time_advanced.py`
- `src/cs2_analytics/visualization/heatmap.py`

For each, add an optional `demo_id: str | None = None` parameter and forward to every `repo.get_*()` call. Example for `round_analyzer.py` (final form):

```python
from cs2_analytics.data.repository import ParsedDataRepository


def analyze_rounds(repo: ParsedDataRepository, demo_id: str | None = None) -> None:
    kills = repo.get_kills(demo_id=demo_id)
    total = len(kills)
    print("Total kills:", total)
    if total == 0:
        print("Headshots: 0")
        print("Headshot rate: n/a")
        return
    headshots = int(kills["headshot"].sum())
    print("Headshots:", headshots)
    print("Headshot rate:", headshots / total)
```

Apply the same pattern to the others. For `death_zones.py`, both `repo.get_kills()` and `repo.get_ticks()` must take `demo_id=demo_id`. For `heatmap.py`, forward `demo_id` to whichever repo getters it calls.

- [ ] **Step 6.4: Wire `--demo` into the CLI**

In `src/cs2_analytics/cli.py`, add `--demo` to both `_add_analyze` and `_add_visualize`, and pass it through every handler.

Patch `_add_analyze`:

```python
def _add_analyze(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("analyze", help="Run analysis on parsed data")
    p.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path("parsed"),
        help="Directory containing parquet files (default: parsed/)",
    )
    p.add_argument(
        "--demo",
        dest="demo_id",
        default=None,
        help="Restrict analysis to a single demo by its stem. Default: all demos.",
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
```

Patch all four `_handle_analyze_*` to forward `demo_id`:

```python
def _handle_analyze_rounds(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    try:
        analyze_rounds(repo, demo_id=args.demo_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _handle_analyze_death_zones(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    try:
        death_zone_stats(repo, args.player, args.map_name, demo_id=args.demo_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _handle_analyze_entry_kills(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    try:
        entry_kill_stats(repo, demo_id=args.demo_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _handle_analyze_reaction_time(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    try:
        if args.advanced:
            reaction_time_advanced(repo, args.player, demo_id=args.demo_id)
        else:
            reaction_time(repo, args.player, demo_id=args.demo_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
```

Patch `_add_visualize` analogously — add the same `--demo` argument and forward via `demo_id=args.demo_id`:

```python
def _add_visualize(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("visualize", help="Render visualizations from parsed data")
    p.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path("parsed"),
        help="Directory containing parquet files (default: parsed/)",
    )
    p.add_argument(
        "--demo",
        dest="demo_id",
        default=None,
        help="Restrict visualization to a single demo by its stem. Default: all demos.",
    )
    leaf = p.add_subparsers(dest="visualize_command", required=True)

    hm = leaf.add_parser("heatmap", help="Per-player KDE heatmap on a map")
    hm.add_argument("--player", required=True, help="Player name")
    hm.add_argument("--map", dest="map_name", required=True, help="Map name")
    hm.set_defaults(handler=_handle_visualize_heatmap)


def _handle_visualize_heatmap(args: argparse.Namespace) -> int:
    repo = ParsedDataRepository(args.parsed_dir)
    try:
        player_heatmap_map(repo, args.player, args.map_name, demo_id=args.demo_id)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
```

- [ ] **Step 6.5: Run, confirm pass**

Run: `uv run pytest -v`
Expected: every test green, including the new `test_analyze_demo_missing_returns_nonzero`.

- [ ] **Step 6.6: Commit**

```powershell
git add src/cs2_analytics tests/test_cli.py
git commit -m "feat(cli): --demo filter on analyze and visualize"
```

---

## Task 7: End-to-end smoke for nested layout

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 7.1: Add a real demo smoke test**

Append to `tests/test_smoke.py`:

```python
def test_parse_writes_nested_layout_and_blocks_overwrite(tmp_path: Path) -> None:
    from cs2_analytics.cli import main

    demo = Path("demos/13-03-2026_Inf_3Stack.dem")
    if not demo.exists():
        pytest.skip("real demo file not present in this checkout")

    parsed = tmp_path / "parsed"
    rc = main(["parse", str(demo), "--output-dir", str(parsed)])
    assert rc == 0
    assert (parsed / demo.stem / "kills.parquet").exists()
    assert (parsed / demo.stem / "rounds.parquet").exists()

    rc2 = main(["parse", str(demo), "--output-dir", str(parsed)])
    assert rc2 == 2  # without --force

    rc3 = main(["parse", str(demo), "--output-dir", str(parsed), "--force"])
    assert rc3 == 0
```

Note the `from pathlib import Path` may need adding at the top of `test_smoke.py` if it isn't already present.

- [ ] **Step 7.2: Run**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: all green (the new test skips if `demos/13-03-2026_Inf_3Stack.dem` isn't present; on the user's machine it should run).

- [ ] **Step 7.3: Commit**

```powershell
git add tests/test_smoke.py
git commit -m "test(smoke): nested parsed layout + overwrite gate"
```

---

## Task 8: Manual end-to-end verification on real demo data

This task does not write code — it confirms the pipeline works against the real demo before we update docs.

- [ ] **Step 8.1: Wipe the legacy `parsed/` directory**

```powershell
Remove-Item -Recurse -Force parsed -ErrorAction SilentlyContinue
```

- [ ] **Step 8.2: Parse one demo into the new layout**

```powershell
uv run cs2-analytics parse demos/13-03-2026_Inf_3Stack.dem
uv run cs2-analytics ticks demos/13-03-2026_Inf_3Stack.dem
```

Expected:
- `parsed/13-03-2026_Inf_3Stack/{kills,damage,rounds,weapon_fire,ticks}.parquet` all exist.
- Per-file `wrote ...` lines, ending with `parsed: 13-03-2026_Inf_3Stack` and `wrote .../ticks.parquet`.

- [ ] **Step 8.3: Re-run `parse` without `--force` → expect exit 2**

```powershell
uv run cs2-analytics parse demos/13-03-2026_Inf_3Stack.dem
echo $LASTEXITCODE
```

Expected: stderr contains `already exists`, `$LASTEXITCODE` is `2`.

- [ ] **Step 8.4: Run the existing analyses across the store**

```powershell
uv run cs2-analytics analyze rounds
uv run cs2-analytics analyze reaction-time --player AngelsHy4per --advanced
```

Expected: both produce the same output as the foundation smoke baseline (40 reaction events).

- [ ] **Step 8.5: Run with `--demo` filter**

```powershell
uv run cs2-analytics analyze --demo 13-03-2026_Inf_3Stack rounds
uv run cs2-analytics analyze --demo nope rounds
```

Expected: first matches step 8.4; second prints an `error:` line and exits 1.

- [ ] **Step 8.6: `parse-batch` against `demos/`**

```powershell
uv run cs2-analytics parse-batch demos/
```

Expected: `skip: 13-03-2026_Inf_3Stack (already parsed)` (the demo dir already exists from step 8.2), plus `parse: ...` for any other `.dem` files, then `parse-batch: N parsed, 1 skipped, 0 failed`. If `demos/` contains only the one file, the summary is `0 parsed, 1 skipped, 0 failed`.

- [ ] **Step 8.7: Lint and full test pass**

```powershell
uv run ruff check
uv run ruff format --check
uv run pytest -q
```

Expected: all green.

No commit for this task (verification only).

---

## Task 9: Update STATUS.md and CLAUDE.md

**Files:**
- Modify: `STATUS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 9.1: Update `CLAUDE.md`**

Find the "## Common commands" section in `CLAUDE.md`. Replace the parsing block (the two `parse` / `ticks` lines) with:

```markdown
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
```

Find the "## Data flow" section. Update the parsing arrow box to show the per-demo layout:

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
```

Find the "## Module conventions" section. Add a bullet:

```markdown
- **Storage is per-demo.** `parsed/<demo-stem>/<table>.parquet`. Every `repo.save_*` takes a `demo_id` argument; every `repo.get_*` accepts an optional `demo_id` (defaults to aggregating across all demos and adding a `demo_id` column).
```

- [ ] **Step 9.2: Update `STATUS.md`**

Set `**Last updated:**` to today. Replace the "## Where we are" section's leading paragraph and the Phase 2 entry under "Next phases" with the merged-state equivalents:

Top of file:

```markdown
**Last updated:** 2026-05-15

## Where we are

**Phase 2 (Storage layer + batch processing) — ✅ MERGED.**

Per-demo parquet layout: `parsed/<demo-stem>/{kills,damage,rounds,weapon_fire,ticks}.parquet`. `ParsedDataRepository` aggregates across demos on read and tags rows with `demo_id`. New CLI: `parse-batch` for bulk ingest, `--force` on `parse`/`ticks`, `--demo <stem>` filter on `analyze`/`visualize`.

**Upgrade from Phase 0+1:** delete `parsed/` and re-run `parse` + `ticks`. The old flat layout is not auto-migrated.
```

Move the existing "Phase 2 — Storage layer + batch processing" block from "Next phases" into a "Phase history" sub-section or remove it; promote "Phase 3a — Flask web UI" to the next-up slot.

- [ ] **Step 9.3: Commit**

```powershell
git add STATUS.md CLAUDE.md
git commit -m "docs: Phase 2 storage layer merged"
```

---

## Task 10: PR

- [ ] **Step 10.1: Push branch**

```powershell
git push -u origin feature/phase2-storage
```

- [ ] **Step 10.2: Open the PR**

```powershell
gh pr create --title "Phase 2: per-demo storage layer + batch processing" --body "@'
## Summary
- Per-demo parquet layout: parsed/<demo-stem>/*.parquet
- ParsedDataRepository: write side takes demo_id; read side aggregates with a demo_id column
- New CLI: parse-batch, --force on parse/ticks, --demo on analyze/visualize
- analyze rounds tolerates an empty store

## Spec / plan
- Spec: docs/superpowers/specs/2026-05-15-phase2-storage-design.md
- Plan: docs/superpowers/plans/2026-05-15-phase2-storage.md

## Test plan
- [x] uv run pytest -q  (expect green)
- [x] uv run ruff check  (expect clean)
- [x] cs2-analytics parse demos/13-03-2026_Inf_3Stack.dem  (nested layout written)
- [x] re-parse without --force  (exit 2)
- [x] analyze --demo <stem> rounds  (matches single-demo output)
- [x] parse-batch demos/  (skips existing, parses missing)

## Upgrade procedure
rm -rf parsed/ ; re-run parse + ticks. Documented in STATUS.md.
'@"
```

Web-UI fallback if `gh` is unavailable: open the branch on github.com and click "Compare & pull request"; paste the body above.

- [ ] **Step 10.3: Merge after CI / self-review**

Squash-merge once green. Then locally:

```powershell
git switch main
git pull
git branch -d feature/phase2-storage
```

---

## Done

After Task 10 merges, the project state matches the spec's "Goal" exactly: per-demo storage, aggregating reads, parse-batch, --force, --demo. Phase 3a (Flask UI) becomes unblocked.
