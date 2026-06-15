"""
Spatial autocorrelation (Moran's I).

Tests whether MES scores cluster in space — i.e. whether well-served and
under-served tracts form contiguous patches rather than being randomly
scattered. Uses queen-contiguity spatial weights and the PySAL `esda` Moran
implementation (methodology §3.9). Also exposes Local Moran's I (LISA) to map
statistically significant low-low clusters ("cold spots" of mobility access).
"""
from __future__ import annotations

import warnings

import geopandas as gpd
import numpy as np

try:
    import esda
    import libpysal
except ImportError as exc:  # pragma: no cover
    raise ImportError("esda and libpysal are required for spatial autocorrelation") from exc


def _queen_weights(gdf: gpd.GeoDataFrame):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # silence island/disconnected-component warnings
        w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False)
    w.transform = "r"  # row-standardize
    return w


def compute_morans_i(
    gdf: gpd.GeoDataFrame, variable: str = "MES", permutations: int = 999
) -> dict:
    """Global Moran's I for `variable`.

    Returns I, the pseudo p-value, z-score, and the expected I under the null.
    Rows with missing `variable` are dropped before building the weights.
    """
    sub = gdf.dropna(subset=[variable]).copy()
    w = _queen_weights(sub)
    moran = esda.Moran(sub[variable].values, w, permutations=permutations)
    return {
        "I": float(moran.I),
        "expected_I": float(moran.EI),
        "z_score": float(moran.z_sim),
        "p_value": float(moran.p_sim),
        "n": int(len(sub)),
    }


def compute_local_morans(
    gdf: gpd.GeoDataFrame, variable: str = "MES", permutations: int = 999
) -> gpd.GeoDataFrame:
    """Local Moran's I (LISA) with cluster labels.

    Adds columns: 'lisa_I', 'lisa_p', and 'lisa_cluster' where cluster is one of
    {'HH','LL','HL','LH','ns'} (high-high, low-low, high-low, low-high, or not
    significant at p<0.05). 'LL' tracts are mobility cold spots.
    """
    sub = gdf.dropna(subset=[variable]).copy()
    w = _queen_weights(sub)
    lisa = esda.Moran_Local(sub[variable].values, w, permutations=permutations)

    labels = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    sig = lisa.p_sim < 0.05
    cluster = np.array(["ns"] * len(sub), dtype=object)
    for code, name in labels.items():
        cluster[(lisa.q == code) & sig] = name

    sub["lisa_I"] = lisa.Is
    sub["lisa_p"] = lisa.p_sim
    sub["lisa_cluster"] = cluster
    return sub
