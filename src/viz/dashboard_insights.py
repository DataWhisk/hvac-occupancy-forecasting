"""
Derived stakeholder-facing insight helpers for dashboard narrative cards.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

POSTGRES_DOW_LABELS = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


def _fmt_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def derive_occupancy_insights(
    heatmap_df: pd.DataFrame,
    space_stats_df: pd.DataFrame,
    low_space_count: int = 3,
) -> Dict[str, object]:
    if heatmap_df.empty and space_stats_df.empty:
        return {
            "busiest_day": "N/A",
            "busiest_hour": "N/A",
            "busiest_hour_avg_occ": "N/A",
            "highest_util_space": "N/A",
            "highest_util_avg_occ": "N/A",
            "low_util_spaces": [],
        }

    busiest_day = "N/A"
    busiest_hour = "N/A"
    busiest_hour_avg_occ = "N/A"
    if not heatmap_df.empty:
        heat = heatmap_df.copy()
        heat["avg_occ"] = pd.to_numeric(heat["avg_occ"], errors="coerce")
        heat = heat.dropna(subset=["avg_occ"])
        if not heat.empty:
            by_day = (
                heat.groupby("day_of_week", as_index=False)["avg_occ"]
                .mean()
                .sort_values("avg_occ", ascending=False)
            )
            if not by_day.empty:
                busiest_day = POSTGRES_DOW_LABELS.get(int(by_day.iloc[0]["day_of_week"]), "N/A")

            busiest_cell = heat.sort_values("avg_occ", ascending=False).iloc[0]
            hour = int(busiest_cell["hour_of_day"])
            busiest_hour = f"{hour:02d}:00"
            busiest_hour_avg_occ = _fmt_number(float(busiest_cell["avg_occ"]), decimals=2)

    highest_util_space = "N/A"
    highest_util_avg_occ = "N/A"
    low_util_spaces: List[str] = []
    if not space_stats_df.empty:
        spaces = space_stats_df.copy()
        spaces["avg_occ"] = pd.to_numeric(spaces["avg_occ"], errors="coerce")
        spaces = spaces.dropna(subset=["avg_occ"]).sort_values("avg_occ", ascending=False)
        if not spaces.empty:
            top_row = spaces.iloc[0]
            highest_util_space = str(top_row["space_label"])
            highest_util_avg_occ = _fmt_number(float(top_row["avg_occ"]), decimals=2)

            low_rows = (
                spaces.sort_values("avg_occ", ascending=True)
                .head(low_space_count)["space_label"]
                .astype(str)
                .tolist()
            )
            low_util_spaces = low_rows

    return {
        "busiest_day": busiest_day,
        "busiest_hour": busiest_hour,
        "busiest_hour_avg_occ": busiest_hour_avg_occ,
        "highest_util_space": highest_util_space,
        "highest_util_avg_occ": highest_util_avg_occ,
        "low_util_spaces": low_util_spaces,
    }


def derive_hvac_insights(
    zone_stats_df: pd.DataFrame,
    comfort_summary_df: pd.DataFrame,
) -> Dict[str, str]:
    if zone_stats_df.empty:
        return {
            "high_variability_zone": "N/A",
            "high_variability_std_temp": "N/A",
            "hottest_zone": "N/A",
            "hottest_zone_avg_temp": "N/A",
            "coldest_zone": "N/A",
            "coldest_zone_avg_temp": "N/A",
            "overall_out_of_band_pct": "N/A",
        }

    zones = zone_stats_df.copy()
    zones["std_temp"] = pd.to_numeric(zones["std_temp"], errors="coerce")
    zones["avg_temp"] = pd.to_numeric(zones["avg_temp"], errors="coerce")

    variability_row = zones.sort_values("std_temp", ascending=False).iloc[0]
    hottest_row = zones.sort_values("avg_temp", ascending=False).iloc[0]
    coldest_row = zones.sort_values("avg_temp", ascending=True).iloc[0]

    out_of_band = None
    if not comfort_summary_df.empty and "out_of_band_pct" in comfort_summary_df.columns:
        out_of_band = pd.to_numeric(
            comfort_summary_df.iloc[0]["out_of_band_pct"],
            errors="coerce",
        )
    if out_of_band is None or pd.isna(out_of_band):
        out_of_band = pd.to_numeric(
            zones.get("comfort_exceedance_pct", pd.Series(dtype=float)),
            errors="coerce",
        ).mean()

    return {
        "high_variability_zone": str(variability_row["space_id"]),
        "high_variability_std_temp": _fmt_number(variability_row["std_temp"], decimals=2),
        "hottest_zone": str(hottest_row["space_id"]),
        "hottest_zone_avg_temp": _fmt_number(hottest_row["avg_temp"], decimals=2),
        "coldest_zone": str(coldest_row["space_id"]),
        "coldest_zone_avg_temp": _fmt_number(coldest_row["avg_temp"], decimals=2),
        "overall_out_of_band_pct": _fmt_number(out_of_band, decimals=2),
    }
