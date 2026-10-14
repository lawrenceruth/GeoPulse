# GeoPulse - Hyper-Local Retail Mobility Analytics

## 1. Project Overview

GeoPulse is a geospatial retail analytics portfolio project designed to explore how simulated mobility patterns can support retail site-selection decisions.

The project generates synthetic mobile GPS observations, processes them using Google BigQuery's geospatial capabilities, transforms catchment data through dbt, and presents analytical results in an interactive Streamlit dashboard.

The current implementation focuses on store catchments, hourly observation patterns, geographic overlap, and shared device observations around simulated retail locations in Lagos, Nigeria.

**Data limitation:** All GPS observations and store locations are synthetic. They do not represent verified real-world people, customer visits, purchases, or actual retail performance.

## 2. Domain

**Retail Strategy & Geospatial Analytics**

## 3. Business Problem

Retailers evaluating new locations need to understand how proposed stores might overlap with existing locations.

Static demographic information alone may not capture differences in geographic coverage or the timing of observed mobility patterns.

GeoPulse explores how synthetic location observations and geospatial analysis can help answer questions such as:

- How many GPS observations fall within each store's catchment?
- How many distinct simulated devices appear within each catchment?
- At what times do observations peak?
- How much geographic area do two store catchments share?
- How many simulated devices appear in multiple catchments?
- Which locations may warrant further investigation before a real site-selection decision?

The results demonstrate analytical methods rather than establish real customer behaviour or financial cannibalization.

## 4. Case Study

A fictional coffee-chain real estate team is evaluating store locations in Lagos.

GeoPulse analyses synthetic GPS observations around five simulated store locations. Each location has a 500-metre catchment used to identify nearby observations.

The analysis compares catchment activity, hourly observation patterns, shared device IDs, and geographic overlap. These measures can help demonstrate how a retailer might investigate potential location conflicts.

The results are exploratory. Shared device observations and overlapping catchments do not prove that customers switch stores, that sales are lost, or that a new location would cannibalize an existing store.

## 5. Implemented Architecture

The current pipeline is:

Synthetic GPS Data Generation
->->
BigQuery Raw GPS and Store Location Tables
->->
BigQuery GEOGRAPHY and Spatial Processing
->->
500-Metre Store Catchment Analysis
->->
dbt Staging and Catchment Summary Models
->->
Hourly Observation and Geographic Overlap Analysis
->->
Streamlit Dashboard with Folium and Plotly

### Implemented Components

- **Data generation:** Python scripts generate synthetic GPS observations.
- **Data platform:** Google BigQuery stores the raw data and spatially processed tables.
- **Spatial processing:** BigQuery geospatial SQL creates store catchments and matches GPS observations to them.
- **Analytical modelling:** dbt stages catchment data and produces store-level summary metrics.
- **Additional analysis:** SQL calculates hourly observation patterns, shared-device measures, and geographic catchment overlap.
- **Visualization:** Streamlit provides interactive filters, map layers, KPI cards, tables, and charts.

The dbt project is maintained in the `geopulse/` directory.

## 6. Technology Stack

### Data Generation
- Python
- Pandas
- NumPy

### Data Platform
- Google BigQuery
- BigQuery GEOGRAPHY data type
- Google Cloud authentication

### Spatial Processing
- BigQuery geospatial SQL
- `ST_GEOGPOINT`
- `ST_DISTANCE`
- `ST_BUFFER`
- `ST_INTERSECTION`
- `ST_AREA`

### Data Transformation and Modelling
- SQL
- dbt

### Visualization
- Streamlit
- Folium
- Plotly

### Development and Version Control
- Git
- GitHub

Snowflake, Apache Spark, Apache Sedona, Kepler.gl, React, H3, and Apache Airflow are not part of the current implemented pipeline. They may be considered as future enhancements if they provide a clear benefit.

## 7. Development Stages

### Stage 1 - Synthetic Data Generation

Generate synthetic GPS observations containing:

- DeviceID
- Latitude
- Longitude
- Timestamp

The dataset is designed for portfolio-scale analysis. Generated records should remain clearly identified as synthetic, and large raw data files should not be committed to GitHub.

### Stage 2 - BigQuery Spatial Processing

Load GPS observations and simulated store locations into BigQuery.

Create spatial representations of GPS points, generate 500-metre store catchments, and identify observations within those catchments using BigQuery geospatial SQL.

### Stage 3 - Analytical Modelling

Use dbt to transform catchment records into store-level summary metrics.

Analyse observation counts, distinct device IDs, average distances, hourly patterns, shared-device observations, and geographic overlap.

### Stage 4 - Interactive Dashboard

Present the implemented analysis through Streamlit, Folium, and Plotly.

Allow users to filter store locations and explore catchment activity, hourly observations, and geographic overlap.

### Stage 5 - Future Enhancements

Potential extensions include:

- Automated pipeline orchestration
- H3 hexagonal spatial aggregation
- Additional temporal filters
- More advanced map visualizations
- Historical comparisons and scenario analysis
- Distributed spatial processing where scale requirements justify it
- Real retail sales or transaction data, if legitimately available and appropriately governed

These enhancements remain future work until implemented and tested.

## 8. Core Analytical Metrics

The current project includes or investigates the following measures:

- Total GPS observations
- Distinct simulated devices
- GPS observations within each store catchment
- Average distance from matched observations to a store
- Hourly observation counts
- Shared device IDs across catchments
- Geographic catchment overlap area
- Catchment overlap percentage

### Interpretation Guidelines

- **GPS observations** are generated location records, not confirmed visits.
- **Distinct devices** are simulated identifiers, not verified individual customers.
- **Hourly peaks** reflect the synthetic data-generation patterns.
- **Shared devices** indicate that the same simulated identifier appears in multiple catchments; they do not establish customer switching.
- **Geographic overlap** measures shared catchment area, not sales loss.
- **Cannibalization** remains a business hypothesis requiring real-world validation and appropriate sales, customer, and location evidence.

## 9. Data Quality and Integrity

Data preparation and analytical development should consider:

- Missing or invalid coordinates
- Invalid timestamps
- Duplicate observations
- Spatial join completeness
- Store assignment consistency
- Correct distance calculations
- Accurate aggregation of distinct devices
- dbt model compilation and tests
- Consistency between SQL results and dashboard metrics

Validation claims should be based on checks that have actually been executed.

## 10. Scalability and Reproducibility

The current implementation uses BigQuery for spatial processing and analytical queries.

Future scalability work should evaluate query cost, partitioning, clustering, data volume, and processing requirements before introducing additional distributed-processing tools.

The repository should document required dependencies, cloud authentication, dataset names, model dependencies, and dashboard startup instructions. Large generated datasets and secrets must remain outside version control.

## 11. Portfolio Objective

GeoPulse demonstrates practical work in:

- Synthetic data generation
- SQL analytics
- Geospatial data processing
- BigQuery
- dbt modelling and testing
- Interactive dashboard development
- Data visualization
- Git and GitHub workflow
- Business-oriented analytical storytelling
- Responsible interpretation of synthetic data

The repository is intended to be clear, reproducible, and suitable for professional portfolio presentation.

## 12. Development Principles

GeoPulse is developed incrementally.

Each meaningful component should be:

1. Implemented
2. Tested
3. Documented
4. Committed to the appropriate Git branch
5. Reviewed before being merged into `main`

The `main` branch should remain clean, tested, and presentation-ready.

Documentation must reflect the actual state of the implementation. Planned technologies and unimplemented features must be labelled as future work rather than presented as completed capabilities.
