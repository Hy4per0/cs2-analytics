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
