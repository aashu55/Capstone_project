"""
Transit-access sub-index.

Source: GTFS feeds (one per city). Using the parsed feed we derive, for each
stop, the number of trips during the AM peak (07:00–09:00) and aggregate to the
tract level within a 0.5-mile (≈805 m) buffer of each tract centroid. Three
metrics are produced and averaged (methodology §3.4 / Step 3):

  * stop_density   — stops per km² of tract land area
  * mean_frequency — mean AM-peak trips/hour across nearby stops
  * service_span   — hours of the day with at least one nearby trip

Each metric is min–max normalized to 0–100 before averaging.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from src.config import CRS_GEOGRAPHIC, CRS_PROJECTED
from src.processing.normalizer import minmax_normalize

BUFFER_M = 804.672          # 0.5 miles in metres
AM_PEAK = (7 * 3600, 9 * 3600)   # seconds since midnight


def _to_seconds(timestr: str) -> int | float:
    """GTFS times can exceed 24:00:00 (after-midnight service). Parse to seconds."""
    try:
        h, m, s = (int(x) for x in str(timestr).split(":"))
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return np.nan


def stop_am_peak_trips(stop_times: pd.DataFrame) -> pd.Series:
    """Count AM-peak (07:00–09:00) trips per stop, returned as trips/hour.

    `stop_times` must have 'stop_id' and 'departure_time' columns (raw GTFS).
    """
    st = stop_times[["stop_id", "departure_time"]].copy()
    st["secs"] = st["departure_time"].map(_to_seconds)
    peak = st[(st["secs"] >= AM_PEAK[0]) & (st["secs"] < AM_PEAK[1])]
    trips = peak.groupby("stop_id").size()
    hours = (AM_PEAK[1] - AM_PEAK[0]) / 3600.0
    return (trips / hours).rename("trips_per_hr")


def stop_service_span(stop_times: pd.DataFrame) -> pd.Series:
    """Number of distinct service hours (0–23+) with >=1 departure, per stop."""
    st = stop_times[["stop_id", "departure_time"]].copy()
    st["hr"] = (st["departure_time"].map(_to_seconds) // 3600)
    return st.dropna(subset=["hr"]).groupby("stop_id")["hr"].nunique().rename("service_span")


def build_transit_index(
    stops: pd.DataFrame,
    stop_times: pd.DataFrame,
    tracts: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Compute the transit sub-index per tract.

    Parameters
    ----------
    stops      : GTFS stops with 'stop_id', 'stop_lat', 'stop_lon'.
    stop_times : GTFS stop_times with 'stop_id', 'departure_time'.
    tracts     : tract polygons with 'GEOID'.

    Returns
    -------
    DataFrame with ['GEOID', 'stop_density', 'mean_frequency',
                    'service_span', 'transit_score'].
    """
    freq = stop_am_peak_trips(stop_times)
    span = stop_service_span(stop_times)

    stops = stops.copy()
    stops_gdf = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs=CRS_GEOGRAPHIC,
    ).to_crs(CRS_PROJECTED)
    stops_gdf = stops_gdf.merge(freq, on="stop_id", how="left").merge(span, on="stop_id", how="left")
    stops_gdf[["trips_per_hr", "service_span"]] = stops_gdf[
        ["trips_per_hr", "service_span"]
    ].fillna(0)

    tr = tracts.to_crs(CRS_PROJECTED).copy()
    tr["GEOID"] = tr["GEOID"].astype(str).str.zfill(11)
    tr["area_km2"] = tr.geometry.area / 1e6

    # Buffer each tract centroid by 0.5 mi and spatial-join the stops within it.
    buffers = tr[["GEOID", "area_km2"]].copy()
    buffers["geometry"] = tr.geometry.centroid.buffer(BUFFER_M)
    buffers = gpd.GeoDataFrame(buffers, geometry="geometry", crs=CRS_PROJECTED)

    joined = gpd.sjoin(stops_gdf, buffers, how="inner", predicate="within")
    agg = joined.groupby("GEOID").agg(
        n_stops=("stop_id", "nunique"),
        mean_frequency=("trips_per_hr", "mean"),
        service_span=("service_span", "max"),
    )

    out = tr[["GEOID", "area_km2"]].merge(agg, on="GEOID", how="left")
    out[["n_stops", "mean_frequency", "service_span"]] = out[
        ["n_stops", "mean_frequency", "service_span"]
    ].fillna(0)
    out["stop_density"] = out["n_stops"] / out["area_km2"].replace(0, np.nan)

    # Normalize the three components and average.
    d = minmax_normalize(out["stop_density"])
    f = minmax_normalize(out["mean_frequency"])
    s = minmax_normalize(out["service_span"])
    out["transit_score"] = pd.concat([d, f, s], axis=1).mean(axis=1)
    return out[
        ["GEOID", "stop_density", "mean_frequency", "service_span", "transit_score"]
    ]
