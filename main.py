from parser.parse_demo import parse_demo
from analysis.round_analyzer import analyze_rounds
from dataset.tick_dataset import generate_tick_dataset
from visualization.heatmap import player_heatmap_map 
from analysis.death_zones import death_zone_stats
from analysis.entry_kills import entry_kill_stats
from analysis.reaction_time import reaction_time
from analysis.reaction_time_advanced import reaction_time_advanced

demo_path = "demos/13-03-2026_Inf_3Stack.dem"
output_dir = "parsed"

parse_demo(demo_path, output_dir)

# # Analyze rounds and print stats
# analyze_rounds()

# generate tick dataset (with sampling)
generate_tick_dataset(demo_path, output_dir)

# # Example usage of heatmap and death zone analysis
# player_heatmap_map("AngelsHy4per", "de_inferno")

# # Analyze death zones for a specific player
# death_zone_stats("AngelsHy4per")

# # Analyze entry kills
# entry_kill_stats()

# reaction_time("AngelsHy4per")

reaction_time_advanced("AngelsHy4per")