"""
Index validity via inter-sub-index correlation.

The four sub-indices are treated as *complementary formative components* of a
composite, not as repeated reflective measures of a single latent construct.
The appropriate validity evidence is therefore that the sub-indices are
positively but only moderately correlated --- related enough to form a coherent
composite, yet distinct enough that each contributes non-redundant information.
Cronbach's alpha (a reliability statistic for reflective scales) is deliberately
NOT used as the validity argument here (Chapter 3/4).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np

SUB_COLS = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]


def subindex_correlation(gdf: gpd.GeoDataFrame, cols=None):
    """Pearson correlation matrix among the four normalized sub-indices."""
    cols = cols or SUB_COLS
    return gdf[cols].apply(lambda c: c.astype(float)).corr()


def validity_summary(gdf: gpd.GeoDataFrame, cols=None) -> dict:
    """Mean / min / max off-diagonal inter-sub-index correlation.

    Interpretation: values in a moderate band (roughly 0.2--0.7) support
    'related but non-redundant'; near 1.0 would signal redundancy, near 0 would
    signal the components share no coherent gradient.
    """
    cols = cols or SUB_COLS
    corr = subindex_correlation(gdf, cols).values
    iu = np.triu_indices(len(cols), k=1)
    off = corr[iu]
    return {
        "mean_inter_index_r": float(off.mean()),
        "min_inter_index_r": float(off.min()),
        "max_inter_index_r": float(off.max()),
    }
