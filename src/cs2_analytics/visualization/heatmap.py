import matplotlib.pyplot as plt
import pandas as pd
from awpy.plot import heatmap


def player_heatmap_map(player_name, map_name):

    ticks = pd.read_parquet("parsed/ticks.parquet")

    player_data = ticks[ticks["name"] == player_name].copy()

    # Prepare points as list of (X, Y, Z) tuples
    points = list(player_data[["X", "Y", "Z"]].itertuples(index=False, name=None))

    fig, ax = heatmap(
        map_name=map_name,
        points=points,
        method="kde",
        cmap="inferno",
        alpha=0.6,
        kde_lower_bound=0.01,  # Adjust as needed for better visibility
    )

    plt.title(f"Heatmap - {player_name}")

    plt.show()
