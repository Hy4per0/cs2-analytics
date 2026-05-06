from pathlib import Path

from awpy.data import NAVS_DIR
from awpy.nav import Nav


def _point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Return True if point (x, y) is inside the polygon using ray casting."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    for i in range(n):
        x_i, y_i = polygon[i]
        x_j, y_j = polygon[(i + 1) % n]
        intersect = ((y_i > y) != (y_j > y)) and (
            x < (x_j - x_i) * (y - y_i) / (y_j - y_i + 1e-12) + x_i
        )
        if intersect:
            inside = not inside

    return inside


nav_cache = {}


def load_nav(map_name):

    if map_name not in nav_cache:
        nav_path = Path(NAVS_DIR) / f"{map_name}.json"
        nav_cache[map_name] = Nav.from_json(nav_path)

    return nav_cache[map_name]


def get_zone(map_name: str, x: float, y: float) -> str:

    nav = load_nav(map_name)

    for area in nav.areas.values():
        xs = [corner.x for corner in area.corners]
        ys = [corner.y for corner in area.corners]

        if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys):
            return str(area.area_id)

    return "unknown"
