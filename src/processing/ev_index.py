"""
EV-charging access sub-index.

Source: DOE/NREL Alternative Fuels Data Center (AFDC). For each tract we count
public Level-2 and DC-fast chargers located inside the tract, express it as
chargers per 1,000 residents, and measure the distance from the tract centroid
to the nearest DC-fast station. Both metrics are normalized to 0–100 and
averaged (methodology §3.4 / Step 6).

Distance is inverted before normalization so that *closer* stations yield a
*higher* score, consistent with every other sub-index where higher = better.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from src.config import CRS_GEOGRAPHIC, CRS_PROJECTED
from src.processing.normalizer import minmax_normalize


def stations_to_gdf(stations: pd.DataFrame) -> gpd.GeoDataFrame:
    """Build a point GeoDataFrame from AFDC station records.

    Expects 'latitude'/'longitude' columns and an EV connector-level/DCFC count.
    """
    geom = [Point(xy) for xy in zip(stations["longitude"], stations["latitude"])]
    return gpd.GeoDataFrame(stations.copy(), geometry=geom, crs=CRS_GEOGRAPHIC)


def build_ev_index(
    stations: pd.DataFrame,
    tracts: gpd.GeoDataFrame,
    population: pd.Series | None = None,
) -> pd.DataFrame:
    """Compute the EV sub-index per tract.

    Parameters
    ----------
    stations   : AFDC stations with columns 'latitude', 'longitude', and
                 optionally 'ev_dc_fast_num' (DCFC port count). A station with
                 ev_dc_fast_num > 0 is treated as a DC-fast site for the
                 nearest-distance metric.
    tracts     : tract polygons with 'GEOID'.
    population : optional Series indexed by GEOID with tract population, used
                 for the per-1,000-resident density. If omitted, raw counts
                 are used.

    Returns
    -------
    DataFrame with ['GEOID', 'charger_count', 'charger_per_1k',
                    'dist_to_dcfc_km', 'ev_score'].
    """
    tr = tracts.to_crs(CRS_PROJECTED).copy()
    tr["GEOID"] = tr["GEOID"].astype(str).str.zfill(11)

    sta = stations_to_gdf(stations).to_crs(CRS_PROJECTED)
    if "ev_dc_fast_num" not in sta.columns:
        sta["ev_dc_fast_num"] = 0
    sta["ev_dc_fast_num"] = pd.to_numeric(sta["ev_dc_fast_num"], errors="coerce").fillna(0)

    # --- Count chargers inside each tract ---
    joined = gpd.sjoin(sta, tr[["GEOID", "geometry"]], how="inner", predicate="within")
    counts = joined.groupby("GEOID").size().rename("charger_count")

    out = tr[["GEOID", "geometry"]].merge(counts, on="GEOID", how="left")
    out["charger_count"] = out["charger_count"].fillna(0).astype(int)

    # --- Chargers per 1,000 residents ---
    if population is not None:
        pop = population.copy()
        pop.index = pop.index.astype(str).str.zfill(11)
        out["population"] = out["GEOID"].map(pop)
        out["charger_per_1k"] = out["charger_count"] / (out["population"] / 1000.0)
        out["charger_per_1k"] = out["charger_per_1k"].replace([np.inf, -np.inf], np.nan)
    else:
        out["charger_per_1k"] = out["charger_count"].astype(float)

    # --- Distance from centroid to nearest DC-fast station ---
    dcfc = sta[sta["ev_dc_fast_num"] > 0]
    centroids = out.set_geometry(out.geometry.centroid)
    if len(dcfc) > 0:
        nearest = gpd.sjoin_nearest(
            centroids[["GEOID", "geometry"]], dcfc[["geometry"]], distance_col="dist_m"
        )
        dist = nearest.groupby("GEOID")["dist_m"].min() / 1000.0
        out["dist_to_dcfc_km"] = out["GEOID"].map(dist)
    else:
        out["dist_to_dcfc_km"] = np.nan

    # --- Normalize: density (higher better) + proximity (closer better) ---
    density_norm = minmax_normalize(out["charger_per_1k"])
    # Invert distance so nearer = higher score.
    proximity = -out["dist_to_dcfc_km"]
    proximity_norm = minmax_normalize(proximity)

    out["ev_score"] = pd.concat([density_norm, proximity_norm], axis=1).mean(axis=1)
    return out[
        ["GEOID", "charger_count", "charger_per_1k", "dist_to_dcfc_km", "ev_score"]
    ]
