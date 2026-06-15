"""
Equity correlation analysis.

Computes Pearson correlations between the Mobility Equity Score (and each
sub-index) and tract demographic variables, with two-sided p-values and 95%
confidence intervals from the Fisher z-transformation (methodology §3.8).

A negative correlation between MES and, say, percent non-white indicates that
more-disadvantaged neighborhoods receive *less* mobility infrastructure — the
core equity question of the study.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DEMOGRAPHIC_VARS = [
    "median_income",
    "pct_nonwhite",
    "pct_no_vehicle",
    "pct_renter",
]


def fisher_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% CI for a Pearson r via the Fisher z-transformation."""
    if n < 4 or abs(r) >= 1.0:
        return (np.nan, np.nan)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    crit = stats.norm.ppf(1 - alpha / 2)
    return float(np.tanh(z - crit * se)), float(np.tanh(z + crit * se))


def run_equity_correlations(
    mes_df: pd.DataFrame,
    demo_df: pd.DataFrame,
    target: str = "MES",
    demo_vars: list[str] | None = None,
) -> pd.DataFrame:
    """Pearson r between `target` and each demographic variable.

    Returns a tidy DataFrame: variable, r, p_value, ci_low, ci_high, n.
    """
    demo_vars = demo_vars or DEMOGRAPHIC_VARS
    # Reduce the left frame to GEOID + target so demographic columns that may
    # already live in mes_df don't collide with demo_df on the merge.
    left = mes_df[["GEOID", target]].copy()
    right = demo_df.copy()
    for frame in (left, right):
        frame["GEOID"] = frame["GEOID"].astype(str).str.zfill(11)
    df = left.merge(right, on="GEOID", how="inner")

    results = []
    for var in demo_vars:
        if var not in df.columns:
            continue
        pair = df[[target, var]].apply(pd.to_numeric, errors="coerce").dropna()
        n = len(pair)
        if n < 4:
            results.append(dict(variable=var, r=np.nan, p_value=np.nan,
                                ci_low=np.nan, ci_high=np.nan, n=n))
            continue
        r, p = stats.pearsonr(pair[target], pair[var])
        lo, hi = fisher_ci(r, n)
        results.append(dict(variable=var, r=r, p_value=p, ci_low=lo, ci_high=hi, n=n))

    return pd.DataFrame(results)


def correlation_matrix(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Pearson correlation matrix among the given columns (for heatmaps)."""
    return df[cols].apply(pd.to_numeric, errors="coerce").corr()
