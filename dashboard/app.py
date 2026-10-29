"""GeoPulse | Retail Mobility Analytics (Streamlit dashboard)

Run:  streamlit run app.py
Needs Streamlit >= 1.50 (uses width="stretch" and st.dataframe(height="content")).
Put the .streamlit/config.toml from the notes next to this file for theme + minimal toolbar.
"""
from __future__ import annotations

import html
import json
import math
import os
import re
from pathlib import Path

from google.oauth2 import service_account

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk  # ships with Streamlit; if missing: pip install pydeck
import streamlit as st
from google.cloud import bigquery
from streamlit_folium import st_folium

try:  # H3 cells are assigned in Python (BigQuery has no H3 library in africa-south1)
    import h3  # pip install h3
except ImportError:
    h3 = None

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
PROJECT_ID = os.getenv("GEOPULSE_PROJECT_ID", "careflow-process-mining-509421")
RAW_DATASET = f"{PROJECT_ID}.geopulse_raw"
MART_TABLE = f"{PROJECT_ID}.geopulse.mart_store_catchment_summary"
FULL_DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "gps_pings.csv.gz"

LEKKI_A, LEKKI_B = "Lekki A", "Lekki B"  # store names are shortened once, right after loading
LEKKI_IDS = ("STORE_001", "STORE_002")
# H3: the dataset lives in africa-south1, where no BigQuery H3 function library exists, so ping coordinates are
# read from BigQuery and the H3 cell is assigned with the Python `h3` package. Set GEOPULSE_PING_TABLE to the raw
# GPS table (the one holding each ping's latitude/longitude) if automatic detection picks the wrong one.
PING_TABLE = os.getenv("GEOPULSE_PING_TABLE")
H3_RESOLUTIONS = {"Resolution 8 · about 0.74 km² per hexagon": 8, "Resolution 9 · about 0.11 km² per hexagon": 9}
# Tables whose last-modified time defines "Data refreshed" (the newest one wins).
FRESHNESS_TABLES = [MART_TABLE, f"{RAW_DATASET}.store_locations", f"{RAW_DATASET}.store_catchment_areas",
                    f"{RAW_DATASET}.store_catchments"]
H3_PALETTE = ["#EBD9A8", "#E0B96A", "#C98B3F", "#A0562A", "#5C2E14"]  # pale sand to deep terracotta
H3_BREAKS = (0.05, 0.15, 0.40, 0.70, 1.0)  # class limits as a share of the busiest hexagon
DIST_MIN_SPREAD_M = 25  # below this spread, distance is scored neutral (50) instead of magnified

SAGE, SAGE_DARK, SAGE_LIGHT = "#87917A", "#526047", "#DCE1D4"
IVORY, CARD, ZEBRA = "#F1EEE4", "#FFFDF8", "#EEF0E8"
CHARCOAL, MUTED, BORDER = "#292E28", "#555D52", "#C8CCBF"
NAV, NAV_HOVER, TERRACOTTA = "#526047", "#414D38", "#B56C36"

STORE_COLORS = {
    "Lekki A": "#2F3E2A",
    "Lekki B": "#C0773A",
    "Victoria Island": "#3F7F8C",
    "Ikeja": "#8C6BB1",
    "Yaba": "#B8A04A",
}

