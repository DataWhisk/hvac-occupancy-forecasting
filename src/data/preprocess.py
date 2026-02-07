"""
Data preprocessing and feature engineering for HVAC occupancy forecasting.

Functions for cleaning, merging, and transforming raw data into
feature-ready datasets for modeling and control optimization.
"""

import pandas as pd
import numpy as np
from typing import Optional, List


def merge_occupancy_hvac(
    occ_df: pd.DataFrame,
    hvac_df: pd.DataFrame,
    freq: str = "15min",
    how: str = "inner",
) -> pd.DataFrame:
    """
    Merge occupancy and HVAC data on timestamp and zone.

    Aligns occupancy counts with HVAC states/setpoints at a common frequency.
    This merged dataset is the foundation for "opportunity for savings" analysis.

    Args:
        occ_df: Occupancy DataFrame with columns [timestamp, zone_id, occupancy_count].
        hvac_df: HVAC DataFrame with columns [timestamp, zone_id, setpoint, state, ...].
        freq: Target resampling frequency (e.g., "15min", "1H").
        how: Merge type ("inner", "outer", "left", "right").

    Returns:
        Merged DataFrame with aligned occupancy and HVAC data.

    TODO:
        - Handle timezone differences between data sources
        - Implement resampling/aggregation logic for different frequencies
        - Add data quality flags for missing or interpolated values
    """
    # TODO: Implement merging logic
    raise NotImplementedError("Implement merge logic once data schemas are confirmed")


def add_weather_features(
    df: pd.DataFrame,
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add weather features to the merged occupancy/HVAC dataset.

    Weather conditions affect both occupancy patterns and HVAC energy usage.

    Args:
        df: Merged occupancy/HVAC DataFrame.
        weather_df: Weather DataFrame with columns [timestamp, temperature, humidity, ...].

    Returns:
        DataFrame with weather features added.

    TODO:
        - Handle temporal alignment (weather data may be hourly, HVAC may be 15min)
        - Add derived features (heating/cooling degree days, etc.)
    """
    # TODO: Implement weather feature addition
    raise NotImplementedError("Implement weather feature merging")


def add_tou_features(
    df: pd.DataFrame,
    tou_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add time-of-use pricing features to the dataset.

    TOU rates are essential for computing cost savings from HVAC optimization.

    Args:
        df: DataFrame with timestamp column.
        tou_df: TOU pricing DataFrame.

    Returns:
        DataFrame with TOU rate columns added.

    TODO:
        - Map timestamps to TOU periods (peak, off-peak, etc.)
        - Handle holiday schedules
        - Support multiple rate structures
    """
    # TODO: Implement TOU feature addition
    raise NotImplementedError("Implement TOU feature merging")


def engineer_features(
    df: pd.DataFrame,
    include_time_features: bool = True,
    include_lag_features: bool = True,
    lag_periods: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Engineer features for occupancy forecasting models.

    Creates time-based features, lag features, and rolling statistics
    that help forecasting models capture temporal patterns.

    Args:
        df: Input DataFrame with timestamp and occupancy columns.
        include_time_features: Add hour, day of week, month, etc.
        include_lag_features: Add lagged occupancy values.
        lag_periods: List of lag periods (e.g., [1, 4, 96] for 15min data = 15min, 1hr, 1day).

    Returns:
        DataFrame with engineered features.

    TODO:
        - Add academic calendar features (semester, breaks, exam periods)
        - Add building-specific event features if available
        - Consider zone clustering features (similar rooms behave similarly)
    """
    if lag_periods is None:
        lag_periods = [1, 4, 96]  # 15min, 1hr, 1day for 15min frequency data

    result = df.copy()

    if include_time_features:
        # TODO: Implement time feature extraction
        # result['hour'] = result['timestamp'].dt.hour
        # result['day_of_week'] = result['timestamp'].dt.dayofweek
        # result['is_weekend'] = result['day_of_week'].isin([5, 6])
        # result['month'] = result['timestamp'].dt.month
        pass

    if include_lag_features:
        # TODO: Implement lag feature creation
        # for lag in lag_periods:
        #     result[f'occupancy_lag_{lag}'] = result.groupby('zone_id')['occupancy_count'].shift(lag)
        pass

    # TODO: Add rolling statistics (mean, std over past N periods)

    return result


def compute_opportunity_for_savings(
    df: pd.DataFrame,
    occupancy_col: str = "occupancy_count",
    hvac_state_col: str = "hvac_on",
    energy_col: Optional[str] = "energy_kwh",
) -> pd.DataFrame:
    """
    Identify "opportunity for savings" periods in historical data.

    An "opportunity" is defined as a period where:
    - Occupancy is zero (or below threshold)
    - HVAC is actively running (consuming energy)

    This analysis quantifies potential energy and cost savings.

    Args:
        df: Merged occupancy/HVAC DataFrame.
        occupancy_col: Column name for occupancy count.
        hvac_state_col: Column name for HVAC on/off state.
        energy_col: Column name for energy consumption (optional).

    Returns:
        DataFrame with opportunity flags and potential savings metrics.

    TODO:
        - Define occupancy threshold (zero vs. low occupancy)
        - Account for HVAC pre-conditioning needs (some pre-heating/cooling is OK)
        - Add comfort constraint considerations
        - Integrate TOU pricing for cost savings estimation
    """
    result = df.copy()

    # TODO: Implement opportunity detection logic
    # result['is_opportunity'] = (result[occupancy_col] == 0) & (result[hvac_state_col] == True)
    # result['potential_energy_savings'] = result['is_opportunity'] * result[energy_col]

    raise NotImplementedError("Implement opportunity for savings calculation")
