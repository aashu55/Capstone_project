# Measuring Equity in Urban Mobility Infrastructure: A Composite-Index and Interactive-Dashboard Approach

**Initial Draft — Chapters 1–3**
**EMGT 7945 · Engineering Management Capstone**
**Aashritha Kanagala · Northeastern University · Summer 2026**
**Submitted: June 15, 2026**

---

> *Note on draft status.* This draft establishes the problem, situates it in the
> literature, and specifies the methodology in full. The data pipeline, Mobility
> Equity Score (MES) computation, and interactive dashboard are implemented and
> run end-to-end for all three Phase-1 cities (Chicago, Houston, Seattle) on
> **measured open data across every dimension**: transit (GTFS — CTA, METRO
> Houston, King County Metro), walkability (EPA Smart Location Database), bicycle
> (OpenStreetMap), EV charging (OpenStreetMap `amenity=charging_station`), and
> demographics (Census ACS 5-year 2019–2023). One data caveat is carried forward
> to Chapter 5: the EV layer uses community-maintained OSM charging points (a
> lower-bound proxy relative to the authoritative DOE/NREL AFDC inventory, which
> was unreachable on the development network); the measures are also supply-side
> throughout. Chapter 4 (Results) is forthcoming and will present the substantive
> findings; the correlation and clustering machinery is already validated on the
> live data.

---

## Chapter 1 — Introduction

### 1.1 Background and Motivation

Mobility is a precondition for opportunity. Access to jobs, education, health
care, and social participation is mediated by the transportation options
available where a person lives. Yet the infrastructure that enables mobility —
frequent public transit, walkable streets, connected bicycle networks, and,
increasingly, electric-vehicle (EV) charging — is not distributed evenly across
urban space. Decades of transportation and land-use research have documented
that low-income neighborhoods and communities of color frequently experience a
"mobility burden": longer trips, fewer modal choices, and higher exposure to the
costs of car dependence (Litman, 2023; Karner et al., 2020). As cities pursue
decarbonization and "20-minute neighborhood" goals, the question of *who*
benefits from new mobility investment — and who is left behind — has moved to
the center of transportation policy.

The challenge for planners and researchers is that mobility equity is
multidimensional and spatially heterogeneous. A neighborhood may enjoy excellent
bus service but lack safe cycling infrastructure; another may be highly walkable
yet far from any fast EV charger as the vehicle fleet electrifies. Existing
public tools tend to measure one dimension at a time. The U.S. EPA's Smart
Location Database characterizes the built environment and walkability; the U.S.
Department of Energy's Alternative Fuels Data Center (AFDC) inventories charging
stations; transit agencies publish service data through the General Transit Feed
Specification (GTFS). No widely-used, reproducible tool combines these supply-side
layers into a single, neighborhood-level measure of mobility access that can be
compared across cities and cross-referenced against demographic disadvantage.

### 1.2 Problem Statement

This project addresses that gap by constructing a **Mobility Equity Score (MES)**
— a composite 0–100 index computed at the U.S. Census tract level that
integrates four mobility dimensions (transit access, walkability, bicycle
infrastructure, and EV-charging access) and by delivering an **interactive
dashboard** that lets analysts and policymakers explore the score, identify
"mobility deserts," and examine how mobility access correlates with
neighborhood demographics. The work is explicitly *supply-side*: it measures the
infrastructure made available to a neighborhood, not the travel behavior or
realized accessibility of its residents. This scope is a deliberate, stated
limitation (§5) and shapes the interpretation of every result.

### 1.3 Research Questions

1. **Measurement.** Can heterogeneous, publicly-available mobility datasets be
   integrated into a single, transparent, tract-level composite index that is
   reproducible and comparable across cities?
2. **Distribution.** How is mobility infrastructure spatially distributed within
   each study city, and where are the "mobility deserts" (tracts in the bottom
   quartile of the MES) and "compounded deserts" (bottom quartile on two or more
   dimensions)?
3. **Equity.** Is the MES associated with neighborhood demographic
   characteristics — median household income, racial composition, vehicle
   access, and tenure — and in what direction and magnitude?
4. **Robustness.** Are the conclusions sensitive to methodological choices,
   specifically the weighting of sub-indices and the percentile threshold used
   to define a mobility desert?

### 1.4 Objectives

- Build a modular, documented Python pipeline that ingests eight public data
  sources and produces tract-level sub-indices for four mobility dimensions.
- Define and compute the MES under a transparent normalization and weighting
  scheme, with mobility-desert and compounded-desert classifications.
