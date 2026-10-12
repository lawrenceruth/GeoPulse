import json
import folium
from streamlit_folium import st_folium
import streamlit as st
import pandas as pd
from google.cloud import bigquery
import plotly.express as px

PROJECT_ID = "careflow-process-mining-509421"

st.set_page_config(
    page_title="GeoPulse | Retail Mobility Analytics",
    page_icon="📍",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F4F8F5;
        color: #18352D;
    }
    h1, h2, h3 {
        color: #124734 !important;
    }
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"] {
        color: #24483B !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("📍 GeoPulse")
st.subheader("Hyper-Local Retail Mobility Analytics")

st.markdown("""
Welcome to GeoPulse, a retail location analytics dashboard.

This dashboard helps us explore:

- Simulated store locations and catchment areas
- GPS ping observations around each store
- Comparisons between store catchments
- Geographic overlap between the two Lekki locations
- Hourly patterns in simulated GPS observations
""")

st.info("""
**Data note:** GeoPulse uses synthetic GPS observations and simulated
store locations. These results do not represent verified customer visits,
purchases, or actual sales cannibalization.
""")


@st.cache_data(ttl=600)
def load_store_summary():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            store_id,
            store_name,
            matched_gps_pings,
            unique_devices,
            avg_distance_meters
        FROM `{PROJECT_ID}.geopulse.mart_store_catchment_summary`
        ORDER BY store_id
    """

    return client.query(query).to_dataframe()


@st.cache_data(ttl=600)
def load_store_map_data():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            s.StoreID AS store_id,
            s.StoreName AS store_name,
            ST_Y(s.location) AS latitude,
            ST_X(s.location) AS longitude,
            ST_ASGEOJSON(a.catchment_geometry) AS catchment_geojson
        FROM `{PROJECT_ID}.geopulse_raw.store_locations` AS s
        LEFT JOIN `{PROJECT_ID}.geopulse_raw.store_catchment_areas` AS a
            ON s.StoreID = a.StoreID
        ORDER BY s.StoreID
    """

    return client.query(query).to_dataframe()


try:
    with st.spinner("Loading store metrics from BigQuery..."):
        stores = load_store_summary()

except Exception as error:
    st.error("Unable to load the GeoPulse store summary from BigQuery.")
    st.caption(
        "Check the error below before changing your Google credentials "
        "or project settings."
    )
    st.code(str(error))
    st.stop()


if stores.empty:
    st.error("The store summary query returned no records.")
    st.stop()

# Dashboard overview metrics
overview1, overview2, overview3 = st.columns(3)

overview1.metric("Total Store Locations", "5")
overview2.metric("Catchment Radius", "500 m")
overview3.metric("Data Source", "BigQuery")

st.divider()

st.sidebar.header("Dashboard Filters")

store_options = stores["store_name"].tolist()

selected_stores = st.sidebar.multiselect(
    "Select stores",
    options=store_options,
    default=store_options,
)

filtered = stores[
    stores["store_name"].isin(selected_stores)
].copy()

if filtered.empty:
    st.info("Select at least one store to display its metrics.")
    st.stop()



# KPI cards — calculate metrics from selected catchment records

@st.cache_data(ttl=600)
def load_selected_kpis(store_ids):
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            COUNT(*) AS total_pings,
            COUNT(DISTINCT DeviceID) AS total_unique_devices,
            AVG(distance_meters) AS average_distance
        FROM `{PROJECT_ID}.geopulse_raw.store_catchments`
        WHERE StoreID IN UNNEST(@store_ids)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "store_ids", "STRING", list(store_ids)
            )
        ]
    )

    result = client.query(
        query, job_config=job_config
    ).to_dataframe()

    return result.iloc[0]


selected_store_ids = filtered["store_id"].tolist()

kpi = load_selected_kpis(tuple(selected_store_ids))

total_pings = int(kpi["total_pings"] or 0)
total_store_devices = int(kpi["total_unique_devices"] or 0)
average_distance = kpi["average_distance"]

k1, k2, k3 = st.columns(3)

k1.metric("Total Matched GPS Pings", f"{total_pings:,}")
k2.metric("Total Unique Devices", f"{total_store_devices:,}")
k3.metric(
    "Average Distance to Store",
    f"{average_distance:,.1f} m"
    if pd.notna(average_distance)
    else "N/A",
)


st.caption(
    "Unique devices are counted once across the selected catchments. "
    "GPS pings remain observations, not verified customer visits."
)

st.divider()


# Interactive store map
st.header("Store Locations and Catchment Areas")

