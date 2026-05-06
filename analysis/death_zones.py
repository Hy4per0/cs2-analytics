import pandas as pd

from utils.map_zones_awpy import get_zone


def death_zone_stats(player_name):

    kills = pd.read_parquet("parsed/kills.parquet")
    ticks = pd.read_parquet("parsed/ticks.parquet")

    deaths = kills[kills["user_name"] == player_name]

    zones = []

    # ticki tylko dla tego gracza
    player_ticks = ticks[ticks["name"] == player_name]

    for _, row in deaths.iterrows():
        death_tick = row["tick"]

        # znajdź najbliższy tick
        closest = player_ticks.iloc[(player_ticks["tick"] - death_tick).abs().argsort()[:1]]

        if closest.empty:
            continue

        x = closest.iloc[0]["X"]
        y = closest.iloc[0]["Y"]

        zone = get_zone("de_inferno", x, y)

        zones.append(zone)

    zone_counts = pd.Series(zones).value_counts()

    print("Death zones:")
    print(zone_counts)
