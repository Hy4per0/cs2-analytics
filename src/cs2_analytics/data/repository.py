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
