"""
Visualization and dashboard utilities for HVAC occupancy analysis.

Functions for creating plots and dashboards that visualize:
- Occupancy patterns over time
- "Opportunity for savings" analysis
- Forecasting model performance
- Control policy simulations
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
import matplotlib.pyplot as plt


def plot_daily_opportunity_for_savings(
    df: pd.DataFrame,
    date_col: str = "date",
    opportunity_energy_col: str = "opportunity_energy_kwh",
    total_energy_col: str = "total_energy_kwh",
    figsize: Tuple[int, int] = (12, 6),
    title: Optional[str] = None,
) -> plt.Figure:
    """
    Plot daily "opportunity for savings" over time.

    Shows a time series of energy that could have been saved each day
    if HVAC had been turned off during unoccupied periods.

    Args:
        df: DataFrame with daily aggregated data.
        date_col: Column name for date.
        opportunity_energy_col: Column for energy during opportunity periods.
        total_energy_col: Column for total daily energy (for context).
        figsize: Figure size tuple.
        title: Optional plot title.

    Returns:
        matplotlib Figure object.

    TODO:
        - Implement the visualization
        - Add comparison bars (opportunity vs total)
        - Add cumulative savings line
        - Support plotly for interactive version
    """
    # TODO: Implement daily opportunity plot
    # fig, ax = plt.subplots(figsize=figsize)
    # ax.bar(df[date_col], df[opportunity_energy_col], label='Opportunity for Savings')
    # ax.set_xlabel('Date')
    # ax.set_ylabel('Energy (kWh)')
    # ax.set_title(title or 'Daily Opportunity for HVAC Energy Savings')
    # ax.legend()
    # return fig

    raise NotImplementedError("Implement daily opportunity plot")


def plot_example_day_timeline(
    df: pd.DataFrame,
    date: str,
    zone_id: Optional[str] = None,
    figsize: Tuple[int, int] = (14, 8),
) -> plt.Figure:
    """
    Plot a detailed timeline for a single day showing occupancy and HVAC.

    Creates a multi-panel visualization showing:
    - Occupancy count over the day
    - HVAC state/setpoint over the day
    - Highlighted "opportunity" periods
    - TOU rate periods (if available)

    This is useful for presentations to show concrete examples of savings.

    Args:
        df: DataFrame with timestamp-level data.
        date: Date string (YYYY-MM-DD) to plot.
        zone_id: Optional zone to filter to.
        figsize: Figure size tuple.

    Returns:
        matplotlib Figure object.

    TODO:
        - Implement multi-panel timeline plot
        - Add shading for opportunity periods
        - Add TOU rate overlay
        - Support interactive plotly version
    """
    # TODO: Implement example day timeline
    # fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)
    # Filter to specified date and zone
    # Panel 1: Occupancy
    # Panel 2: HVAC state/setpoint
    # Panel 3: Energy consumption with opportunity highlighting

    raise NotImplementedError("Implement example day timeline plot")


def plot_occupancy_heatmap(
    df: pd.DataFrame,
    zone_id: Optional[str] = None,
    agg_func: str = "mean",
    figsize: Tuple[int, int] = (12, 8),
) -> plt.Figure:
    """
    Plot a heatmap of occupancy patterns by hour and day of week.

    Helps visualize typical occupancy patterns to understand
    building usage and identify consistent low-occupancy periods.

    Args:
        df: DataFrame with timestamp and occupancy columns.
        zone_id: Optional zone to filter to.
        agg_func: Aggregation function ("mean", "median", "max").
        figsize: Figure size tuple.

    Returns:
        matplotlib Figure object.

    TODO:
        - Implement heatmap visualization
        - Add option for by-zone comparison
        - Support seasonal breakdown
        - Add annotations for key patterns
    """
    # TODO: Implement occupancy heatmap
    # Pivot data to hour x day_of_week matrix
    # Use seaborn heatmap or matplotlib imshow

    raise NotImplementedError("Implement occupancy heatmap")


def plot_savings_summary(
    savings_dict: dict,
    figsize: Tuple[int, int] = (10, 6),
) -> plt.Figure:
    """
    Plot a summary of savings analysis results.

    Creates a dashboard-style summary with:
    - Total energy savings (kWh)
    - Total cost savings ($)
    - Breakdown by time period
    - Comparison to baseline

    Suitable for presentations and reports.

    Args:
        savings_dict: Dictionary with savings metrics from analysis.
        figsize: Figure size tuple.

    Returns:
        matplotlib Figure object.

    TODO:
        - Implement summary dashboard
        - Add key metrics as text annotations
        - Add pie chart for breakdown
        - Support export to HTML/image
    """
    # TODO: Implement savings summary visualization

    raise NotImplementedError("Implement savings summary plot")


def create_interactive_dashboard(
    df: pd.DataFrame,
    port: int = 8050,
) -> None:
    """
    Launch an interactive dashboard for exploring the data.

    Creates a web-based dashboard (using Dash or Streamlit) for
    interactive exploration of occupancy, HVAC, and savings data.

    Args:
        df: DataFrame with all relevant data.
        port: Port to run the dashboard server on.

    TODO:
        - Implement using Dash or Streamlit
        - Add filters for date range, zone
        - Add interactive plots
        - Add what-if scenario tools
    """
    # TODO: Implement interactive dashboard
    # Consider using:
    # - Dash (plotly): More flexible, steeper learning curve
    # - Streamlit: Simpler, faster to develop

    raise NotImplementedError("Implement interactive dashboard")
