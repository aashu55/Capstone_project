"""
Weighting methodology and sensitivity analysis.

The baseline MES weights the four sub-indices equally. Because that choice is a
value judgement, §3.6 tests three data-driven / expert alternatives and reports
how much the equity conclusions move:

  * equal   — 0.25 each (baseline)
  * entropy — objective weights from the dispersion of each sub-index
  * pca      — weights from the first principal-component loadings
  * ahp      — Analytic Hierarchy Process weights from expert pairwise judgement

`compare_weighting_schemes` recomputes the MES under every scheme and returns
each scheme's equity-correlation table so they can be laid side by side.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from src.analysis.equity_correlation import run_equity_correlations
from src.processing.mes_builder import NORM_COLS, apply_weights_and_flags

# Manually elicited AHP weights (placeholder until the expert survey is run;
# transit weighted highest, EV lowest — see §3.6).
AHP_WEIGHTS = {"transit": 0.40, "walk": 0.30, "bike": 0.15, "ev": 0.15}


def _cols_to_components(weights_by_col: dict[str, float]) -> dict[str, float]:
    """Map *_norm column weights back to the {transit,walk,bike,ev} keys."""
    mapping = {"transit_norm": "transit", "walk_norm": "walk",
               "bike_norm": "bike", "ev_norm": "ev"}
    return {mapping[c]: float(w) for c, w in weights_by_col.items()}


def entropy_weights(df: pd.DataFrame, sub_cols: list[str] | None = None) -> dict[str, float]:
    """Entropy weighting: indices that discriminate more between tracts get more weight.

    Standard entropy method: normalize each column to a probability vector,
    compute its Shannon entropy, take redundancy (1 - entropy) as the
    information content, and normalize to sum to 1.
    """
    sub_cols = sub_cols or NORM_COLS
    X = df[sub_cols].apply(pd.to_numeric, errors="coerce").dropna()
    col_sums = X.sum()
    p = X / col_sums.replace(0, np.nan)
    k = 1.0 / np.log(len(X))
    entropy = -k * (p * np.log(p + 1e-12)).sum()
    redundancy = 1 - entropy
    weights = redundancy / redundancy.sum()
    return _cols_to_components(weights.to_dict())


def pca_weights(df: pd.DataFrame, sub_cols: list[str] | None = None) -> dict[str, float]:
    """PCA weighting from the (absolute) first principal-component loadings."""
    sub_cols = sub_cols or NORM_COLS
    X = df[sub_cols].apply(pd.to_numeric, errors="coerce").dropna()
    pca = PCA(n_components=1).fit(X)
    loadings = np.abs(pca.components_[0])
    weights = loadings / loadings.sum()
    return _cols_to_components(dict(zip(sub_cols, weights)))


def all_schemes(mes_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Return the weight dict for every scheme, derived from `mes_df`."""
    return {
        "equal": {"transit": 0.25, "walk": 0.25, "bike": 0.25, "ev": 0.25},
        "entropy": entropy_weights(mes_df),
        "pca": pca_weights(mes_df),
        "ahp": dict(AHP_WEIGHTS),
    }


def compare_weighting_schemes(
    mes_df: pd.DataFrame, demo_df: pd.DataFrame
) -> dict[str, dict]:
    """Recompute MES + equity correlations under each weighting scheme.

    `mes_df` must already contain the NORM_COLS (run `compute_mes` first).
    Returns {scheme: {'weights': ..., 'correlations': DataFrame,
                      'mes': Series indexed by GEOID}}.
    """
    schemes = all_schemes(mes_df)
    results: dict[str, dict] = {}
    for name, weights in schemes.items():
        reweighted = apply_weights_and_flags(mes_df, weights)
        corr = run_equity_correlations(reweighted, demo_df)
        results[name] = {
            "weights": weights,
            "correlations": corr,
            "mes": reweighted.set_index("GEOID")["MES"],
        }
    return results