- Quantify the relationship between the MES and demographic disadvantage using
  correlation analysis, and characterize spatial clustering using spatial
  autocorrelation and unsupervised clustering.
- Test robustness through weighting-scheme and threshold sensitivity analyses.
- Deliver an interactive Plotly Dash dashboard for exploration and comparison,
  plus static figures and tables suitable for an academic report and policy
  brief.

### 1.5 Scope and Significance

The Phase-1 study covers three structurally different U.S. cities — Chicago
(mature, high transit), Houston (auto-oriented, sprawling), and Seattle
(progressive transit and EV investment) — chosen to stress-test the method
across mobility regimes. The contribution is threefold: (i) a *reproducible
integration* of mobility datasets that are usually analyzed in isolation; (ii) a
*composite equity metric* with explicit, testable methodological choices; and
(iii) a *decision-support dashboard* that translates the analysis for
non-technical stakeholders. The significance is practical — the tool can help
agencies prioritize investment toward under-served neighborhoods — and
methodological, in demonstrating how open data and modern geospatial tooling can
operationalize "mobility justice" concepts at scale.

### 1.6 Organization of the Report

Chapter 2 reviews the literature on transportation equity, composite indicator
construction, and the four mobility dimensions. Chapter 3 specifies the
methodology in full: study-area selection, data sources, preprocessing,
sub-index computation, normalization and MES construction, weighting and
threshold sensitivity, and the statistical and dashboard methods. Chapters 4 and
5 (forthcoming) present results and discussion.

---

## Chapter 2 — Literature Review

### 2.1 Transportation Equity and Mobility Justice

Transportation equity scholarship distinguishes *horizontal equity* (equal
treatment of equals) from *vertical equity* (favoring the disadvantaged), and
increasingly frames access to mobility as a matter of justice rather than mere
efficiency (Martens, 2017; Litman, 2023). Karner et al. (2020) synthesize the
field and argue for distributional analyses that pair infrastructure or service
measures with demographic data at fine spatial resolution — precisely the design
adopted here. The "mobility justice" literature (Sheller, 2018) further situates
transportation access within broader patterns of spatial and social inequality,
motivating the cross-referencing of the MES against income, race, vehicle
access, and tenure.

A persistent methodological tension is between *accessibility* measures
(opportunities reachable within a travel-time budget; Levine et al., 2012) and
*supply* measures (infrastructure present in or near a place). Accessibility is
theoretically richer but data-intensive and behaviorally contingent; supply
measures are transparent and reproducible but silent on whether residents can
actually use the infrastructure. This project adopts a supply-side framing for
reproducibility and cross-city comparability, while explicitly acknowledging the
trade-off (§5).

### 2.2 Composite Indicators in Public Policy

Composite indicators compress multiple variables into a single, communicable
number; the OECD/JRC *Handbook on Constructing Composite Indicators* (Nardo et
al., 2008) is the canonical methodological reference and structures the choices
made in Chapter 3: framework definition, data selection, treatment of missing
data, normalization, weighting and aggregation, and robustness/sensitivity
analysis. The handbook stresses that normalization and weighting are value-laden
and that any composite must be accompanied by uncertainty and sensitivity
analysis — a requirement this study meets through its weighting-scheme and
threshold tests (§3.6, §3.7). Well-known applied examples (e.g., the UNDP Human
Development Index; the CDC/ATSDR Social Vulnerability Index) demonstrate both the
communicative power and the contestability of composites, reinforcing the need
for transparency about every modeling decision.

### 2.3 The Four Mobility Dimensions

**Transit access.** Service quality is commonly proxied by stop density,
frequency (trips per hour), and span of service, computed from GTFS feeds within
a walkable buffer of residences (typically 0.25–0.5 mi). GTFS has become the de
facto standard for transit supply analysis, and open libraries now make
feed-level frequency computation tractable.

**Walkability.** The EPA Smart Location Database (SLD) provides the National
Walkability Index (`NatWalkInd`, 1–20), a block-group measure built from
intersection density, transit proximity, and employment/household mix. It is the
most widely-used national, consistently-computed walkability measure and is
adopted here directly, with areal interpolation to harmonize its 2019-vintage
block groups to the study's 2023 tracts (§3.3).

**Bicycle infrastructure.** OpenStreetMap (OSM), accessed via the OSMnx library
(Boeing, 2017), is the standard open source for bicycle-network extraction.
Dedicated infrastructure (cycleways, paths, tracks, and marked on-street lanes)
can be filtered from the cyclable network and summarized as lane length per unit
area, a common supply proxy for bikeability.

