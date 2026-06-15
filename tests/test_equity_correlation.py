"""Tests for the equity correlation analysis."""
import numpy as np
import pandas as pd

from src.analysis.equity_correlation import fisher_ci, run_equity_correlations


def test_fisher_ci_brackets_r():
    lo, hi = fisher_ci(0.5, n=100)
    assert lo < 0.5 < hi
    assert -1 <= lo and hi <= 1


def test_fisher_ci_small_n_is_nan():
    lo, hi = fisher_ci(0.5, n=3)
    assert np.isnan(lo) and np.isnan(hi)


def test_perfect_correlation_detected():
    n = 50
    geoids = [f"{17031000000 + i:011d}" for i in range(n)]
    mes = pd.DataFrame({"GEOID": geoids, "MES": np.arange(n, dtype=float)})
    demo = pd.DataFrame({"GEOID": geoids, "median_income": np.arange(n, dtype=float)})
    res = run_equity_correlations(mes, demo, demo_vars=["median_income"])
    row = res.iloc[0]
    assert row["r"] > 0.99
    assert row["p_value"] < 0.001
    assert row["n"] == n


def test_negative_relationship():
    n = 60
    rng = np.random.default_rng(1)
    geoids = [f"{17031000000 + i:011d}" for i in range(n)]
    x = rng.uniform(0, 100, n)
    mes = pd.DataFrame({"GEOID": geoids, "MES": x})
    demo = pd.DataFrame({"GEOID": geoids, "pct_nonwhite": 100 - x + rng.normal(0, 5, n)})
    res = run_equity_correlations(mes, demo, demo_vars=["pct_nonwhite"])
    assert res.iloc[0]["r"] < -0.8
