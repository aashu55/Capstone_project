"""
Fetch public EV charging stations from OpenStreetMap (no API key required).

This is a *reachable, key-free* alternative to the DOE/NREL AFDC API
(`fetch_afdc.py`), used when the NREL endpoint is unavailable. It queries OSM
`amenity=charging_station` points for each city and writes them in the same CSV
schema the EV sub-index expects (`latitude`, `longitude`, `ev_dc_fast_num`), so
`build_subindices.py` consumes them transparently.

Caveat: OSM charging-station coverage is community-maintained and less complete
than the authoritative AFDC inventory; treat the OSM-derived EV sub-index as a
lower-bound proxy and prefer `fetch_afdc.py` when an NREL key + network are
available.

Run:
    python -m src.data_collection.fetch_osm_ev            # all cities
    python -m src.data_collection.fetch_osm_ev seattle    # one city
"""
from __future__ import annotations

import sys

import osmnx as ox
import pandas as pd

from src.config import AFDC_DIR, CITIES

ox.settings.use_cache = True

# OSM tags that indicate DC-fast / rapid charging.
DCFAST_SOCKETS = ["socket:chademo", "socket:type2_combo", "socket:ccs",
                  "socket:tesla_supercharger"]


def _is_dc_fast(row) -> int:
    """Infer a DC-fast station from OSM tags (socket type or rated output)."""
    for col in DCFAST_SOCKETS:
        if col in row and pd.notna(row[col]):
            return 1
    for col in ("output", "charging_station:output", "maxpower", "socket:output"):
        if col in row and pd.notna(row[col]):
            txt = str(row[col]).lower().replace("kw", "").strip()
            try:
                if float(txt.split()[0]) >= 50:
                    return 1
            except (ValueError, IndexError):
                pass
    return 0


def fetch_city_ev(city_key: str) -> pd.DataFrame:
    cfg = CITIES[city_key]
    print(f"[{cfg['name']}] querying OSM charging stations ...")
    gdf = ox.features_from_place(cfg["place_name"], tags={"amenity": "charging_station"})
    gdf = gdf[gdf.geometry.type == "Point"].copy()
    gdf["latitude"] = gdf.geometry.y
    gdf["longitude"] = gdf.geometry.x
    gdf["ev_dc_fast_num"] = gdf.apply(_is_dc_fast, axis=1)

    out_cols = ["latitude", "longitude", "ev_dc_fast_num"]
    if "name" in gdf.columns:
        gdf["station_name"] = gdf["name"].astype(str)
        out_cols = ["station_name"] + out_cols
    df = pd.DataFrame(gdf[out_cols])
    df["source"] = "OSM"

    out = AFDC_DIR / f"{city_key}_chargers.csv"
    df.to_csv(out, index=False)
    print(f"[{cfg['name']}] {len(df)} stations ({int(df['ev_dc_fast_num'].sum())} DC-fast) -> {out.name}")
    return df


def main(cities: list[str] | None = None) -> None:
    for key in (cities or list(CITIES)):
        fetch_city_ev(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
