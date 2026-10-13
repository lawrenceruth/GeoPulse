# GeoPulse: Hyper-Local Retail Mobility Analytics

GeoPulse is a geospatial analytics project that analyzes anonymized mobile GPS movement data to understand retail foot traffic, store catchments, and potential store cannibalization. It explores how simulated retail store locations can support catchment-area analysis and location-planning decisions.

The project combines BigQuery geospatial SQL, dbt analytical modelling, and an interactive Streamlit dashboard to examine synthetic observation patterns around five simulated retail locations in Lagos, Nigeria.

> **Data integrity note:** All GPS observations and store locations are synthetic. They do not represent verified individuals, actual customer visits, purchases, or real-world sales cannibalization.

## Project Overview

GeoPulse demonstrates a reproducible analytical workflow for exploring:

- Synthetic GPS observations around simulated retail stores.
- Store catchments defined by a 500-metre radius.
- Matched GPS pings and distinct device counts.
- Hourly patterns in synthetic GPS observations.
- Geographic overlap between two Lekki catchment polygons.
- Store-level comparisons through an interactive dashboard.

The project is designed to demonstrate data generation, geospatial SQL, analytical modelling, visualization, and Git-based project management.

## Business Problem

Retail location-planning teams need ways to compare potential store locations and understand how their geographic catchments relate to one another.

GeoPulse uses a synthetic case study to explore questions such as:

- How many GPS observations fall within each simulated store's catchment?
- How do observation counts vary by hour?
- How many distinct simulated device IDs are matched to each catchment?
- How much geographic area do two catchment polygons share?
- What additional analysis would be needed before making real retail investment decisions?

**Important limitation:** GPS observations within a catchment are not proof of store visits. Shared device IDs and overlapping polygons do not establish customer switching, purchases, lost revenue, or actual sales cannibalization.

## Project Architecture

```text
Synthetic GPS Data
        |
        v
Python Data Generation
        |
        v
BigQuery Geospatial Data
        |
        v
Geospatial SQL Processing
        |
        +------------------------+
        |                        |
        v                        v
Store Catchments          Catchment Polygons
        |                        |
        v                        v
dbt Staging Model       Geographic Overlap SQL
        |
        v
dbt Catchment Summary
        |
        v
Streamlit Dashboard
(Folium + Plotly)
```

### Implemented Pipeline

1. Synthetic GPS observations are generated using Python.
2. GPS records, simulated store locations, and catchment geometries are stored in BigQuery.
3. BigQuery geospatial SQL matches GPS observations to store catchments and calculates polygon overlap.
4. dbt provides staging and catchment-summary models.
5. Streamlit presents the map, KPIs, store comparison, hourly line chart, and geographic overlap visualization.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Synthetic data generation and dashboard application |
| Pandas | Data preparation for dashboard visualizations |
| Google BigQuery | Data storage, SQL analytics, and geospatial processing |
| BigQuery GEOGRAPHY | Store locations, catchment polygons, and spatial operations |
| SQL | Catchment matching, hourly aggregation, and polygon overlap |
| dbt | Staging and analytical modelling |
| Streamlit | Interactive dashboard |
| Folium | Interactive store map and catchment polygons |
| Plotly | Interactive charts |
| Git and GitHub | Version control and project collaboration |

## Core Analytics

### 1. Store Catchment Analysis

Each simulated store has a 500-metre catchment. BigQuery spatial queries match GPS observations to these areas.

Dashboard metrics include:

- Matched GPS pings.
- Distinct simulated device IDs.
- Average distance from matched pings to a store.
- Store-level observation comparisons.

Counts across different store catchments may overlap. A device or GPS observation can be associated with more than one catchment, so store-level counts should not automatically be summed and interpreted as unique people or visits.

### 2. Hourly GPS Observation Patterns

An interactive line chart compares hourly synthetic GPS ping counts for GeoPulse Lekki A and GeoPulse Lekki B.

- Time labels use West Africa Time (WAT, UTC+1).
- The chart compares observation patterns across the two simulated catchments.
- Similar hourly patterns do not demonstrate that customers switched between stores.

