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
