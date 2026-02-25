"""
Data loading utilities for HVAC occupancy forecasting.

Functions to load raw data from various sources:
- Occupancy data (Wi-Fi/locator-derived)
- HVAC data (setpoints, states, energy use)
- Weather data (historical)
- Time-of-use (TOU) pricing data
- Space metadata (room IDs, internal/external, floor, area)
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def load_occupancy(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load raw occupancy data from CSV.

    Occupancy data is typically derived from Wi-Fi or locator systems and contains
    timestamps with occupancy counts per zone/room.

    Args:
        path: Path to the occupancy CSV file.
        parse_dates: Whether to parse timestamp columns as datetime.

    Returns:
        DataFrame with columns like: timestamp, zone_id, occupancy_count.

    TODO:
        - Determine actual column names from raw data files
        - Handle multiple file formats if needed (CSV, parquet, etc.)
        - Add validation for expected columns
    """
    # TODO: Implement actual loading logic once data format is known
    raise NotImplementedError("Implement once raw data format is confirmed")


def load_hvac(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load raw HVAC data from CSV.

    HVAC data includes setpoints, operational states, and energy consumption
    for each zone/room over time.

    Args:
        path: Path to the HVAC data CSV file.
        parse_dates: Whether to parse timestamp columns as datetime.

    Returns:
        DataFrame with columns like: timestamp, zone_id, setpoint, state, energy_kwh.

    TODO:
        - Determine actual column names from raw HVAC data
        - Handle different HVAC data sources (BMS exports, etc.)
        - Add unit conversion if needed (e.g., BTU to kWh)
    """
    # TODO: Implement actual loading logic once data format is known
    raise NotImplementedError("Implement once raw data format is confirmed")


def load_weather(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load historical weather data.

    Weather data should be aligned by timestamp with occupancy/HVAC data
    and includes temperature, humidity, etc.

    Args:
        path: Path to the weather data CSV file.
        parse_dates: Whether to parse timestamp columns as datetime.

    Returns:
        DataFrame with columns like: timestamp, temperature, humidity, etc.

    TODO:
        - Determine weather data source (NOAA, local station, etc.)
        - Handle timezone alignment with building data
        - Add interpolation for missing timestamps
    """
    # TODO: Implement actual loading logic once data format is known
    raise NotImplementedError("Implement once raw data format is confirmed")

import pandas as pd
import requests

def fetch_historical_weather(lat=33.6695, lon=-117.8231, start_date='2017-08-28', end_date='2018-01-05'):
    """
    Fetches historical hourly temperature data from Open-Meteo.
    Defaults are set to Irvine, CA for the dates in the occupancy dataset.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles"
    }
    
    print("Fetching weather data...")
    response = requests.get(url, params=params)
    response.raise_for_status() # Check for any errors
    
    data = response.json()
    
    # Extract the time and temperature arrays
    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    
    # Create a DataFrame
    weather_df = pd.DataFrame({
        'timestamp': pd.to_datetime(times),
        'outside_temp': temps
    })
    
    # Set the index to match our pipeline structure
    weather_df = weather_df.set_index('timestamp')
    
    return weather_df


def load_tou(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load time-of-use (TOU) electricity pricing data.

    TOU data contains electricity prices by time period (peak, off-peak, etc.)
    used for estimating cost savings from HVAC optimization.

    Args:
        path: Path to the TOU pricing data CSV file.
        parse_dates: Whether to parse timestamp/time columns as datetime.

    Returns:
        DataFrame with columns like: time_period, rate_kwh, period_type.

    TODO:
        - Determine TOU schedule format (hourly, period-based, etc.)
        - Handle seasonal rate variations
        - Support multiple utility rate structures
    """
    # TODO: Implement actual loading logic once data format is known
    raise NotImplementedError("Implement once raw data format is confirmed")


def load_space_metadata(path: str) -> pd.DataFrame:
    """
    Load space/room metadata.

    Metadata includes room IDs, whether rooms are internal or external,
    floor numbers, areas, and other static attributes.

    Args:
        path: Path to the space metadata CSV file.

    Returns:
        DataFrame with columns like: zone_id, room_name, is_external, floor, area_sqft.

    TODO:
        - Determine metadata schema from facilities data
        - Add validation for zone_id consistency with other data
        - Include HVAC zone to room mapping if needed
    """
    # TODO: Implement actual loading logic once data format is known
    raise NotImplementedError("Implement once raw data format is confirmed")


