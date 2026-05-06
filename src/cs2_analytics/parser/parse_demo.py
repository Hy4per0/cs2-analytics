import pandas as pd
from demoparser2 import DemoParser


def parse_demo(demo_path: str) -> dict[str, pd.DataFrame]:
    """Parse a CS2 .dem file into event tables.

    Returns a dict mapping table name to DataFrame. Persistence is the
    caller's responsibility (typically via ParsedDataRepository.save_*).
    """
    print(f"Parsing demo: {demo_path}")

    parser = DemoParser(demo_path)
    tables = {
        "kills": pd.DataFrame(parser.parse_event("player_death")),
        "damage": pd.DataFrame(parser.parse_event("player_hurt")),
        "rounds": pd.DataFrame(parser.parse_event("round_start")),
        "weapon_fire": pd.DataFrame(parser.parse_event("weapon_fire")),
    }

    print("Parsing complete")
    return tables
