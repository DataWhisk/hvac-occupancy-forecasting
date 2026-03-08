"""Visualization and dashboard utilities for HVAC occupancy analysis."""

from .dashboard_data import (
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
from .dashboard_insights import derive_hvac_insights, derive_occupancy_insights
try:
    from .dashboards import (
        plot_daily_opportunity_for_savings,
        plot_occupancy_over_time,
        plot_example_day_timeline,
        plot_occupancy_heatmap,
        plot_savings_summary,
    )
except ModuleNotFoundError:  # pragma: no cover - optional visualization deps
    plot_daily_opportunity_for_savings = None
    plot_occupancy_over_time = None
    plot_example_day_timeline = None
    plot_occupancy_heatmap = None
    plot_savings_summary = None

__all__ = [
    "plot_daily_opportunity_for_savings",
    "plot_occupancy_over_time",
    "plot_example_day_timeline",
    "plot_occupancy_heatmap",
    "plot_savings_summary",
    "fetch_occupancy_kpis",
    "fetch_occupancy_daily",
    "fetch_occupancy_heatmap",
    "fetch_occupancy_space_stats",
    "fetch_hvac_kpis",
    "fetch_hvac_daily",
    "fetch_hvac_hourly",
    "fetch_hvac_zone_stats",
    "fetch_hvac_comfort_summary",
    "derive_occupancy_insights",
    "derive_hvac_insights",
]
