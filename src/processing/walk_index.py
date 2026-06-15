"""
Walkability sub-index.

Source: EPA Smart Location Database (SLD) v3. The key field is `NatWalkInd`,
the National Walkability Index (1–20), reported at the Census *block-group*
level on 2019-vintage geometry. Because the study's tract boundaries are the
2023 (2020-decade) TIGER tracts, a direct GEOID join loses ~half of Houston's
tracts where boundaries were redrawn. We therefore areally interpolate: each
2023 tract's walkability is the area-weighted mean of the NatWalkInd of every
2019 block group it overlaps (methodology §3.3 / §3.4). The result is min–max
normalized to 0–100.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src.config import CRS_PROJECTED
from src.processing.normalizer import minmax_normalize


def attach_walkability(blockgroups_2019: gpd.GeoDataFrame, epa_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Join NatWalkInd onto 2019 block-group geometry by GEOID."""
    bg = blockgroups_2019.copy()
    bg["GEOID"] = bg["GEOID"].astype(str).str.zfill(12)
    epa = epa_df.copy()
    epa["GEOID"] = epa["GEOID"].astype(str).str.zfill(12)
    epa["NatWalkInd"] = pd.to_numeric(epa["NatWalkInd"], errors="coerce")
    merged = bg.merge(epa[["GEOID", "NatWalkInd"]], on="GEOID", how="left")
    return merged.dropna(subset=["NatWalkInd"])


def areal_interpolate(
    blockgroups: gpd.GeoDataFrame,
    tracts: gpd.GeoDataFrame,
    value_col: str = "NatWalkInd",
) -> pd.DataFrame:
    """Area-weighted mean of `value_col` from block groups onto tracts.

    NatWalkInd is an *intensive* quantity (an index, not a count), so the
    correct interpolation is an area-weighted average over each tract's
    intersecting block-group pieces.
    """
    bg = blockgroups.to_crs(CRS_PROJECTED)[[value_col, "geometry"]].copy()
    tr = tracts.to_crs(CRS_PROJECTED).copy()
    tr["GEOID"] = tr["GEOID"].astype(str).str.zfill(11)
    tr = tr[["GEOID", "geometry"]]

    pieces = gpd.overlay(tr, bg, how="intersection", keep_geom_type=True)
    pieces["piece_area"] = pieces.geometry.area
    pieces["weighted"] = pieces[value_col] * pieces["piece_area"]

    grp = pieces.groupby("GEOID").agg(
        weighted_sum=("weighted", "sum"), area_sum=("piece_area", "sum")
    )
    grp["walk_raw"] = grp["weighted_sum"] / grp["area_sum"]
    return grp.reset_index()[["GEOID", "walk_raw"]]


def build_walk_index(
    blockgroups_2019: gpd.GeoDataFrame,
    epa_df: pd.DataFrame,
    tracts: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Return ['GEOID', 'walk_raw', 'walk_score'] (0–100) for the 2023 tracts."""
    bg = attach_walkability(blockgroups_2019, epa_df)
    agg = areal_interpolate(bg, tracts, value_col="NatWalkInd")
    agg["walk_score"] = minmax_normalize(agg["walk_raw"])
    return agg[["GEOID", "walk_raw", "walk_score"]]
