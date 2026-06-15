"""
Fetch the bicycle network from OpenStreetMap via OSMnx (no API key required).

For each city we download the cyclable street network, convert it to an edges
GeoDataFrame, and save it for the bike sub-index. OSMnx caches raw responses
under its own cache dir so re-runs are fast.

Run:
    python -m src.data_collection.fetch_osm            # all study cities
    python -m src.data_collection.fetch_osm seattle    # a single city
"""
from __future__ import annotations

import sys

import geopandas as gpd
import osmnx as ox

from src.config import CITIES, CRS_GEOGRAPHIC, RAW_DIR

OSM_DIR = RAW_DIR / "osm"
OSM_DIR.mkdir(parents=True, exist_ok=True)

ox.settings.use_cache = True
ox.settings.log_console = False
# Retain the cycleway tag so on-street lanes (not just separate cycleways) count.
ox.settings.useful_tags_way = list(
    set(ox.settings.useful_tags_way) | {"highway", "cycleway", "bicycle"}
)


def _flatten_tag(value) -> str:
    """OSM way tags can be a list (multiple values on one way). Reduce to a
    single representative string so the field survives GeoJSON round-tripping."""
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else ""
    return "" if value is None else str(value)


def fetch_city_bike_network(city_key: str) -> gpd.GeoDataFrame:
    """Download the bike network for one city and save its edges as GeoJSON."""
    cfg = CITIES[city_key]
    print(f"[{cfg['name']}] querying OSM bike network for '{cfg['place_name']}' ...")
    graph = ox.graph_from_place(cfg["place_name"], network_type="bike")
    edges = ox.graph_to_gdfs(graph, nodes=False).to_crs(CRS_GEOGRAPHIC)

    for col in ("cycleway", "bicycle"):
        if col not in edges.columns:
            edges[col] = ""
    keep = ["highway", "cycleway", "bicycle", "name", "length", "geometry"]
    keep = [c for c in keep if c in edges.columns]
    edges = edges[keep].copy()
    for col in ("highway", "cycleway", "bicycle", "name"):
        if col in edges.columns:
            edges[col] = edges[col].map(_flatten_tag)

    out_path = OSM_DIR / f"{city_key}_bike_edges.geojson"
    edges.reset_index(drop=True).to_file(out_path, driver="GeoJSON")
    print(f"[{cfg['name']}] wrote {len(edges)} bike edges -> {out_path.name}")
    return edges


def main(cities: list[str] | None = None) -> None:
    for key in (cities or list(CITIES)):
        fetch_city_bike_network(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
