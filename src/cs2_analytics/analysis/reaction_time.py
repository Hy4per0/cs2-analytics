import pandas as pd


def reaction_time(player_name):

    fires = pd.read_parquet("parsed/weapon_fire.parquet")
    kills = pd.read_parquet("parsed/kills.parquet")

    player_fires = fires[fires["user_name"] == player_name]

    reaction_times = []

    for _, kill in kills.iterrows():
        attacker = kill["attacker_name"]
        tick = kill["tick"]

        if attacker != player_name:
            continue

        # pierwszy strzał przed killem
        shots = player_fires[player_fires["tick"] <= tick]

        if shots.empty:
            continue

        first_shot = shots.iloc[-1]["tick"]

        reaction = tick - first_shot

        reaction_times.append(reaction)

    if len(reaction_times) == 0:
        print("No reaction data")
        return

    avg_reaction = sum(reaction_times) / len(reaction_times)

    print("\nReaction time (ticks):", avg_reaction)
