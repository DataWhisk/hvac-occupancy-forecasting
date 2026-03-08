"""
Streamlit proof-of-concept dashboard for PostgreSQL-backed occupancy and HVAC insights.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from typing import Optional, Tuple

# Make `src.*` imports work even when streamlit is launched outside repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.viz.dashboard_data import (
    fetch_hvac_comfort_summary,
    fetch_hvac_daily,
    fetch_hvac_hourly,
    fetch_hvac_kpis,
    fetch_hvac_zone_stats,
    fetch_occupancy_daily,
    fetch_occupancy_heatmap,
    fetch_occupancy_kpis,
    fetch_occupancy_space_stats,
)
from src.viz.dashboard_insights import POSTGRES_DOW_LABELS, derive_hvac_insights, derive_occupancy_insights

DOW_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _fmt_int(value: object) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return "N/A"
    return f"{int(numeric):,}"


def _fmt_float(value: object, decimals: int = 2) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return "N/A"
    return f"{float(numeric):,.{decimals}f}"


def _extract_bounds(kpi_df: pd.DataFrame) -> Tuple[date, date]:
    if kpi_df.empty or pd.isna(kpi_df.iloc[0]["min_ts"]) or pd.isna(kpi_df.iloc[0]["max_ts"]):
        today = pd.Timestamp.utcnow().date()
        return today, today
    min_date = pd.Timestamp(kpi_df.iloc[0]["min_ts"]).date()
    max_date = pd.Timestamp(kpi_df.iloc[0]["max_ts"]).date()
    return min_date, max_date


def _normalize_selected_range(
    value: object,
    default_start: date,
    default_end: date,
) -> Tuple[date, date]:
    if isinstance(value, tuple) and len(value) == 2:
        start, end = value
        return (start or default_start, end or default_end)
    if isinstance(value, list) and len(value) == 2:
        start, end = value
        return (start or default_start, end or default_end)
    if isinstance(value, date):
        return value, value
    return default_start, default_end


def _to_datetime_window(start_day: date, end_day: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(start_day)
    end = pd.Timestamp(end_day) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return start, end


@st.cache_data(ttl=900, show_spinner=False)
def _cached_occ_kpis(schema: str, env_path: str, start_ts: Optional[pd.Timestamp], end_ts: Optional[pd.Timestamp]) -> pd.DataFrame:
    return fetch_occupancy_kpis(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_occ_daily(schema: str, env_path: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    return fetch_occupancy_daily(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_occ_heatmap(schema: str, env_path: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    return fetch_occupancy_heatmap(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_occ_space_stats(schema: str, env_path: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    return fetch_occupancy_space_stats(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_hvac_kpis(schema: str, env_path: str, start_ts: Optional[pd.Timestamp], end_ts: Optional[pd.Timestamp]) -> pd.DataFrame:
    return fetch_hvac_kpis(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_hvac_daily(schema: str, env_path: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    return fetch_hvac_daily(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_hvac_hourly(schema: str, env_path: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    return fetch_hvac_hourly(schema=schema, env_path=env_path, start_ts=start_ts, end_ts=end_ts)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_hvac_zone_stats(
    schema: str,
    env_path: str,
    comfort_low: float,
    comfort_high: float,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> pd.DataFrame:
    return fetch_hvac_zone_stats(
        schema=schema,
        env_path=env_path,
        comfort_low=comfort_low,
        comfort_high=comfort_high,
        start_ts=start_ts,
        end_ts=end_ts,
    )


@st.cache_data(ttl=900, show_spinner=False)
def _cached_hvac_comfort_summary(
    schema: str,
    env_path: str,
    comfort_low: float,
    comfort_high: float,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> pd.DataFrame:
    return fetch_hvac_comfort_summary(
        schema=schema,
        env_path=env_path,
        comfort_low=comfort_low,
        comfort_high=comfort_high,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def _load_kpis(schema: str, env_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    occ = _cached_occ_kpis(schema=schema, env_path=env_path, start_ts=None, end_ts=None)
    hvac = _cached_hvac_kpis(schema=schema, env_path=env_path, start_ts=None, end_ts=None)
    return occ, hvac


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def main() -> None:
    st.set_page_config(
        page_title="HVAC & Occupancy POC Dashboard",
        page_icon="🏢",
        layout="wide",
    )
    st.title("HVAC & Occupancy POC Dashboard")
    st.caption(
        "PostgreSQL-backed historical dashboard with separate occupancy and HVAC insights. "
        "No direct occupancy↔HVAC join is used in this version."
    )

    with st.sidebar:
        st.header("Settings")
        env_path = st.text_input("Env file path", value=".env")
        schema = st.text_input("DB schema", value="public")
        top_n = st.slider("Top-N for ranking charts", min_value=5, max_value=30, value=10, step=1)
        st.divider()
        st.subheader("HVAC Comfort Band (°F)")
        comfort_low = st.number_input("Lower bound", value=70.0, step=0.5)
        comfort_high = st.number_input("Upper bound", value=76.0, step=0.5)
        if comfort_high <= comfort_low:
            st.error("Upper comfort bound must be greater than lower bound.")
            st.stop()

    try:
        occ_kpis_all, hvac_kpis_all = _load_kpis(schema=schema, env_path=env_path)
    except Exception as exc:
        st.error(f"Failed to load dashboard KPI data from PostgreSQL: {exc}")
        st.stop()

    occ_min, occ_max = _extract_bounds(occ_kpis_all)
    hvac_min, hvac_max = _extract_bounds(hvac_kpis_all)

    with st.sidebar:
        st.divider()
        st.subheader("Occupancy Date Range")
        selected_occ = st.date_input(
            "Occupancy window",
            value=(occ_min, occ_max),
            min_value=occ_min,
            max_value=occ_max,
            key="occ_window",
        )
        st.subheader("HVAC Date Range")
        selected_hvac = st.date_input(
            "HVAC window",
            value=(hvac_min, hvac_max),
            min_value=hvac_min,
            max_value=hvac_max,
            key="hvac_window",
        )

    occ_start_date, occ_end_date = _normalize_selected_range(selected_occ, occ_min, occ_max)
    hvac_start_date, hvac_end_date = _normalize_selected_range(selected_hvac, hvac_min, hvac_max)
    occ_start_ts, occ_end_ts = _to_datetime_window(occ_start_date, occ_end_date)
    hvac_start_ts, hvac_end_ts = _to_datetime_window(hvac_start_date, hvac_end_date)

    tabs = st.tabs(["Overview", "Occupancy Insights", "HVAC Insights"])

    with tabs[0]:
        st.subheader("Coverage & KPI Snapshot")
        left, right = st.columns(2)

        with left:
            st.markdown("**Occupancy Dataset (`space_occupancy`)**")
            row = occ_kpis_all.iloc[0] if not occ_kpis_all.empty else {}
            c1, c2, c3 = st.columns(3)
            c1.metric("Rows", _fmt_int(row.get("rows")))
            c2.metric("Spaces", _fmt_int(row.get("spaces")))
            c3.metric("Date Span", f"{occ_min} → {occ_max}")
            c4, c5, c6 = st.columns(3)
            c4.metric("Average Occupancy", _fmt_float(row.get("avg_occ")))
            c5.metric("Median Occupancy", _fmt_float(row.get("median_occ")))
            c6.metric("Peak Occupancy", _fmt_int(row.get("peak_occ")))

        with right:
            st.markdown("**HVAC Dataset (`hvac`)**")
            row = hvac_kpis_all.iloc[0] if not hvac_kpis_all.empty else {}
            c1, c2, c3 = st.columns(3)
            c1.metric("Rows", _fmt_int(row.get("rows")))
            c2.metric("VAV Zones", _fmt_int(row.get("zones")))
            c3.metric("Date Span", f"{hvac_min} → {hvac_max}")
            c4, c5, c6 = st.columns(3)
            c4.metric("Average Zone Temp (°F)", _fmt_float(row.get("avg_temp")))
            c5.metric("Median Zone Temp (°F)", _fmt_float(row.get("median_temp")))
            c6.metric("P95 Zone Temp (°F)", _fmt_float(row.get("p95_temp")))

        st.info(
            "This POC intentionally keeps occupancy and HVAC analyses separate because current "
            "database identifiers and time ranges do not support a trustworthy direct join."
        )

    with tabs[1]:
        st.subheader("Occupancy Trends and Room Utilization")
        try:
            occ_kpis = _cached_occ_kpis(schema=schema, env_path=env_path, start_ts=occ_start_ts, end_ts=occ_end_ts)
            occ_daily = _cached_occ_daily(schema=schema, env_path=env_path, start_ts=occ_start_ts, end_ts=occ_end_ts)
            occ_heatmap = _cached_occ_heatmap(schema=schema, env_path=env_path, start_ts=occ_start_ts, end_ts=occ_end_ts)
            occ_spaces = _cached_occ_space_stats(schema=schema, env_path=env_path, start_ts=occ_start_ts, end_ts=occ_end_ts)
        except Exception as exc:
            st.error(f"Failed to load occupancy insights: {exc}")
            st.stop()

        if occ_daily.empty:
            st.warning("No occupancy data found for the selected date range.")
        else:
            row = occ_kpis.iloc[0] if not occ_kpis.empty else {}
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows (Filtered)", _fmt_int(row.get("rows")))
            m2.metric("Spaces (Filtered)", _fmt_int(row.get("spaces")))
            m3.metric("Peak Occupancy (Filtered)", _fmt_int(row.get("peak_occ")))

            occ_daily = _coerce_numeric(occ_daily, ["avg_occ", "peak_occ", "samples"])
            fig_daily = px.line(
                occ_daily,
                x="day",
                y=["avg_occ", "peak_occ"],
                markers=True,
                labels={"value": "Occupancy", "variable": "Metric", "day": "Date"},
                title="Daily Occupancy Trend",
            )
            st.plotly_chart(fig_daily, use_container_width=True)

            if not occ_heatmap.empty:
                heat = _coerce_numeric(occ_heatmap, ["day_of_week", "hour_of_day", "avg_occ"])
                heat["day_name"] = heat["day_of_week"].map(POSTGRES_DOW_LABELS)
                heat["day_name"] = pd.Categorical(heat["day_name"], categories=DOW_ORDER, ordered=True)
                pivot = (
                    heat.pivot(index="day_name", columns="hour_of_day", values="avg_occ")
                    .reindex(DOW_ORDER)
                )
                fig_heat = px.imshow(
                    pivot,
                    aspect="auto",
                    labels={"x": "Hour of Day", "y": "Day of Week", "color": "Avg Occupancy"},
                    title="Occupancy Heatmap (Average Count)",
                    color_continuous_scale="YlGnBu",
                )
                st.plotly_chart(fig_heat, use_container_width=True)

            if not occ_spaces.empty:
                spaces = _coerce_numeric(occ_spaces, ["avg_occ", "peak_occ", "samples"])
                top_spaces = spaces.sort_values("avg_occ", ascending=False).head(top_n).sort_values("avg_occ")
                fig_top = px.bar(
                    top_spaces,
                    x="avg_occ",
                    y="space_label",
                    orientation="h",
                    labels={"avg_occ": "Average Occupancy", "space_label": "Space"},
                    title=f"Top {top_n} Spaces by Average Occupancy",
                )
                st.plotly_chart(fig_top, use_container_width=True)

                insights = derive_occupancy_insights(occ_heatmap, occ_spaces)
                i1, i2, i3 = st.columns(3)
                i1.metric("Busiest Day", str(insights["busiest_day"]))
                i2.metric(
                    "Busiest Hour",
                    str(insights["busiest_hour"]),
                    delta=f"Avg {insights['busiest_hour_avg_occ']}",
                )
                i3.metric(
                    "Highest-Utilization Space",
                    str(insights["highest_util_space"]),
                    delta=f"Avg {insights['highest_util_avg_occ']}",
                )
                low_spaces = insights["low_util_spaces"]
                if low_spaces:
                    st.caption("Low-utilization spaces (candidate review list): " + ", ".join(low_spaces))

    with tabs[2]:
        st.subheader("HVAC Zone Temperature Behavior")
        try:
            hvac_kpis = _cached_hvac_kpis(schema=schema, env_path=env_path, start_ts=hvac_start_ts, end_ts=hvac_end_ts)
            hvac_daily = _cached_hvac_daily(schema=schema, env_path=env_path, start_ts=hvac_start_ts, end_ts=hvac_end_ts)
            hvac_hourly = _cached_hvac_hourly(schema=schema, env_path=env_path, start_ts=hvac_start_ts, end_ts=hvac_end_ts)
            hvac_zones = _cached_hvac_zone_stats(
                schema=schema,
                env_path=env_path,
                comfort_low=float(comfort_low),
                comfort_high=float(comfort_high),
                start_ts=hvac_start_ts,
                end_ts=hvac_end_ts,
            )
            hvac_comfort = _cached_hvac_comfort_summary(
                schema=schema,
                env_path=env_path,
                comfort_low=float(comfort_low),
                comfort_high=float(comfort_high),
                start_ts=hvac_start_ts,
                end_ts=hvac_end_ts,
            )
        except Exception as exc:
            st.error(f"Failed to load HVAC insights: {exc}")
            st.stop()

        if hvac_daily.empty:
            st.warning("No HVAC data found for the selected date range.")
        else:
            row = hvac_kpis.iloc[0] if not hvac_kpis.empty else {}
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows (Filtered)", _fmt_int(row.get("rows")))
            m2.metric("Zones (Filtered)", _fmt_int(row.get("zones")))
            m3.metric("P95 Temp (Filtered)", _fmt_float(row.get("p95_temp")))

            hvac_daily = _coerce_numeric(hvac_daily, ["avg_temp", "p95_temp", "samples"])
            fig_daily = px.line(
                hvac_daily,
                x="day",
                y=["avg_temp", "p95_temp"],
                markers=True,
                labels={"value": "Temperature (°F)", "variable": "Metric", "day": "Date"},
                title="Daily HVAC Temperature Profile",
            )
            st.plotly_chart(fig_daily, use_container_width=True)

            hvac_hourly = _coerce_numeric(hvac_hourly, ["hour_of_day", "avg_temp", "p90_temp"])
            fig_hourly = px.line(
                hvac_hourly,
                x="hour_of_day",
                y=["avg_temp", "p90_temp"],
                markers=True,
                labels={"hour_of_day": "Hour of Day", "value": "Temperature (°F)", "variable": "Metric"},
                title="Hourly HVAC Temperature Profile",
            )
            st.plotly_chart(fig_hourly, use_container_width=True)

            hvac_zones = _coerce_numeric(
                hvac_zones,
                ["avg_temp", "std_temp", "min_temp", "max_temp", "comfort_exceedance_pct", "samples"],
            )
            hottest = hvac_zones.sort_values("avg_temp", ascending=False).head(top_n).sort_values("avg_temp")
            coldest = hvac_zones.sort_values("avg_temp", ascending=True).head(top_n).sort_values("avg_temp", ascending=False)

            c_left, c_right = st.columns(2)
            with c_left:
                fig_hot = px.bar(
                    hottest,
                    x="avg_temp",
                    y="space_id",
                    orientation="h",
                    title=f"Hottest {top_n} Zones (Average Temp)",
                    labels={"avg_temp": "Average Temp (°F)", "space_id": "Zone"},
                )
                st.plotly_chart(fig_hot, use_container_width=True)
            with c_right:
                fig_cold = px.bar(
                    coldest,
                    x="avg_temp",
                    y="space_id",
                    orientation="h",
                    title=f"Coldest {top_n} Zones (Average Temp)",
                    labels={"avg_temp": "Average Temp (°F)", "space_id": "Zone"},
                )
                st.plotly_chart(fig_cold, use_container_width=True)

            variability = hvac_zones.sort_values("std_temp", ascending=False).head(top_n).sort_values("std_temp")
            fig_var = px.bar(
                variability,
                x="std_temp",
                y="space_id",
                orientation="h",
                title=f"Highest Variability Zones (Top {top_n} by Temp Std Dev)",
                labels={"std_temp": "Std Dev (°F)", "space_id": "Zone"},
            )
            st.plotly_chart(fig_var, use_container_width=True)

            insights = derive_hvac_insights(hvac_zones, hvac_comfort)
            i1, i2, i3 = st.columns(3)
            i1.metric(
                "Highest Variability Zone",
                str(insights["high_variability_zone"]),
                delta=f"Std {insights['high_variability_std_temp']} °F",
            )
            i2.metric(
                "Hottest vs Coldest Zone",
                f"{insights['hottest_zone']} / {insights['coldest_zone']}",
                delta=f"{insights['hottest_zone_avg_temp']} °F / {insights['coldest_zone_avg_temp']} °F",
            )
            i3.metric(
                "Out-of-Band Share",
                f"{insights['overall_out_of_band_pct']}%",
                delta=f"Band {comfort_low:.1f}°F to {comfort_high:.1f}°F",
            )


if __name__ == "__main__":
    main()