**EV-charging access.** As fleets electrify, equitable access to public charging
— especially DC-fast charging for households without home charging — is an
emerging equity concern. The DOE/NREL AFDC is the authoritative U.S. inventory
of public stations and supports density and proximity measures at the
neighborhood scale.

### 2.4 Spatial Analysis Methods

Because mobility infrastructure is spatially structured, the analysis employs
established spatial-statistical tools. Global and local Moran's I (Anselin,
1995), implemented in the PySAL ecosystem (Rey & Anselin, 2007), test whether
MES values cluster in space and locate statistically significant
low-low "cold spots." Unsupervised K-means clustering with silhouette-based model
selection (Rousseeuw, 1987) is used to derive an interpretable typology of
neighborhood mobility profiles, complementing the single-number MES with a
multidimensional classification.

### 2.5 Existing Tools and the Gap Addressed

Agencies and researchers can consult the EPA SLD for walkability, the AFDC for
chargers, transit agencies' GTFS for service, and bespoke bike-network analyses.
National equity screening tools (e.g., the USDOT Equitable Transportation
Community Explorer; the CDC Social Vulnerability Index) provide disadvantage
indices but are not mobility-infrastructure composites at tract level across
modes. The gap this project fills is an *integrated, reproducible,
cross-city, multi-modal* mobility-supply composite with an exploratory
dashboard — bringing the four dimensions into a single comparable frame and
pairing them with demographic context.

---

## Chapter 3 — Methodology

### 3.1 Study Area Selection and City FIPS Codes

Three cities were selected to span distinct mobility regimes (Table 3.1). The
analytical unit is the 2023 Census tract; counties are identified by FIPS code
for data retrieval.

**Table 3.1 — Study cities.**

| City | State (FIPS) | County (FIPS) | Tracts | Rationale |
|------|-------------|---------------|--------|-----------|
| Chicago | Illinois (17) | Cook (031) | 1,332 | Mature, high-frequency transit; diverse demographics |
| Houston | Texas (48) | Harris (201) | 1,115 | Auto-oriented, sprawling; large low-income population |
| Seattle | Washington (53) | King (033) | 495 | Progressive transit and EV investment; equity focus |

Phase 2 will extend the method to Phoenix (AZ), Atlanta (GA), and Detroit (MI)
after pipeline validation.

### 3.2 Data Collection Pipeline

Eight public sources feed the pipeline (Table 3.2). Each is retrieved by a
dedicated, independently-runnable Python module under `src/data_collection/`.

**Table 3.2 — Data sources and access.**

| # | Layer | Source | Endpoint / file | Key |
|---|-------|--------|-----------------|-----|
| 1 | Tract boundaries (2023) | Census TIGER/Line | `…/TIGER2023/TRACT/tl_2023_{ss}_tract.zip` | none |
| 2 | Block groups (2023, 2019) | Census TIGER/Line | `…/TIGER{2023,2019}/BG/tl_{yyyy}_{ss}_bg.zip` | none |
| 3 | Demographics (ACS 5-yr 2019–2023) | Census API | `api.census.gov/data/2023/acs/acs5` | Census |
| 4 | Walkability | EPA Smart Location Database v3 | `edg.epa.gov/…/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv` | none |
| 5 | Bicycle network | OpenStreetMap (OSMnx) | Overpass via `graph_from_place(..., 'bike')` | none |
| 6 | EV charging | DOE/NREL AFDC | `developer.nrel.gov/api/alt-fuel-stations/v1.json` | NREL |
| 7 | Transit service | GTFS (transit.land / agency) | `transit.land/api/v2/rest/feeds`; agency zips | transit.land (opt.) |
| 8 | (derived) Tract centroids & areas | computed | — | none |

ACS variables retrieved: median household income (`B19013_001E`); total
population and White-alone-non-Hispanic (`B03002_001E`, `B03002_003E`) for
percent non-white; zero-vehicle owner/renter households (`B25044_003E`,
`B25044_010E`); renter-occupied and total occupied units (`B25003_003E`,
`B25003_001E`) for percent renter.

### 3.3 Data Preprocessing

All layers are reprojected to a common geographic CRS (EPSG:4326) for storage
and mapping and to USA Contiguous Albers Equal Area (EPSG:5070) for any
length/area/distance computation, so metrics are in true metres and not degrees.
GEOIDs are coerced to zero-padded strings (11 digits for tracts, 12 for block
groups) to guarantee exact joins.

