import matplotlib.pyplot as plt
from awpy.plot import heatmap

from cs2_analytics.data.repository import ParsedDataRepository


def player_heatmap_map(repo: ParsedDataRepository, player_name: str, map_name: str) -> None:
    """Render a KDE heatmap of a player's positions on a given map."""
    ticks = repo.get_ticks()
    player_data = ticks[ticks["name"] == player_name].copy()
    points = list(player_data[["X", "Y", "Z"]].itertuples(index=False, name=None))

    fig, ax = heatmap(
        map_name=map_name,
        points=points,
        method="kde",
        cmap="inferno",
        alpha=0.6,
        kde_lower_bound=0.01,
    )

    plt.title(f"Heatmap - {player_name}")
    plt.show()
