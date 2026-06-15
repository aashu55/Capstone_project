"""
Assemble the four sub-indices into the composite MES GeoJSON for each city.

Reads the per-city sub-index CSVs produced by `build_subindices.py`, computes
the MES and desert flags (`mes_builder.compute_mes`), joins tract geometry and
demographics, and writes `data/processed/mes_scores/{city}_mes.geojson` plus a
summary-statistics CSV for the Chapter 4 tables.

Demographics come from the Census ACS when CENSUS_API_KEY is set and the
per-city CSV exists; otherwise a clearly-labelled spatial PLACEHOLDER is
generated so the dashboard and equity analysis are runnable end-to-end.

Run:
    python -m src.processing.build_mes            # all cities
    python -m src.processing.build_mes chicago    # one city
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from src.config import (CITIES, CRS_PROJECTED, MES_DIR, OUTPUTS_DIR,
                        PROCESSED_DIR, SUB_INDEX_DIR, TIGER_DIR)
from src.processing.mes_builder import compute_mes, mes_summary


def _load_subindex(kind: str, city_key: str) -> pd.DataFrame:
    df = pd.read_csv(SUB_INDEX_DIR / f"{kind}_{city_key}.csv", dtype={"GEOID": str})
    df["GEOID"] = df["GEOID"].str.zfill(11)
    return df


def make_placeholder_demographics(tracts: gpd.GeoDataFrame, seed: int = 7) -> pd.DataFrame:
    """Spatial PLACEHOLDER demographics (NOT real ACS values).

    Generates median income, % non-white, % zero-vehicle, % renter with a mild
    distance-to-centre gradient and reproducible noise, so the equity-analysis
    code path is exercised with realistic-looking inputs. Replace by running
    `python -m src.data_collection.fetch_census` once CENSUS_API_KEY is set.
    """
    tr = tracts.to_crs(CRS_PROJECTED)
    cent = tr.geometry.centroid
    core = cent.union_all().centroid
    d = cent.distance(core)
    d = (d - d.min()) / (d.max() - d.min())          # 0 = central, 1 = peripheral
    rng = np.random.default_rng(seed)
    n = len(tr)
    return pd.DataFrame({
        "GEOID": tracts["GEOID"].astype(str).str.zfill(11).values,
        "total_population": (rng.normal(4000, 1200, n)).clip(500).round().astype(int),
        # central tracts: lower income, more renters, more non-white (synthetic)
        "median_income": (35000 + 70000 * d + rng.normal(0, 12000, n)).clip(15000),
        "pct_nonwhite": (75 - 45 * d + rng.normal(0, 12, n)).clip(2, 99),
        "pct_no_vehicle": (35 - 28 * d + rng.normal(0, 6, n)).clip(0, 80),
        "pct_renter": (70 - 45 * d + rng.normal(0, 10, n)).clip(5, 98),
        "demo_placeholder": 1,   # marker so this is never mistaken for real ACS data
    })


def load_demographics(city_key: str, tracts: gpd.GeoDataFrame) -> tuple[pd.DataFrame, bool]:
    """Return (demographics, is_real). Real ACS data (from fetch_census) has no
    `demo_placeholder` column; the generated placeholder is flagged and written
    to a separate file so it can never overwrite or masquerade as real data."""
    real_path = PROCESSED_DIR / f"demographics_{city_key}.csv"
    if real_path.exists():
        df = pd.read_csv(real_path, dtype={"GEOID": str})
        df["GEOID"] = df["GEOID"].str.zfill(11)
        if "demo_placeholder" not in df.columns:
            return df, True
    # No real data — (re)generate the labelled placeholder.
    demo = make_placeholder_demographics(tracts)
    demo.to_csv(PROCESSED_DIR / f"demographics_{city_key}_PLACEHOLDER.csv", index=False)
    return demo, False


def build_city_mes(city_key: str) -> dict:
    cfg = CITIES[city_key]
    print(f"\n=== {cfg['name']} MES ===")
    tracts = gpd.read_file(TIGER_DIR / f"{city_key}_tracts.geojson")[["GEOID", "NAMELSAD", "geometry"]]
    tracts["GEOID"] = tracts["GEOID"].astype(str).str.zfill(11)

    transit = _load_subindex("transit", city_key)
    walk = _load_subindex("walk", city_key)
    bike = _load_subindex("bike", city_key)
    ev = _load_subindex("ev", city_key)

    mes = compute_mes(transit, walk, bike, ev)
    demo, demo_real = load_demographics(city_key, tracts)

    gdf = tracts.merge(mes, on="GEOID", how="inner").merge(demo, on="GEOID", how="left")
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=tracts.crs)

    out = MES_DIR / f"{city_key}_mes.geojson"
    gdf.to_file(out, driver="GeoJSON")

    summ = mes_summary(gdf)
    print(f"  tracts={summ['n_tracts']} meanMES={summ['mean']:.1f} "
          f"deserts={summ['pct_mobility_desert']:.1f}% "
          f"compounded={summ['pct_compounded_desert']:.1f}% "
          f"(demographics={'real' if demo_real else 'PLACEHOLDER'})")
    return {"city": cfg["name"], **summ, "demographics_real": demo_real}


def main(cities: list[str] | None = None) -> None:
    rows = [build_city_mes(k) for k in (cities or list(CITIES))]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUTS_DIR / "mes_summary_by_city.csv", index=False)
    print(f"\nWrote summary -> {OUTPUTS_DIR / 'mes_summary_by_city.csv'}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
