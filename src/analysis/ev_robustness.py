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

from src.analysis.spatial_autocorrelation import compute_morans_i
from src.config import DESERT_PERCENTILE

SUB3 = ["transit_norm", "walk_norm", "bike_norm"]
DEMO_VARS = ["median_income", "pct_renter", "pct_no_vehicle"]


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0


def mes_without_ev(gdf: gpd.GeoDataFrame, demo_var: str = "median_income") -> dict:
    """Correlation of `demo_var` with the full vs. EV-dropped MES (income only)."""
    g = gdf.copy()
    g["MES_noEV"] = g[SUB3].astype(float).mean(axis=1)
    d = g[["MES", "MES_noEV", demo_var]].apply(lambda c: c.astype(float)).dropna()
    r_full, p_full = pearsonr(d["MES"], d[demo_var])
    r_no, p_no = pearsonr(d["MES_noEV"], d[demo_var])
    return {"n": int(len(d)), "demo_var": demo_var,
            "r_full_MES": float(r_full), "r_noEV_MES": float(r_no),
            "delta_r": float(abs(r_full - r_no))}


def ev_robustness_full(gdf: gpd.GeoDataFrame) -> dict:
    """Comprehensive EV-drop robustness (professor's request).

    Recomputes a three-dimension MES (transit, walk, bike; equal 1/3 weights)
    and checks whether the income/renter/zero-vehicle associations, the
    mobility-desert set, and the spatial-clustering strength all remain, so the
    principal conclusions are shown not to depend on the least-certain (EV)
    dimension.
    """
    g = gdf.copy()
    g["MES_noEV"] = g[SUB3].astype(float).mean(axis=1)

    # (a) demographic correlations, full vs. no-EV
    corr = {}
    for v in DEMO_VARS:
        d = g[["MES", "MES_noEV", v]].apply(lambda c: c.astype(float)).dropna()
        corr[v] = {"full": float(pearsonr(d["MES"], d[v])[0]),
                   "noEV": float(pearsonr(d["MES_noEV"], d[v])[0])}
        corr[v]["delta"] = abs(corr[v]["full"] - corr[v]["noEV"])

    # (b) mobility-desert set overlap (bottom quartile)
    full_cut = g["MES"].quantile(DESERT_PERCENTILE)
    no_cut = g["MES_noEV"].quantile(DESERT_PERCENTILE)
    desert_full = set(g.loc[g["MES"] < full_cut, "GEOID"])
    desert_no = set(g.loc[g["MES_noEV"] < no_cut, "GEOID"])
    desert_jaccard = _jaccard(desert_full, desert_no)

    # (c) spatial-clustering strength, full vs. no-EV
    moran_full = compute_morans_i(g, "MES")["I"]
    moran_no = compute_morans_i(g, "MES_noEV")["I"]

    return {
        "n": int(len(g)),
        "corr": corr,
        "max_delta_r": max(c["delta"] for c in corr.values()),
        "desert_jaccard": float(desert_jaccard),
        "moran_full": float(moran_full),
        "moran_noEV": float(moran_no),
    }
