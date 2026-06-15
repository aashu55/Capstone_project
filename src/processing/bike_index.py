"""
Bicycle-infrastructure sub-index.

Source: OpenStreetMap via OSMnx. We extract the cyclable network for a city,
keep edges tagged as dedicated bike infrastructure (cycleway / path / track),
clip them to each Census tract, and compute bike-lane kilometres per square
kilometre of tract land area. The density is min–max normalized to 0–100
(methodology §3.4 / Step 5).
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src.config import CRS_PROJECTED
from src.processing.normalizer import minmax_normalize

BIKE_HIGHWAY_TAGS = {"cycleway", "path", "track"}
# cycleway tag values that indicate *no* dedicated provision.
CYCLEWAY_NEGATIVE = {"", "no", "none", "nan", "separate"}


def filter_bike_edges(edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only edges that represent dedicated cycling infrastructure.

    An edge qualifies if its `highway` tag is a dedicated cycleway/path/track,
    OR it carries a positive `cycleway` tag (an on-street marked lane on an
    otherwise general road, e.g. cycleway=lane / track / shared_lane). Fields
    are simple strings (see fetch_osm._flatten_tag).
    """
    edges = edges.copy()
    hw = edges["highway"].astype(str).str.lower()
    hw_mask = hw.isin(BIKE_HIGHWAY_TAGS)
    if "cycleway" in edges.columns:
        cw = edges["cycleway"].astype(str).str.lower()
        cw_mask = ~cw.isin(CYCLEWAY_NEGATIVE)
        return edges[hw_mask | cw_mask]
    return edges[hw_mask]


def build_bike_index(
    bike_edges: gpd.GeoDataFrame,
    tracts: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Compute bike-lane density (km per km²) per tract and normalize to 0–100.

    Parameters
    ----------
    bike_edges : edges GeoDataFrame from OSMnx (already filtered or raw — this
                 function filters defensively).
    tracts     : tract polygons with a 'GEOID' column.

    Returns
    -------
    DataFrame with ['GEOID', 'bike_km', 'bike_density', 'bike_score'].
    """
    edges = filter_bike_edges(bike_edges).to_crs(CRS_PROJECTED)
    tr = tracts.to_crs(CRS_PROJECTED).copy()
    tr["GEOID"] = tr["GEOID"].astype(str).str.zfill(11)
    tr["area_km2"] = tr.geometry.area / 1e6

    # Clip bike edges to tract boundaries; each segment inherits its tract GEOID.
    clipped = gpd.overlay(
        edges[["geometry"]], tr[["GEOID", "geometry"]], how="intersection"
    )
    clipped["len_km"] = clipped.geometry.length / 1000.0
    bike_km = clipped.groupby("GEOID")["len_km"].sum().rename("bike_km")

    out = tr[["GEOID", "area_km2"]].merge(bike_km, on="GEOID", how="left")
    out["bike_km"] = out["bike_km"].fillna(0.0)
    out["bike_density"] = out["bike_km"] / out["area_km2"].replace(0, pd.NA)
    out["bike_score"] = minmax_normalize(out["bike_density"])
    return out[["GEOID", "bike_km", "bike_density", "bike_score"]]
