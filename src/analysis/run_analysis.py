"""
Run the full statistical analysis suite and write outputs for the report.

Loads each city's MES GeoJSON and produces, under data/outputs/:
  * equity_correlations_{city}.csv  — Pearson r, p, 95% CI vs demographics
  * morans_i.csv                    — global Moran's I per city
  * clustering_{city}.csv           — cluster metrics; cluster_typology.csv
  * desert_sensitivity_{city}.csv   — 20/25/30th-percentile threshold test
  * weighting_sensitivity_{city}.csv — equal/entropy/PCA/AHP correlation deltas
  * figures: choropleths (MES + 4 sub-indices), elbow/silhouette, equity gap,
    correlation heatmap, LISA cold-spot map.

Run:
    python -m src.analysis.run_analysis
"""
from __future__ import annotations

import sys
import warnings

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from src.analysis.clustering import label_clusters, run_clustering  # noqa: E402
from src.analysis.equity_correlation import (correlation_matrix,  # noqa: E402
                                             run_equity_correlations)
from src.analysis.sensitivity_analysis import threshold_sensitivity  # noqa: E402
from src.analysis.spatial_autocorrelation import (compute_local_morans,  # noqa: E402
                                                  compute_morans_i)
from src.analysis.weighting_methods import compare_weighting_schemes  # noqa: E402
from src.config import CITIES, MES_DIR, OUTPUTS_DIR  # noqa: E402

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")
FIG_DIR = OUTPUTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

SUB_COLS = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]
SUB_TITLES = {"MES": "Mobility Equity Score", "transit_norm": "Transit",
              "walk_norm": "Walkability", "bike_norm": "Bicycle", "ev_norm": "EV Charging"}


def _load(city_key: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(MES_DIR / f"{city_key}_mes.geojson")
    gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11)
    return gdf


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def choropleth_png(gdf: gpd.GeoDataFrame, city: str) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(24, 5))
    for ax, col in zip(axes, ["MES"] + SUB_COLS):
        gdf.plot(column=col, cmap="RdYlGn", linewidth=0.05, edgecolor="grey",
                 legend=True, ax=ax, vmin=0, vmax=100,
                 legend_kwds={"shrink": 0.6})
        ax.set_title(f"{CITIES[city]['name']} — {SUB_TITLES[col]}")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"choropleth_{city}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def elbow_silhouette_png(metrics: dict, city: str) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.plot(metrics["k_range"], metrics["inertias"], "o-")
    a1.set(xlabel="k", ylabel="Inertia", title=f"{CITIES[city]['name']} — Elbow")
    a2.plot(metrics["k_range"], metrics["sil_scores"], "o-", color="darkorange")
    a2.axvline(metrics["k"], ls="--", color="grey")
    a2.set(xlabel="k", ylabel="Silhouette", title=f"Silhouette (best k={metrics['k']})")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"clustering_{city}.png", dpi=150)
    plt.close(fig)


def corr_heatmap_png(gdf: gpd.GeoDataFrame, city: str) -> None:
    cols = ["MES"] + SUB_COLS + ["median_income", "pct_nonwhite",
                                 "pct_no_vehicle", "pct_renter"]
    cols = [c for c in cols if c in gdf.columns]
    cm = correlation_matrix(gdf, cols)
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="vlag", center=0, ax=ax,
                cbar_kws={"shrink": 0.7})
    ax.set_title(f"{CITIES[city]['name']} — correlation matrix")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"corr_heatmap_{city}.png", dpi=150)
    plt.close(fig)


def lisa_png(lisa_gdf: gpd.GeoDataFrame, city: str) -> None:
    colors = {"HH": "#d7191c", "LL": "#2c7bb6", "HL": "#fdae61",
              "LH": "#abd9e9", "ns": "#dddddd"}
    fig, ax = plt.subplots(figsize=(7, 7))
    for cl, c in colors.items():
        sub = lisa_gdf[lisa_gdf["lisa_cluster"] == cl]
        if len(sub):
            sub.plot(ax=ax, color=c, linewidth=0.1, edgecolor="white",
                     label=f"{cl} (n={len(sub)})")
    ax.legend(title="LISA cluster", loc="lower left", fontsize=8)
    ax.set_title(f"{CITIES[city]['name']} — MES spatial clusters (LISA)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"lisa_{city}.png", dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Per-city analysis
# --------------------------------------------------------------------------- #
def analyze_city(city_key: str, morans_rows: list) -> None:
    name = CITIES[city_key]["name"]
    print(f"\n=== Analysis: {name} ===")
    gdf = _load(city_key)
    demo_cols = ["GEOID", "median_income", "pct_nonwhite", "pct_no_vehicle", "pct_renter"]
    demo = gdf[[c for c in demo_cols if c in gdf.columns]].copy()

    # 1. Equity correlations
    corr = run_equity_correlations(gdf, demo)
    corr.to_csv(OUTPUTS_DIR / f"equity_correlations_{city_key}.csv", index=False)
    print("  equity correlations:\n", corr.round(3).to_string(index=False))

    # 2. Global Moran's I
    mi = compute_morans_i(gdf, "MES")
    morans_rows.append({"city": name, **mi})
    print(f"  Moran's I = {mi['I']:.3f} (p={mi['p_value']:.3f})")

    # 3. Local Moran's I (LISA) map
    lisa = compute_local_morans(gdf, "MES")
    lisa_png(lisa, city_key)

    # 4. Clustering
    clustered, metrics = run_clustering(gdf)
    names = label_clusters(metrics["centroids"])
    typ = metrics["centroids"].round(1)
    typ["cluster"] = typ.index
    typ["label"] = typ["cluster"].map(names)
    typ["n_tracts"] = typ["cluster"].map(clustered["cluster"].value_counts())
    typ.to_csv(OUTPUTS_DIR / f"cluster_typology_{city_key}.csv", index=False)
    elbow_silhouette_png(metrics, city_key)
    print(f"  clusters: k={metrics['k']} silhouette={metrics['silhouette']:.3f}")

    # 5. Desert threshold sensitivity
    sens = threshold_sensitivity(gdf, demo)
    sens.to_csv(OUTPUTS_DIR / f"desert_sensitivity_{city_key}.csv", index=False)

    # 6. Weighting sensitivity
    schemes = compare_weighting_schemes(gdf, demo)
    rows = []
    for scheme, res in schemes.items():
        for _, r in res["correlations"].iterrows():
            rows.append({"scheme": scheme, **r.to_dict()})
    pd.DataFrame(rows).to_csv(OUTPUTS_DIR / f"weighting_sensitivity_{city_key}.csv", index=False)

    # 7. Figures
    choropleth_png(gdf, city_key)
    corr_heatmap_png(gdf, city_key)


def main(cities: list[str] | None = None) -> None:
    morans_rows: list[dict] = []
    for key in (cities or list(CITIES)):
        analyze_city(key, morans_rows)
    pd.DataFrame(morans_rows).to_csv(OUTPUTS_DIR / "morans_i.csv", index=False)
    print(f"\nAll outputs written to {OUTPUTS_DIR}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
