import pandas as pd


def analyze_rounds():

    kills = pd.read_parquet("parsed/kills.parquet")

    print("Total kills:", len(kills))

    headshots = kills["headshot"].sum()
    print("Headshots:", headshots)

    print("Headshot rate:", headshots / len(kills))