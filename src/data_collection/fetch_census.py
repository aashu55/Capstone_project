"""
Fetch ACS 5-year demographic data via the Census API (requires CENSUS_API_KEY).

Pulls the variables listed in `config.ACS_VARIABLES` for every tract in each
study county, derives the equity variables used in the correlation analysis
(percent non-white, percent zero-vehicle households, percent renter), and
writes one CSV per city.

Get a free key at https://api.census.gov/data/key_signup.html and put it in
`.env` as CENSUS_API_KEY.

Run:
    python -m src.data_collection.fetch_census
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

from src.config import (ACS_DATASET, ACS_VARIABLES, ACS_YEAR, CENSUS_API_KEY,
                        CITIES, PROCESSED_DIR)

API_BASE = f"https://api.census.gov/data/{ACS_YEAR}/{ACS_DATASET}"


def _fetch_county_tracts(state: str, county: str) -> pd.DataFrame:
    """Query all tracts in one county for the configured ACS variables."""
    get_vars = ",".join(ACS_VARIABLES.keys())
    params = {
        "get": get_vars,
        "for": "tract:*",
        "in": f"state:{state}+county:{county}",
        "key": CENSUS_API_KEY,
    }
    resp = requests.get(API_BASE, params=params, timeout=120)
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def derive_equity_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw ACS codes and compute the percent-based equity variables."""
    df = df.rename(columns=ACS_VARIABLES)
    df["GEOID"] = (df["state"] + df["county"] + df["tract"]).str.zfill(11)

    num = df.apply(lambda c: pd.to_numeric(c, errors="coerce") if c.name in
                   ACS_VARIABLES.values() else c)

    pop = num["total_population"].replace(0, pd.NA)
    occ = num["total_occupied"].replace(0, pd.NA)
    out = pd.DataFrame({"GEOID": df["GEOID"]})
    out["median_income"] = num["median_income"].where(num["median_income"] > 0)
    out["total_population"] = num["total_population"]
    out["pct_nonwhite"] = (1 - num["white_nonhispanic"] / pop) * 100
    out["pct_no_vehicle"] = (
        (num["owner_no_vehicle"] + num["renter_no_vehicle"]) / occ * 100
    )
    out["pct_renter"] = num["renter_occupied"] / occ * 100
    return out


def fetch_city_demographics(city_key: str) -> pd.DataFrame:
    cfg = CITIES[city_key]
    frames = [_fetch_county_tracts(cfg["state_fips"], c) for c in cfg["county_fips"]]
    raw = pd.concat(frames, ignore_index=True)
    demo = derive_equity_variables(raw)
    out = PROCESSED_DIR / f"demographics_{city_key}.csv"
    demo.to_csv(out, index=False)
    print(f"[{cfg['name']}] {len(demo)} tracts -> {out.name}")
    return demo


def main(cities: list[str] | None = None) -> None:
    if not CENSUS_API_KEY:
        raise SystemExit(
            "CENSUS_API_KEY not set. Copy .env.example to .env and add your key "
            "(free: https://api.census.gov/data/key_signup.html)."
        )
    for key in (cities or list(CITIES)):
        fetch_city_demographics(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