### 3. Geographic Catchment Overlap

BigQuery's geospatial functions calculate the intersection of the two Lekki catchment polygons.

The analysis reports:

- Area of each catchment.
- Shared geographic area.
- Percentage of each catchment covered by the shared area.

The overlap percentage describes polygon geometry only. It is not a measure of customer overlap, sales loss, or cannibalization.

### 4. Interactive Map

The dashboard displays simulated store locations and their 500-metre catchment polygons. Users can filter stores to explore the map, KPI cards, comparison table, and store-level chart.

### Key BigQuery Objects

The project uses the following tables and views in Google Cloud project `careflow-process-mining-509421`. GeoPulse objects are kept in the `geopulse_raw`, `geopulse`, and related GeoPulse datasets; this project must not modify the separate CareFlow datasets.

| Object | Purpose |
|---|---|
| `geopulse_raw.gps_pings` | Synthetic GPS observations |
| `geopulse_raw.gps_pings_spatial` | GPS observations with BigQuery geography values |
| `geopulse_raw.store_locations` | Simulated store locations |
| `geopulse_raw.store_catchments` | GPS observations matched to store catchments |
| `geopulse_raw.store_catchment_areas` | 500-metre catchment polygons |
| `geopulse.stg_store_catchments` | dbt staging view |
| `geopulse.mart_store_catchment_summary` | dbt store catchment summary |

## Project Structure

```text
GeoPulse/
├── dashboard/
│   ├── app.py
│   └── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── dbt/
├── docs/
│   └── project_blueprint.md
├── notebooks/
├── sql/
│   ├── spatial_processing/
│   └── cannibalization_analysis/
├── src/
│   ├── data_generation/
│   ├── data_loading/
│   └── spatial_processing/
└── tests/
```

The dbt project is maintained separately in the `geopulse/` directory. Generated data files, credentials, and local environment files should not be committed to Git.

### Run the Dashboard Locally

**Prerequisites**

- Python 3.12 or a compatible Python version.
- Access to the Google Cloud project and the GeoPulse BigQuery datasets.
- Google Cloud authentication configured for the account with appropriate BigQuery permissions.

**1. Clone the repository**

```powershell
git clone https://github.com/lawrenceruth/GeoPulse.git
cd GeoPulse
```

**2. Create and activate a virtual environment**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use an approved environment activation method for your machine rather than changing system-wide execution policy unnecessarily.

**3. Install dashboard dependencies**

```powershell
python -m pip install --upgrade pip
pip install -r dashboard/requirements.txt
```

**4. Authenticate with Google Cloud**

Install the Google Cloud CLI if needed, then authenticate using your own authorized Google account:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project careflow-process-mining-509421
```

The authenticated account needs permission to query the required GeoPulse BigQuery tables. Never commit access tokens, service-account keys, or other credentials.

**5. Launch Streamlit**

```powershell
streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

### Reproducibility and Data Limitations

- Synthetic GPS data can be regenerated using the project's data-generation script and its documented configuration.
- Large generated datasets are excluded from Git and must be generated locally or supplied through an authorized data source.
- The dashboard queries BigQuery, so valid cloud authentication, dataset access, and the required tables must be available.
- GPS pings are independently generated observations, not continuous device trajectories.
- Simulated store coordinates and activity patterns are not verified real-world points of interest or observed customer behavior.
- Catchment overlap is a geographic measure. Actual retail cannibalization would require additional validated evidence, such as observed store visits, transaction data, and a suitable causal or comparative analysis.

### Current Implementation Status

**Implemented:** Synthetic GPS data generation, BigQuery geospatial tables, 500-metre catchment analysis, dbt staging and summary models, hourly Lekki observation analysis, polygon overlap analysis, and the interactive Streamlit dashboard.

**Potential future enhancements:** Automated data orchestration, additional spatial processing frameworks, more advanced trajectory analysis, and validated retail demand or sales modelling. These should be treated as future work until implemented and tested.