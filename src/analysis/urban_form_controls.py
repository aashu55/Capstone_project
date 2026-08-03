"""
Multivariable control for urban form.

The bivariate MES--income association is confounded by urban form: dense,
central tracts tend to be both lower-income and better supplied with mobility
infrastructure. This module adds two urban-form controls --- population density
and distance to the central business district (CBD) --- and refits the MES on
income with and without them, so the report can show how much of the raw
income association is accounted for by urban form (methodology §3, Chapter 4).

All relationships are associational, never causal.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import statsmodels.api as sm

from src.config import CRS_PROJECTED

# Approximate CBD coordinates (lat, lon) for each study city.
CBD = {
    "chicago": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "seattle": (47.6062, -122.3321),
}


def add_urban_form(gdf: gpd.GeoDataFrame, city: str) -> gpd.GeoDataFrame:
    """Add `pop_density` (per km^2) and `dist_cbd_km` columns.

    Density uses the tract's geometric land area (EPSG:5070); distance is the
    projected centroid-to-CBD distance in kilometres.
    """
    g = gdf.copy()
    proj = g.to_crs(CRS_PROJECTED)
    area_km2 = proj.geometry.area / 1e6
    g["pop_density"] = g["total_population"] / area_km2.replace(0, np.nan)

    cbd = gpd.GeoSeries(
        gpd.points_from_xy([CBD[city][1]], [CBD[city][0]]), crs="EPSG:4326"
    ).to_crs(CRS_PROJECTED).iloc[0]
    g["dist_cbd_km"] = proj.geometry.centroid.distance(cbd) / 1000.0
    return g


def multivariable_ols(gdf: gpd.GeoDataFrame,
                      controls=("pop_density", "dist_cbd_km")) -> dict:
    """Refit MES ~ income, then MES ~ income + urban-form controls.

    Returns both fitted models and the income coefficient before/after controls
    so the attenuation is explicit.
    """
    cols = ["MES", "median_income", *controls]
    d = gdf[cols].apply(lambda c: c.astype(float)).dropna()

    base = sm.OLS(d["MES"], sm.add_constant(d[["median_income"]])).fit()
    full = sm.OLS(d["MES"], sm.add_constant(d[["median_income", *controls]])).fit()
    return {
        "n": int(len(d)),
        "income_coef_raw": float(base.params["median_income"]),
        "income_p_raw": float(base.pvalues["median_income"]),
        "income_coef_controlled": float(full.params["median_income"]),
        "income_p_controlled": float(full.pvalues["median_income"]),
        "r2_raw": float(base.rsquared),
        "r2_controlled": float(full.rsquared),
        "base_model": base,
        "full_model": full,
    }
