"""
Fetch Census TIGER/Line tract & block-group boundaries (no API key required).

Downloads the per-state TIGER 2023 shapefiles, filters to the study counties,
and writes one GeoJSON of tracts (and one of block groups, used by the
walkability aggregation) per city.

Run:
    python -m src.data_collection.fetch_tiger            # all study cities
    python -m src.data_collection.fetch_tiger chicago    # a single city
"""
from __future__ import annotations

import io
import sys
import zipfile

import geopandas as gpd
import requests

from src.config import CITIES, CRS_GEOGRAPHIC, TIGER_DIR

TIGER_BASE = "https://www2.census.gov/geo/tiger/TIGER2023"
TRACT_URL = TIGER_BASE + "/TRACT/tl_2023_{state}_tract.zip"
BG_URL = TIGER_BASE + "/BG/tl_2023_{state}_bg.zip"


def _download_shapefile(url: str) -> gpd.GeoDataFrame:
    """Download a zipped shapefile to memory and read it with geopandas."""
    resp = requests.get(url, timeout=180, headers={"User-Agent": "umed-research/1.0"})
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    shp = next(n for n in zf.namelist() if n.endswith(".shp"))
    # geopandas can read a shapefile from inside a zip via the /vsizip/ syntax,
    # but reading from the extracted bytes is simplest and avoids temp dirs.
    tmp = TIGER_DIR / "_tmp_shp"
    tmp.mkdir(exist_ok=True)
    zf.extractall(tmp)
    gdf = gpd.read_file(tmp / shp)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return gdf.to_crs(CRS_GEOGRAPHIC)


def fetch_city_boundaries(city_key: str) -> dict[str, gpd.GeoDataFrame]:
    """Download and filter tracts + block groups for one city. Returns both."""
    cfg = CITIES[city_key]
    state, counties = cfg["state_fips"], set(cfg["county_fips"])

    print(f"[{cfg['name']}] downloading TIGER tracts for state {state} ...")
    tracts = _download_shapefile(TRACT_URL.format(state=state))
    tracts = tracts[tracts["COUNTYFP"].isin(counties)].copy()
    tracts["GEOID"] = tracts["GEOID"].astype(str).str.zfill(11)

    print(f"[{cfg['name']}] downloading TIGER block groups ...")
    bgs = _download_shapefile(BG_URL.format(state=state))
    bgs = bgs[bgs["COUNTYFP"].isin(counties)].copy()
    bgs["GEOID"] = bgs["GEOID"].astype(str).str.zfill(12)

    tract_path = TIGER_DIR / f"{city_key}_tracts.geojson"
    bg_path = TIGER_DIR / f"{city_key}_blockgroups.geojson"
    tracts.to_file(tract_path, driver="GeoJSON")
    bgs.to_file(bg_path, driver="GeoJSON")
    print(f"[{cfg['name']}] wrote {len(tracts)} tracts -> {tract_path.name}, "
          f"{len(bgs)} block groups -> {bg_path.name}")
    return {"tracts": tracts, "blockgroups": bgs}


def fetch_blockgroups_2019(city_key: str) -> gpd.GeoDataFrame:
    """Download 2019-vintage block groups for one city.

    The EPA Smart Location Database v3 uses 2019 (2010-decade) block-group
    geometry, so the walkability areal interpolation joins NatWalkInd to these
    polygons rather than the 2023 boundaries used elsewhere.
    """
    cfg = CITIES[city_key]
    state, counties = cfg["state_fips"], set(cfg["county_fips"])
    url = f"{TIGER_BASE.replace('TIGER2023', 'TIGER2019')}/BG/tl_2019_{state}_bg.zip"
    print(f"[{cfg['name']}] downloading 2019 TIGER block groups ...")
    bgs = _download_shapefile(url)
    bgs = bgs[bgs["COUNTYFP"].isin(counties)].copy()
    bgs["GEOID"] = bgs["GEOID"].astype(str).str.zfill(12)
    out = TIGER_DIR / f"{city_key}_blockgroups_2019.geojson"
    bgs.to_file(out, driver="GeoJSON")
    print(f"[{cfg['name']}] wrote {len(bgs)} 2019 block groups -> {out.name}")
    return bgs


def main(cities: list[str] | None = None) -> None:
    for key in (cities or list(CITIES)):
        fetch_city_boundaries(key)
        fetch_blockgroups_2019(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