try:
    map_data = load_store_map_data()

    map_data = map_data[
        map_data["store_name"].isin(selected_stores)
    ].copy()

    if map_data.empty:
        st.info("Select a store to display its location.")
    else:
        center = [
            map_data["latitude"].mean(),
            map_data["longitude"].mean(),
        ]

        store_map = folium.Map(
            location=center,
            zoom_start=11,
            tiles="CartoDB positron",
        )

        colors = [
            "#087F5B", "#176B87", "#3D806D",
            "#57958A", "#124734"
        ]

        for index, (_, store) in enumerate(map_data.iterrows()):
            color = colors[index % len(colors)]

            if pd.notna(store["catchment_geojson"]):
                geometry = json.loads(store["catchment_geojson"])

                folium.GeoJson(
                    geometry,
                    name=f"{store['store_name']} catchment",
                    style_function=lambda feature, c=color: {
                        "fillColor": c,
                        "color": c,
                        "weight": 2,
                        "fillOpacity": 0.22,
                    },
                    tooltip=f"{store['store_name']} — 500 m catchment",
                ).add_to(store_map)

            folium.Marker(
                location=[
                    store["latitude"],
                    store["longitude"],
                ],
                tooltip=store["store_name"],
                popup=(
                    f"<b>{store['store_name']}</b><br>"
                    f"Store ID: {store['store_id']}<br>"
                    "Catchment radius: 500 m"
                ),
            ).add_to(store_map)

        folium.LayerControl().add_to(store_map)

        st_folium(
            store_map,
            use_container_width=True,
            height=520,
            returned_objects=[],
        )

        st.caption(
            "Shaded areas show simulated 500-metre catchments. "
            "Overlap does not prove customer switching or sales loss."
        )

except Exception as error:
    st.error("The store map could not be loaded.")
    st.code(str(error))


# Store comparison table
st.header("Store Catchment Summary")

display = filtered.rename(
    columns={
        "store_id": "Store ID",
        "store_name": "Store",
        "matched_gps_pings": "Matched GPS Pings",
        "unique_devices": "Unique Devices",
        "avg_distance_meters": "Average Distance (m)",
    }
)

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    height=300,
)

# Store comparison chart
st.header("Matched GPS Pings by Store")

fig = px.bar(
    filtered,
    x="store_name",
    y="matched_gps_pings",
    color="store_name",
    text="matched_gps_pings",
    hover_data={
    "store_name": True,
    "matched_gps_pings": ":,",
    "unique_devices": ":,",
    "avg_distance_meters": ":.1f",
},
    labels={
        "store_name": "Store",
        "matched_gps_pings": "Matched GPS Pings",
        "color": "Store",
    },
    color_discrete_sequence=[
        "#087F5B",
        "#176B87",
        "#3D806D",
        "#57958A",
        "#124734",
    ],
)

fig.update_traces(texttemplate="%{text:,}", textposition="outside")
fig.update_layout(
    showlegend=False,
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#F4F8F5",
    font_color="#18352D",
    yaxis_title="Matched GPS Pings",
    xaxis_title="",
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Metrics are calculated from the existing dbt store catchment summary "
    "in BigQuery. The displayed total adds store-level counts together."
)


st.divider()

st.subheader("Hourly GPS Observation Patterns — Lekki")
st.caption(
    "Hourly synthetic GPS pings within the 500 m catchments of "
    "GeoPulse Lekki A and GeoPulse Lekki B. Hours are shown in "
    "West Africa Time (WAT, UTC+1). These observations do not "
    "represent verified customer visits or purchases."
)

@st.cache_data(ttl=300)
def load_hourly_lekki_data():
    query = """
    WITH lekki_pings AS (
        SELECT
            StoreID,
            DeviceID,
            Timestamp,
            EXTRACT(
                HOUR FROM DATETIME(Timestamp, 'Africa/Lagos')
            ) AS hour_wat
        FROM
            `careflow-process-mining-509421.geopulse_raw.store_catchments`
        WHERE StoreID IN ('STORE_001', 'STORE_002')
    )
    SELECT
        hour_wat,
        COUNTIF(StoreID = 'STORE_001') AS store_a_pings,
        COUNTIF(StoreID = 'STORE_002') AS store_b_pings
    FROM lekki_pings
    GROUP BY hour_wat
    ORDER BY hour_wat
    """

    client = bigquery.Client()
    return client.query(query).to_dataframe()

hourly = load_hourly_lekki_data()

