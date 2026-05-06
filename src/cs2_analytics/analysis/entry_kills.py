import pandas as pd

from cs2_analytics.data.repository import ParsedDataRepository


def entry_kill_stats(repo: ParsedDataRepository) -> None:
    kills = repo.get_kills()
    rounds = repo.get_rounds()

    entry_killers = []
    entry_deaths = []

    for _, r in rounds.iterrows():
        start_tick = r["tick"]

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
