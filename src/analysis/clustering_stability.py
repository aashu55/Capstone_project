"""
Clustering stability check.

A single K-means run can produce clusters that are artefacts of one random
seed. This module reports the silhouette score and, crucially, the label
stability across multiple random initializations via the Adjusted Rand Index
(ARI): an ARI near 1.0 means the partition is reproducible and not seed-driven
(Chapter 4). The silhouette-selected k differs by city (Chicago & Seattle -> 2,
Houston -> 3), so cluster labels are NEVER matched mechanically across cities.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURES = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]


def cluster_with_stability(gdf: gpd.GeoDataFrame, k: int,
                           feat=None, seeds=range(5)) -> dict:
    """K-means with silhouette + multi-seed ARI stability for a given k."""
    feat = feat or FEATURES
    X = StandardScaler().fit_transform(gdf[feat].dropna())
    base = KMeans(n_clusters=k, n_init=25, random_state=42).fit(X)
    sil = silhouette_score(X, base.labels_)
    runs = [KMeans(n_clusters=k, n_init=25, random_state=s).fit_predict(X)
            for s in seeds]
    aris = [adjusted_rand_score(runs[0], r) for r in runs[1:]]
    return {
        "k": k,
        "n": int(X.shape[0]),
        "silhouette": round(float(sil), 3),
        "mean_ARI": round(float(np.mean(aris)), 3),
        "min_ARI": round(float(np.min(aris)), 3),
    }
