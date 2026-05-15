from cs2_analytics.data.repository import ParsedDataRepository


def reaction_time(
    repo: ParsedDataRepository, player_name: str, demo_id: str | None = None
) -> None:
    fires = repo.get_weapon_fire(demo_id=demo_id)
    kills = repo.get_kills(demo_id=demo_id)

    player_fires = fires[fires["user_name"] == player_name]

    reaction_times = []

    for _, kill in kills.iterrows():
        attacker = kill["attacker_name"]
        tick = kill["tick"]

        if attacker != player_name:
            continue

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
