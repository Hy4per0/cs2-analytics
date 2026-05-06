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

    def save_kills(self, df: pd.DataFrame) -> None:
        self._save("kills", df)

    def save_damage(self, df: pd.DataFrame) -> None:
        self._save("damage", df)

    def save_rounds(self, df: pd.DataFrame) -> None:
        self._save("rounds", df)

    def save_weapon_fire(self, df: pd.DataFrame) -> None:
        self._save("weapon_fire", df)

    def save_ticks(self, df: pd.DataFrame) -> None:
        self._save("ticks", df)

    def get_kills(self) -> pd.DataFrame:
        return self._get("kills")

    def get_damage(self) -> pd.DataFrame:
        return self._get("damage")

    def get_rounds(self) -> pd.DataFrame:
        return self._get("rounds")

    def get_weapon_fire(self) -> pd.DataFrame:
        return self._get("weapon_fire")

    def get_ticks(self) -> pd.DataFrame:
        return self._get("ticks")
