"""
Run the advanced-validation suite (post full-draft feedback) for every city and
write results to data/outputs/. Produces:
  * urban_form_ols.csv        — income coefficient before/after urban-form controls
  * spatial_regression.csv    — spatial lag & error AIC + preferred model
  * index_validity.csv        — inter-sub-index correlation summary
  * clustering_stability.csv  — silhouette + multi-seed ARI per city
  * ev_robustness.csv         — MES vs MES-without-EV income correlations

Run:
    python -m src.analysis.run_validation
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from src.analysis.clustering_stability import cluster_with_stability
from src.analysis.ev_robustness import mes_without_ev
from src.analysis.index_validity import validity_summary
from src.analysis.spatial_regression import spatial_models
from src.analysis.urban_form_controls import add_urban_form, multivariable_ols
from src.config import CITIES, MES_DIR, OUTPUTS_DIR


def _k_for(city_key: str) -> int:
    """Silhouette-selected k from the existing cluster typology output."""
    p = OUTPUTS_DIR / f"cluster_typology_{city_key}.csv"
    return len(pd.read_csv(p)) if p.exists() else 2


def run_city(city_key: str) -> dict:
    name = CITIES[city_key]["name"]
    print(f"\n=== Validation: {name} ===")
    gdf = gpd.read_file(MES_DIR / f"{city_key}_mes.geojson")
    gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11)
    gdf = add_urban_form(gdf, city_key)

    ols = multivariable_ols(gdf)
    print(f"  income coef: raw={ols['income_coef_raw']:.4g} (p={ols['income_p_raw']:.3g}) "
          f"-> controlled={ols['income_coef_controlled']:.4g} (p={ols['income_p_controlled']:.3g})")

    sp = spatial_models(gdf)
    print(f"  spatial: lag AIC={sp['lag']['aic']:.0f}, error AIC={sp['error']['aic']:.0f} "
          f"-> prefer {sp['prefer']}; income coef ({sp['prefer']})="
          f"{sp[sp['prefer']]['coefs']['median_income']:.4g}")

    iv = validity_summary(gdf)
    print(f"  index validity: inter-index r mean={iv['mean_inter_index_r']:.3f} "
          f"[{iv['min_inter_index_r']:.2f},{iv['max_inter_index_r']:.2f}]")

    cs = cluster_with_stability(gdf, k=_k_for(city_key))
    print(f"  clustering k={cs['k']}: silhouette={cs['silhouette']}, mean ARI={cs['mean_ARI']}")

    ev = mes_without_ev(gdf)
    print(f"  EV robustness: r(MES,income)={ev['r_full_MES']:.3f} vs "
          f"r(MES_noEV,income)={ev['r_noEV_MES']:.3f} (Δ={ev['delta_r']:.3f})")

    return {
        "city": name,
        "ols_income_raw": ols["income_coef_raw"],
        "ols_income_ctrl": ols["income_coef_controlled"],
        "ols_income_p_ctrl": ols["income_p_controlled"],
        "spatial_prefer": sp["prefer"],
        "spatial_aic_lag": sp["lag"]["aic"],
        "spatial_aic_error": sp["error"]["aic"],
        "spatial_income_coef": sp[sp["prefer"]]["coefs"]["median_income"],
        "inter_index_r_mean": iv["mean_inter_index_r"],
        "cluster_k": cs["k"],
        "cluster_silhouette": cs["silhouette"],
        "cluster_mean_ARI": cs["mean_ARI"],
        "ev_r_full": ev["r_full_MES"],
        "ev_r_noEV": ev["r_noEV_MES"],
        "ev_delta_r": ev["delta_r"],
    }


def main(cities: list[str] | None = None) -> None:
    rows = [run_city(k) for k in (cities or list(CITIES))]
    df = pd.DataFrame(rows)
    out = OUTPUTS_DIR / "validation_summary.csv"
    df.to_csv(out, index=False)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
