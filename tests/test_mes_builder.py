"""Tests for MES construction and desert flagging."""
import numpy as np
import pandas as pd
import pytest

from src.processing.mes_builder import (apply_weights_and_flags, compute_mes,
                                        merge_sub_indices, mes_summary)


def _frames(n=20, seed=0):
    rng = np.random.default_rng(seed)
    geoids = [f"{17031000000 + i:011d}" for i in range(n)]
    mk = lambda col: pd.DataFrame({"GEOID": geoids, col: rng.uniform(0, 100, n)})
    return (mk("transit_score"), mk("walk_score"), mk("bike_score"), mk("ev_score"))


def test_merge_aligns_on_geoid():
    t, w, b, e = _frames()
    merged = merge_sub_indices(t, w, b, e)
    assert len(merged) == 20
    assert set(merged.columns) >= {"GEOID", "transit_score", "walk_score",
                                   "bike_score", "ev_score"}


def test_compute_mes_range_and_flags():
    t, w, b, e = _frames()
    df = compute_mes(t, w, b, e)
    assert df["MES"].between(0, 100).all()
    # bottom quartile flagged as deserts -> roughly 25%
    assert 0 < df["mobility_desert"].mean() <= 0.35
    assert df["compounded_desert"].dtype == bool
    assert df["desert_count"].between(0, 4).all()


def test_equal_weights_is_mean_of_norms():
    t, w, b, e = _frames()
    df = compute_mes(t, w, b, e)
    expected = df[["transit_norm", "walk_norm", "bike_norm", "ev_norm"]].mean(axis=1)
    assert np.allclose(df["MES"], expected)


def test_weights_must_sum_to_one():
    t, w, b, e = _frames()
    with pytest.raises(ValueError):
        compute_mes(t, w, b, e, weights={"transit": 0.5, "walk": 0.5,
                                         "bike": 0.5, "ev": 0.5})


def test_reweighting_changes_mes():
    t, w, b, e = _frames()
    base = compute_mes(t, w, b, e)
    skew = apply_weights_and_flags(base, {"transit": 0.7, "walk": 0.1,
                                          "bike": 0.1, "ev": 0.1})
    assert not np.allclose(base["MES"], skew["MES"])


def test_summary_keys():
    t, w, b, e = _frames()
    summ = mes_summary(compute_mes(t, w, b, e))
    assert {"mean", "std", "iqr", "pct_mobility_desert"} <= set(summ)