st.set_page_config(
    page_title="GeoPulse | Retail Mobility Analytics",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Styling (plain string + token replacement, so CSS braces never need doubling)
# ----------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap');
.stApp { background:__IVORY__; color:__CHARCOAL__; font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(241,238,228,.98); }
h1,h2,h3,h4 { color:__CHARCOAL__ !important; letter-spacing:-.02em; }
hr { border-color:__BORDER__; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] { background:__NAV__; border-right:1px solid #3F4A37; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] summary { color:#FFFDF8 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { font-weight:600; padding:2px 6px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:__NAV_HOVER__; border-radius:7px; }
[data-testid="stSidebar"] [data-testid="stExpander"] { border:1px solid #87917A; border-radius:10px; background:transparent; }

/* Sidebar buttons (Select all / Clear / Reset / downloads) */
[data-testid="stSidebar"] .stButton > button, [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
  background:__NAV__ !important; color:#FFFDF8 !important; border:1px solid #87917A !important; box-shadow:none !important; opacity:1 !important; }
[data-testid="stSidebar"] .stButton > button p, [data-testid="stSidebar"] [data-testid="stDownloadButton"] button p { color:#FFFDF8 !important; }
[data-testid="stSidebar"] .stButton > button:hover, [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
  background:__NAV_HOVER__ !important; border-color:__SAGE_LIGHT__ !important; }

/* Sidebar multiselect: every layer painted the sidebar colour (also when empty), tags lighter */
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] input {
  background:__NAV__ !important; background-color:__NAV__ !important; box-shadow:none !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  border:1px solid #87917A !important; border-radius:10px !important; max-height:none !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] input { color:#FFFDF8 !important; -webkit-text-fill-color:#FFFDF8 !important; caret-color:#FFFDF8 !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] input::placeholder { color:#DCE1D4 !important; -webkit-text-fill-color:#DCE1D4 !important; opacity:1; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] [data-baseweb="tag"] {
  background:#7A8A6B !important; border:1px solid #A9B59B !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] [data-baseweb="tag"] * {
  color:#FFFDF8 !important; fill:#FFFDF8 !important; background:transparent !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] svg { fill:__SAGE_LIGHT__ !important; }
/* Sidebar expanders and toggles: no white strips */
[data-testid="stSidebar"] [data-testid="stExpander"] details, [data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover { background:transparent !important; }
[data-testid="stHeaderActionElements"] { display:none; }
/* Dropdown list opens in a portal outside the sidebar */
div[data-baseweb="popover"] ul[role="listbox"], div[data-baseweb="popover"] li[role="option"] { background:__NAV__ !important; color:#FFFDF8 !important; }
div[data-baseweb="popover"] li[role="option"]:hover, div[data-baseweb="popover"] li[aria-selected="true"] { background:__NAV_HOVER__ !important; }

/* ---- Main area ---- */
.eyebrow { text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; color:__SAGE_DARK__; font-weight:700; margin-bottom:.3rem; }
.hero { padding:1.2rem 1.45rem; border:1px solid __BORDER__; border-radius:14px; background:linear-gradient(115deg,#FFFDF8 0%,#E2E6D9 100%); margin-bottom:.9rem; position:relative; }
.hero-title { font-family:'Playfair Display',serif; font-size:2.1rem; line-height:1.15; color:__CHARCOAL__; margin:0; }
.hero-sub { color:__MUTED__; margin-top:.45rem; font-size:.98rem; }
.filter-note { color:__MUTED__; font-size:.86rem; margin:-.3rem 0 .7rem; }
.callout { background:#E1E6D9; border:1px solid #BCC5B2; border-left:5px solid __SAGE_DARK__; border-radius:10px; padding:.95rem 1.15rem; margin:.3rem 0 1rem; color:__CHARCOAL__; }
.callout b.h { font-size:1.08rem; }
.callout .why { display:block; margin-top:.35rem; color:__MUTED__; }
.icard { min-height:92px; box-sizing:border-box; background:__CARD__; border:1px solid __BORDER__; border-left:4px solid __SAGE_DARK__; border-radius:9px; padding:.8rem 1rem; margin:0 0 .65rem; color:__CHARCOAL__; }
.icard b { display:block; margin-bottom:.2rem; }
.rank-badge { display:inline-block; background:__SAGE_DARK__; color:#FFFDF8; border-radius:999px; padding:.2rem .55rem; font-weight:800; margin-right:.35rem; }
.legend-panel { background:__CARD__; border:1px solid __BORDER__; padding:.7rem .9rem; border-radius:9px; font-size:.86rem; color:__CHARCOAL__; }
.empty { background:#E1E6D9; border:1px solid #BCC5B2; border-left:5px solid __SAGE_DARK__; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0 1rem; }
.footer { border-top:1px solid __BORDER__; margin-top:1.5rem; padding:.65rem 0; color:__MUTED__; font-size:.78rem; }

[data-testid="stMetric"] { background:__CARD__; border:1px solid __BORDER__; border-radius:12px; padding:14px 16px; box-shadow:0 3px 10px rgba(41,46,40,.06); }
[data-testid="stMetricLabel"] { color:__MUTED__ !important; font-size:.84rem !important; line-height:1.2 !important; }
[data-testid="stMetricValue"] { color:__SAGE_DARK__ !important; font-weight:700 !important; font-size:clamp(1.1rem,1.7vw,1.8rem) !important; overflow-wrap:anywhere; }
div[data-testid="stPlotlyChart"] { background:__CARD__; border:1px solid __BORDER__; border-radius:12px; overflow:hidden; }
div[data-testid="stDataFrame"] { background:__CARD__; border:1px solid __BORDER__; border-radius:12px; overflow:hidden; }
[data-testid="stDownloadButton"] button, .stButton > button { border-radius:8px; border:1px solid #87917A; font-weight:600; }
.stSlider label, .stSlider p { color:__CHARCOAL__ !important; font-weight:700 !important; }
.tbl { width:100%; border-collapse:collapse; background:__CARD__; border:1px solid __BORDER__; border-radius:12px; overflow:hidden; font-size:.92rem; }
.tbl th { background:__SAGE_DARK__; color:#FFFDF8; text-align:left; padding:.55rem .75rem; font-weight:700; }
.tbl td { padding:.6rem .75rem; border-bottom:1px solid __BORDER__; color:__CHARCOAL__; vertical-align:top; }
.tbl tr:nth-child(even) td { background:#EEF0E8; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
@media (prefers-reduced-motion: no-preference) { .hero { animation: arrive .4s ease-out both; } @keyframes arrive { from{opacity:.65;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} } }
</style>
"""
_TOKENS = {"IVORY": IVORY, "CHARCOAL": CHARCOAL, "BORDER": BORDER, "NAV": NAV, "NAV_HOVER": NAV_HOVER,
           "SAGE": SAGE, "SAGE_DARK": SAGE_DARK, "SAGE_LIGHT": SAGE_LIGHT, "CARD": CARD, "MUTED": MUTED}
for _k, _v in _TOKENS.items():
    CSS = CSS.replace(f"__{_k}__", _v)
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Data access (client is cached; each query is cached)
# ----------------------------------------------------------------------------

@st.cache_resource
def get_client() -> bigquery.Client:
    try:
        service_account_info = st.secrets["gcp_service_account"]
    except (FileNotFoundError, KeyError):
        service_account_info = None

    if service_account_info is not None:
        credentials = service_account.Credentials.from_service_account_info(
            dict(service_account_info)
        )
        return bigquery.Client(
            project=PROJECT_ID,
            credentials=credentials,
        )

    # Local development: use Google Cloud CLI credentials.
    return bigquery.Client(project=PROJECT_ID)

def query_df(sql: str, params=None) -> pd.DataFrame:
    cfg = bigquery.QueryJobConfig(query_parameters=params or [])
    return get_client().query(sql, job_config=cfg).to_dataframe()


@st.cache_data(ttl=600, show_spinner="Loading data…")
def load_store_summary() -> pd.DataFrame:
    return query_df(f"""
        SELECT store_id, store_name, matched_gps_pings, unique_devices, avg_distance_meters
        FROM `{MART_TABLE}` ORDER BY store_id""")


@st.cache_data(ttl=600, show_spinner="Loading data…")
def load_store_map_data() -> pd.DataFrame:
    return query_df(f"""
        SELECT s.StoreID AS store_id, s.StoreName AS store_name,
               ST_Y(s.location) AS latitude, ST_X(s.location) AS longitude,
               ST_ASGEOJSON(a.catchment_geometry) AS catchment_geojson
        FROM `{RAW_DATASET}.store_locations` s
        LEFT JOIN `{RAW_DATASET}.store_catchment_areas` a ON s.StoreID = a.StoreID
        ORDER BY s.StoreID""")


@st.cache_data(ttl=300, show_spinner="Loading data…")
def load_selected_kpis(store_ids: tuple) -> pd.Series:
    return query_df(f"""
        SELECT COUNT(*) AS total_pings, COUNT(DISTINCT DeviceID) AS total_unique_devices,
               AVG(distance_meters) AS average_distance
        FROM `{RAW_DATASET}.store_catchments`
        WHERE StoreID IN UNNEST(@store_ids)""",
        [bigquery.ArrayQueryParameter("store_ids", "STRING", list(store_ids))]).iloc[0]


@st.cache_data(ttl=300, show_spinner="Loading data…")
def load_hourly_all() -> pd.DataFrame:
    return query_df(f"""
        SELECT StoreID AS store_id,
               EXTRACT(HOUR FROM DATETIME(Timestamp, 'Africa/Lagos')) AS hour_wat,
               COUNT(*) AS pings
        FROM `{RAW_DATASET}.store_catchments`
        GROUP BY store_id, hour_wat ORDER BY store_id, hour_wat""")


@st.cache_data(ttl=300, show_spinner="Loading data…")
def load_lekki_overlap() -> pd.DataFrame:
    return query_df(f"""
      WITH a AS (SELECT StoreName, catchment_geometry FROM `{RAW_DATASET}.store_catchment_areas` WHERE StoreID='STORE_001'),
           b AS (SELECT StoreName, catchment_geometry FROM `{RAW_DATASET}.store_catchment_areas` WHERE StoreID='STORE_002')
      SELECT ST_AREA(a.catchment_geometry) AS store_a_area_sqm,
             ST_AREA(b.catchment_geometry) AS store_b_area_sqm,
             ST_AREA(ST_INTERSECTION(a.catchment_geometry, b.catchment_geometry)) AS shared_area_sqm,
             SAFE_DIVIDE(ST_AREA(ST_INTERSECTION(a.catchment_geometry, b.catchment_geometry)), ST_AREA(a.catchment_geometry))*100 AS pct_a,
             SAFE_DIVIDE(ST_AREA(ST_INTERSECTION(a.catchment_geometry, b.catchment_geometry)), ST_AREA(b.catchment_geometry))*100 AS pct_b
      FROM a CROSS JOIN b""")


@st.cache_data(ttl=300, show_spinner="Loading data…")
def load_shared_devices() -> int:
    df = query_df(f"""
      SELECT COUNT(DISTINCT a.DeviceID) AS shared_device_ids
      FROM `{RAW_DATASET}.store_catchments` a
      JOIN `{RAW_DATASET}.store_catchments` b ON a.DeviceID = b.DeviceID
      WHERE a.StoreID='STORE_001' AND b.StoreID='STORE_002'""")
    return int(df.iloc[0]["shared_device_ids"])


@st.cache_data(ttl=300, show_spinner="Loading data…")
def load_data_freshness() -> str | None:
    """Newest last-modified time across the mart and the raw tables the dashboard reads."""
    stamps = []
    for table_id in FRESHNESS_TABLES:
        try:
            stamps.append(pd.Timestamp(get_client().get_table(table_id).modified))
        except Exception:
            continue
    if not stamps:
        return None
    return fmt_wat(max(stamps))


def fmt_wat(ts: pd.Timestamp) -> str:
    ts = pd.Timestamp(ts).tz_convert("Africa/Lagos")
    return f"{ts.day} {ts:%b %Y}, {ts.hour}:{ts:%M} WAT"


@st.cache_data(ttl=600, show_spinner=False)
def data_pulled_at() -> str:
    """Time of the latest pull from BigQuery. The cache entry is created at pull time and renewed every 10 minutes."""
    return fmt_wat(pd.Timestamp.now(tz="Africa/Lagos"))


@st.cache_data(ttl=3600, show_spinner="Loading data…")
def detect_ping_source() -> dict:
    """Find the raw GPS table that holds ping coordinates (store_catchments only has distances)."""
    cols = query_df(f"SELECT table_name, column_name, data_type FROM `{RAW_DATASET}.INFORMATION_SCHEMA.COLUMNS`")
    best, best_score = None, -1
    for table, grp in cols.groupby("table_name"):
        if PING_TABLE and table != PING_TABLE:
            continue
        names = {c.lower(): c for c in grp["column_name"]}
        pick = lambda options: next((names[o] for o in options if o in names), None)
        dev = pick(("deviceid", "device_id", "device", "ad_id", "maid"))
        ts = pick(("timestamp", "ts", "event_time", "ping_time", "datetime", "recorded_at"))
        lat = pick(("latitude", "lat", "ping_latitude", "gps_latitude"))
        lon = pick(("longitude", "lon", "lng", "long", "ping_longitude", "gps_longitude"))
        geog = grp.loc[grp["data_type"] == "GEOGRAPHY", "column_name"]
        if not (dev and ts and ((lat and lon) or not geog.empty)):
            continue
        score = (2 if re.search("gps|ping", table, re.I) else 0) + (1 if (lat and lon) else 0)
        if score > best_score:
            best_score = score
            best = {"table": f"{RAW_DATASET}.{table}", "dev": f"`{dev}`", "ts": f"`{ts}`",
                    "lat": f"SAFE_CAST(`{lat}` AS FLOAT64)" if lat and lon else f"ST_Y(`{geog.iloc[0]}`)",
                    "lon": f"SAFE_CAST(`{lon}` AS FLOAT64)" if lat and lon else f"ST_X(`{geog.iloc[0]}`)"}
    if best is None:
        summary = "; ".join(f"{t}: {', '.join(g['column_name'])}" for t, g in cols.groupby("table_name"))
        raise RuntimeError("No table with ping coordinates plus DeviceID and Timestamp was found in "
                           f"{RAW_DATASET}. Tables and columns: {summary}. Load the GPS pings table into BigQuery "
                           "or set GEOPULSE_PING_TABLE.")
    return best


@st.cache_data(ttl=600, show_spinner="Loading ping coordinates…")
def load_ping_points() -> pd.DataFrame:
    """Return one distance-validated GPS coordinate per store-matched ping."""
    s = detect_ping_source()

    def build(string_ts: bool) -> str:
        on_ts = (
            "CAST(g.ts AS STRING) = CAST(c.Timestamp AS STRING)"
            if string_ts
            else "g.ts = c.Timestamp"
        )

        return f"""
            WITH gps_candidates AS (
                SELECT
                    CAST({s['dev']} AS STRING) AS device_id,
                    {s['ts']} AS ts,
                    {s['lat']} AS lat,
                    {s['lon']} AS lon
                FROM `{s['table']}`
                WHERE {s['dev']} IS NOT NULL
                  AND {s['ts']} IS NOT NULL
                  AND {s['lat']} IS NOT NULL
                  AND {s['lon']} IS NOT NULL
            ),

            ranked_matches AS (
                SELECT
                    c.StoreID AS store_id,
                    CAST(c.DeviceID AS STRING) AS device_id,
                    g.lat,
                    g.lon,
                    ABS(
                        c.distance_meters -
                        ST_DISTANCE(
                            ST_GEOGPOINT(g.lon, g.lat),
                            ST_GEOGPOINT(sl.Longitude, sl.Latitude)
                        )
                    ) AS distance_difference_m,

                    ROW_NUMBER() OVER (
                        PARTITION BY
                            c.StoreID,
                            CAST(c.DeviceID AS STRING),
                            c.Timestamp
                        ORDER BY
                            ABS(
                                c.distance_meters -
                                ST_DISTANCE(
                                    ST_GEOGPOINT(g.lon, g.lat),
                                    ST_GEOGPOINT(sl.Longitude, sl.Latitude)
                                )
                            ),
                            g.lat,
                            g.lon
                    ) AS match_rank

                FROM `{RAW_DATASET}.store_catchments` c

                JOIN gps_candidates g
                  ON g.device_id = CAST(c.DeviceID AS STRING)
                 AND {on_ts}

                JOIN `{RAW_DATASET}.store_locations` sl
                  ON sl.StoreID = c.StoreID
            )

            SELECT
                store_id,
                device_id,
                lat,
                lon
            FROM ranked_matches
            WHERE match_rank = 1
              AND distance_difference_m < 0.01
        """

    try:
        return query_df(build(False))
    except Exception:
        # Retry if source and catchment timestamp types differ.
        return query_df(build(True))



def _h3_cell(lat: float, lng: float, res: int) -> str:
    return h3.latlng_to_cell(lat, lng, res) if hasattr(h3, "latlng_to_cell") else h3.geo_to_h3(lat, lng, res)


def _h3_polygon(cell: str) -> str:
    ring = h3.cell_to_boundary(cell) if hasattr(h3, "cell_to_boundary") else h3.h3_to_geo_boundary(cell)
    coords = [[lng, lat] for lat, lng in ring]
    return json.dumps({"type": "Polygon", "coordinates": [coords + [coords[0]]]})


@st.cache_data(ttl=600, show_spinner="Assigning pings to H3 hexagons…")
def load_h3_cells(resolution: int) -> tuple[pd.DataFrame, dict]:
    """Matched pings per (store, H3 cell). Rows come from store_catchments, so totals equal the store table."""
    if h3 is None:
        raise RuntimeError("The Python h3 package is not installed. Run:  pip install h3")
    pts = load_ping_points()
    total_rows = len(pts)
    pts = pts.dropna(subset=["lat", "lon"])
    unique = pts[["lat", "lon"]].drop_duplicates().copy()
    unique["h3_cell"] = [_h3_cell(float(a), float(b), resolution) for a, b in zip(unique["lat"], unique["lon"])]
    pts = pts.merge(unique, on=["lat", "lon"], how="left")
    out = (pts.groupby(["store_id", "h3_cell"])
           .agg(pings=("device_id", "size"), devices=("device_id", "nunique")).reset_index())
    polygons = {c: _h3_polygon(c) for c in out["h3_cell"].unique()}
    out["boundary_geojson"] = out["h3_cell"].map(polygons)
    return out, {"unmatched": total_rows - len(pts)}



# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
esc = html.escape


def short(name: str) -> str:
    return str(name).replace("GeoPulse ", "")


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def venn_centre_distance(overlap_fraction: float) -> float:
    """Centre distance (unit radius) of two equal circles whose overlap is the given share of each circle."""
    f = min(max(overlap_fraction, 0.0), 1.0)
    lo, hi = 0.0, 1.0  # x = d / 2r
    for _ in range(60):
        x = (lo + hi) / 2
        area = (2 / math.pi) * (math.acos(x) - x * math.sqrt(1 - x * x))
        lo, hi = (x, hi) if area > f else (lo, x)
    return 2 * (lo + hi) / 2


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="eyebrow">{esc(kicker)}</div><div class="hero">'
        f'<p class="hero-title">{esc(title)}</p><div class="hero-sub">{esc(subtitle)}</div></div>',
        unsafe_allow_html=True)


def callout(headline: str, why: str = "") -> None:
    why_html = f'<span class="why">{esc(why)}</span>' if why else ""
    st.markdown(f'<div class="callout"><b class="h">{esc(headline)}</b>{why_html}</div>', unsafe_allow_html=True)


def icard(title: str, body: str) -> None:
    st.markdown(f'<div class="icard"><b>{esc(title)}</b>{esc(body)}</div>', unsafe_allow_html=True)


def display_table(df: pd.DataFrame, column_config: dict | None = None) -> None:
    if df is None or df.empty:
        st.info("No rows match the current filters.")
        return
    fmt = {}
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            fmt[col] = "{:,}"
        elif pd.api.types.is_float_dtype(df[col]):
            fmt[col] = "{:.4f}" if col in ("Latitude", "Longitude") else "{:,.1f}"

    def zebra(frame: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
        for i, idx in enumerate(frame.index):
            styles.loc[idx, :] = f"background-color:{CARD if i % 2 == 0 else ZEBRA};color:{CHARCOAL}"
        return styles

    try:
        st.dataframe(df.style.format(fmt, na_rep="—").apply(zebra, axis=None), width="stretch",
                     hide_index=True, height="content", column_config=column_config)
    except Exception:
        st.dataframe(df, width="stretch", hide_index=True, height="content")


def html_table(df: pd.DataFrame) -> None:
    """Text-heavy table that wraps long sentences instead of clipping them."""
    head = "".join(f"<th>{esc(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{esc(str(v))}</td>" for v in row) + "</tr>" for row in df.itertuples(index=False))
    st.markdown(f'<table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>', unsafe_allow_html=True)


# Short column names so compact tables never clip
COMPACT_COLS = {"store_name": "Store", "matched_gps_pings": "Pings", "unique_devices": "Devices", "avg_distance_meters": "Avg dist (m)"}


def apply_plot_theme(fig: go.Figure, height: int = 330) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=18, r=18, t=54, b=18),
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family="DM Sans, sans-serif", color=CHARCOAL, size=13),
        title=dict(font=dict(family="Playfair Display, serif", size=18, color=CHARCOAL)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=CHARCOAL, size=12)),
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font_color=CHARCOAL),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=CHARCOAL))
    fig.update_yaxes(showgrid=False, zeroline=False, showline=True, linecolor=BORDER, tickfont=dict(color=CHARCOAL))
    return fig


CHART_CONFIG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}}

# ----------------------------------------------------------------------------
# Map
# ----------------------------------------------------------------------------
PULSE_CSS = """
<style>
.gp-pin { position:relative; }
.gp-core { position:absolute; border-radius:50%; background:var(--c); border:2px solid #FFFDF8; box-shadow:0 0 0 1px rgba(41,46,40,.35), 0 2px 6px rgba(0,0,0,.3); z-index:2; }
.gp-ring { position:absolute; inset:0; border-radius:50%; background:var(--c); border:2px solid var(--c); opacity:0;
           animation:gp-pulse 2.4s ease-out infinite; z-index:1; }
.gp-r2 { animation-delay:1.2s; }
@keyframes gp-pulse { 0% { transform:scale(.28); opacity:.65; } 70% { opacity:.12; } 100% { transform:scale(1); opacity:0; } }
</style>
"""


def build_map(map_data, selected_names, summary, show_catchments=True, show_labels=True, show_density=False):
    data = map_data[map_data["store_name"].isin(selected_names)].copy()
    if data.empty:
        return None
    data = data.merge(summary[["store_name", "matched_gps_pings"]], on="store_name", how="left")
    data["matched_gps_pings"] = data["matched_gps_pings"].fillna(0)
    m = folium.Map(location=[data["latitude"].mean(), data["longitude"].mean()], zoom_start=12,
                   tiles="OpenStreetMap", control_scale=True, prefer_canvas=True)
    fg_stores = folium.FeatureGroup(name="Store locations (marker size = ping volume)", show=True)
    fg_catch = folium.FeatureGroup(name="500 m catchments", show=show_catchments)
    fg_density = folium.FeatureGroup(name="Relative ping-volume rings", show=show_density)
    max_pings = max(float(data["matched_gps_pings"].fillna(0).max()), 1)
    bounds = []
    for _, s in data.iterrows():
        pings = int(s["matched_gps_pings"] or 0)
        ratio = pings / max_pings
        color = SAGE_DARK if ratio >= .66 else (SAGE if ratio >= .33 else "#B2A27B")
        lat, lon = float(s["latitude"]), float(s["longitude"])
        bounds.append([lat, lon])
        name = esc(str(s["store_name"]))
        if pd.notna(s.get("catchment_geojson")):
            try:
                folium.GeoJson(json.loads(s["catchment_geojson"]),
                               style_function=lambda f, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": .18},
                               tooltip=f"{name} · 500 m simulated catchment").add_to(fg_catch)
            except (TypeError, ValueError):
                pass
        popup = (f"<div style='font-family:Arial,sans-serif;min-width:190px;color:{CHARCOAL}'><b style='color:{SAGE_DARK}'>{name}</b><hr>"
                 f"<div>Matched GPS pings: {pings:,}</div><div>Catchment radius: 500 m</div><small>Simulated observations</small></div>")
        # Live pulsating marker: solid core (size = ping volume) with two staggered expanding rings.
        core = 14 + 14 * ratio
        box = core * 3.6
        pin_html = (f"<div class='gp-pin' style='width:{box:.0f}px;height:{box:.0f}px;--c:{color}'>"
                    f"<span class='gp-ring'></span><span class='gp-ring gp-r2'></span>"
                    f"<span class='gp-core' style='width:{core:.0f}px;height:{core:.0f}px;"
                    f"left:{(box - core) / 2:.0f}px;top:{(box - core) / 2:.0f}px'></span></div>")
        folium.Marker([lat, lon], tooltip=f"{name} · {pings:,} pings" if show_labels else None,
                      popup=folium.Popup(popup, max_width=280),
                      icon=folium.DivIcon(html=pin_html, icon_size=(box, box), icon_anchor=(box / 2, box / 2))).add_to(fg_stores)
        folium.Circle([lat, lon], radius=180 + 620 * ratio, color=color, weight=1, fill=True, fill_color=color,
                      fill_opacity=.13, tooltip=f"Relative store ping volume: {pings:,}").add_to(fg_density)
    fg_catch.add_to(m); fg_density.add_to(m); fg_stores.add_to(m)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    if len(bounds) > 1:
        m.fit_bounds(bounds, padding=(40, 40), max_zoom=15)
    else:
        b = bounds[0]
        m.fit_bounds([[b[0] - .006, b[1] - .008], [b[0] + .006, b[1] + .008]])
    m.get_root().header.add_child(folium.Element(PULSE_CSS))
    return m

# ----------------------------------------------------------------------------
# Load essentials
# ----------------------------------------------------------------------------
try:
    with st.spinner("Loading GeoPulse data…"):
        stores = load_store_summary()
        map_data = load_store_map_data()
except Exception as exc:
    st.error("GeoPulse could not load its BigQuery data. Check your Google Cloud credentials and dataset access.")
    st.code(str(exc))
    st.stop()
if stores.empty:
    st.error("The store summary returned no records. Check the dbt mart table before continuing.")
    st.stop()

stores = stores.assign(store_name=stores["store_name"].map(short))
map_data = map_data.assign(store_name=map_data["store_name"].map(short))
store_options = stores["store_name"].tolist()
name_by_id = dict(zip(stores["store_id"], stores["store_name"]))

# ----------------------------------------------------------------------------
# Sidebar: navigation, filters, one methodology box, one downloads box
# ----------------------------------------------------------------------------
st.sidebar.markdown("<div class='eyebrow' style='color:#FFFDF8'>RETAIL INTELLIGENCE</div>", unsafe_allow_html=True)
st.sidebar.markdown(
    "<div style='display:flex;align-items:center;gap:9px;margin:.2rem 0 .35rem'>"
    "<div style='width:31px;height:31px;border-radius:9px;background:#87917A;border:2px solid #FFFDF8;display:flex;"
    "align-items:center;justify-content:center;color:#FFFDF8;font-weight:800'>G</div>"
    "<div style='font-size:1.55rem;font-weight:750;letter-spacing:-.04em;color:#FFFDF8'>GeoPulse</div></div>",
    unsafe_allow_html=True)
st.sidebar.caption("Hyper-local retail mobility analytics")

PAGES = ["Executive Dashboard", "Spatial Mobility Map Analysis", "H3 Hexagon Density", "3D Hexagon View", "Hourly Activity Patterns",
         "Store and Catchment Analysis", "Final Candidate Recommendation", "Contact the Author"]
page = st.sidebar.radio("Reports", PAGES, label_visibility="collapsed")

if "geopulse_pending_map_store" in st.session_state:
    pending = st.session_state.pop("geopulse_pending_map_store")
    if pending in store_options:
        st.session_state["geopulse_selected_stores"] = [pending]
if "geopulse_selected_stores" not in st.session_state:
    # Widget state is dropped on pages without filters (Contact), so restore the last choice from a backup.
    st.session_state["geopulse_selected_stores"] = [s for s in st.session_state.get("_geopulse_stores_backup", store_options) if s in store_options]
st.session_state.setdefault("geopulse_hour_range", (0, 23))


def select_all_stores():
    st.session_state["geopulse_selected_stores"] = store_options.copy()


def clear_all_stores():
    st.session_state["geopulse_selected_stores"] = []


def reset_filters():
    select_all_stores()
    st.session_state["geopulse_hour_range"] = (0, 23)
    st.session_state["weight_ping"] = 60


with st.sidebar:
    if page != "Contact the Author":
        st.markdown("### Store filters")
        c_all, c_clear = st.columns(2)
        c_all.button("Select all", width="stretch", on_click=select_all_stores)
        c_clear.button("Clear", width="stretch", on_click=clear_all_stores)
        st.button("↺ Reset filters", width="stretch", on_click=reset_filters)
        st.multiselect("Select one or more stores", options=store_options, key="geopulse_selected_stores",
                       placeholder="Choose stores…", format_func=short,
                       help="Leave all stores selected to view the full network.")
        st.caption(f"{len(st.session_state['geopulse_selected_stores'])} of {len(store_options)} stores selected")
        with st.expander("Data & downloads"):
            st.caption(
                "Complete GPS dataset · 194.20 MB compressed · 10,000,000 records. "
                "Independent of the store filter."
            )

            if st.toggle("Prepare full download", key="prep_full_download"):
                st.link_button(
                    "Download gps_pings.csv.gz",
                    url="https://github.com/lawrenceruth/GeoPulse/releases/download/v1.0.0/gps_pings.csv.gz",
                    help="Download the complete compressed GPS dataset from GitHub Releases.",
                    width="stretch",
                )

        st.divider()
    st.caption("GeoPulse • Research prototype")

selected_stores = list(st.session_state["geopulse_selected_stores"])
st.session_state["_geopulse_stores_backup"] = selected_stores

filtered = stores[stores["store_name"].isin(selected_stores)].copy()
map_selection = map_data[map_data["store_name"].isin(selected_stores)]
network_pings = max(float(stores["matched_gps_pings"].sum()), 1.0)

if not selected_stores and page != "Contact the Author":
    st.markdown("<div class='empty'><b>No stores selected</b><br>Choose one or more stores in the sidebar, "
                "or restore the whole network.</div>", unsafe_allow_html=True)
    st.button("Select all stores", type="primary", on_click=select_all_stores)
    st.stop()


def filter_note() -> None:
    if len(selected_stores) < len(store_options):
        st.markdown(f"<div class='filter-note'>Showing {len(selected_stores)} of {len(store_options)} stores: "
                    f"{esc(', '.join(short(s) for s in selected_stores))}</div>", unsafe_allow_html=True)


def focus_store(store_name: str) -> None:
    if list(st.session_state.get("geopulse_selected_stores", [])) != [store_name]:
        st.session_state["geopulse_pending_map_store"] = store_name
        st.rerun()

# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def compute_scores(frame: pd.DataFrame, weight_ping: int) -> pd.DataFrame:
    """Score all stores on the whole network so a store's score does not move with the sidebar filter."""
    df = frame.copy()
    p_min, p_max = float(df["matched_gps_pings"].min()), float(df["matched_gps_pings"].max())
    d_min, d_max = float(df["avg_distance_meters"].min()), float(df["avg_distance_meters"].max())
    df["Ping score"] = (df["matched_gps_pings"] - p_min) / (p_max - p_min) * 100 if p_max > p_min else 100.0
    spread = d_max - d_min
    df["Distance score"] = (d_max - df["avg_distance_meters"]) / spread * 100 if spread >= DIST_MIN_SPREAD_M else 50.0
    df["Score"] = ((df["Ping score"] * weight_ping + df["Distance score"] * (100 - weight_ping)) / 100).round(1)
    return df


def page_executive() -> None:
    page_header("GEOPULSE / OVERVIEW", "Executive Dashboard",
                "Where simulated GPS activity concentrates across the store network.")
    filter_note()
    ranked_sel = filtered.sort_values("matched_gps_pings", ascending=False).reset_index(drop=True)
    net_avg = float(stores["matched_gps_pings"].mean())
    net_ppd = network_pings / max(float(stores["unique_devices"].sum()), 1.0)

    if len(filtered) == 1:
        s = filtered.iloc[0]
        rank = int(stores["matched_gps_pings"].rank(method="min", ascending=False)[stores["store_name"] == s["store_name"]].iloc[0])
        share = float(s["matched_gps_pings"]) / network_pings * 100
        delta = (float(s["matched_gps_pings"]) / net_avg - 1) * 100
        leader = stores.sort_values("matched_gps_pings", ascending=False).iloc[0]
        gap = int(leader["matched_gps_pings"] - s["matched_gps_pings"])
        tail = "It is the network leader." if gap == 0 else f"It trails the leader, {short(leader['store_name'])}, by {gap:,} pings."
        callout(f"{short(s['store_name'])} ranks #{rank} of {len(stores)} stores with {share:.1f}% of network pings.",
                f"That is {abs(delta):.0f}% {'above' if delta >= 0 else 'below'} the average store ({net_avg:,.0f} pings). {tail}")
    else:
        top, low = ranked_sel.iloc[0], ranked_sel.iloc[-1]
        sel_share = float(filtered["matched_gps_pings"].sum()) / network_pings * 100
        top_share = float(top["matched_gps_pings"]) / network_pings * 100
        if len(filtered) == len(stores) and len(stores) >= 4:
            top3 = float(ranked_sel.head(3)["matched_gps_pings"].sum()) / network_pings * 100
            head = f"{short(top['store_name'])} leads with {int(top['matched_gps_pings']):,} pings ({top_share:.1f}%); the top three stores hold {top3:.1f}% of all activity."
        else:
            head = f"{short(top['store_name'])} leads the selection with {int(top['matched_gps_pings']):,} pings ({top_share:.1f}% of network); the selection holds {sel_share:.1f}% in total."
        low_share = float(low["matched_gps_pings"]) / network_pings * 100
        callout(head, f"Activity sits in a few catchments, so the gaps between stores matter more than network averages. "
                      f"{short(low['store_name'])} holds just {low_share:.1f}%.")

    with st.spinner("Updating KPIs…"):
        try:
            kpi = load_selected_kpis(tuple(filtered["store_id"].tolist()))
        except Exception as exc:
            st.error("Unable to load selected-store KPIs from BigQuery.")
            st.code(str(exc))
            st.stop()
    pings, devices = int(kpi["total_pings"] or 0), int(kpi["total_unique_devices"] or 0)
    avg_dist = kpi["average_distance"]
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Stores selected", f"{len(filtered):,}", help="Simulated store locations included.")
    k2.metric("Matched GPS pings", f"{pings:,}", help="GPS observations inside the selected 500 m catchments; repeats included.")
    k3.metric("Distinct devices", f"{devices:,}", help="Distinct DeviceIDs across the selected catchments, counted once even if seen at several stores.")
    k4.metric("Pings per device", f"{pings / max(devices, 1):.2f}", help="Average observations per device: higher means more repeat sightings.")
    k5.metric("Average distance", f"{avg_dist:,.0f} m" if pd.notna(avg_dist) else "N/A", help="Mean distance from a matched ping to its store.")

    left, right = st.columns([1.15, 1])
    with left:
        chart_data = stores.copy() if len(filtered) == 1 else filtered.copy()
        chart_data["Filter"] = chart_data["store_name"].isin(selected_stores).map({True: "Selected store", False: "Other stores"})
        fig = px.bar(chart_data.sort_values("matched_gps_pings"), x="matched_gps_pings", y="store_name", orientation="h",
                     color="Filter", color_discrete_map={"Selected store": SAGE_DARK, "Other stores": BORDER},
                     text="matched_gps_pings", title="Observed pings by store",
                     labels={"matched_gps_pings": "Matched GPS pings", "store_name": ""})
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=[0, float(chart_data["matched_gps_pings"].max()) * 1.25], tickformat=",")
        apply_plot_theme(fig, 320)
        event = st.plotly_chart(fig, width="stretch", config=CHART_CONFIG, on_select="rerun",
                                selection_mode="points", key="geopulse_executive_bar")
        points = event.selection.points if event and hasattr(event, "selection") else []
        if points and points[-1].get("y") in store_options:
            focus_store(points[-1]["y"])
        st.caption("Click a bar to focus the whole dashboard on that store.")
    with right:
        st.markdown("#### Executive readout")
        if len(filtered) == 1:
            s = filtered.iloc[0]
            ppd = float(s["matched_gps_pings"]) / max(float(s["unique_devices"]), 1)
            icard("Repeat sightings", f"{ppd:.2f} pings per device here versus {net_ppd:.2f} across the network.")
            dist_gap = float(s["avg_distance_meters"]) - float(stores["avg_distance_meters"].mean())
            icard("Distance", f"Average ping-to-store distance is {s['avg_distance_meters']:.0f} m, "
                              f"{abs(dist_gap):.1f} m {'above' if dist_gap >= 0 else 'below'} the network mean.")
        else:
            top, low = ranked_sel.iloc[0], ranked_sel.iloc[-1]
            second = ranked_sel.iloc[1]
            lead_pct = (float(top["matched_gps_pings"]) / max(float(second["matched_gps_pings"]), 1) - 1) * 100
            icard("Volume leader", f"{short(top['store_name'])} records {lead_pct:.0f}% more pings than {short(second['store_name'])}.")
            median = float(filtered["matched_gps_pings"].median())
            icard("Weakest store", f"{short(low['store_name'])} records {int(low['matched_gps_pings']):,} pings, "
                                   f"{float(low['matched_gps_pings']) / max(median, 1) * 100:.0f}% of the median store ({median:,.0f}). "
                                   "Check its location and data coverage.")
            d_min, d_max = float(filtered["avg_distance_meters"].min()), float(filtered["avg_distance_meters"].max())
            if d_max - d_min < DIST_MIN_SPREAD_M:
                icard("Distance", f"Every store averages {d_min:.0f}–{d_max:.0f} m from its pings, so distance does not separate them. Rely on volume and overlap.")
            else:
                far = filtered.loc[filtered["avg_distance_meters"].idxmax()]
                icard("Distance", f"{short(far['store_name'])} draws pings from {d_max - d_min:.0f} m farther out than the closest-fitting store.")

    st.divider()
    t_col, m_col = st.columns(2)
    with t_col:
        st.markdown("#### Store comparison")
        display_table(filtered[["store_name", "matched_gps_pings", "unique_devices", "avg_distance_meters"]].rename(columns=COMPACT_COLS))
        st.download_button("Download selected-store summary CSV", data=filtered.to_csv(index=False).encode("utf-8"),
                           file_name="geopulse_store_summary.csv", mime="text/csv")
    with m_col:
        st.markdown("#### Geographic context")
        m = build_map(map_selection, selected_stores, filtered, True)
        if m:
            st_folium(m, use_container_width=True, height=262, returned_objects=[], key="geopulse_exec_map")
    st.markdown(
        '<div class="callout" style="margin-top:1.2rem"><b class="h">Disclaimer</b><span class="why">'
        "GeoPulse is a research prototype built on Synthetic store locations and GPS observations. Pings do not show verified visits, "
        "purchases, traffic or sales, and catchment overlap is geometry, not evidence of customer switching or lost sales. "
        "Scores are illustrative: real decisions need footfall, rent, demographics, competition and sales data.</span></div>",
        unsafe_allow_html=True)


def page_spatial() -> None:
    page_header("GEOPULSE / SPATIAL", "Spatial Mobility Map Analysis",
                "Store locations, ping volume and 500 m catchments on a street-level map.")
    filter_note()
    coords = map_selection[["store_name", "latitude", "longitude"]].reset_index(drop=True)
    if len(coords) >= 2:
        pairs = [(haversine_km(a.latitude, a.longitude, b.latitude, b.longitude), a.store_name, b.store_name)
                 for i, a in coords.iterrows() for j, b in coords.iterrows() if i < j]
        near, far = min(pairs), max(pairs)
        if near[0] * 1000 < 1000:
            head = f"{short(near[1])} and {short(near[2])} sit only {near[0] * 1000:,.0f} m apart, so their 500 m catchments overlap."
        else:
            head = f"The closest pair, {short(near[1])} and {short(near[2])}, are {near[0]:.1f} km apart, so their catchments do not overlap."
        callout(head, f"The widest gap is {far[0]:.1f} km ({short(far[1])} to {short(far[2])}); stores that far apart serve different parts of Lagos.")
    elif len(coords) == 1:
        callout(f"{short(coords.iloc[0]['store_name'])}'s 500 m catchment covers about 0.78 km².",
                "Select more stores to compare spacing and overlap.")

    c1, c2 = st.columns([1, 3])
    with c1:
        show_catch = st.toggle("Show catchment overlays", value=True)
        show_labels = st.toggle("Show store labels on hover", value=True)
        show_density = st.toggle("Show ping-volume rings", value=False)
        st.metric("Stores on map", len(map_selection))
        st.markdown('<div class="legend-panel"><b>How to read the map</b><br>Marker size and shade show relative ping '
                    'volume. Shaded circles are the 500 m catchments. Click a marker to focus the dashboard on that store.<br><br>'
                    '<span class="dot" style="background:#526047"></span>Higher &nbsp;<span class="dot" style="background:#87917A"></span>Mid '
                    '&nbsp;<span class="dot" style="background:#B2A27B"></span>Lower</div>',
                    unsafe_allow_html=True)
    with c2:
        m = build_map(map_selection, selected_stores, filtered, show_catch, show_labels, show_density)
        if m:
            result = st_folium(m, use_container_width=True, height=600, returned_objects=["last_object_clicked"], key="geopulse_main_map")
            clicked = result.get("last_object_clicked") if result else None
            if clicked and clicked.get("lat") is not None and clicked.get("lng") is not None:
                near = map_selection.assign(_d=(map_selection["latitude"] - float(clicked["lat"])).abs()
                                            + (map_selection["longitude"] - float(clicked["lng"])).abs()).sort_values("_d").iloc[0]
                if float(near["_d"]) < 0.003:
                    focus_store(near["store_name"])
        else:
            st.info("No store coordinates are available for this selection.")
    st.markdown("#### Location register")
    display_table(map_selection[["store_id", "store_name", "latitude", "longitude"]].rename(
        columns={"store_id": "Store ID", "store_name": "Store", "latitude": "Latitude", "longitude": "Longitude"}))


def page_hourly() -> None:
    page_header("GEOPULSE / OBSERVATIONS", "Hourly Activity Patterns",
                "When simulated GPS pings arrive across the day (WAT), for the selected stores.")
    filter_note()
    try:
        raw = load_hourly_all()
    except Exception as exc:
        st.error("Hourly observation data could not be loaded.")
        st.code(str(exc))
        return
    raw = raw.assign(store_name=raw["store_id"].map(name_by_id), hour_wat=raw["hour_wat"].astype(int))
    raw = raw[raw["store_name"].isin(selected_stores)]
    if raw.empty:
        st.warning("No hourly observations were returned for the selected stores.")
        return
    names = sorted(raw["store_name"].unique())
    grid = pd.MultiIndex.from_product([names, range(24)], names=["store_name", "hour_wat"])
    hourly = raw.set_index(["store_name", "hour_wat"])["pings"].reindex(grid, fill_value=0).reset_index()
    hourly["pings"] = hourly["pings"].astype(int)
    daily = hourly.groupby("store_name")["pings"].transform("sum").clip(lower=1)
    hourly["share"] = hourly["pings"] / daily * 100
    hourly["hour_label"] = hourly["hour_wat"].map(lambda h: f"{h:02d}:00")

    total = hourly.groupby("hour_wat")["pings"].sum()
    top2 = total.nlargest(2)
    top2_share = float(top2.sum()) / max(float(total.sum()), 1) * 100
    h1, h2 = sorted(top2.index)
    callout(f"{h1:02d}:00 and {h2:02d}:00 WAT are the busiest hours, holding {top2_share:.0f}% of selected-store pings "
            f"({top2_share / (200 / 24):.1f}× the share of a flat day).",
            "Manual footfall counts in these two windows will show whether real behaviour mirrors the simulated peaks.")

    hour_range = st.slider("Hour range (WAT)", 0, 23, key="geopulse_hour_range")
    o1, o2 = st.columns([1, 1])
    normalised = o1.toggle("Show each store as % of its daily pings", value=False)
    layout = o2.radio("Chart layout", ["Combined", "One panel per store"], index=1, horizontal=True, label_visibility="collapsed")
    view = hourly[hourly["hour_wat"].between(hour_range[0], hour_range[1])]
    y_col = "share" if normalised else "pings"
    y_label = "Share of daily pings (%)" if normalised else "GPS pings"
    hours_axis = [f"{h:02d}:00" for h in range(24)]
    peaks = view.loc[view.groupby("store_name")[y_col].idxmax()]
    if layout == "Combined":
        fig = px.line(view, x="hour_label", y=y_col, color="store_name", markers=True, color_discrete_map=STORE_COLORS,
                      category_orders={"hour_label": hours_axis}, labels={"hour_label": "Hour (WAT)", y_col: y_label, "store_name": ""},
                      title="Hourly GPS pings by store")
        fig.update_traces(line_width=2.5, marker=dict(size=5))
        fig.for_each_trace(lambda t: t.update(line_dash="dash") if t.name == LEKKI_B else None)  # Lekki B dashed so it never hides Lekki A
        fig.add_trace(go.Scatter(x=peaks["hour_label"], y=peaks[y_col], mode="markers", name="Peak hour",
                                 marker=dict(size=12, symbol="diamond", color="#FFFDF8", line=dict(width=2, color=CHARCOAL)),
                                 hovertemplate="Peak: %{x}<extra></extra>"))
        apply_plot_theme(fig, 400)
        fig.update_layout(hovermode="x unified", margin=dict(l=25, r=30, t=55, b=80),
                          legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=.5, title_text=""))
        fig.update_xaxes(type="category", dtick=2)
    else:
        fig = px.area(view, x="hour_label", y=y_col, facet_col="store_name", facet_col_wrap=3, color="store_name",
                      color_discrete_map=STORE_COLORS, category_orders={"hour_label": hours_axis},
                      labels={"hour_label": "", y_col: y_label}, title="Hourly GPS pings, one panel per store")
        fig.for_each_annotation(lambda a: a.update(text=short(a.text.split("=")[-1])))
        panel_rows = math.ceil(view["store_name"].nunique() / 3)
        apply_plot_theme(fig, 150 + 190 * panel_rows)
        fig.update_layout(showlegend=False, margin=dict(l=25, r=20, t=70, b=70 if panel_rows > 1 else 30))
        fig.update_xaxes(type="category", dtick=6, showticklabels=True)
        # Titles of the lower row (e.g. Victoria Island, Yaba) move beneath their own chart so they
        # no longer sit on top of the upper row's hour labels.
        titles = list(fig.layout.annotations)
        if panel_rows > 1 and titles:
            top_y = max(a.y for a in titles)
            axis_domains = [tuple(ax.domain) for ax in fig.select_yaxes()]

            def move_lower_titles(a):
                if a.y < top_y - 1e-6:
                    bottom = min(b for b, t in axis_domains if abs(t - a.y) < 1e-3)
                    a.update(y=bottom - 0.055, yanchor="top")

            fig.for_each_annotation(move_lower_titles)
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

    morning = float(total.loc[7:9].sum()) / max(float(total.sum()), 1) * 100
    evening = float(total.loc[17:19].sum()) / max(float(total.sum()), 1) * 100
    roll = total.rolling(3).sum().dropna()
    q_end = int(roll.idxmin())
    q_share = float(roll.min()) / max(float(total.sum()), 1) * 100
    c1, c2 = st.columns(2)
    with c1:
        icard("Two rush windows", f"07:00–09:59 holds {morning:.0f}% of pings and 17:00–19:59 holds {evening:.0f}%: "
                                  f"{morning + evening:.0f}% of activity in 6 of 24 hours.")
    with c2:
        icard("Quietest window", f"{q_end - 2:02d}:00–{q_end:02d}:59 is the lowest three-hour block, with only {q_share:.1f}% of pings.")

    summary = hourly.loc[hourly.groupby("store_name")["pings"].idxmax()].copy()
    summary["Daily pings"] = summary["store_name"].map(hourly.groupby("store_name")["pings"].sum())
    summary = summary.rename(columns={"store_name": "Store", "hour_label": "Peak hour", "pings": "Peak-hour pings"})
    summary["Peak hour share of day (%)"] = summary["Peak-hour pings"] / summary["Daily pings"] * 100
    summary["Store"] = summary["Store"].map(short)
    st.markdown("#### Peak summary")
    display_table(summary[["Store", "Peak hour", "Peak-hour pings", "Daily pings", "Peak hour share of day (%)"]].reset_index(drop=True))

    with st.expander("Hourly data table and download"):
        wide = view.pivot(index="hour_label", columns="store_name", values="pings").reset_index().rename(columns={"hour_label": "Hour (WAT)"})
        display_table(wide)
        st.download_button("Download hourly data CSV", data=wide.to_csv(index=False).encode("utf-8"),
                           file_name="geopulse_hourly_activity.csv", mime="text/csv")


def page_catchment() -> None:
    page_header("GEOPULSE / CATCHMENTS", "Store and Catchment Analysis",
                "How much the two Lekki catchments overlap, and how all stores compare.")
    filter_note()
    try:
        overlap = load_lekki_overlap()
        shared_devices = load_shared_devices()
    except Exception as exc:
        overlap, shared_devices = pd.DataFrame(), 0
        st.error("Catchment overlap metrics could not be loaded.")
        st.code(str(exc))

    if overlap.empty:
        st.warning("No overlap result returned. Confirm both Lekki catchment polygons exist.")
    else:
        r = overlap.iloc[0]
        a_dev = float(stores.loc[stores["store_name"] == LEKKI_A, "unique_devices"].iloc[0])
        dev_share = shared_devices / max(a_dev, 1) * 100
        callout(f"Lekki A and Lekki B share {r['pct_a']:.1f}% of their catchment and {shared_devices:,} observed devices "
                f"({dev_share:.0f}% of Lekki A's devices).",
                "A second Lekki site would largely compete for the same ground. Plan them as one market until real sales show separate demand.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Shared area", f"{r['shared_area_sqm'] / 1_000_000:.2f} km²", help="Area where the two modelled 500 m polygons intersect.")
        m2.metric("Lekki A overlap", f"{r['pct_a']:.1f}%", help="Share of Lekki A's catchment that lies inside Lekki B's.")
        m3.metric("Lekki B overlap", f"{r['pct_b']:.1f}%", help="Share of Lekki B's catchment that lies inside Lekki A's.")
        m4.metric("Shared device IDs", f"{shared_devices:,}", help="Devices observed in both catchments. This does not prove one person visited both stores.")

    left, right = st.columns(2)
    with left:
        if not overlap.empty:
            frac = (float(r["pct_a"]) + float(r["pct_b"])) / 200
            d = venn_centre_distance(frac)
            fig = go.Figure()
            fig.add_shape(type="circle", x0=-1, y0=-1, x1=1, y1=1, fillcolor=STORE_COLORS[LEKKI_A], opacity=.45, line=dict(color=STORE_COLORS[LEKKI_A], width=2))
            fig.add_shape(type="circle", x0=d - 1, y0=-1, x1=d + 1, y1=1, fillcolor=STORE_COLORS[LEKKI_B], opacity=.45, line=dict(color=STORE_COLORS[LEKKI_B], width=2))
            fig.add_annotation(x=-1.1, y=0, text="<b>Lekki A</b>", showarrow=False, xanchor="right", font=dict(color=CHARCOAL, size=14))
            fig.add_annotation(x=d + 1.1, y=0, text="<b>Lekki B</b>", showarrow=False, xanchor="left", font=dict(color=CHARCOAL, size=14))
            fig.add_annotation(x=d / 2, y=0, text=f"<b>{frac * 100:.1f}%</b><br>shared", showarrow=False, font=dict(color=CHARCOAL, size=14))
            fig.update_xaxes(visible=False, range=[-2.4, d + 2.4], fixedrange=True)
            fig.update_yaxes(visible=False, range=[-1.15, 1.15], fixedrange=True, scaleanchor="x")
            fig.update_layout(title="Catchment overlap (area-proportional)", height=340, margin=dict(l=10, r=10, t=50, b=10),
                              paper_bgcolor=CARD, plot_bgcolor=CARD, showlegend=False,
                              title_font=dict(family="Playfair Display, serif", size=18, color=CHARCOAL))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        if not overlap.empty and {LEKKI_A, LEKKI_B} <= set(stores["store_name"]):
            a_dev = float(stores.loc[stores["store_name"] == LEKKI_A, "unique_devices"].iloc[0])
            b_dev = float(stores.loc[stores["store_name"] == LEKKI_B, "unique_devices"].iloc[0])
            fig = go.Figure()
            fig.add_bar(y=[LEKKI_A, LEKKI_B], x=[shared_devices, shared_devices], orientation="h", name="Seen at both stores",
                        marker_color=SAGE_DARK, text=[f"{shared_devices:,} ({shared_devices / a_dev * 100:.0f}%)",
                                                      f"{shared_devices:,} ({shared_devices / b_dev * 100:.0f}%)"],
                        textposition="inside", insidetextanchor="middle", textfont=dict(color="#FFFDF8"))
            fig.add_bar(y=[LEKKI_A, LEKKI_B], x=[a_dev - shared_devices, b_dev - shared_devices], orientation="h", name="Only at this store",
                        marker_color=BORDER, text=[f"{a_dev - shared_devices:,.0f}", f"{b_dev - shared_devices:,.0f}"],
                        textposition="inside", insidetextanchor="middle", textfont=dict(color=CHARCOAL))
            fig.update_layout(barmode="stack", title="Devices shared between the Lekki stores")
            fig.update_xaxes(title="Distinct devices", tickformat=",")
            apply_plot_theme(fig, 340)
            st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
    if len(filtered) > 1:
        d_min, d_max = float(filtered["avg_distance_meters"].min()), float(filtered["avg_distance_meters"].max())
        if d_max - d_min < DIST_MIN_SPREAD_M:
            icard("Distance does not separate stores", f"All selected stores sit within {d_max - d_min:.1f} m of each other on average distance, so volume and overlap matter more.")

    st.markdown("#### Store comparison")
    display_table(filtered[["store_id", "store_name", "matched_gps_pings", "unique_devices", "avg_distance_meters"]].rename(
        columns={"store_id": "Store ID", **COMPACT_COLS}))
    st.caption("Overlap is geometric. It does not prove lost sales or customer switching.")


def page_recommendation() -> None:
    page_header("GEOPULSE / DECISION SUPPORT", "Final Candidate Recommendation",
                "A transparent screening score to decide where to validate first, not an investment decision.")
    filter_note()
    weight_ping = st.slider("Matched-ping volume weight (%)", 0, 100, 60, 5, key="weight_ping",
                            help="The rest of the weight goes to average ping-to-store distance.")
    scores = compute_scores(stores, weight_ping)
    spread = float(stores["avg_distance_meters"].max() - stores["avg_distance_meters"].min())
    st.caption(f"Weights: volume {weight_ping}% · distance {100 - weight_ping}%. Both components are scored 0–100 across the whole network."
               + (f" Distance differs by only {spread:.0f} m across stores, so it is scored neutral (50) for all rather than magnifying a tiny gap."
                  if spread < DIST_MIN_SPREAD_M else ""))
    rec = scores[scores["store_name"].isin(selected_stores)].sort_values("Score", ascending=False).reset_index(drop=True)
    try:
        ov = load_lekki_overlap()
        pct_overlap = float(ov.iloc[0]["pct_a"]) if not ov.empty else None
    except Exception:
        pct_overlap = None

    top = rec.iloc[0]
    lekki_top = [n for n in rec.head(3)["store_name"] if n in (LEKKI_A, LEKKI_B)]
    why = ("Use the ranking to decide where to validate first, not where to invest.")
    if len(lekki_top) == 2 and pct_overlap is not None:
        why = f"Lekki A and Lekki B both rank in the top three but overlap {pct_overlap:.0f}%, so count them as one candidate. " + why
    callout(f"{short(top['store_name'])} scores highest ({top['Score']:.1f}/100) at {weight_ping}% volume and {100 - weight_ping}% distance weighting.", why)

    st.markdown("#### Ranked shortlist")
    cols = st.columns(min(3, len(rec)))
    for i, (_, row) in enumerate(rec.head(3).iterrows()):
        flag = "⚠️ Overlaps with the other Lekki store" if row["store_name"] in (LEKKI_A, LEKKI_B) else "&nbsp;"
        cols[i].markdown(f'<div class="icard"><span class="rank-badge">#{i + 1}</span><b style="display:inline">{esc(row["store_name"])}</b><br>'
                         f'<span style="font-size:1.35rem;font-weight:800;color:{SAGE_DARK}">{row["Score"]:.1f}</span> / 100<br>'
                         f'<small>{flag}</small></div>', unsafe_allow_html=True)

    st.markdown("#### Scorecard")
    score_cols = ["store_id", "store_name", "matched_gps_pings", "unique_devices", "avg_distance_meters", "Ping score", "Distance score", "Score"]
    if spread < DIST_MIN_SPREAD_M:
        score_cols.remove("Distance score")  # identical for every store, so it adds no information
    table = rec[score_cols].rename(
        columns={"store_id": "Store ID", "store_name": "Store", "matched_gps_pings": "Matched pings", "unique_devices": "Unique devices",
                 "avg_distance_meters": "Average distance (m)", "Score": "Screening score"})
    display_table(table)
    st.download_button("Download scorecard CSV", data=table.to_csv(index=False).encode("utf-8"),
                       file_name="geopulse_candidate_scorecard.csv", mime="text/csv")

    rec["Rank group"] = ["Top 3" if i < 3 else "Other" for i in rec.index]
    fig = px.bar(rec, x="store_name", y="Score", color="Rank group", color_discrete_map={"Top 3": SAGE_DARK, "Other": BORDER},
                 text="Score", title="Screening score by store", labels={"store_name": "", "Score": "Score / 100", "Rank group": "Rank"})
    fig.update_traces(texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False)
    fig.update_yaxes(range=[0, 110], tickformat=".0f")
    apply_plot_theme(fig, 320)
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

    st.markdown("#### Hotspot hexagons to validate first")
    hotspots = None
    try:
        hx, _ = load_h3_cells(9)
        hx = hx.assign(store_name=hx["store_id"].map(name_by_id))
        hx = hx[hx["store_name"].isin(selected_stores)]
        hotspots = (hx.groupby("h3_cell")
                    .agg(pings=("pings", "sum"), stores=("store_name", lambda s: ", ".join(sorted({short(x) for x in s}))))
                    .reset_index().sort_values("pings", ascending=False).reset_index(drop=True))
        hotspots["share"] = hotspots["pings"] / max(int(hotspots["pings"].sum()), 1) * 100
        display_table(hotspots.head(5).assign(Rank=lambda d: range(1, len(d) + 1))[["Rank", "h3_cell", "stores", "pings", "share"]].rename(
            columns={"h3_cell": "H3 cell", "stores": "Stores", "pings": "Pings", "share": "Share of pings (%)"}))
        st.caption("Resolution 9 hexagons, about 0.11 km² each. See the H3 Hexagon Density and 3D Hexagon View pages for the map.")
    except Exception:
        st.caption("Hexagon hotspots appear here once the H3 data loads (see the H3 Hexagon Density page).")

    st.markdown("#### Action plan")
    low = scores.sort_values("matched_gps_pings").iloc[0]
    peak_txt = "its busiest hours"
    try:
        h = load_hourly_all()
        h = h[h["store_id"] == top["store_id"]]
        if not h.empty:
            peak_txt = f"{int(h.loc[h['pings'].idxmax(), 'hour_wat']):02d}:00 WAT (its peak hour)"
    except Exception:
        pass
    plan = [
        {"Action": f"Shortlist {short(top['store_name'])} for site validation",
         "Evidence": f"Score {top['Score']:.1f}/100; {top['matched_gps_pings'] / network_pings * 100:.1f}% of network pings",
         "Validate by": f"Manual footfall counts around {peak_txt}"},
    ]
    if hotspots is not None and not hotspots.empty:
        top3_share = float(hotspots.head(3)["pings"].sum()) / max(int(hotspots["pings"].sum()), 1) * 100
        plan.append({"Action": "Validate the hotspot hexagons first",
                     "Evidence": f"The top 3 hexagons hold {top3_share:.0f}% of matched pings; the busiest covers {hotspots.iloc[0]['stores']}",
                     "Validate by": "Count footfall inside those hexagons before surveying the rest of each catchment"})
    plan += [
        {"Action": "Treat Lekki A and Lekki B as one market",
         "Evidence": f"{pct_overlap:.0f}% catchment overlap" if pct_overlap is not None else "Catchment overlap unavailable",
         "Validate by": "Compare real sales per store before approving two Lekki sites"},
        {"Action": f"Investigate {short(low['store_name'])}'s low activity",
         "Evidence": f"{int(low['matched_gps_pings']):,} pings ({low['matched_gps_pings'] / network_pings * 100:.1f}% of network)",
         "Validate by": "Check location, catchment coverage and data gaps"},
        {"Action": "Replace simulated inputs with real data",
         "Evidence": "Scores use only ping volume and distance",
         "Validate by": "Add rent, sales, competition, access and demographics, then re-run the weights"},
    ]
    for i, row in enumerate(plan, start=1):
        row["Priority"] = i
    html_table(pd.DataFrame(plan)[["Priority", "Action", "Evidence", "Validate by"]])
    st.caption("No real sales, rent, demographics or verified visitor data are included, so this page names no winning real-world site.")


def page_contact() -> None:
    page_header("GEOPULSE / CONTACT", "Contact the Author",
                "Connect with Lawrence Ruth about GeoPulse, analytics projects or professional opportunities.")
    st.markdown('<div class="callout"><b class="h">Lawrence Ruth</b><span class="why">Data Analytics · Business Intelligence · Retail Mobility Analytics</span></div>',
                unsafe_allow_html=True)
    st.markdown("### Get in touch")
    for label, text, url in [
        ("Gmail", "lawrenceruth34@gmail.com", "mailto:lawrenceruth34@gmail.com"),
        ("LinkedIn", "Connect on LinkedIn", "https://www.linkedin.com/in/ruth-lawrence-8519073b7"),
        ("GitHub", "github.com/lawrenceruth", "https://github.com/lawrenceruth"),
        ("Instagram", "@lawrenceruth369", "https://www.instagram.com/lawrenceruth369"),
        ("Notion Portfolio", "Lawrence Ruth — Business Intelligence / Data Analyst",
         "https://app.notion.com/p/Lawrence-Ruth-Business-Intelligence-Data-Analyst-36c00a4b9b2e80229207effb4603381d?source=copy_link"),
    ]:
        st.markdown(f"**{label}:** [{text}]({url})")
    st.divider()
    st.caption("Thank you for exploring GeoPulse. This portfolio project uses simulated mobility observations to demonstrate geospatial and retail analytics workflows.")

FOCUS_BUSIEST, FOCUS_ALL = "Busiest hexagons", "All selected stores"


def h3_classes(pings: pd.Series):
    """Colour class per hexagon, scaled to the busiest hexagon so tall towers stand out from low ones."""
    top = max(float(pings.max()), 1.0)
    edges = [0.0] + [top * f for f in H3_BREAKS]
    codes = pd.cut(pings, bins=edges, labels=False, include_lowest=True).fillna(0).astype(int)
    return codes, edges


def h3_legend(title: str, edges: list) -> str:
    items, lo = "", 1
    for i, colour in enumerate(H3_PALETTE):
        hi = max(int(round(edges[i + 1])), lo)
        items += (f'<span style="margin-right:14px"><span class="dot" style="background:{colour};border-radius:2px"></span>'
                  f'{lo:,}–{hi:,}</span>')
        lo = hi + 1
    return f'<div class="legend-panel"><b>{title}</b> &nbsp; {items}</div>'


def hex_focus_bounds(cells: pd.DataFrame, grid: pd.DataFrame, half: int, focus: str):
    """Bounding box (min_lat, min_lon, max_lat, max_lon) of the hexagons the map should open on."""
    if focus == FOCUS_BUSIEST:
        sub = grid.head(max(half, 3))
    elif focus == FOCUS_ALL:
        sub = grid
    else:
        sub = grid[grid["h3_cell"].isin(cells.loc[cells["store_name"] == focus, "h3_cell"].unique())]
    if sub.empty:
        sub = grid
    lats, lons = [], []
    for boundary in sub["boundary"]:
        for lng, lat in json.loads(boundary)["coordinates"][0]:
            lats.append(lat)
            lons.append(lng)
    min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
    pad = max(0.004 - (max_lat - min_lat) / 2, 0), max(0.004 - (max_lon - min_lon) / 2, 0)  # never zoom closer than ~1 km
    return min_lat - pad[0], min_lon - pad[1], max_lat + pad[0], max_lon + pad[1]


def build_h3_grid(resolution: int):
    """Hexagon table for the selected stores plus the checks both H3 pages show."""
    cells, info = load_h3_cells(resolution)
    cells = cells.assign(store_name=cells["store_id"].map(name_by_id))
    cells = cells[cells["store_name"].isin(selected_stores)]
    if cells.empty:
        return None
    by_store = cells.groupby("store_name")["pings"].sum()
    expected = filtered.set_index("store_name")["matched_gps_pings"]
    diff = (by_store.reindex(expected.index).fillna(0) - expected).abs()
    grid = (cells.groupby("h3_cell")
            .agg(pings=("pings", "sum"), boundary=("boundary_geojson", "first"),
                 stores=("store_name", lambda s: ", ".join(sorted({short(x) for x in s}))))
            .reset_index().sort_values("pings", ascending=False).reset_index(drop=True))
    total = int(grid["pings"].sum())
    grid["share"] = grid["pings"] / max(total, 1) * 100
    half = int((grid["pings"].cumsum() / max(total, 1) < 0.5).sum()) + 1
    return {"cells": cells, "grid": grid, "total": total, "half": half, "diff": diff, "info": info}


def page_h3() -> None:
    page_header("GEOPULSE / H3 DENSITY", "H3 Hexagon Density",
                "Matched GPS pings grouped into H3 hexagons, so activity compares on equal-sized areas.")
    filter_note()
    r1, r2, r3 = st.columns([1.7, 1.2, 1.1])
    res_label = r1.radio("Hexagon size", list(H3_RESOLUTIONS), index=1)
    resolution = H3_RESOLUTIONS[res_label]
    focus = r2.selectbox("Zoom to", [FOCUS_BUSIEST, FOCUS_ALL] + sorted(selected_stores),
                         help="Opens the map on the busiest hexagons, the whole network, or a single store.")
    show_outline = r3.toggle("Show 500 m catchment outlines", value=True)
    try:
        data = build_h3_grid(resolution)
    except Exception as exc:
        st.error("Pings could not be assigned to H3 hexagons.")
        st.code(str(exc))
        return
    if data is None:
        st.warning("No hexagons contain matched pings for the selected stores.")
        return
    cells, grid, total, half, diff, info = (data[k] for k in ("cells", "grid", "total", "half", "diff", "info"))
    top = grid.iloc[0]
    cell_area = "0.74 km²" if resolution == 8 else "0.11 km²"
    callout(f"The busiest {half} of {len(grid)} hexagons hold half of all matched pings (each hexagon is about {cell_area}).",
            f"The top cell, covering {top['stores']}, holds {top['share']:.1f}% ({int(top['pings']):,} pings). "
            "Start field validation in these cells rather than across whole catchments.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Hexagons with pings", f"{len(grid):,}", help="H3 cells that contain at least one matched ping.")
    k2.metric("Matched GPS pings", f"{total:,}", help="Store-matched pings. A ping inside two catchments counts once per store, as in the store table.")
    k3.metric("Busiest hexagon", f"{int(top['pings']):,}", help="Pings in the single densest cell.")
    k4.metric("Median pings per hexagon", f"{grid['pings'].median():,.0f}", help="Typical cell activity; compare with the busiest cell.")
    if bool((diff == 0).all()):
        st.caption(f"✓ Hexagon totals match the store table for every selected store ({total:,} pings).")
    else:
        st.warning("Hexagon totals differ from the store table for: " + ", ".join(short(n) for n in diff[diff > 0].index)
                   + ". Check that every ping row in store_catchments has coordinates.")

    codes, edges = h3_classes(grid["pings"])
    features = []
    for i, row in grid.iterrows():
        features.append({"type": "Feature", "geometry": json.loads(row["boundary"]),
                         "properties": {"Hexagon": row["h3_cell"], "Pings": f"{int(row['pings']):,}",
                                        "Share of pings": f"{row['share']:.1f}%", "Stores": row["stores"],
                                        "fill": H3_PALETTE[int(codes.iloc[i])]}})
    m = folium.Map(tiles="OpenStreetMap", control_scale=True, zoom_start=12)
    folium.GeoJson({"type": "FeatureCollection", "features": features},
                   style_function=lambda f: {"fillColor": f["properties"]["fill"], "color": "#6B7260", "weight": 1, "fillOpacity": .82},
                   tooltip=folium.GeoJsonTooltip(fields=["Pings", "Share of pings", "Stores", "Hexagon"], sticky=True)).add_to(m)
    if show_outline:
        for _, s in map_selection.iterrows():
            if pd.notna(s.get("catchment_geojson")):
                folium.GeoJson(json.loads(s["catchment_geojson"]), interactive=False,
                               style_function=lambda f: {"fill": False, "color": CHARCOAL, "weight": 1.5, "dashArray": "5 5"}).add_to(m)
    min_lat, min_lon, max_lat, max_lon = hex_focus_bounds(cells, grid, half, focus)
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(30, 30), max_zoom=16)
    st_folium(m, use_container_width=True, height=560, returned_objects=[], key=f"geopulse_h3_map_{resolution}_{focus}")
    st.markdown(h3_legend("Pings per hexagon", edges), unsafe_allow_html=True)

    st.markdown("#### Busiest hexagons")
    table = grid.head(10).assign(Rank=lambda d: range(1, len(d) + 1))[["Rank", "h3_cell", "stores", "pings", "share"]].rename(
        columns={"h3_cell": "H3 cell", "stores": "Stores", "pings": "Pings", "share": "Share of pings (%)"})
    display_table(table)
    st.download_button("Download all hexagon counts CSV", data=grid[["h3_cell", "stores", "pings", "share"]].to_csv(index=False).encode("utf-8"),
                       file_name=f"geopulse_h3_res{resolution}.csv", mime="text/csv")
    if info.get("unmatched"):
        st.caption(f"{info['unmatched']:,} matched pings had no coordinates and are not drawn.")
    st.caption(f"H3 resolution {resolution}. Ping coordinates come from BigQuery; each ping's hexagon is assigned in Python. "
               "Hexagons are equal-sized, so counts compare directly across areas.")


def hex_to_rgb(hex_color: str) -> list[int]:
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def page_3d() -> None:
    page_header("GEOPULSE / 3D ACTIVITY", "3D Hexagon View",
                "Each hexagon is a tower: the taller and darker it is, the more matched pings it holds.")
    filter_note()
    c1, c2, c3, c4 = st.columns([1.6, 1, 1, 1.2])
    res_label = c1.radio("Hexagon size", list(H3_RESOLUTIONS), index=1)
    resolution = H3_RESOLUTIONS[res_label]
    exaggeration = c2.slider("Tower height", 0.5, 3.0, 1.0, 0.1, help="Stretches every tower by the same factor. Counts are unchanged.")
    pitch = c3.slider("Tilt", 0, 70, 50, 5, help="0 looks straight down; higher angles show tower height.")
    focus = c4.selectbox("Zoom to", [FOCUS_BUSIEST, FOCUS_ALL] + sorted(selected_stores),
                         help="Opens the view on the busiest hexagons, the whole network, or a single store.")
    try:
        data = build_h3_grid(resolution)
    except Exception as exc:
        st.error("Pings could not be assigned to H3 hexagons.")
        st.code(str(exc))
        return
    if data is None:
        st.warning("No hexagons contain matched pings for the selected stores.")
        return
    cells, grid, total, half, diff, info = (data[k] for k in ("cells", "grid", "total", "half", "diff", "info"))
    top = grid.iloc[0]
    median = float(grid["pings"].median())
    top10_share = float(grid.head(10)["pings"].sum()) / max(total, 1) * 100
    callout(f"The tallest tower holds {int(top['pings']):,} pings, {int(top['pings']) / max(median, 1):.0f}× the median hexagon, in {top['stores']}.",
            f"Just {half} of {len(grid)} hexagons hold half of all matched pings, so activity is concentrated in a few spots. "
            "Plan manual counts at the tallest towers first.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Hexagons shown", f"{len(grid):,}", help="H3 cells with at least one matched ping.")
    k2.metric("Matched GPS pings", f"{total:,}", help="Store-matched pings. A ping in two catchments counts once per store, as in the store table.")
    k3.metric("Tallest tower", f"{int(top['pings']):,}", help="Pings in the densest hexagon.")
    k4.metric("Top 10 hexagons", f"{top10_share:.0f}% of pings", help="Share of all matched pings held by the ten busiest hexagons.")
    if bool((diff == 0).all()):
        st.caption(f"✓ Hexagon totals match the store table for every selected store ({total:,} pings).")
    else:
        st.warning("Hexagon totals differ from the store table for: " + ", ".join(short(n) for n in diff[diff > 0].index) + ".")

    codes, edges = h3_classes(grid["pings"])
    grid["color"] = [hex_to_rgb(H3_PALETTE[int(c)]) + [240] for c in codes]
    grid["pings_label"] = grid["pings"].map(lambda v: f"{int(v):,}")
    grid["share_label"] = grid["share"].map(lambda v: f"{v:.1f}%")
    base_height_m = 2000 if resolution == 8 else 800
    elevation_scale = base_height_m * exaggeration / max(float(grid["pings"].max()), 1)

    layers = [pdk.Layer("H3HexagonLayer", data=grid[["h3_cell", "pings", "color", "pings_label", "share_label", "stores"]],
                        get_hexagon="h3_cell", get_fill_color="color", get_elevation="pings", elevation_scale=elevation_scale,
                        extruded=True, coverage=0.9, opacity=0.95, pickable=True, auto_highlight=True,
                        highlight_color=[41, 46, 40, 255])]
    outlines = [{"type": "Feature", "geometry": json.loads(g), "properties": {}} for g in map_selection["catchment_geojson"].dropna()]
    if outlines:
        layers.append(pdk.Layer("GeoJsonLayer", data={"type": "FeatureCollection", "features": outlines}, stroked=True, filled=False,
                                get_line_color=[41, 46, 40, 200], line_width_min_pixels=1.5))
    labels = map_selection.assign(label=map_selection["store_name"].map(short))[["label", "latitude", "longitude"]]
    # Labels are drawn last, without depth testing, so towers can never hide them
    layers.append(pdk.Layer("TextLayer", data=labels, get_position=["longitude", "latitude"], get_text="label", get_size=15,
                            get_color=[41, 46, 40, 255], get_pixel_offset=[0, -24], billboard=True, background=True,
                            get_background_color=[255, 253, 248, 235], background_padding=[6, 3],
                            parameters={"depthTest": False}))

    min_lat, min_lon, max_lat, max_lon = hex_focus_bounds(cells, grid, half, focus)
    span = max(max_lat - min_lat, max_lon - min_lon, 0.01)
    zoom = min(max(math.log2(421 / (span * 1.5)), 9.0), 15.5)
    view = pdk.ViewState(latitude=(min_lat + max_lat) / 2, longitude=(min_lon + max_lon) / 2, zoom=zoom, pitch=pitch, bearing=-20)
    tooltip = {"html": "<b>{pings_label} pings</b><br/>{share_label} of selected pings<br/>{stores}<br/><small>{h3_cell}</small>",
               "style": {"backgroundColor": "#FFFDF8", "color": "#292E28", "fontFamily": "DM Sans, sans-serif",
                         "border": "1px solid #C8CCBF", "borderRadius": "8px", "padding": "6px 10px"}}
    deck = pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip, map_style="light")
    try:
        st.pydeck_chart(deck, width="stretch", height=620)
    except TypeError:  # older Streamlit without width="stretch"
        st.pydeck_chart(deck, use_container_width=True, height=620)

    st.markdown(h3_legend("Pings per hexagon (tower height and colour)", edges)
                .replace("</div>", "<br>Drag to pan, hold Ctrl or Shift and drag to rotate, scroll to zoom. Hover a tower for its numbers.</div>"),
                unsafe_allow_html=True)
    if info.get("unmatched"):
        st.caption(f"{info['unmatched']:,} matched pings had no coordinates and are not drawn.")
    st.caption(f"H3 resolution {resolution}. Tower height is proportional to ping count; the Tower height slider changes the scale, not the data. "
               "Basemap © OpenStreetMap contributors © CARTO.")


ROUTES = {
    "Executive Dashboard": page_executive,
    "Spatial Mobility Map Analysis": page_spatial,
    "H3 Hexagon Density": page_h3,
    "3D Hexagon View": page_3d,
    "Hourly Activity Patterns": page_hourly,
    "Store and Catchment Analysis": page_catchment,
    "Final Candidate Recommendation": page_recommendation,
    "Contact the Author": page_contact,
}
ROUTES[page]()

pulled, modified = data_pulled_at(), load_data_freshness()
st.markdown(f'<div class="footer">Data refreshed: {esc(pulled)} · Source tables last modified: {esc(modified or "unavailable")} · Source: BigQuery</div>',
            unsafe_allow_html=True)
