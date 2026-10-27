# GeoPulse dbt Models

This dbt project turns the raw store-catchment table in BigQuery into the summary table the GeoPulse dashboard reads. It is small on purpose: one staging view and one mart table.

```text
raw (geopulse_raw)            staging (view)              mart (table)
store_catchments  ───────▶  stg_store_catchments  ───────▶  mart_store_catchment_summary
one row per ping inside                                      one row per store
a store's 500 m catchment                                    ──▶ Streamlit dashboard
```

## What's in the project

```text
geopulse/
├── dbt_project.yml
└── models/
    ├── staging/
    │   ├── sources.yml                       # points dbt at the raw dataset
    │   └── stg_store_catchments.sql
    └── marts/
        ├── mart_store_catchment_summary.sql
        └── schema.yml                        # mart descriptions and tests
```

The standard dbt folders (`tests/`, `macros/`, `analyses/`, `seeds/`, `snapshots/`) are not used yet.

## Models

### `stg_store_catchments` (view)

A cleaned-up view over `store_catchments` in the raw dataset. Each row is one GPS ping that fell inside a store's 500 m catchment, with the store, the device, the timestamp and the ping's distance from the store. Because it is a view, it always reflects the raw table.

### `mart_store_catchment_summary` (table)

One row per store. This is what the dashboard's Executive page, store tables, scorecard and filters are built on.

| Column | Meaning |
|---|---|
| `store_id` | Store key, for example `STORE_001` |
| `store_name` | Store name, for example Lekki A |
| `matched_gps_pings` | Pings inside the store's catchment |
| `unique_devices` | Distinct devices seen in that catchment |
| `avg_distance_meters` | Average distance from those pings to the store |

Two things to keep in mind when reading the mart:

- **A ping in two catchments counts once per store.** The two Lekki catchments overlap by about 81.6%, so the five stores add up to 213,256 matched pings, which is more than the number of distinct pings.
- **Don't add `unique_devices` across stores.** Each store counts its own distinct devices, so the store figures sum to 190,604 while the network has 120,761 distinct devices. The dashboard counts network-wide devices straight from the raw table.

The map pages, the Lekki overlap and the H3 views read the raw tables directly. dbt only builds the summary.

## Configuration

Set in `dbt_project.yml`:

| Setting | Value |
|---|---|
| Project and profile | `geopulse` |
| Version | `1.0.0` |
| Staging models | views |
| Mart models | tables |

## Running it

You need dbt with the BigQuery adapter (`dbt-bigquery`) and a `geopulse` profile with your project, dataset, authentication and dataset location (`africa-south1`). Run these from the repository root:

```powershell
cd geopulse
dbt debug    # checks the connection and the profile
dbt run      # builds the staging view and the mart table
dbt test     # runs the tests in schema.yml
```

To rebuild only the mart: `dbt run --select mart_store_catchment_summary`.

## Git notes

- **Credentials stay out of the repo.** dbt reads `profiles.yml` from `~/.dbt/` by default, which is outside the repository. Don't copy it in, and never commit a service-account key.
- **Ignored on purpose:** `target/`, `dbt_packages/` and `logs/` are generated, so they are listed in `.gitignore`.

## How it connects to the rest of the project

- The dashboard reads `mart_store_catchment_summary` for its store figures and checks its H3 hexagon totals against this table.
- A daily Airflow pipeline is drafted but not deployed yet. When it runs, it will call dbt to rebuild this mart.

For the project overview, dashboard setup and the limits of the simulated data, see the root [README.md](../README.md).