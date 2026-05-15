import math

from cs2_analytics.data.repository import ParsedDataRepository


def angle_between(p1x, p1y, p2x, p2y):
    dx = p2x - p1x
    dy = p2y - p1y
    return math.degrees(math.atan2(dy, dx))


def angle_diff(a, b):
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def reaction_time_advanced(
    repo: ParsedDataRepository, player_name: str, demo_id: str | None = None
) -> None:
    ticks = repo.get_ticks(demo_id=demo_id)
    fires = repo.get_weapon_fire(demo_id=demo_id)

    player_ticks = ticks[ticks["name"] == player_name]

    reaction_times = []

    for _, fire in fires.iterrows():
        if fire["user_name"] != player_name:
            continue

        fire_tick = fire["tick"]

        pt = player_ticks[player_ticks["tick"] == fire_tick]

        if pt.empty:
            continue

        px = pt.iloc[0]["X"]
        py = pt.iloc[0]["Y"]
        yaw = pt.iloc[0]["yaw"]

        enemies = ticks[
            (ticks["tick"] == fire_tick) & (ticks["team_name"] != pt.iloc[0]["team_name"])
        ]

        for _, enemy in enemies.iterrows():
            ex = enemy["X"]
            ey = enemy["Y"]

            enemy_angle = angle_between(px, py, ex, ey)

            diff = angle_diff(yaw, enemy_angle)

            if diff < 15:  # enemy roughly in crosshair
                reaction_times.append(fire_tick)

    if not reaction_times:
        print("No reaction events found")
        return

    print("Detected reaction events:", len(reaction_times))
