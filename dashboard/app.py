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
