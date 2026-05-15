from cs2_analytics.data.repository import ParsedDataRepository


def analyze_rounds(repo: ParsedDataRepository, demo_id: str | None = None) -> None:
    kills = repo.get_kills(demo_id=demo_id)
    total = len(kills)
    print("Total kills:", total)
    if total == 0:
        print("Headshots: 0")
        print("Headshot rate: n/a")
        return
    headshots = int(kills["headshot"].sum())
    print("Headshots:", headshots)
    print("Headshot rate:", headshots / total)
