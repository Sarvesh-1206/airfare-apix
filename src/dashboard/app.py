"""Streamlit dashboard for India Real-Time Airfare Price Index (APIx)."""

import os
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_option_menu import option_menu

from api_client import APIClient


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="APIx — India Real-Time Airfare Price Index",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Styling
# ============================================================================

st.markdown(
    """
    <style>
    :root {
        --apix-ink: #172033;
        --apix-muted: #536174;
        --apix-blue: #005ea8;
        --apix-surface: #ffffff;
        --apix-page: #f4f7fb;
        --apix-border: #d6dee9;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--apix-page) !important;
        color: var(--apix-ink) !important;
    }

    [data-testid="stHeader"] {
        background: var(--apix-page) !important;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, p, label, [data-testid="stCaptionContainer"] {
        color: var(--apix-ink) !important;
    }

    [data-testid="stMetric"] {
        min-height: 116px;
        background: var(--apix-surface) !important;
        padding: 1.15rem 1.25rem !important;
        border: 1px solid var(--apix-border) !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(23, 32, 51, 0.06);
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p {
        color: var(--apix-muted) !important;
        font-size: 0.82rem !important;
        font-weight: 650 !important;
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div {
        color: var(--apix-ink) !important;
        font-size: clamp(1.35rem, 2vw, 2rem) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
    }

    [data-testid="stMetricDelta"] {
        color: var(--apix-muted) !important;
    }

    [data-testid="stSidebar"] {
        background: #eef3f8 !important;
        border-right: 1px solid var(--apix-border);
    }

    [data-testid="stSidebar"] * {
        color: var(--apix-ink);
    }

    [data-testid="stSidebar"] .nav-link {
        color: #334155 !important;
        border-radius: 7px;
        margin: 3px 0;
    }

    [data-testid="stSidebar"] .nav-link:hover {
        background: #dce8f4 !important;
        color: #123a61 !important;
    }

    [data-testid="stSidebar"] .nav-link-selected {
        background: var(--apix-blue) !important;
        color: #ffffff !important;
        font-weight: 700;
    }

    [data-testid="stSidebar"] .nav-link-selected span,
    [data-testid="stSidebar"] .nav-link-selected svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: var(--apix-border) !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--apix-border);
        border-radius: 8px;
        overflow: hidden;
    }

    .status-connected {
        color: #15803d !important;
        font-weight: 700;
    }

    .status-unavailable {
        color: #b91c1c !important;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# Session State
# ============================================================================

if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient()

if "page" not in st.session_state:
    st.session_state.page = "Overview"

api_client = st.session_state.api_client

# ============================================================================
# Cache Functions
# ============================================================================


@st.cache_data(ttl=30)
def get_latest_index() -> Optional[dict[str, Any]]:
    """Fetch latest index with caching."""
    try:
        return api_client.latest_index()
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_index_history() -> Optional[dict[str, Any]]:
    """Fetch index history with caching."""
    try:
        return api_client.index_history()
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_route_indices() -> Optional[dict[str, Any]]:
    """Fetch route indices with caching."""
    try:
        return api_client.route_indices()
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_lead_time_indices(
    fare_class: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Fetch lead-time indices with caching."""
    try:
        return api_client.lead_time_indices(fare_class=fare_class)
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_quality_report() -> Optional[dict[str, Any]]:
    """Fetch quality report with caching."""
    try:
        return api_client.quality_report()
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_summary() -> Optional[dict[str, Any]]:
    """Fetch summary with caching."""
    try:
        return api_client.summary()
    except requests.RequestException as e:
        return None


@st.cache_data(ttl=30)
def get_health_status() -> Optional[dict[str, Any]]:
    """Fetch health status with caching."""
    try:
        return api_client.health()
    except requests.RequestException as e:
        return None


# ============================================================================
# Helper Functions
# ============================================================================


def format_number(value: Any, decimals: int = 2) -> str:
    """Format a number for display."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: Any, decimals: int = 2) -> str:
    """Format a percentage for display."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (ValueError, TypeError):
        return str(value)


def get_status_color(status: str) -> str:
    """Get color for status badge."""
    status = str(status).upper()
    if status == "PASS":
        return "#22c55e"  # Green
    elif status == "REVIEW":
        return "#f59e0b"  # Amber
    elif status == "FAIL":
        return "#ef4444"  # Red
    return "#6b7280"  # Gray


def check_api_connection() -> bool:
    """Check if API is available."""
    try:
        health = get_health_status()
        return health is not None
    except Exception:
        return False


def prepare_route_chart_data(
    df: pd.DataFrame,
    value_column: str,
    chart_name: str,
) -> Optional[pd.DataFrame]:
    """Return clean route chart data using only real API dataframe values."""
    required_columns = {"route", value_column}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        st.warning(
            f"Unable to render {chart_name}: required route data is unavailable."
        )
        return None

    chart_df = df[["route", value_column]].copy()
    chart_df["route"] = chart_df["route"].astype("string").str.strip()
    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    chart_df = chart_df.loc[
        chart_df["route"].notna()
        & chart_df["route"].ne("")
        & chart_df[value_column].notna()
        & pd.notna(chart_df[value_column])
    ].copy()

    if chart_df.empty:
        st.warning(f"Unable to render {chart_name}: no valid route values are available.")
        return None

    return chart_df


# ============================================================================
# Sidebar
# ============================================================================


def render_sidebar() -> str:
    """Render sidebar navigation."""
    with st.sidebar:
        st.markdown("## ✈️ APIx")
        st.markdown("### India Real-Time Airfare Price Index")

        st.markdown("---")

        pages = [
            "Overview",
            "Route Analysis",
            "Lead-Time Analysis",
            "Historical Index",
            "Data Quality",
            "Methodology",
            "API / Data Access",
        ]

        selected = option_menu(
            menu_title=None,
            options=pages,
            icons=[
                "speedometer2",
                "map",
                "hourglass-split",
                "graph-up",
                "clipboard-check",
                "book",
                "plug",
            ],
            menu_icon="cast",
            default_index=0,
        )

        st.markdown("---")

        # Status and metadata
        is_connected = check_api_connection()

        if is_connected:
            status_text = "● API Connected"
            status_class = "status-connected"
            st.markdown(
                f"<div class='{status_class}'>{status_text}</div>",
                unsafe_allow_html=True,
            )
        else:
            status_text = "● API Unavailable"
            status_class = "status-unavailable"
            st.markdown(
                f"<div class='{status_class}'>{status_text}</div>",
                unsafe_allow_html=True,
            )

        # Latest collection date
        latest = get_latest_index()
        if latest and latest.get("date"):
            st.caption(f"Latest: {latest.get('date')}")
        else:
            st.caption("No data available")

        # Refresh button
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    return selected


# ============================================================================
# Overview Page
# ============================================================================


def render_kpi_cards(latest: Optional[dict[str, Any]]) -> None:
    """Render KPI cards for overview."""
    if not latest:
        st.error("Unable to load APIx data. Backend is unavailable.")
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="APIx",
            value=format_number(latest.get("value"), 2),
            delta=None,
        )

    with col2:
        daily_change = latest.get("daily_change_pct")
        st.metric(
            label="Daily Change",
            value=format_percentage(daily_change, 2),
            delta=None,
        )

    with col3:
        cumulative_change = latest.get("cumulative_change_pct")
        st.metric(
            label="Cumulative Change",
            value=format_percentage(cumulative_change, 2),
            delta=None,
        )

    with col4:
        summary = get_summary()
        observations = (
            summary.get("history_observations")
            if summary
            else latest.get("route_observations")
        )
        st.metric(
            label="Observations",
            value=format_number(observations, 0),
            delta=None,
        )

    with col5:
        routes_available = latest.get("routes_available")
        routes_expected = latest.get("routes_expected", 6)
        if routes_available:
            route_text = f"{int(routes_available)} / {routes_expected}"
        else:
            route_text = "—"
        st.metric(
            label="Routes Covered",
            value=route_text,
            delta=None,
        )


