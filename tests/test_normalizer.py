"""Tests for the normalization utilities."""
import numpy as np
import pandas as pd

from src.processing.normalizer import (minmax_normalize, normalize_columns,
                                       percentile_normalize)


def test_minmax_basic_range():
    s = pd.Series([0, 5, 10])
    out = minmax_normalize(s)
    assert out.min() == 0
    assert out.max() == 100
    assert out.iloc[1] == 50


def test_minmax_constant_series_returns_midpoint():
    s = pd.Series([7, 7, 7])
    out = minmax_normalize(s)
    assert (out == 50).all()


def test_minmax_preserves_nan():
    s = pd.Series([1.0, np.nan, 3.0])
    out = minmax_normalize(s)
    assert out.isna().sum() == 1
    assert out.iloc[0] == 0
    assert out.iloc[2] == 100


def test_percentile_monotonic():
    s = pd.Series([10, 20, 30, 40])
    out = percentile_normalize(s)
    assert out.is_monotonic_increasing


def test_normalize_columns_adds_suffix():
    df = pd.DataFrame({"a": [0, 1, 2], "b": [10, 10, 10]})
    out = normalize_columns(df, ["a", "b"])
    assert "a_norm" in out.columns and "b_norm" in out.columns
    assert out["a_norm"].max() == 100
