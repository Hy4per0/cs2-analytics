# CS2 Analytics

Two-stage Counter-Strike 2 analytics pipeline:

1. **Demo analysis** — parses `.dem` files into parquet tables, computes player statistics (heatmaps, death zones, entry kills, reaction time).
2. **Computer vision** — extracts frames from gameplay clips, trains a YOLOv11 segmentation model to detect players.

Setup, CLI usage, and architecture details: TBD (added in final task of foundation refactor).
