"""
Data loading utilities for HVAC occupancy forecasting.

Functions to load raw data from various sources:
- Occupancy data (Wi-Fi/locator-derived)
- HVAC data (setpoints, states, energy use)
- Weather data (historical)
- Time-of-use (TOU) pricing data
- Space metadata (room IDs, internal/external, floor, area)
"""

import re
from pathlib import Path
from typing import List, Optional

import pandas as pd


def _dedupe_columns(columns: List[str]) -> List[str]:
    """
    Make duplicate column names unique while preserving original order.

    Example:
      ["A", "B", "A"] -> ["A", "B", "A__dup2"]
    """
    seen = {}
    out = []
    for col in columns:
        count = seen.get(col, 0) + 1
        seen[col] = count
        out.append(col if count == 1 else f"{col}__dup{count}")
    return out


def _natural_week_sort_key(path: Path):
    """Sort weekly files by month/day encoded in filename when possible."""
    # Matches names like BrenHall2024Week_May12.csv
    m = re.search(r"Week_([A-Za-z]+)(\d+)", path.stem)
    if not m:
        return (path.stem,)

    month_name = m.group(1).lower()
    day = int(m.group(2))
    month_order = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    month_num = month_order.get(month_name[:3], 99)
    return (month_num, day, path.stem)


def load_occupancy(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load occupancy data from a CSV file OR a directory of CSV files.

    Supported input schemas are normalized to common columns:
      - access_point
      - interval_begin
      - count
      - source_file

    Known source variants:
      1) ap, interval_begin_time, count
      2) access_point, interval_begin, count

    Args:
        path: Path to one CSV file or a folder of CSV files.
        parse_dates: Whether to parse interval_begin as datetime.

    Returns:
        Normalized occupancy dataframe.
    """
    input_path = Path(path)

    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.csv"))
    else:
        raise FileNotFoundError(f"Occupancy path does not exist: {path}")

    if not files:
        raise FileNotFoundError(f"No CSV files found at: {path}")

    frames = []
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        df.columns = _dedupe_columns(df.columns.tolist())

        rename_map = {}
        if "ap" in df.columns:
            rename_map["ap"] = "access_point"
        if "interval_begin_time" in df.columns:
            rename_map["interval_begin_time"] = "interval_begin"

        if rename_map:
            df = df.rename(columns=rename_map)

        for required_col in ["access_point", "interval_begin", "count"]:
            if required_col not in df.columns:
                raise ValueError(
                    f"Missing required column '{required_col}' in {f.name}. "
                    f"Columns found: {list(df.columns)[:10]}..."
                )

        keep_cols = ["access_point", "interval_begin", "count"]
        out = df[keep_cols].copy()
        out["source_file"] = f.name

        if parse_dates:
            out["interval_begin"] = pd.to_datetime(out["interval_begin"], errors="coerce")

        # Normalize type
        out["count"] = pd.to_numeric(out["count"], errors="coerce")

        frames.append(out)

    occ = pd.concat(frames, ignore_index=True)

    if parse_dates and "interval_begin" in occ.columns:
        occ = occ.sort_values("interval_begin", kind="stable").reset_index(drop=True)

    return occ


def load_hvac(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    Load raw HVAC data from a CSV file OR a directory of weekly CSV files.

    Supported patterns:
    - Single file: data/raw/hvac/some_export.csv
    - Directory:   data/raw/hvac/brenhall_2024_weekly/

    Notes for Bren Hall weekly exports:
    - Very wide schema (thousands of columns)
    - Some duplicate header names are expected
    - Timestamp column is expected to be "Timestamp"

    Args:
        path: Path to one CSV file or a folder of CSV files.
        parse_dates: Whether to parse timestamp columns as datetime.

    Returns:
        Combined DataFrame sorted by Timestamp when available.
    """
    input_path = Path(path)

    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.csv"), key=_natural_week_sort_key)
    else:
        raise FileNotFoundError(f"HVAC path does not exist: {path}")

    if not files:
        raise FileNotFoundError(f"No CSV files found at: {path}")

    frames = []
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        df.columns = _dedupe_columns(df.columns.tolist())
        df["source_file"] = f.name
        frames.append(df)

    hvac = pd.concat(frames, ignore_index=True)

    if parse_dates and "Timestamp" in hvac.columns:
        # Example source format:
        # 2024-04-28T00:00:00-07:00 Los_Angeles
        # Keep only the ISO8601 portion before the first space.
        ts = hvac["Timestamp"].astype(str).str.split(" ").str[0]
        hvac["Timestamp"] = pd.to_datetime(ts, errors="coerce")
        hvac = hvac.sort_values("Timestamp", kind="stable").reset_index(drop=True)

    return hvac


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