A key preprocessing problem is **geographic vintage mismatch**. The EPA SLD v3
is published on 2019-vintage (2010-decade) block-group boundaries, whereas the
study uses 2023 (2020-decade) tracts to align with the 2019–2023 ACS. A naive
GEOID-prefix join loses tracts wherever boundaries were redrawn — empirically,
about 57% of Houston's tracts. The pipeline therefore performs **areal
interpolation**: `NatWalkInd` is joined to 2019 block-group polygons (a 100%
GEOID match against the SLD) and then area-weighted onto 2023 tracts via a
geometric overlay, with each tract's value the area-weighted mean of its
overlapping block-group pieces. Because `NatWalkInd` is an intensive index
(not a count), area-weighted averaging is the correct interpolation.

Missing values are preserved rather than imputed so that data gaps remain
visible; normalization functions propagate `NaN`, and a constant input maps to
the scale midpoint rather than producing undefined values. Tracts with zero land
area or no population are guarded against division-by-zero in density metrics.

### 3.4 Sub-Index Computation

Each sub-index is computed at tract level and then normalized (§3.5).

**Transit (`transit_index.py`).** From GTFS `stops` and `stop_times`, AM-peak
(07:00–09:00) departures per stop are converted to trips/hour, and the daily
service span (distinct hours with ≥1 departure) is computed. Stops are spatially
joined to a 0.5-mile (804.7 m) buffer of each tract centroid, yielding stop
density (stops/km²), mean AM-peak frequency, and service span. The three
components are normalized and averaged.

**Walkability (`walk_index.py`).** Area-weighted `NatWalkInd` per tract (§3.3),
normalized to 0–100.

**Bicycle (`bike_index.py`).** From the OSM cyclable network, edges are retained
as dedicated infrastructure when `highway ∈ {cycleway, path, track}` or a
positive `cycleway` tag is present (e.g., `lane`, `track`, `shared_lane`). Edges
are clipped to tracts by overlay; bike-lane kilometres per km² of tract land
area form the raw metric, normalized to 0–100.

**EV charging (`ev_index.py`).** Public Level-2 and DC-fast stations are spatially
joined to tracts. Two metrics are computed: chargers per 1,000 residents, and the
distance from each tract centroid to the nearest DC-fast station (inverted so
that proximity raises the score). Both are normalized and averaged. The
authoritative source is the DOE/NREL AFDC inventory (`fetch_afdc.py`); where that
API is unreachable, the pipeline falls back to OpenStreetMap
`amenity=charging_station` points (`fetch_osm_ev.py`), a key-free but
lower-bound proxy whose completeness limitation is noted in §5.

### 3.5 Normalization and MES Construction

Each raw sub-index is placed on a common 0–100 scale by **min–max
normalization**:

```
x_norm = (x − x_min) / (x_max − x_min) × 100
```

computed within each city so scores are interpretable relative to that city's
own distribution. A robust percentile-rank variant is retained for sensitivity
checks. The composite is a weighted sum of the four normalized sub-indices:

```
MES = w_transit·transit_norm + w_walk·walk_norm + w_bike·bike_norm + w_ev·ev_norm,   Σw = 1
```

The **baseline** uses equal weights (0.25 each), the most defensible default
absent strong prior information (Nardo et al., 2008). The MES therefore ranges
0–100, with higher values indicating better mobility-infrastructure access.

### 3.6 Weighting Methodology and Sensitivity Analysis

Because equal weighting is itself a value choice, three alternatives are computed
and compared (`weighting_methods.py`):

- **Entropy weighting** — objective weights derived from each sub-index's
  dispersion; dimensions that discriminate more between tracts receive more
  weight (redundancy = 1 − Shannon entropy, normalized to sum to 1).
- **PCA weighting** — weights from the absolute loadings of the first principal
  component of the four sub-indices.
- **AHP weighting** — expert pairwise-judgement weights (Analytic Hierarchy
  Process); a provisional vector (transit 0.40, walk 0.30, bike 0.15, EV 0.15)
  is used pending a structured expert survey.

For each scheme the MES is recomputed and the equity correlations (§3.8) are
re-estimated; the analysis reports how much the sign, magnitude, and significance
of those correlations move across schemes, establishing whether conclusions are
weighting-robust.

### 3.7 Mobility-Desert Classification

