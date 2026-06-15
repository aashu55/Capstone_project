"""
Dashboard helper functions: data loading, figure builders, text generation.

Kept separate from layout/callbacks so the plotting logic is unit-testable and
the callback module stays thin.
"""
from __future__ import annotations

import json
from functools import lru_cache

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import CITIES, MES_DIR, PROCESSED_DIR

SUB_INDEX_LABELS = {
    "transit_norm": "Transit",
    "walk_norm": "Walkability",
    "bike_norm": "Bicycle",
    "ev_norm": "EV Charging",
}
LAYER_COLUMN = {
    "MES": "MES",
    "Transit": "transit_norm",
    "Walkability": "walk_norm",
    "Bicycle": "bike_norm",
    "EV Charging": "ev_norm",
}


def available_cities() -> list[dict]:
    """Cities that have a computed MES file on disk (for the dropdown)."""
    opts = []
    for key, cfg in CITIES.items():
        if (MES_DIR / f"{key}_mes.geojson").exists():
            opts.append({"label": cfg["name"], "value": key})
    return opts


@lru_cache(maxsize=8)
def load_city(city_key: str) -> gpd.GeoDataFrame:
    """Load a city's MES GeoJSON (cached)."""
    gdf = gpd.read_file(MES_DIR / f"{city_key}_mes.geojson")
    gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11)
    return gdf


@lru_cache(maxsize=8)
def load_demographics(city_key: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"demographics_{city_key}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype={"GEOID": str})
    df["GEOID"] = df["GEOID"].str.zfill(11)
    return df


def choropleth(gdf: gpd.GeoDataFrame, layer: str, desert_only: bool = False) -> go.Figure:
    """Choropleth map of the selected layer at tract level."""
    col = LAYER_COLUMN[layer]
    data = gdf.copy()
    if desert_only and "mobility_desert" in data.columns:
        data = data[data["mobility_desert"]]

    # Simplify geometry (~50 m tolerance) so the choropleth payload stays small
    # and the dev server renders quickly even for 1,300+ tract cities.
    data = data.copy()
    data["geometry"] = data.geometry.simplify(0.0005, preserve_topology=True)
    geojson = json.loads(data.to_json())
    center = data.geometry.union_all().centroid
    fig = px.choropleth_mapbox(
        data,
        geojson=geojson,
        locations=data.index,
        color=col,
        color_continuous_scale="YlOrRd_r",   # dark red = lowest = worst served
        range_color=(0, 100),
        mapbox_style="carto-positron",
        center={"lat": center.y, "lon": center.x},
        zoom=9.5,
        opacity=0.75,
        labels={col: layer},
        hover_data={"GEOID": True, "MES": ":.1f"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar_title=layer)
    return fig


def subindex_bar(row: pd.Series, city_medians: pd.Series) -> go.Figure:
    """Horizontal grouped bars: a tract's 4 sub-indices vs the city median."""
    cols = list(SUB_INDEX_LABELS)
    labels = [SUB_INDEX_LABELS[c] for c in cols]
    fig = go.Figure()
    fig.add_bar(y=labels, x=[row[c] for c in cols], name="This tract",
                orientation="h", marker_color="#c0392b")
    fig.add_bar(y=labels, x=[city_medians[c] for c in cols], name="City median",
                orientation="h", marker_color="#7f8c8d")
    fig.update_layout(barmode="group", xaxis_range=[0, 100],
                      margin=dict(l=10, r=10, t=10, b=10), height=260,
                      legend=dict(orientation="h", y=1.15))
    return fig


def interpretation_text(row: pd.Series, threshold: float = 33.0) -> str:
    """Auto-generate a plain-language reading of which sub-indices are low."""
    low = [SUB_INDEX_LABELS[c] for c in SUB_INDEX_LABELS if row[c] < threshold]
    if not low:
        return "This tract scores at or above the citywide midpoint across all four mobility dimensions."
    if len(low) == 1:
        return f"This tract is underserved in {low[0].lower()} access."
    joined = ", ".join(low[:-1]) + f" and {low[-1]}"
    sev = "severely " if len(low) >= 3 else ""
    return f"This tract is {sev}underserved across {joined.lower()}."


def equity_gap_figure(city_keys: list[str]) -> go.Figure:
    """Median MES of the poorest vs richest income quintile, per city."""
    rows = []
    for key in city_keys:
        gdf = load_city(key)
        if "median_income" not in gdf.columns:
            continue
        merged = gdf.dropna(subset=["median_income", "MES"])
        if merged.empty:
            continue
        merged["quintile"] = pd.qcut(merged["median_income"], 5,
                                     labels=False, duplicates="drop")
        q_min, q_max = merged["quintile"].min(), merged["quintile"].max()
        rows.append({"city": CITIES[key]["name"], "group": "Poorest quintile",
                     "MES": merged.loc[merged["quintile"] == q_min, "MES"].median()})
        rows.append({"city": CITIES[key]["name"], "group": "Richest quintile",
                     "MES": merged.loc[merged["quintile"] == q_max, "MES"].median()})
    if not rows:
        return go.Figure().update_layout(
            title="Equity gap requires demographic data (set CENSUS_API_KEY)")
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="city", y="MES", color="group", barmode="group",
                 color_discrete_map={"Poorest quintile": "#c0392b",
                                     "Richest quintile": "#2980b9"},
                 labels={"MES": "Median MES", "city": ""})
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.15), yaxis_range=[0, 100])
    return fig


def ranked_table(gdf: gpd.GeoDataFrame, rank_by: str, n: int = 20) -> pd.DataFrame:
    """Top-n most disadvantaged tracts by the chosen column (ascending)."""
    col = LAYER_COLUMN.get(rank_by, "MES")
    cols = ["GEOID", "MES", "transit_norm", "walk_norm", "bike_norm", "ev_norm"]
    cols = [c for c in cols if c in gdf.columns]
    out = gdf[cols].sort_values(col).head(n).round(1)
    return out