if not hourly.empty:
    hourly = hourly.sort_values("hour_wat")

    hourly_chart_data = hourly.melt(
        id_vars="hour_wat",
        value_vars=["store_a_pings", "store_b_pings"],
        var_name="store",
        value_name="gps_pings",
    )

    hourly_chart_data["store"] = hourly_chart_data["store"].map({
        "store_a_pings": "GeoPulse Lekki A",
        "store_b_pings": "GeoPulse Lekki B",
    })

    hourly_chart_data["hour_label"] = hourly_chart_data[
        "hour_wat"
    ].map(lambda hour: f"{int(hour):02d}:00")

    fig_hourly = px.line(
        hourly_chart_data,
        x="hour_label",
        y="gps_pings",
        color="store",
        markers=True,
        title="Hourly GPS Pings by Lekki Store",
        labels={
            "hour_label": "Hour of Day (WAT)",
            "gps_pings": "Synthetic GPS Pings",
            "store": "Store",
        },
        category_orders={
            "hour_label": [
                f"{hour:02d}:00" for hour in range(24)
            ],
            "store": ["GeoPulse Lekki A", "GeoPulse Lekki B"],
        },
    )

    fig_hourly.update_layout(
        hovermode="x unified",
        xaxis=dict(type="category"),
        legend_title_text="Store",
    )

    st.plotly_chart(fig_hourly, use_container_width=True)

    st.caption(
        "Interpretation: compare the timing and relative volume of "
        "synthetic observations across the two catchments. Similar "
        "patterns alone do not establish customer switching or "
        "actual sales cannibalization."
    )
else:
    st.info("No hourly GPS observations are available for the two Lekki stores.")


st.divider()

st.subheader("Geographic Catchment Overlap — Lekki")
st.caption(
    "This analysis measures the geometric intersection between "
    "the two simulated 500 m catchment polygons. It does not "
    "measure actual customer switching or sales cannibalization."
)

@st.cache_data(ttl=300)
def load_lekki_overlap():
    query = """
    WITH lekki_catchments AS (
        SELECT
            StoreID,
            StoreName,
            catchment_geometry
        FROM
            `careflow-process-mining-509421.geopulse_raw.store_catchment_areas`
        WHERE StoreID IN ('STORE_001', 'STORE_002')
    ),
    store_a AS (
        SELECT *
        FROM lekki_catchments
        WHERE StoreID = 'STORE_001'
    ),
    store_b AS (
        SELECT *
        FROM lekki_catchments
        WHERE StoreID = 'STORE_002'
    )
    SELECT
        a.StoreName AS store_a,
        b.StoreName AS store_b,
        ST_AREA(a.catchment_geometry) AS store_a_area_sqm,
        ST_AREA(b.catchment_geometry) AS store_b_area_sqm,
        ST_AREA(
            ST_INTERSECTION(
                a.catchment_geometry,
                b.catchment_geometry
            )
        ) AS shared_area_sqm,
        SAFE_DIVIDE(
            ST_AREA(ST_INTERSECTION(
                a.catchment_geometry,
                b.catchment_geometry
            )),
            ST_AREA(a.catchment_geometry)
        ) * 100 AS pct_store_a_area_overlapping,
        SAFE_DIVIDE(
            ST_AREA(ST_INTERSECTION(
                a.catchment_geometry,
                b.catchment_geometry
            )),
            ST_AREA(b.catchment_geometry)
        ) * 100 AS pct_store_b_area_overlapping
    FROM store_a AS a
    CROSS JOIN store_b AS b
    """

    client = bigquery.Client()
    return client.query(query).to_dataframe()


overlap = load_lekki_overlap()

if not overlap.empty:
    result = overlap.iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Shared Geographic Area",
        f"{result['shared_area_sqm']:,.0f} m²",
    )

    col2.metric(
        "Store A Area Overlapping",
        f"{result['pct_store_a_area_overlapping']:.2f}%",
    )

    col3.metric(
        "Store B Area Overlapping",
        f"{result['pct_store_b_area_overlapping']:.2f}%",
    )

    area_data = pd.DataFrame({
        "Area Type": [
            "Lekki A Catchment",
            "Lekki B Catchment",
            "Shared Area",
        ],
        "Area (m²)": [
            result["store_a_area_sqm"],
            result["store_b_area_sqm"],
            result["shared_area_sqm"],
        ],
    })

    fig_overlap = px.bar(
        area_data,
        x="Area Type",
        y="Area (m²)",
        color="Area Type",
        text="Area (m²)",
        title="Catchment Areas and Their Shared Geographic Area",
    )

    fig_overlap.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

    fig_overlap.update_layout(
        showlegend=False,
        yaxis_title="Area (square metres)",
        xaxis_title="",
    )

    st.plotly_chart(fig_overlap, use_container_width=True)

    st.caption(
        "Interpretation: the shared area indicates how much the "
        "two simulated geographic catchments intersect. It is a "
        "spatial planning indicator, not evidence of lost revenue."
    )
else:
    st.warning(
        "No geographic overlap results were returned. "
        "Check that both Lekki catchment polygons exist in BigQuery."
    )