A tract is a **mobility desert** if its MES falls below the city's 25th
percentile. A **compounded desert** is a tract in the bottom quartile of two or
more individual sub-indices — capturing places disadvantaged on multiple
dimensions simultaneously. Because the 25th-percentile cut is arbitrary, a
**threshold sensitivity analysis** (`sensitivity_analysis.py`) recomputes the
desert set at the 20th, 25th, and 30th percentiles and reports the Jaccard
overlap with the baseline set and the demographic profile of flagged tracts at
each threshold; high overlap indicates the classification is not an artefact of
the chosen cut-off.

### 3.8 Equity Correlation Analysis

Pearson correlations relate the MES (and each sub-index) to four demographic
variables — median income, percent non-white, percent zero-vehicle households,
and percent renter (`equity_correlation.py`). For each pair the analysis reports
r, the two-sided p-value, the sample size, and the 95% confidence interval from
the Fisher z-transformation:

```
z = arctanh(r),  SE = 1/√(n−3),  CI = tanh(z ± 1.96·SE)
```

A negative MES–income or MES–percent-non-white correlation would indicate that
more-disadvantaged neighborhoods receive less mobility infrastructure (a vertical-
equity concern). All correlations are also rendered as a correlation-matrix
heatmap for the report.

### 3.9 Spatial Autocorrelation (Moran's I)

Global Moran's I (`spatial_autocorrelation.py`) tests whether MES values cluster
spatially, using **queen-contiguity** weights, row-standardized, with 999
conditional permutations for a pseudo p-value. Local Moran's I (LISA) classifies
each tract as high-high, low-low, high-low, low-high, or non-significant
(p < 0.05); low-low clusters are mapped as mobility "cold spots."

### 3.10 Cluster Analysis

K-means clustering (`clustering.py`) on the four standardized sub-indices derives
a typology of neighborhood mobility profiles. The number of clusters k is chosen
by maximizing the mean silhouette score over k ∈ {2,…,7}, with the inertia
(elbow) curve reported for validation. Each cluster is given an interpretable
label from its centroid profile (e.g., "uniformly under-served," "well-served /
multimodal," or "transit-rich, bike-poor") for the Chapter 4 typology table.

### 3.11 Dashboard Development

The interactive dashboard (`src/dashboard/`, Plotly Dash + Dash Bootstrap
Components) follows a modular layout/callbacks/utilities architecture. It
provides: a tract-level choropleth of the MES or any sub-index (reversed
yellow-orange-red scale, darkest = worst) with desert filters; a click-through
side panel showing a tract's MES, city percentile, a sub-index bar chart versus
the city median, an auto-generated plain-language interpretation, and a
demographic summary; a city-comparison equity-gap chart (median MES of the
poorest versus richest income quintile); a ranked table of the most
disadvantaged tracts; and CSV/PNG export. Each MES file records the measurement
status of every layer so placeholder data is never displayed as measured.

### 3.12 Reproducibility and Tooling

The project targets Python 3.11 with a pinned `requirements.txt`. Every stage is
an independently-runnable module, raw downloads are cached, and a `pytest` suite
covers normalization, MES construction and desert flagging, and the correlation
statistics. Code, data-processing scripts, and documentation are version-
controlled, with raw and large artefacts gitignored.

---

## References (selected; to be completed in final draft)

- Anselin, L. (1995). Local Indicators of Spatial Association—LISA. *Geographical Analysis*, 27(2), 93–115.
- Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, 65, 126–139.
- Karner, A., London, J., Rowangould, D., & Manaugh, K. (2020). From transportation equity to transportation justice. *Journal of Planning Literature*, 35(4), 440–459.
- Levine, J., Grengs, J., Shen, Q., & Shen, Q. (2012). Does accessibility require density or speed? *Journal of the American Planning Association*, 78(2), 157–172.
- Litman, T. (2023). *Evaluating Transportation Equity*. Victoria Transport Policy Institute.
- Martens, K. (2017). *Transport Justice: Designing Fair Transportation Systems*. Routledge.
- Nardo, M., Saisana, M., Saltelli, A., et al. (2008). *Handbook on Constructing Composite Indicators*. OECD/JRC.
- Rey, S. J., & Anselin, L. (2007). PySAL: A Python library of spatial analytical methods. *The Review of Regional Studies*, 37(1), 5–27.
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, 53–65.
- Sheller, M. (2018). *Mobility Justice: The Politics of Movement in an Age of Extremes*. Verso.
- U.S. EPA (2021). *Smart Location Database Technical Documentation and User Guide, Version 3.0*.
