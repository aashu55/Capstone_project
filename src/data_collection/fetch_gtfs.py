"""
Fetch GTFS transit feeds (uses TRANSITLAND_API_KEY when available).

Resolves each city's primary GTFS feed via the transit.land v2 REST API,
downloads the latest static feed zip, and saves it under data/raw/gtfs/. The
processing step (`transit_index.py`) parses stops and stop_times from the zip.

Many agencies also publish their GTFS zip directly; for resilience this module
accepts an explicit `direct_url` per city in DIRECT_FEEDS, used as a fallback
(or primary) when transit.land lookup is unavailable.

Get a free transit.land key at https://www.transit.land/documentation and put
it in `.env` as TRANSITLAND_API_KEY.

Run:
    python -m src.data_collection.fetch_gtfs
"""
from __future__ import annotations

import sys
import zipfile

import requests

from src.config import CITIES, GTFS_DIR, TRANSITLAND_API_KEY

TL_FEEDS = "https://transit.land/api/v2/rest/feeds"

# Known direct static-GTFS endpoints for the primary operator in each city,
# used as a fallback when the transit.land API is unavailable.
DIRECT_FEEDS = {
    "chicago": "https://www.transitchicago.com/downloads/sch_data/google_transit.zip",
    "houston": "https://www.ridemetro.org/SiteCollectionDocuments/googletransitfeed/google_transit.zip",
    "seattle": "https://metro.kingcounty.gov/GTFS/google_transit.zip",
}


def _download_zip(url: str, dest) -> bool:
    try:
        resp = requests.get(url, timeout=300, headers={"User-Agent": "umed-research/1.0"})
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        # Validate it is actually a zip.
        with zipfile.ZipFile(dest) as zf:
            zf.testzip()
        return True
    except (requests.RequestException, zipfile.BadZipFile) as exc:
        print(f"  download failed for {url}: {exc}")
        if dest.exists():
            dest.unlink()
        return False


def transitland_feed_url(city_key: str) -> str | None:
    """Look up the city's GTFS feed URL via transit.land (needs an API key)."""
    if not TRANSITLAND_API_KEY:
        return None
    cfg = CITIES[city_key]
    params = {"apikey": TRANSITLAND_API_KEY, "search": cfg["name"], "spec": "gtfs"}
    try:
        resp = requests.get(TL_FEEDS, params=params, timeout=60)
        resp.raise_for_status()
        feeds = resp.json().get("feeds", [])
        for feed in feeds:
            url = (feed.get("urls") or {}).get("static_current")
            if url:
                return url
    except requests.RequestException as exc:
        print(f"  transit.land lookup failed: {exc}")
    return None


def fetch_city_gtfs(city_key: str) -> bool:
    cfg = CITIES[city_key]
    dest = GTFS_DIR / f"{city_key}_gtfs.zip"
    print(f"[{cfg['name']}] fetching GTFS feed ...")
    url = transitland_feed_url(city_key) or DIRECT_FEEDS.get(city_key)
    if not url:
        print(f"  no feed URL available for {city_key}")
        return False
    ok = _download_zip(url, dest)
    if ok:
        print(f"  saved -> {dest.name}")
    return ok


def main(cities: list[str] | None = None) -> None:
    for key in (cities or list(CITIES)):
        fetch_city_gtfs(key)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
