"""
Central configuration for the Urban Mobility Equity Dashboard.

Defines study cities, their Census FIPS codes, file-system paths, the ACS
variable list, and the default MES weighting scheme. Every module imports
from here so that adding a city or changing a path happens in one place.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SUB_INDEX_DIR = PROCESSED_DIR / "sub_indices"
MES_DIR = PROCESSED_DIR / "mes_scores"
OUTPUTS_DIR = DATA_DIR / "outputs"

TIGER_DIR = RAW_DIR / "tiger"
EPA_DIR = RAW_DIR / "epa_walkability"
GTFS_DIR = RAW_DIR / "gtfs"
AFDC_DIR = RAW_DIR / "afdc"

for _d in (TIGER_DIR, EPA_DIR, GTFS_DIR, AFDC_DIR, SUB_INDEX_DIR, MES_DIR, OUTPUTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# API keys (.env)
# --------------------------------------------------------------------------- #
load_dotenv(PROJECT_ROOT / ".env")
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
NREL_API_KEY = os.getenv("NREL_API_KEY")
TRANSITLAND_API_KEY = os.getenv("TRANSITLAND_API_KEY")

# --------------------------------------------------------------------------- #
# Study cities
# --------------------------------------------------------------------------- #
# `state_fips` / `county_fips` are used to filter Census TIGER tracts and to
# query the ACS API. `place_name` is the OSMnx geocoding string. `state_abbr`
# feeds the AFDC EV-charger query.
CITIES = {
    "chicago": {
        "name": "Chicago",
        "state_fips": "17",
        "county_fips": ["031"],          # Cook County
        "state_abbr": "IL",
        "place_name": "Chicago, Illinois, USA",
    },
    "houston": {
        "name": "Houston",
        "state_fips": "48",
        "county_fips": ["201"],          # Harris County
        "state_abbr": "TX",
        "place_name": "Houston, Texas, USA",
    },
    "seattle": {
        "name": "Seattle",
        "state_fips": "53",
        "county_fips": ["033"],          # King County
        "state_abbr": "WA",
        "place_name": "Seattle, Washington, USA",
    },
}

# Phase-2 expansion cities (not yet fetched): Phoenix AZ, Atlanta GA, Detroit MI.

# --------------------------------------------------------------------------- #
# ACS 5-year variables (2019–2023)
# --------------------------------------------------------------------------- #
ACS_YEAR = 2023
ACS_DATASET = "acs/acs5"
ACS_VARIABLES = {
    "B19013_001E": "median_income",         # Median household income
    "B03002_001E": "total_population",       # Total population
    "B03002_003E": "white_nonhispanic",      # White alone, not Hispanic
    "B25044_003E": "owner_no_vehicle",       # Owner-occupied, no vehicle
    "B25044_010E": "renter_no_vehicle",      # Renter-occupied, no vehicle
    "B25003_003E": "renter_occupied",        # Renter-occupied housing units
    "B25003_001E": "total_occupied",         # Total occupied housing units
}

# --------------------------------------------------------------------------- #
# MES weighting & desert thresholds
# --------------------------------------------------------------------------- #
DEFAULT_WEIGHTS = {"transit": 0.25, "walk": 0.25, "bike": 0.25, "ev": 0.25}
DESERT_PERCENTILE = 0.25          # tracts below this MES percentile = mobility desert
DESERT_SENSITIVITY = [0.20, 0.25, 0.30]   # thresholds tested in sensitivity analysis

# Coordinate reference systems
CRS_GEOGRAPHIC = "EPSG:4326"      # lat/lon for storage & mapping
CRS_PROJECTED = "EPSG:5070"       # USA Contiguous Albers Equal Area, metres (for areas/buffers)
SUB_INDICES = ["transit", "walk", "bike", "ev"]
