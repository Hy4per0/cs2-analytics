from pathlib import Path

import pandas as pd
from demoparser2 import DemoParser


def generate_tick_dataset(demo_path: str, output_dir: str):

    print("Generating tick dataset...")

    parser = DemoParser(demo_path)

    df = parser.parse_ticks(
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

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(df)

    # tick sampling (every 16 ticks)
    df = df[df["tick"] % 16 == 0]

    df.to_parquet(f"{output_dir}/ticks.parquet")

    print("Tick dataset saved")
    print("Rows:", len(df))
