# GeoPulse: Hyper-Local Retail Mobility Analytics

GeoPulse is a geospatial analytics project that analyzes anonymized mobile GPS movement data to understand retail foot traffic, store catchments, and potential store cannibalization.

## Project Overview

Retailers often rely on static demographic information when evaluating new store locations. GeoPulse explores how dynamic movement patterns can provide additional insight into where customers travel throughout the day.

The project simulates large-scale mobile GPS data and processes it through a geospatial data pipeline to produce actionable retail mobility metrics.

## Business Problem

A retail real estate team needs to evaluate potential store locations using dynamic movement patterns rather than relying only on static demographic data.

GeoPulse is designed to answer questions such as:

- Where does foot traffic concentrate throughout the day?
- Which store catchments receive the most visitors?
- What are the peak traffic periods?
- How much movement occurs between multiple store locations?
- Where might a new store overlap with an existing store's customer traffic?

## Project Architecture

```text
Mobile GPS Data
      |
      v
Synthetic Data Generation
      |
      v
Snowflake Geospatial Data Lake
      |
      v
Apache Sedona / PySpark
      |
      v
500m Store Catchment Analysis
      |
      v
dbt ELT & Analytical Models
      |
      v
Footfall & Cannibalization Metrics
      |
      v
Kepler.gl / React
      |
      v
Interactive Mobility Dashboard
```

## Technology Stack

- Python
- Pandas
- PySpark
- Apache Sedona
- Snowflake
- SQL
- dbt
- Kepler.gl
- React
- Airflow
- Git & GitHub

## Core Analytics

GeoPulse will produce metrics including:

- Total GPS pings
- Unique devices
- Hourly footfall
- Peak traffic hour
- Store catchment visitors
- Cross-store visitors
- Catchment overlap
- Potential cannibalization rate
- Morning traffic
- Evening traffic

## Project Structure

```text
GeoPulse/
|-- dashboard/
|-- data/
|   |-- raw/
|   `-- processed/
|-- dbt/
|-- docs/
|-- notebooks/
|-- sql/
|-- src/
|   |-- data_generation/
|   |-- data_loading/
|   `-- spatial_processing/
`-- tests/

## Synthetic GPS Dataset

The initial synthetic mobility dataset has been generated using Python.

| Attribute | Details |
|---|---|
| GPS records | 10,000,000 |
| Simulated device IDs | Up to 250,000 |
| Simulation window | 7 days |
| Study area | Defined coordinate bounds around Lagos, Nigeria |
| Output format | Gzip-compressed CSV (`.csv.gz`) |
| Random seed | 42 |
| Generator | `src/data_generation/generate_gps_data.py` |
| Output file | `data/raw/gps_pings.csv.gz` |

### Data Generation Notes

- GPS coordinates are generated around synthetic activity hubs within the defined study-area bounds.
- Timestamp generation uses weighted hourly sampling to simulate variations in daily activity.
- Each GPS ping is generated independently; continuous device trajectories are not yet modelled.
- The dataset is synthetic and does not represent actual people, observed customer behaviour, or verified real-world points of interest.
- The generated data file is excluded from Git using `.gitignore`. Run the generator locally to recreate the dataset.

### Current Status

**Completed:** Initial synthetic GPS data generation and record-count verification.

**Next:** Snowflake ingestion, followed by distributed spatial processing and analytical modelling.