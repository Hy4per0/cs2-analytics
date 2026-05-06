import pandas as pd


def entry_kill_stats():

    kills = pd.read_parquet("parsed/kills.parquet")
    rounds = pd.read_parquet("parsed/rounds.parquet")

    entry_killers = []
    entry_deaths = []

    for _, r in rounds.iterrows():

        start_tick = r["tick"]

        # kille po starcie rundy
        round_kills = kills[kills["tick"] >= start_tick]

        if round_kills.empty:
            continue

        first_kill = round_kills.sort_values("tick").iloc[0]

        entry_killers.append(first_kill["attacker_name"])
        entry_deaths.append(first_kill["user_name"])

    print("\nEntry kills:")
    print(pd.Series(entry_killers).value_counts())

    print("\nEntry deaths:")
    print(pd.Series(entry_deaths).value_counts())