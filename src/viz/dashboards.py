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
import xgboost as xgb
from sklearn.metrics import mean_absolute_error


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
    fig, ax1 = plt.subplots(figsize=figsize)
    
    # Sort by date to ensure proper plotting
    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    
    # Primary axis: Bar chart of opportunity energy
    color_opportunity = '#2E86AB'
    ax1.bar(
        df_sorted[date_col],
        df_sorted[opportunity_energy_col],
        label='Opportunity for Savings',
        color=color_opportunity,
        alpha=0.8
    )
    ax1.set_xlabel('Date', fontsize=11)
    ax1.set_ylabel('Opportunity Energy (kWh)', fontsize=11, color=color_opportunity)
    ax1.tick_params(axis='y', labelcolor=color_opportunity)
    
    # Secondary axis: Cumulative savings line
    ax2 = ax1.twinx()
    cumulative_savings = df_sorted[opportunity_energy_col].cumsum()
    color_cumulative = '#A23B72'
    ax2.plot(
        df_sorted[date_col],
        cumulative_savings,
        label='Cumulative Savings',
        color=color_cumulative,
        linewidth=2.5,
        marker='o',
        markersize=4
    )
    ax2.set_ylabel('Cumulative Opportunity Energy (kWh)', fontsize=11, color=color_cumulative)
    ax2.tick_params(axis='y', labelcolor=color_cumulative)
    
    # Set title
    ax1.set_title(
        title or 'Daily Opportunity for HVAC Energy Savings',
        fontsize=13,
        fontweight='bold',
        pad=15
    )
    
    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    # Improve layout
    fig.tight_layout()
    
    return fig

def plot_occupancy_over_time(df, time_col='interval_begin_time', occ_col='count'):
    """
    Plots total occupancy count over time based on interval timestamps.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 1. Prepare data
    # Group by the exact time to get the TOTAL occupancy across all 'ap' locations
    # and sort chronologically
    timeline = df.groupby(time_col)[occ_col].sum().reset_index()
    timeline = timeline.sort_values(by=time_col)
    
    # 2. Plot the data
    ax.plot(
        timeline[time_col], 
        timeline[occ_col], 
        color='#2E86AB',  
        linewidth=2,
        label='Total Occupancy',
        drawstyle='steps-post' # Keeps the step-style plotting appropriate for intervals
    )
    
    # 3. Formatting
    # Note: Removed hardcoded set_xlim so the graph auto-adjusts to your Dec 2017/Jan 2018 data
    ax.set_title("Total Occupancy Over Time", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Date & Time", fontsize=11)
    ax.set_ylabel("Total Occupancy Count", fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Rotate dates to make them readable
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    return fig


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
