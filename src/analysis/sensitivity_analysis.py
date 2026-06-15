"""
Mobility-desert threshold sensitivity.

The baseline flags the bottom 25% of tracts as mobility deserts. §3.7 tests
whether the set of flagged tracts — and their demographic profile — is stable
when the cut-off moves to the 20th and 30th percentiles. High overlap (Jaccard
close to 1) means the desert classification is not an artefact of the arbitrary
25% choice.
"""
from __future__ import annotations

import pandas as pd

from src.config import DESERT_SENSITIVITY


def jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets of GEOIDs."""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def desert_sets(mes_df: pd.DataFrame, thresholds=DESERT_SENSITIVITY) -> dict[float, set]:
    """GEOIDs flagged as deserts at each threshold percentile."""
    out: dict[float, set] = {}
    for p in thresholds:
        cut = mes_df["MES"].quantile(p)
        out[p] = set(mes_df.loc[mes_df["MES"] < cut, "GEOID"])
    return out


def threshold_sensitivity(
    mes_df: pd.DataFrame,
    demo_df: pd.DataFrame | None = None,
    thresholds=DESERT_SENSITIVITY,
    baseline: float = 0.25,
) -> pd.DataFrame:
    """Compare desert classifications across thresholds.

    Returns one row per threshold with: percentile, n_deserts, % of tracts,
    Jaccard overlap with the baseline (25%) set, and — if `demo_df` is given —
    the mean median-income and mean percent-non-white of flagged tracts (to
    show the demographic profile is stable).
    """
    sets = desert_sets(mes_df, sorted(set(thresholds) | {baseline}))
    base = sets[baseline]

    demo = None
    if demo_df is not None:
        demo = demo_df.copy()
        demo["GEOID"] = demo["GEOID"].astype(str).str.zfill(11)
        demo = demo.set_index("GEOID")

    rows = []
    for p in thresholds:
        flagged = sets[p]
        row = {
            "percentile": p,
            "n_deserts": len(flagged),
            "pct_of_tracts": 100.0 * len(flagged) / len(mes_df),
            "jaccard_vs_baseline": jaccard(flagged, base),
        }
        if demo is not None:
            ids = [g for g in flagged if g in demo.index]
            if "median_income" in demo.columns:
                row["mean_median_income"] = float(demo.loc[ids, "median_income"].mean())
            if "pct_nonwhite" in demo.columns:
                row["mean_pct_nonwhite"] = float(demo.loc[ids, "pct_nonwhite"].mean())
        rows.append(row)
    return pd.DataFrame(rows)
