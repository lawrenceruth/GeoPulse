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