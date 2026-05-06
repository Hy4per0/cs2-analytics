from demoparser2 import DemoParser
import pandas as pd
from pathlib import Path


def parse_demo(demo_path: str, output_dir: str):

    print(f"Parsing demo: {demo_path}")

    parser = DemoParser(demo_path)

    kills = parser.parse_event("player_death")
    damage = parser.parse_event("player_hurt")
    rounds = parser.parse_event("round_start")
    weapon_fire = parser.parse_event("weapon_fire")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    kills_df = pd.DataFrame(kills)
    kills_df.to_parquet(f"{output_dir}/kills.parquet")

    damage_df = pd.DataFrame(damage)
    damage_df.to_parquet(f"{output_dir}/damage.parquet")

    rounds_df = pd.DataFrame(rounds)
    rounds_df.to_parquet(f"{output_dir}/rounds.parquet")

    weapon_fire_df = pd.DataFrame(weapon_fire)
    weapon_fire_df.to_parquet(f"{output_dir}/weapon_fire.parquet")

    print("Parsing complete")