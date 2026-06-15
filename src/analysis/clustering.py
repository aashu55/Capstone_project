"""
K-means cluster typology of mobility profiles.

Clusters tracts on their four normalized sub-indices to discover recurring
"mobility profiles" (e.g. transit-rich/bike-poor, uniformly under-served). The
number of clusters k is selected by maximizing the mean silhouette score across
a candidate range, with the elbow (inertia) curve reported alongside for
validation (methodology §3.10).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]


def run_clustering(
    mes_df: pd.DataFrame,
    k_range=range(2, 8),
    features: list[str] | None = None,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict]:
    """K-means with silhouette-based k selection.

    Returns
    -------
    (df, metrics) where `df` is `mes_df` with a 'cluster' column added (NaN for
    rows that had missing features) and `metrics` holds the chosen k, the
    silhouette score, and the per-k inertia / silhouette curves.
    """
    features = features or CLUSTER_FEATURES
    valid = mes_df.dropna(subset=features)
    X = StandardScaler().fit_transform(valid[features])

    k_list = list(k_range)
    inertias, sil_scores = [], []
    for k in k_list:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        inertias.append(float(km.inertia_))
        sil_scores.append(float(silhouette_score(X, labels)))

    best_k = k_list[int(np.argmax(sil_scores))]
    final = KMeans(n_clusters=best_k, random_state=random_state, n_init=10)
    valid_labels = final.fit_predict(X)

    out = mes_df.copy()
    out["cluster"] = np.nan
    out.loc[valid.index, "cluster"] = valid_labels
    out["cluster"] = out["cluster"].astype("Int64")

    metrics = {
        "k": best_k,
        "silhouette": max(sil_scores),
        "k_range": k_list,
        "inertias": inertias,
        "sil_scores": sil_scores,
        "centroids": pd.DataFrame(
            StandardScaler().fit(valid[features]).inverse_transform(final.cluster_centers_),
            columns=features,
        ),
    }
    return out, metrics


def label_clusters(centroids: pd.DataFrame, features: list[str] | None = None) -> dict[int, str]:
    """Assign a human-readable name to each cluster from its centroid profile.

    Heuristic for the Chapter 4 typology table: a cluster whose mean MES-proxy
    (row mean of the features) is in the bottom third is "Under-served"; top
    third "Well-served"; otherwise we name it by its single strongest and
    weakest sub-index (e.g. "Transit-rich, bike-poor").
    """
    features = features or CLUSTER_FEATURES
    short = {"transit_norm": "transit", "walk_norm": "walk",
             "bike_norm": "bike", "ev_norm": "EV"}
    means = centroids[features].mean(axis=1)
    lo, hi = means.quantile(1 / 3), means.quantile(2 / 3)

    names: dict[int, str] = {}
    for idx, row in centroids.iterrows():
        m = means[idx]
        if m <= lo:
            names[idx] = "Uniformly under-served"
        elif m >= hi:
            names[idx] = "Well-served / multimodal"
        else:
            strongest = short[row[features].idxmax()]
            weakest = short[row[features].idxmin()]
            names[idx] = f"{strongest.capitalize()}-rich, {weakest}-poor"
    return names
