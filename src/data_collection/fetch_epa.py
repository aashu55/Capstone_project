"""
Fetch the EPA Smart Location Database (SLD) v3 walkability data (no API key).

The SLD is a national, block-group-level dataset. The single field we need is
`NatWalkInd` (National Walkability Index, 1–20). The full geodatabase is very
large (~1.5 GB), so we download the distributed CSV, keep only the GEOID and
NatWalkInd columns, filter to the study states, and save a per-city CSV. The
block-group *geometry* is taken from the TIGER block-group file
(`fetch_tiger.py`) and joined at processing time.

Run:
    python -m src.data_collection.fetch_epa
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

from src.config import CITIES, EPA_DIR

# EPA EDG distribution of the SLD v3 (single ~200 MB CSV, not zipped).
SLD_CSV = (
    "https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv"
)

# The SLD CSV stores GEOID10 in lossy scientific notation, so we reconstruct
# the 12-digit block-group GEOID from the intact FIPS component columns:
#   STATEFP(2) + COUNTYFP(3) + TRACTCE(6) + BLKGRPCE(1)
FIPS_COLS = ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE"]
FIPS_WIDTHS = {"STATEFP": 2, "COUNTYFP": 3, "TRACTCE": 6, "BLKGRPCE": 1}
WALK_COL = "NatWalkInd"


def download_sld_csv() -> pd.DataFrame:
    """Download the SLD CSV (cached locally) and return GEOID + NatWalkInd."""
    cache = EPA_DIR / "sld_v3_natwalkind.parquet"
    if cache.exists():
        print(f"[EPA] using cached {cache.name}")
        return pd.read_parquet(cache)

    raw_csv = EPA_DIR / "sld_v3_full.csv"
    if not raw_csv.exists():
        print(f"[EPA] downloading SLD CSV (~200 MB) from {SLD_CSV} ...")
        with requests.get(SLD_CSV, timeout=900, stream=True,
                          headers={"User-Agent": "umed-research/1.0"}) as resp:
            resp.raise_for_status()
            with open(raw_csv, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    df = pd.read_csv(raw_csv, usecols=FIPS_COLS + [WALK_COL], low_memory=False)
    geoid = ""
    for col in FIPS_COLS:
        part = (pd.to_numeric(df[col], errors="coerce")
                .astype("Int64").astype(str).str.zfill(FIPS_WIDTHS[col]))
        geoid = geoid + part if isinstance(geoid, pd.Series) else part
    out = pd.DataFrame({"GEOID": geoid, "NatWalkInd": df[WALK_COL]})
    out.to_parquet(cache, index=False)
    print(f"[EPA] cached {len(out):,} block groups -> {cache.name}")
    return out


def fetch_city_walkability(city_key: str, sld: pd.DataFrame) -> pd.DataFrame:
    """Filter the national SLD to one city's counties and save a CSV."""
    cfg = CITIES[city_key]
    prefixes = {cfg["state_fips"] + c for c in cfg["county_fips"]}
    mask = sld["GEOID"].str[:5].isin(prefixes)
    city = sld[mask].copy()
    out = EPA_DIR / f"{city_key}_walkability.csv"
    city.to_csv(out, index=False)
    print(f"[{cfg['name']}] {len(city):,} block groups -> {out.name}")
    return city


def main(cities: list[str] | None = None) -> None:
    sld = download_sld_csv()
    for key in (cities or list(CITIES)):
        fetch_city_walkability(key, sld)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
