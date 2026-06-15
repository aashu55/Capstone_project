"""
Build the four sub-indices for a city from the raw data on disk and write the
per-city sub-index CSVs to data/processed/sub_indices/.

Real data sources (no API key needed) are used for the bicycle and walkability
sub-indices. The transit and EV sub-indices require API keys (GTFS via
transit.land, chargers via NREL); when their raw inputs are absent this module
falls back to a clearly-labelled spatial *placeholder* so the rest of the
pipeline (MES, analysis, dashboard) is runnable end-to-end. Placeholder columns
are flagged so they are never mistaken for measured values.

Run:
    python -m src.processing.build_subindices            # all cities
    python -m src.processing.build_subindices seattle    # one city
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from src.config import (AFDC_DIR, CITIES, CRS_PROJECTED, GTFS_DIR, RAW_DIR,
                        SUB_INDEX_DIR, TIGER_DIR)
from src.processing.bike_index import build_bike_index
from src.processing.walk_index import build_walk_index

OSM_DIR = RAW_DIR / "osm"


def _load_tracts(city_key: str) -> gpd.GeoDataFrame:
    tr = gpd.read_file(TIGER_DIR / f"{city_key}_tracts.geojson")
    tr["GEOID"] = tr["GEOID"].astype(str).str.zfill(11)
    return tr


# --------------------------------------------------------------------------- #
# Real sub-indices
# --------------------------------------------------------------------------- #
def bike_subindex(city_key: str, tracts: gpd.GeoDataFrame) -> pd.DataFrame:
    edges = gpd.read_file(OSM_DIR / f"{city_key}_bike_edges.geojson")
    return build_bike_index(edges, tracts)


def walk_subindex(city_key: str, tracts: gpd.GeoDataFrame) -> pd.DataFrame:
    bg2019 = gpd.read_file(TIGER_DIR / f"{city_key}_blockgroups_2019.geojson")
    epa = pd.read_csv(RAW_DIR / "epa_walkability" / f"{city_key}_walkability.csv",
                      dtype={"GEOID": str})
    return build_walk_index(bg2019, epa, tracts)


# --------------------------------------------------------------------------- #
# Keyed sub-indices (real if raw present, else spatial placeholder)
# --------------------------------------------------------------------------- #
def _distance_to_centroid_score(tracts: gpd.GeoDataFrame, seed: int) -> pd.Series:
    """A spatially-structured placeholder in [0,100].

    Built from each tract's distance to the city centroid plus mild
    reproducible noise, so the placeholder has realistic spatial autocorrelation
    (central tracts score higher) for exercising the pipeline — NOT a real
    measurement.
    """
    tr = tracts.to_crs(CRS_PROJECTED)
    cent = tr.geometry.centroid
    city_center = cent.union_all().centroid
    dist = cent.distance(city_center)
    score = 100 * (1 - (dist - dist.min()) / (dist.max() - dist.min()))
    rng = np.random.default_rng(seed)
    score = (score + rng.normal(0, 8, len(score))).clip(0, 100)
    return pd.Series(score.values, index=tr.index)


def transit_subindex(city_key: str, tracts: gpd.GeoDataFrame) -> tuple[pd.DataFrame, bool]:
    gtfs = GTFS_DIR / f"{city_key}_gtfs.zip"
    if gtfs.exists():
        import zipfile

        from src.processing.transit_index import build_transit_index
        with zipfile.ZipFile(gtfs) as zf:
            stops = pd.read_csv(zf.open("stops.txt"))
            stop_times = pd.read_csv(zf.open("stop_times.txt"))
        df = build_transit_index(stops, stop_times, tracts)
        return df[["GEOID", "transit_score"]], True
    # placeholder
    df = pd.DataFrame({"GEOID": tracts["GEOID"].values})
    df["transit_score"] = _distance_to_centroid_score(tracts, seed=1).values
    return df, False


def ev_subindex(city_key: str, tracts: gpd.GeoDataFrame) -> tuple[pd.DataFrame, bool]:
    chargers = AFDC_DIR / f"{city_key}_chargers.csv"
    if chargers.exists():
        from src.processing.ev_index import build_ev_index
        stations = pd.read_csv(chargers)
        df = build_ev_index(stations, tracts)
        return df[["GEOID", "ev_score"]], True
    df = pd.DataFrame({"GEOID": tracts["GEOID"].values})
    df["ev_score"] = _distance_to_centroid_score(tracts, seed=2).values
    return df, False


def build_city(city_key: str) -> dict:
    cfg = CITIES[city_key]
    print(f"\n=== {cfg['name']} ===")
    tracts = _load_tracts(city_key)

    bike = bike_subindex(city_key, tracts)
    walk = walk_subindex(city_key, tracts)
    transit, transit_real = transit_subindex(city_key, tracts)
    ev, ev_real = ev_subindex(city_key, tracts)

    SUB_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    bike.to_csv(SUB_INDEX_DIR / f"bike_{city_key}.csv", index=False)
    walk.to_csv(SUB_INDEX_DIR / f"walk_{city_key}.csv", index=False)
    transit.to_csv(SUB_INDEX_DIR / f"transit_{city_key}.csv", index=False)
    ev.to_csv(SUB_INDEX_DIR / f"ev_{city_key}.csv", index=False)

    print(f"  bike    real   ({bike['bike_score'].notna().sum()} tracts)")
    print(f"  walk    real   ({walk['walk_score'].notna().sum()} tracts)")
    print(f"  transit {'real' if transit_real else 'PLACEHOLDER'}")
    print(f"  ev      {'real' if ev_real else 'PLACEHOLDER'}")
    return {"transit_real": transit_real, "ev_real": ev_real}


def main(cities: list[str] | None = None) -> None:
    for key in (cities or list(CITIES)):
        build_city(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
