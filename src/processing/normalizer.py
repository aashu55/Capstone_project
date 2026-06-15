"""
Normalization utilities for the Mobility Equity Score.

All sub-indices are placed on a common 0–100 scale before being combined, so
that a tract's transit score and its EV score are directly comparable. We use
min–max normalization as the baseline (documented in methodology §3.5) and also
provide a robust percentile-rank variant for sensitivity checks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def minmax_normalize(series: pd.Series, out_min: float = 0.0, out_max: float = 100.0) -> pd.Series:
    """Linearly rescale a series to [out_min, out_max].

    x_norm = (x - x_min) / (x_max - x_min) * (out_max - out_min) + out_min

    A constant series (x_max == x_min) maps to the midpoint of the output range
    rather than producing NaN/inf, which keeps degenerate sub-indices usable.
    NaNs are preserved (not imputed) so missingness stays visible downstream.
    """
    s = pd.to_numeric(series, errors="coerce")
    x_min, x_max = s.min(), s.max()
    if pd.isna(x_min) or pd.isna(x_max) or x_max == x_min:
        midpoint = (out_min + out_max) / 2.0
        return pd.Series(np.where(s.isna(), np.nan, midpoint), index=s.index)
    scaled = (s - x_min) / (x_max - x_min)
    return scaled * (out_max - out_min) + out_min


def percentile_normalize(series: pd.Series, out_min: float = 0.0, out_max: float = 100.0) -> pd.Series:
    """Rank-based normalization, robust to outliers.

    Each value is mapped to its empirical percentile, then rescaled to the
    output range. Used to test whether MES patterns are driven by a few
    extreme tracts (sensitivity analysis).
    """
    s = pd.to_numeric(series, errors="coerce")
    ranks = s.rank(method="average", pct=True)
    return ranks * (out_max - out_min) + out_min


def normalize_columns(
    df: pd.DataFrame,
    columns: list[str],
    method: str = "minmax",
    suffix: str = "_norm",
) -> pd.DataFrame:
    """Return a copy of `df` with normalized versions of `columns` added.

    The new columns are named `<column><suffix>`. `method` is 'minmax' or
    'percentile'.
    """
    fn = {"minmax": minmax_normalize, "percentile": percentile_normalize}[method]
    out = df.copy()
    for col in columns:
        out[f"{col}{suffix}"] = fn(out[col])
    return out
