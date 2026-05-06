from cs2_analytics.data.repository import ParsedDataRepository


def analyze_rounds(repo: ParsedDataRepository) -> None:
    kills = repo.get_kills()

    print("Total kills:", len(kills))

    headshots = kills["headshot"].sum()
    print("Headshots:", headshots)

    print("Headshot rate:", headshots / len(kills))
