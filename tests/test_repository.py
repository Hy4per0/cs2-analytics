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
