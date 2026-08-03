"""
EV-robustness check: recompute the MES without the EV dimension.

The EV sub-index falls back to OpenStreetMap charging points when the
authoritative DOE/NREL AFDC API is unavailable, making it the least certain of
the four dimensions. To show the headline equity relationships are not driven by
that uncertainty, this module builds a three-dimension MES (transit, walk, bike;
equal 1/3 weights) and compares its correlation with median income against the
full four-dimension MES. Similar coefficients => conclusions are robust to the
EV data (Chapter 4).
"""
from __future__ import annotations

import geopandas as gpd
from scipy.stats import pearsonr

SUB3 = ["transit_norm", "walk_norm", "bike_norm"]


def mes_without_ev(gdf: gpd.GeoDataFrame, demo_var: str = "median_income") -> dict:
    """Compare MES--`demo_var` correlation with vs. without the EV dimension."""
    g = gdf.copy()
    g["MES_noEV"] = g[SUB3].astype(float).mean(axis=1)  # equal 1/3 weights
    for target in ("MES", "MES_noEV"):
        pass
    d = g[["MES", "MES_noEV", demo_var]].apply(lambda c: c.astype(float)).dropna()
    r_full, p_full = pearsonr(d["MES"], d[demo_var])
    r_no, p_no = pearsonr(d["MES_noEV"], d[demo_var])
    return {
        "n": int(len(d)),
        "demo_var": demo_var,
        "r_full_MES": float(r_full), "p_full_MES": float(p_full),
        "r_noEV_MES": float(r_no), "p_noEV_MES": float(p_no),
        "delta_r": float(abs(r_full - r_no)),
    }
