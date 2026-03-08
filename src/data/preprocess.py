"""
Data preprocessing and feature engineering for HVAC occupancy forecasting.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)
DEFAULT_LAG_PERIODS = [1, 4, 96]


def _pick_column(columns: Sequence[str], candidates: Sequence[str], label: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Could not find {label} column. Tried: {list(candidates)}")


def normalize_occupancy(
    occ_df: pd.DataFrame,
    zone_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Normalize occupancy input to canonical columns:
    [timestamp, zone_id, occupancy_count].
    """
    columns = list(occ_df.columns)
    timestamp_col = _pick_column(
        columns, ["timestamp", "interval_begin", "beginning", "ds"], "timestamp"
    )
    zone_col = _pick_column(
        columns,
        ["zone_id", "access_point", "space_id", "ap", "user"],
        "zone identifier",
    )
    occupancy_col = _pick_column(
        columns,
        ["occupancy_count", "count", "occupancy", "y"],
        "occupancy",
    )

    out = occ_df[[timestamp_col, zone_col, occupancy_col]].copy()
    out.columns = ["timestamp", "zone_id", "occupancy_count"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["zone_id"] = out["zone_id"].astype(str)
    out["occupancy_count"] = pd.to_numeric(out["occupancy_count"], errors="coerce")
    out = out.dropna(subset=["timestamp", "zone_id", "occupancy_count"])

    if zone_id is not None:
        out = out[out["zone_id"] == str(zone_id)]

    if out.empty:
        raise ValueError("No occupancy rows available after normalization/filtering")

    duplicate_rows = int(out.duplicated(subset=["timestamp", "zone_id"]).sum())
    if duplicate_rows:
        LOGGER.info(
            "Found %s duplicate occupancy rows per [timestamp, zone_id]; aggregating by mean.",
            duplicate_rows,
        )

    out = (
        out.groupby(["timestamp", "zone_id"], as_index=False)["occupancy_count"]
        .mean()
        .sort_values(["zone_id", "timestamp"])
        .reset_index(drop=True)
    )
    return out


def normalize_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize weather input to canonical columns:
    [timestamp, outside_temp].
    """
    columns = list(weather_df.columns)
    timestamp_col = _pick_column(columns, ["timestamp", "time", "ds"], "weather timestamp")
    temp_col = _pick_column(
        columns,
        ["outside_temp", "temperature", "temp", "temperature_2m", "y"],
        "weather temperature",
    )

    out = weather_df[[timestamp_col, temp_col]].copy()
    out.columns = ["timestamp", "outside_temp"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["outside_temp"] = pd.to_numeric(out["outside_temp"], errors="coerce")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp")
    out = out.groupby("timestamp", as_index=False)["outside_temp"].mean()
    return out


def prepare_occupancy_forecast_dataset(
    occ_df: pd.DataFrame,
    weather_df: Optional[pd.DataFrame] = None,
    zone_id: Optional[str] = None,
    freq: str = "15min",
    lag_periods: Optional[List[int]] = None,
    dropna_for_training: bool = True,
) -> pd.DataFrame:
    """
    Build deterministic features for occupancy forecasting.

    Output columns include:
    - timestamp, zone_id, occupancy_count, is_occupied
    - hour, day_of_week, is_weekend
    - occupancy_lag_{k}
    - outside_temp
    """
    if lag_periods is None:
        lag_periods = DEFAULT_LAG_PERIODS

    occ = normalize_occupancy(occ_df, zone_id=zone_id)
    if zone_id is None:
        unique_zones = occ["zone_id"].unique()
        if len(unique_zones) != 1:
            raise ValueError(
                "prepare_occupancy_forecast_dataset requires a single zone. "
                "Pass zone_id explicitly."
            )
        zone_id = str(unique_zones[0])
    else:
        zone_id = str(zone_id)

    occ = occ[occ["zone_id"] == zone_id].copy()
    occ = occ.set_index("timestamp").sort_index()
    full_index = pd.date_range(occ.index.min(), occ.index.max(), freq=freq)
    occ = occ.reindex(full_index)
    occ.index.name = "timestamp"
    occ["zone_id"] = zone_id

    missing_occ = int(occ["occupancy_count"].isna().sum())
    if missing_occ:
        LOGGER.info("Imputing %s missing occupancy points with 0.", missing_occ)
    occ["occupancy_count"] = occ["occupancy_count"].fillna(0.0).clip(lower=0.0)

    if weather_df is not None:
        weather = normalize_weather(weather_df)
        weather = weather.set_index("timestamp").sort_index()
        weather = weather.resample(freq).interpolate("time").ffill().bfill()
        weather = weather.reindex(full_index).interpolate("time").ffill().bfill()
        occ["outside_temp"] = weather["outside_temp"]
    else:
        occ["outside_temp"] = np.nan

    if occ["outside_temp"].notna().any():
        missing_temp = int(occ["outside_temp"].isna().sum())
        if missing_temp:
            median_temp = float(occ["outside_temp"].median())
            LOGGER.info(
                "Imputing %s missing outside_temp points with median %.3f.",
                missing_temp,
                median_temp,
            )
            occ["outside_temp"] = occ["outside_temp"].fillna(median_temp)

    occ["is_occupied"] = occ["occupancy_count"] > 0
    occ["hour"] = occ.index.hour
    occ["day_of_week"] = occ.index.dayofweek
    occ["is_weekend"] = occ["day_of_week"].isin([5, 6]).astype(int)

    for lag in lag_periods:
        occ[f"occupancy_lag_{lag}"] = occ["occupancy_count"].shift(lag)

    if dropna_for_training:
        lag_cols = [f"occupancy_lag_{lag}" for lag in lag_periods]
        before = len(occ)
        occ = occ.dropna(subset=lag_cols)
        dropped = before - len(occ)
        if dropped:
            LOGGER.info("Dropped %s rows with lag-feature NaNs.", dropped)

    return occ.reset_index()


def merge_occupancy_hvac(
    occ_df: pd.DataFrame,
    hvac_df: pd.DataFrame,
    freq: str = "15min",
    how: str = "inner",
) -> pd.DataFrame:
    """
    Merge occupancy and HVAC data on timestamp and zone identifier.
    """
    occ = normalize_occupancy(occ_df)
    hvac_cols = list(hvac_df.columns)
    hvac_timestamp_col = _pick_column(
        hvac_cols, ["timestamp", "Timestamp", "time", "beginning"], "HVAC timestamp"
    )
    hvac_zone_col = _pick_column(
        hvac_cols, ["zone_id", "space_id", "access_point", "ap"], "HVAC zone"
    )

    hvac = hvac_df.copy()
    hvac[hvac_timestamp_col] = pd.to_datetime(hvac[hvac_timestamp_col], errors="coerce")
    hvac[hvac_zone_col] = hvac[hvac_zone_col].astype(str)
    hvac = hvac.dropna(subset=[hvac_timestamp_col, hvac_zone_col]).copy()
    hvac = hvac.rename(
        columns={
            hvac_timestamp_col: "timestamp",
            hvac_zone_col: "zone_id",
        }
    )

    if "hvac_on" not in hvac.columns:
        if "hvac_mode" in hvac.columns:
            hvac["hvac_on"] = hvac["hvac_mode"].astype(str).str.lower().ne("off")
        else:
            hvac["hvac_on"] = True

    occ["timestamp"] = occ["timestamp"].dt.floor(freq)
    hvac["timestamp"] = hvac["timestamp"].dt.floor(freq)
    occ = (
        occ.groupby(["timestamp", "zone_id"], as_index=False)["occupancy_count"]
        .mean()
        .sort_values("timestamp")
    )
    hvac = hvac.groupby(["timestamp", "zone_id"], as_index=False).first().sort_values("timestamp")
    return occ.merge(hvac, on=["timestamp", "zone_id"], how=how)


def add_weather_features(
    df: pd.DataFrame,
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add aligned outside temperature to a timestamped dataframe.
    """
    if "timestamp" not in df.columns:
        raise ValueError("Input dataframe must contain 'timestamp'.")

    base = df.copy()
    base["timestamp"] = pd.to_datetime(base["timestamp"], errors="coerce")
    weather = normalize_weather(weather_df)
    return base.merge(weather, on="timestamp", how="left")


def add_tou_features(
    df: pd.DataFrame,
    tou_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add simple TOU features by matching hour-of-day windows.

    Expected TOU columns:
    - start_hour, end_hour, rate_kwh
    """
    required = {"start_hour", "end_hour", "rate_kwh"}
    if not required.issubset(set(tou_df.columns)):
        raise ValueError(f"TOU dataframe must contain columns: {sorted(required)}")
    if "timestamp" not in df.columns:
        raise ValueError("Input dataframe must contain 'timestamp'.")

    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["hour"] = out["timestamp"].dt.hour
    out["tou_rate"] = np.nan

    for _, row in tou_df.iterrows():
        start = int(row["start_hour"])
        end = int(row["end_hour"])
        rate = float(row["rate_kwh"])
        if start <= end:
            mask = (out["hour"] >= start) & (out["hour"] < end)
        else:
            mask = (out["hour"] >= start) | (out["hour"] < end)
        out.loc[mask, "tou_rate"] = rate

    out["tou_rate"] = out["tou_rate"].ffill().bfill()
    return out


def engineer_features(
    df: pd.DataFrame,
    include_time_features: bool = True,
    include_lag_features: bool = True,
    lag_periods: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Generic feature engineering helper for occupancy time series.
    """
    if lag_periods is None:
        lag_periods = DEFAULT_LAG_PERIODS

    result = df.copy()
    timestamp_col = "timestamp" if "timestamp" in result.columns else "ds"
    target_col = "occupancy_count" if "occupancy_count" in result.columns else "y"

    result[timestamp_col] = pd.to_datetime(result[timestamp_col], errors="coerce")
    result = result.sort_values(timestamp_col).reset_index(drop=True)

    if include_time_features:
        result["hour"] = result[timestamp_col].dt.hour
        result["day_of_week"] = result[timestamp_col].dt.dayofweek
        result["is_weekend"] = result["day_of_week"].isin([5, 6]).astype(int)

    if include_lag_features and target_col in result.columns:
        for lag in lag_periods:
            result[f"{target_col}_lag_{lag}"] = result[target_col].shift(lag)

    return result


def compute_opportunity_for_savings(
    df: pd.DataFrame,
    occupancy_col: str = "occupancy_count",
    hvac_state_col: str = "hvac_on",
    energy_col: Optional[str] = "energy_kwh",
) -> pd.DataFrame:
    """
    Identify historical opportunities for savings:
    occupancy <= 0 while HVAC is on.
    """
    if occupancy_col not in df.columns:
        raise ValueError(f"Missing occupancy column: {occupancy_col}")
    if hvac_state_col not in df.columns:
        raise ValueError(f"Missing HVAC state column: {hvac_state_col}")

    result = df.copy()
    result[occupancy_col] = pd.to_numeric(result[occupancy_col], errors="coerce").fillna(0)
    hvac_on = result[hvac_state_col].astype(bool)
    result["is_opportunity"] = (result[occupancy_col] <= 0) & hvac_on

    if energy_col and energy_col in result.columns:
        energy = pd.to_numeric(result[energy_col], errors="coerce").fillna(0.0)
        result["potential_energy_savings"] = np.where(result["is_opportunity"], energy, 0.0)

    return result
