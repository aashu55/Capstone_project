"""
Mobility Equity Score (MES) construction.

Merges the four sub-indices (transit, walkability, bicycle, EV charging) on the
Census tract GEOID, normalizes each to 0–100, and computes a weighted composite
MES. Tracts in the bottom quartile of MES are flagged as *mobility deserts*; a
tract that falls in the bottom quartile of two or more sub-indices is flagged as
a *compounded desert* (methodology §3.5 and §3.7).
"""
from __future__ import annotations

import pandas as pd

from src.config import DEFAULT_WEIGHTS, DESERT_PERCENTILE
from src.processing.normalizer import minmax_normalize

SUB_SCORE_COLS = {
    "transit": "transit_score",
    "walk": "walk_score",
    "bike": "bike_score",
    "ev": "ev_score",
}
NORM_COLS = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]


def _validate_weights(weights: dict[str, float]) -> dict[str, float]:
    missing = set(DEFAULT_WEIGHTS) - set(weights)
    if missing:
        raise ValueError(f"weights missing keys: {sorted(missing)}")
    total = sum(weights[k] for k in DEFAULT_WEIGHTS)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0, got {total:.4f}")
    return weights


def merge_sub_indices(
    transit_df: pd.DataFrame,
    walk_df: pd.DataFrame,
    bike_df: pd.DataFrame,
    ev_df: pd.DataFrame,
) -> pd.DataFrame:
    """Inner-merge the four sub-index frames on GEOID.

    Each input frame must contain a 'GEOID' column and its `*_score` column.
    GEOID is coerced to a zero-padded string so joins are exact.
    """
    frames = {"transit": transit_df, "walk": walk_df, "bike": bike_df, "ev": ev_df}
    merged: pd.DataFrame | None = None
    for key, frame in frames.items():
        score_col = SUB_SCORE_COLS[key]
        if "GEOID" not in frame.columns or score_col not in frame.columns:
            raise ValueError(f"{key} frame needs columns ['GEOID', '{score_col}']")
        sub = frame[["GEOID", score_col]].copy()
        sub["GEOID"] = sub["GEOID"].astype(str).str.zfill(11)
        merged = sub if merged is None else merged.merge(sub, on="GEOID", how="inner")
    return merged


def compute_mes(
    transit_df: pd.DataFrame,
    walk_df: pd.DataFrame,
    bike_df: pd.DataFrame,
    ev_df: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Combine sub-indices into the composite MES.

    Parameters
    ----------
    *_df : DataFrames with 'GEOID' and the relevant `*_score` column.
    weights : dict with keys ['transit','walk','bike','ev'] summing to 1.0.
              Defaults to equal weighting (0.25 each).

    Returns
    -------
    DataFrame with normalized sub-indices, the MES, and desert flags.
    """
    weights = _validate_weights(weights or dict(DEFAULT_WEIGHTS))
    df = merge_sub_indices(transit_df, walk_df, bike_df, ev_df)

    # Normalize each raw sub-score to 0–100.
    df["transit_norm"] = minmax_normalize(df["transit_score"])
    df["walk_norm"] = minmax_normalize(df["walk_score"])
    df["bike_norm"] = minmax_normalize(df["bike_score"])
    df["ev_norm"] = minmax_normalize(df["ev_score"])

    return apply_weights_and_flags(df, weights)


def apply_weights_and_flags(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """Given a frame that already has NORM_COLS, compute MES and desert flags.

    Separated from `compute_mes` so the weighting-sensitivity analysis can
    re-weight an already-normalized frame without recomputing sub-indices.
    """
    weights = _validate_weights(weights)
    out = df.copy()
    out["MES"] = (
        out["transit_norm"] * weights["transit"]
        + out["walk_norm"] * weights["walk"]
        + out["bike_norm"] * weights["bike"]
        + out["ev_norm"] * weights["ev"]
    )

    # Mobility desert: bottom-quartile MES.
    p_cut = out["MES"].quantile(DESERT_PERCENTILE)
    out["mobility_desert"] = out["MES"] < p_cut

    # Compounded desert: bottom-quartile in >= 2 sub-indices.
    sub_cuts = out[NORM_COLS].quantile(DESERT_PERCENTILE)
    out["desert_count"] = (out[NORM_COLS] < sub_cuts).sum(axis=1)
    out["compounded_desert"] = out["desert_count"] >= 2

    # City percentile rank of each tract's MES (0–100; higher = better served).
    out["MES_percentile"] = out["MES"].rank(pct=True) * 100
    return out


def mes_summary(df: pd.DataFrame) -> dict[str, float]:
    """Summary statistics for a city's MES distribution (for Chapter 4 tables)."""
    mes = df["MES"]
    return {
        "n_tracts": int(mes.notna().sum()),
        "mean": float(mes.mean()),
        "std": float(mes.std()),
        "min": float(mes.min()),
        "q25": float(mes.quantile(0.25)),
        "median": float(mes.median()),
        "q75": float(mes.quantile(0.75)),
        "max": float(mes.max()),
        "iqr": float(mes.quantile(0.75) - mes.quantile(0.25)),
        "pct_mobility_desert": float(df["mobility_desert"].mean() * 100),
        "pct_compounded_desert": float(df["compounded_desert"].mean() * 100),
    }
