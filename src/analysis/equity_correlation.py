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
    method: str = "pearson",
) -> pd.DataFrame:
    """Correlation between `target` and each demographic variable.

    `method` is 'pearson' (linear; the primary analysis) or 'spearman' (rank;
    a monotonic robustness check). Returns a tidy DataFrame: variable, r,
    p_value, ci_low, ci_high, n, method. The 95% CI uses the Fisher
    z-transformation (an accepted approximation for Spearman's rho as well).
    """
    demo_vars = demo_vars or DEMOGRAPHIC_VARS
    corr_fn = {"pearson": stats.pearsonr, "spearman": stats.spearmanr}[method]
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
                                ci_low=np.nan, ci_high=np.nan, n=n, method=method))
            continue
        r, p = corr_fn(pair[target], pair[var])
        lo, hi = fisher_ci(r, n)
        results.append(dict(variable=var, r=r, p_value=p, ci_low=lo, ci_high=hi,
                            n=n, method=method))

    return pd.DataFrame(results)


def internal_consistency(df: pd.DataFrame, cols: list[str]) -> dict:
    """Inter-index structure of a composite's components.

    Reports the mean pairwise (Pearson) inter-index correlation and Cronbach's
    alpha. For a *formative* index of intentionally distinct dimensions (transit,
    walk, bike, EV), a LOW alpha / low mean correlation is expected and desirable
    --- it shows the sub-indices capture complementary, non-redundant information
    rather than measuring one underlying construct.
    """
    X = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    k = len(cols)
    corr = X.corr()
    iu = np.triu_indices(k, k=1)
    mean_inter_r = float(corr.values[iu].mean())
    item_var = X.var(ddof=1).sum()
    total_var = X.sum(axis=1).var(ddof=1)
    alpha = float((k / (k - 1)) * (1 - item_var / total_var))
    return {"mean_inter_index_r": mean_inter_r, "cronbach_alpha": alpha, "n": len(X)}


def correlation_matrix(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Pearson correlation matrix among the given columns (for heatmaps)."""
    return df[cols].apply(pd.to_numeric, errors="coerce").corr()
