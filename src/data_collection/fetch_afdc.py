"""
Fetch EV charging stations from the DOE/NREL AFDC API (requires NREL_API_KEY).

Pulls all public electric stations in each study state, keeps the fields needed
for the EV sub-index (location and DC-fast port count), and writes one CSV per
city. The processing step (`ev_index.py`) does the spatial join to tracts.

Get a free key at https://developer.nrel.gov/signup/ and put it in `.env` as
NREL_API_KEY.

Run:
    python -m src.data_collection.fetch_afdc
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

from src.config import AFDC_DIR, CITIES, NREL_API_KEY

AFDC_URL = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"
KEEP_COLS = [
    "id", "station_name", "latitude", "longitude", "state",
    "ev_level2_evse_num", "ev_dc_fast_num", "ev_network", "access_code",
]


def fetch_state_stations(state_abbr: str) -> pd.DataFrame:
    """All public, available electric stations in a state."""
    params = {
        "api_key": NREL_API_KEY,
        "fuel_type": "ELEC",
        "status": "E",            # available
        "access": "public",
        "state": state_abbr,
        "limit": "all",
    }
    resp = requests.get(AFDC_URL, params=params, timeout=180)
    resp.raise_for_status()
    stations = resp.json().get("fuel_stations", [])
    df = pd.DataFrame(stations)
    cols = [c for c in KEEP_COLS if c in df.columns]
    return df[cols]


def fetch_city_chargers(city_key: str) -> pd.DataFrame:
    cfg = CITIES[city_key]
    df = fetch_state_stations(cfg["state_abbr"])
    out = AFDC_DIR / f"{city_key}_chargers.csv"
    df.to_csv(out, index=False)
    print(f"[{cfg['name']}] {len(df)} stations in {cfg['state_abbr']} -> {out.name}")
    return df


def main(cities: list[str] | None = None) -> None:
    if not NREL_API_KEY:
        raise SystemExit(
            "NREL_API_KEY not set. Copy .env.example to .env and add your key "
            "(free: https://developer.nrel.gov/signup/)."
        )
    for key in (cities or list(CITIES)):
        fetch_city_chargers(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
