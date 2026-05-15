import pandas as pd

from cs2_analytics.data.repository import ParsedDataRepository
from cs2_analytics.utils.maps import get_zone


def death_zone_stats(
    repo: ParsedDataRepository,
    player_name: str,
    map_name: str,
    demo_id: str | None = None,
) -> None:
    kills = repo.get_kills(demo_id=demo_id)
    ticks = repo.get_ticks(demo_id=demo_id)

    deaths = kills[kills["user_name"] == player_name]

    zones = []

    player_ticks = ticks[ticks["name"] == player_name]

    for _, row in deaths.iterrows():
        death_tick = row["tick"]

        closest = player_ticks.iloc[(player_ticks["tick"] - death_tick).abs().argsort()[:1]]

        if closest.empty:
            continue

        x = closest.iloc[0]["X"]
        y = closest.iloc[0]["Y"]

        zone = get_zone(map_name, x, y)

        zones.append(zone)

    zone_counts = pd.Series(zones).value_counts()

    print("Death zones:")
    print(zone_counts)