def render_index_trend(history: Optional[dict[str, Any]]) -> None:
    """Render APIx index trend chart."""
    st.subheader("APIx Index Trend")

    if not history or not history.get("data"):
        st.info(
            "**Building time series**\n\n"
            "APIx currently has 1 collection day. "
            "Additional daily observations are required to reveal meaningful index movement.\n\n"
            "**Base period**: 100.00"
        )
        return

    data = history.get("data", [])

    if len(data) <= 1:
        st.info(
            "**Building time series**\n\n"
            "APIx currently has 1 collection day. "
            "Additional daily observations are required to reveal meaningful index movement.\n\n"
            "**Base period**: 100.00"
        )
        return

    df = pd.DataFrame(data)
    df["collection_date"] = pd.to_datetime(df["collection_date"])
    df = df.sort_values("collection_date")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["collection_date"],
            y=df["apix_index"],
            mode="lines+markers",
            name="APIx",
            line=dict(color="#0066cc", width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>APIx: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="Collection Date",
        yaxis_title="APIx Index",
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#1a1a1a"),
        margin=dict(l=50, r=50, t=30, b=50),
        height=400,
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")

    st.plotly_chart(fig, use_container_width=True)


def render_route_performance(routes: Optional[dict[str, Any]]) -> None:
    """Render route performance panel."""
    st.subheader("Route Performance")

    if not routes or not routes.get("data"):
        st.warning("Unable to load route data.")
        return

    data = routes.get("data", [])
    df = pd.DataFrame(data)

    display_df = df[[
        "route",
        "route_index",
        "route_observations",
        "weight",
        "available_strata",
    ]].copy().sort_values("weight", ascending=False)
    display_df.columns = [
        "Route",
        "Route Index",
        "Observations",
        "DGCA Weight",
        "Available Strata",
    ]
    display_df["Route Index"] = display_df["Route Index"].apply(
        lambda x: format_number(x, 2)
    )
    display_df["Observations"] = display_df["Observations"].apply(
        lambda x: format_number(x, 0)
    )
    display_df["DGCA Weight"] = display_df["DGCA Weight"].apply(
        lambda x: format_percentage(float(x) * 100, 2)
    )
    display_df["Available Strata"] = display_df["Available Strata"].apply(
        lambda x: format_number(x, 0)
    )

    st.caption("Route details")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.caption("DGCA route weights")
    weight_df = prepare_route_chart_data(df, "weight", "DGCA route weights")
    if weight_df is None:
        return
    weight_df["weight_pct"] = weight_df["weight"] * 100
    weight_df = weight_df.sort_values("weight_pct", ascending=False)
    fig = go.Figure(
        go.Bar(
            x=weight_df["weight_pct"],
            y=weight_df["route"],
            orientation="h",
            marker=dict(color="#005ea8"),
            text=weight_df["weight_pct"].map(lambda value: f"{value:.2f}%"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>DGCA weight: %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title=None,
        xaxis_title="DGCA weight (%)",
        yaxis_title=None,
        xaxis=dict(range=[0, max(weight_df["weight_pct"].max() * 1.2, 35)]),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#172033"),
        margin=dict(l=85, r=55, t=20, b=55),
        height=330,
    )
    fig.update_yaxes(
        showgrid=False,
        automargin=True,
        categoryorder="array",
        categoryarray=weight_df["route"].tolist(),
        autorange="reversed",
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#d6dee9")
    st.plotly_chart(fig, use_container_width=True)


def render_data_quality_summary(quality: Optional[dict[str, Any]]) -> None:
    """Render data quality summary."""
    st.subheader("Data Quality Status")

    if not quality:
        st.warning("Unable to load quality data.")
        return

    overall_status = quality.get("overall_status", "UNKNOWN")
    pass_count = quality.get("pass_count", 0)
    review_count = quality.get("review_count", 0)
    fail_count = quality.get("fail_count", 0)

    status_color = get_status_color(overall_status)
    st.markdown(
        f"<div style='background: #fff7e6; border: 1px solid {status_color}; border-left: 6px solid {status_color}; border-radius: 8px; padding: 0.8rem 1rem; max-width: 360px;'>"
        f"<div style='color: #172033; font-size: 0.8rem; font-weight: 650;'>Overall status</div>"
        f"<div style='color: {status_color}; font-size: 1.6rem; font-weight: 750;'>{overall_status}</div></div>",
        unsafe_allow_html=True,
    )

    st.caption("Quality check counts")
    count_col1, count_col2, count_col3 = st.columns(3)

    with count_col1:
        st.metric(label="PASS", value=pass_count)

    with count_col2:
        st.metric(label="REVIEW", value=review_count)

    with count_col3:
        st.metric(label="FAIL", value=fail_count)

    st.markdown("---")
    st.caption(
        "Review items reflect current collection depth and statistical "
        "outlier screening."
    )

    if st.button("View full quality report", key="quality_detail"):
        st.session_state.page = "Data Quality"
        st.rerun()


def render_dataset_metadata(
    summary: Optional[dict[str, Any]],
    lead_time_data: Optional[dict[str, Any]],
) -> None:
    """Render dataset metadata panel."""
    st.subheader("APIx Dataset")

    if not summary:
        st.warning("Unable to load summary data.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.caption("Collection Period")
        base_date = summary.get("base_collection_date", "—")
        st.text(f"Base Date: {base_date}")
        collection_start = summary.get("collection_start", "—")
        st.text(f"Start: {collection_start}")
        collection_end = summary.get("collection_end", "—")
        st.text(f"End: {collection_end}")

    with col2:
        st.caption("Observations & Coverage")
        collection_days = summary.get("collection_days", 0)
        st.text(f"Collection Days: {int(collection_days)}")
        history_obs = summary.get("history_observations", 0)
        st.text(f"History Observations: {int(history_obs)}")
        valid_relatives = summary.get("valid_relative_records", 0)
        st.text(f"Valid Relative Records: {int(valid_relatives)}")

    with col3:
        st.caption("Index & Stratification")
        num_routes = len(summary.get("route_weights", {}))
        st.text(f"Routes: {num_routes}")
        base_idx = summary.get("base_index", 100)
        st.text(f"Base Index: {format_number(base_idx, 2)}")

    with col4:
        st.caption("Fare Classes & Lead Times")
        lead_records = (lead_time_data or {}).get("data", [])
        fare_classes = sorted({
            record.get("fare_class") for record in lead_records
            if record.get("fare_class")
        })
        lead_times = sorted({
            int(record.get("advance_purchase_days"))
            for record in lead_records
            if record.get("advance_purchase_days") is not None
        })
        fare_text = ", ".join(fare_classes) if fare_classes else "—"
        lead_text = ", ".join(f"T+{days}" for days in lead_times) or "—"
        st.text(f"Fare Classes: {fare_text}")
        st.text(f"Lead Times: {lead_text}")


def render_overview() -> None:
    """Render overview page."""
    st.title("APIx Overview")
    st.markdown("India Real-Time Airfare Price Index")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col3:
        if st.button("Refresh", key="overview_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # Fetch data
    latest = get_latest_index()
    history = get_index_history()
    routes = get_route_indices()
    quality = get_quality_report()
    summary = get_summary()
    lead_time_data = get_lead_time_indices()

    # KPI Cards
    render_kpi_cards(latest)

    st.markdown("---")

    # Main sections
    render_index_trend(history)
    render_route_performance(routes)

    st.markdown("---")

    render_data_quality_summary(quality)
    render_dataset_metadata(summary, lead_time_data)


# ============================================================================
# Route Analysis Page
# ============================================================================


def render_route_analysis() -> None:
    """Render route analysis page."""
    st.title("Route Analysis")

    routes = get_route_indices()

    if not routes or not routes.get("data"):
        st.error("Unable to load route data.")
        return

    data = routes.get("data", [])
    df = pd.DataFrame(data)

    # Summary statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Routes", value=len(df))

    with col2:
        total_obs = df.get("route_observations", []).sum() if "route_observations" in df.columns else 0
        st.metric(label="Total Observations", value=format_number(total_obs, 0))

    with col3:
        total_weight = df["weight"].sum() if "weight" in df.columns else None
        coverage_text = (
            format_percentage(total_weight * 100, 2)
            if total_weight is not None
            else "—"
        )
        st.metric(label="Weight Coverage", value=coverage_text)

    st.markdown("---")

    # Route weight chart
    st.subheader("DGCA Route Weights")

    weight_df = prepare_route_chart_data(df, "weight", "DGCA route weights")
    if weight_df is None:
        return
    weight_df["weight_pct"] = weight_df["weight"] * 100
    weight_df = weight_df.sort_values("weight_pct", ascending=False)

    fig = go.Figure(
        go.Bar(
            x=weight_df["weight_pct"],
            y=weight_df["route"],
            orientation="h",
            marker=dict(color="#0066cc"),
            text=weight_df["weight_pct"].map(lambda value: f"{value:.2f}%"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>DGCA weight: %{x:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="DGCA weight (%)",
        yaxis_title=None,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#1a1a1a"),
        margin=dict(l=100, r=65, t=30, b=50),
        height=430,
    )

    fig.update_yaxes(
        showgrid=False,
        automargin=True,
        categoryorder="array",
        categoryarray=weight_df["route"].tolist(),
        autorange="reversed",
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Route index chart
    st.subheader("Route Index Values")

    route_idx_df = prepare_route_chart_data(
        df, "route_index", "route index values"
    )
    if route_idx_df is None:
        return
    route_idx_df = route_idx_df.sort_values("route")

    fig = go.Figure(
        go.Bar(
            x=route_idx_df["route"],
            y=route_idx_df["route_index"],
            marker=dict(color="#22c55e"),
            hovertemplate="<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="Route",
        yaxis_title="Route Index",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#1a1a1a"),
        margin=dict(l=50, r=50, t=30, b=75),
        height=450,
    )

    fig.update_xaxes(
        showgrid=False,
        categoryorder="array",
        categoryarray=route_idx_df["route"].tolist(),
        automargin=True,
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Detailed route table
    st.subheader("Route Details")

    display_df = df[[
        "route",
        "route_index",
        "weight",
        "route_observations",
        "available_strata",
    ]].copy()

    display_df.columns = [
        "Route",
        "Route Index",
        "DGCA Weight",
        "Observations",
        "Available Strata",
    ]

    display_df["Route Index"] = display_df["Route Index"].apply(
        lambda x: format_number(x, 2)
    )
    display_df["DGCA Weight"] = display_df["DGCA Weight"].apply(
        lambda x: f"{float(x) * 100:.2f}%"
    )
    display_df["Observations"] = display_df["Observations"].apply(
        lambda x: format_number(x, 0)
    )
    display_df["Available Strata"] = display_df["Available Strata"].apply(
        lambda x: format_number(x, 0)
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================================
# Lead-Time Analysis Page
# ============================================================================


def render_lead_time_analysis() -> None:
    """Render lead-time analysis page."""
    st.title("Lead-Time Analysis")

    # Fare class selector
    col1, col2 = st.columns([1, 3])

    with col1:
        fare_class = st.selectbox(
            label="Fare Class",
            options=["Economy", "Business"],
            key="lead_time_fare_class",
        )

    lead_times = get_lead_time_indices(fare_class=fare_class)

    if not lead_times or not lead_times.get("data"):
        st.error("Unable to load lead-time data.")
        return

    data = lead_times.get("data", [])
    df = pd.DataFrame(data)

    # Check if this is base period
    if (df["index"] == 100.0).all():
        st.info(
            f"**Base-period values**\n\n"
            f"Additional collection days are required to measure "
            f"{fare_class} lead-time price movement.\n\n"
            f"All lead-time indices are at base (100.00)."
        )

        # Still show the data
        display_df = df[[
            "advance_purchase_days",
            "index",
            "observations",
        ]].copy()

        display_df.columns = ["Lead Time (Days)", "Index", "Observations"]
        display_df["Lead Time (Days)"] = display_df["Lead Time (Days)"].apply(
            lambda x: f"T+{int(x)}"
        )
        display_df["Index"] = display_df["Index"].apply(
            lambda x: format_number(x, 2)
        )
        display_df["Observations"] = display_df["Observations"].apply(
            lambda x: format_number(x, 0)
        )

        st.subheader("Lead-Time Index Values")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        return

    # Chart
    df_sorted = df.sort_values("advance_purchase_days")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_sorted["advance_purchase_days"].apply(lambda x: f"T+{int(x)}"),
            y=df_sorted["index"],
            mode="lines+markers",
            name=f"{fare_class} Index",
            line=dict(color="#0066cc", width=2),
            marker=dict(size=10),
            hovertemplate="<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="Lead Time",
        yaxis_title="Index Value",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#1a1a1a"),
        margin=dict(l=50, r=50, t=30, b=50),
        height=400,
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("Lead-Time Index Values")

    display_df = df.sort_values("advance_purchase_days")[[
        "advance_purchase_days",
        "index",
        "observations",
    ]].copy()

    display_df.columns = ["Lead Time (Days)", "Index", "Observations"]
    display_df["Lead Time (Days)"] = display_df["Lead Time (Days)"].apply(
        lambda x: f"T+{int(x)}"
    )
    display_df["Index"] = display_df["Index"].apply(
        lambda x: format_number(x, 2)
    )
    display_df["Observations"] = display_df["Observations"].apply(
        lambda x: format_number(x, 0)
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================================
# Historical Index Page
# ============================================================================


def render_historical_index() -> None:
    """Render historical index page."""
    st.title("Historical Index")

    history = get_index_history()

    if not history or not history.get("data"):
        st.error("Unable to load historical data.")
        return

    data = history.get("data", [])
    df = pd.DataFrame(data)

    # Check if single day
    if len(df) <= 1:
        st.info(
            "**Building time series**\n\n"
            "APIx currently has 1 collection day. "
            "Additional daily observations are required to reveal meaningful index movement.\n\n"
            "**Base period**: 100.00"
        )

        if len(df) == 1:
            row = df.iloc[0]
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="Date",
                    value=row.get("collection_date", "—"),
                )

            with col2:
                st.metric(
                    label="APIx Index",
                    value=format_number(row.get("apix_index"), 2),
                )

            with col3:
                st.metric(
                    label="Observations",
                    value=format_number(
                        row.get("route_observations"), 0
                    ),
                )

            with col4:
                st.metric(
                    label="Routes",
                    value=format_number(row.get("routes_available"), 0),
                )

        return

    # Historical chart
    df["collection_date"] = pd.to_datetime(df["collection_date"])
    df = df.sort_values("collection_date")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["collection_date"],
            y=df["apix_index"],
            mode="lines+markers",
            name="APIx",
            line=dict(color="#0066cc", width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>APIx: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="Collection Date",
        yaxis_title="APIx Index",
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color="#1a1a1a"),
        margin=dict(l=50, r=50, t=30, b=50),
        height=500,
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e0e0e0")

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("Daily Summary")

    display_df = df[[
        "collection_date",
        "apix_index",
        "daily_change_pct",
        "cumulative_change_pct",
        "routes_available",
        "route_weight_coverage",
        "route_observations",
    ]].copy()

    display_df.columns = [
        "Date",
        "APIx Index",
        "Daily Change %",
        "Cumulative Change %",
        "Routes",
        "Weight Coverage",
        "Observations",
    ]

    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df["APIx Index"] = display_df["APIx Index"].apply(
        lambda x: format_number(x, 2)
    )
    display_df["Daily Change %"] = display_df["Daily Change %"].apply(
        lambda x: format_percentage(x, 2)
    )
    display_df["Cumulative Change %"] = display_df["Cumulative Change %"].apply(
        lambda x: format_percentage(x, 2)
    )
    display_df["Routes"] = display_df["Routes"].apply(
        lambda x: format_number(x, 0)
    )
    display_df["Weight Coverage"] = display_df["Weight Coverage"].apply(
        lambda x: format_percentage(x * 100, 2)
    )
    display_df["Observations"] = display_df["Observations"].apply(
        lambda x: format_number(x, 0)
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================================
# Data Quality Page
# ============================================================================


def render_data_quality() -> None:
    """Render data quality page."""
    st.title("Data Quality")

    quality = get_quality_report()

    if not quality:
        st.error("Unable to load quality data.")
        return

    overall_status = quality.get("overall_status", "UNKNOWN")
    pass_count = quality.get("pass_count", 0)
    review_count = quality.get("review_count", 0)
    fail_count = quality.get("fail_count", 0)

    status_color = get_status_color(overall_status)
    st.markdown(
        f"<div style='background: #fff7e6; border: 1px solid {status_color}; border-left: 6px solid {status_color}; border-radius: 8px; padding: 0.8rem 1rem; max-width: 360px;'>"
        f"<div style='color: #172033; font-size: 0.8rem; font-weight: 650;'>Overall status</div>"
        f"<div style='color: {status_color}; font-size: 1.6rem; font-weight: 750;'>{overall_status}</div></div>",
        unsafe_allow_html=True,
    )

    st.caption("Quality check counts")
    count_col1, count_col2, count_col3 = st.columns(3)

    with count_col1:
        st.metric(label="PASS", value=pass_count)

    with count_col2:
        st.metric(label="REVIEW", value=review_count)

    with count_col3:
        st.metric(label="FAIL", value=fail_count)

    st.markdown("---")

    # QC checks
    st.subheader("Quality Control Checks")

    checks = quality.get("checks", [])

    if not checks:
        st.info("No quality checks available.")
        return

    for check in checks:
        check_name = check.get("check", "Unknown Check")
        status = check.get("status", "UNKNOWN")
        message = check.get("message", "")
        value = check.get("value", "—")
        threshold = check.get("threshold", "—")

        status_color = get_status_color(status)

        col1, col2 = st.columns([0.15, 0.85])

        with col1:
            st.markdown(
                f"<span style='color: {status_color}; font-weight: bold;'>●</span>",
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"**{check_name}** — {status}",
                unsafe_allow_html=True,
            )

            if message:
                st.caption(message)

            if value != "—" or threshold != "—":
                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.caption(f"Value: {format_number(value, 2)}")
                with detail_col2:
                    st.caption(f"Threshold: {format_number(threshold, 2)}")

        st.markdown("---")


# ============================================================================
# Methodology Page
# ============================================================================


def render_methodology() -> None:
    """Render methodology page."""
    st.title("Methodology")

    st.markdown(
        """
    ## APIx Index Calculation
    
    The India Real-Time Airfare Price Index (APIx) measures observed total-fare price 
    movement across domestic aviation routes. The index is constructed from actual 
    booking data without the use of machine learning models in the calculation process.
    
    ### Methodology Flow
    
    1. **Observed Fares** — Raw total-fare bookings collected in real time
    2. **Data Validation** — Quality control checks for completeness and consistency
    3. **Fare Stratification** — Fares organized by route, lead time, and fare class
    4. **Price Relatives** — Observed fares converted to price relatives
    5. **Route Aggregation** — Route-level indices calculated from price relatives
    6. **DGCA Weighting** — Route indices combined using DGCA two-way passenger weights
    7. **Composite APIx** — Weighted composite index value
    
    ---
    
    ### Key Parameters
    
    **Index Base:** First collection day = 100
    
    **Weight Source:** DGCA two-way passenger traffic data
    
    **Lead Times (Advance Purchase Buckets):**
    - T+1 (1 day ahead)
    - T+7 (7 days ahead)
    - T+15 (15 days ahead)
    - T+30 (30 days ahead)
    - T+45 (45 days ahead)
    
    **Fare Classes:**
    - Economy
    - Business
    
    **Routes:**
    - DEL-BOM (Delhi ↔ Mumbai)
    - DEL-BLR (Delhi ↔ Bangalore)
    - BOM-BLR (Mumbai ↔ Bangalore)
    - DEL-CCU (Delhi ↔ Kolkata)
    - DEL-HYD (Delhi ↔ Hyderabad)
    - DEL-MAA (Delhi ↔ Chennai)
    
    ---
    
    ### Important Notes
    
    ⚠️ **ML is NOT used to calculate APIx.**
    
    Machine learning models in the APIx system serve as supporting and forecasting 
    tools only. They are not part of the observed-fare APIx index calculation. 
    The index is derived entirely from:
    - Observed total fares
    - Fare stratification
    - Price relatives
    - DGCA passenger weights
    - Route aggregation
    
    The index reflects actual market conditions based on observed prices, not predictions.
    
    ---
    
    ### Time Series & Base Period
    
    A meaningful APIx time series requires multiple collection days. On the first 
    collection day, all index values equal 100 by definition (base period). Index 
    movement becomes visible once additional daily collections provide comparative 
    observations.
    
    The system automatically scales available route weights on days when certain 
    routes have insufficient data.
    """
    )


# ============================================================================
# API / Data Access Page
# ============================================================================


def render_api_access() -> None:
    """Render API/data access page."""
    st.title("API / Data Access")

    # Status
    st.subheader("API Status")

    is_connected = check_api_connection()

    if is_connected:
        st.success("✓ API is online and responsive")
        base_url = api_client.base_url
        st.code(base_url, language="text")
    else:
        st.error("✗ API is currently unavailable")
        st.caption("Check that the FastAPI backend is running.")

    st.markdown("---")

    # Endpoints
    st.subheader("Available Endpoints")

    endpoints = [
        {
            "method": "GET",
            "endpoint": "/health",
            "description": "Check API health and output file availability",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/index/latest",
            "description": "Retrieve the latest APIx index observation",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/index/history",
            "description": "Retrieve APIx daily time series (with optional date filtering)",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/index/routes",
            "description": "Retrieve route-level APIx indices",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/index/lead-times",
            "description": "Retrieve APIx by lead-time strata and fare class",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/quality",
            "description": "Retrieve statistical quality-control report",
        },
        {
            "method": "GET",
            "endpoint": "/api/v1/summary",
            "description": "Retrieve APIx summary metadata and route weights",
        },
    ]

    for ep in endpoints:
        col1, col2, col3 = st.columns([0.15, 0.35, 0.5])

        with col1:
            st.code(ep["method"], language="text")

        with col2:
            st.code(ep["endpoint"], language="text")

        with col3:
            st.write(ep["description"])

    st.markdown("---")

    st.subheader("Documentation")

    st.markdown(
        """
    For complete API documentation and to test endpoints interactively, 
    visit the Swagger UI:
    
    **{base_url}/docs**
    
    The backend returns JSON-formatted data with the following structure:
    
    - **latest_index()**: Current APIx value, date, daily/cumulative changes
    - **index_history()**: Time series of daily APIx observations
    - **route_indices()**: Route-level indices and DGCA weights
    - **lead_time_indices()**: Index values stratified by lead time and fare class
    - **quality_report()**: QC check results and overall data quality status
    - **summary()**: Metadata including routes, base period, collection statistics
    """.replace("{base_url}", api_client.base_url)
    )


# ============================================================================
# Main App
# ============================================================================


def main() -> None:
    """Main application."""
    # Render sidebar and get selected page
    selected_page = render_sidebar()

    # Render selected page
    if selected_page == "Overview":
        render_overview()
    elif selected_page == "Route Analysis":
        render_route_analysis()
    elif selected_page == "Lead-Time Analysis":
        render_lead_time_analysis()
    elif selected_page == "Historical Index":
        render_historical_index()
    elif selected_page == "Data Quality":
        render_data_quality()
    elif selected_page == "Methodology":
        render_methodology()
    elif selected_page == "API / Data Access":
        render_api_access()


if __name__ == "__main__":
    main()

