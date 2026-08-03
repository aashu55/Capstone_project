"""
Spatial regression (spatial lag and spatial error models).

Because the MES is strongly spatially autocorrelated (global Moran's I ~ 0.9),
tracts are not independent observations and ordinary-least-squares / Pearson
significance is overstated. This module fits a spatial-lag (ML_Lag) and a
spatial-error (ML_Error) model of the MES on socioeconomic and urban-form
predictors, and reports which fits better by AIC. The relationships remain
associational; spatial regression only corrects the inference for spatial
dependence (Chapter 4).
"""
from __future__ import annotations

import warnings

import geopandas as gpd
import numpy as np
from libpysal.weights import Queen
from spreg import ML_Error, ML_Lag

DEFAULT_X = ("median_income", "pct_renter", "pct_no_vehicle",
             "pop_density", "dist_cbd_km")


def spatial_models(gdf: gpd.GeoDataFrame, xcols=DEFAULT_X) -> dict:
    """Fit spatial-lag and spatial-error models of MES ~ xcols.

    Rows with any missing value are dropped and the queen-contiguity weights are
    rebuilt on the retained subset so `w` and the data align.
    """
    cols = ["MES", *xcols]
    sub = gdf.dropna(subset=cols).reset_index(drop=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = Queen.from_dataframe(sub, use_index=False)
        w.transform = "r"

    y = sub[["MES"]].values
    X = sub[list(xcols)].values
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lag = ML_Lag(y, X, w=w, name_y="MES", name_x=list(xcols))
        err = ML_Error(y, X, w=w, name_y="MES", name_x=list(xcols))

    def _coefs(model):
        # betas: [CONSTANT, x1..xk, (rho/lambda)]; name_x aligns to x1..xk
        names = ["CONSTANT", *xcols]
        vals = [float(b) for b in model.betas.flatten()[: len(names)]]
        return dict(zip(names, vals))

    return {
        "n": int(len(sub)),
        "lag": {"aic": float(lag.aic), "coefs": _coefs(lag),
                "rho": float(lag.rho)},
        "error": {"aic": float(err.aic), "coefs": _coefs(err),
                  "lambda": float(err.lam)},
        "prefer": "lag" if lag.aic < err.aic else "error",
        "_lag_model": lag, "_err_model": err,
    }
