#!/usr/bin/env python3
"""
Train and evaluate the occupancy prediction model.

Source of truth:
- PostgreSQL only
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data import (  # noqa: E402
    load_occupancy_from_db,
    load_weather_from_db,
    prepare_occupancy_forecast_dataset,
)
from src.models import ProphetOccupancyModel  # noqa: E402


def _weather_for_range(weather_df: Optional[pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp):
    if weather_df is None or weather_df.empty:
        return None
    weather = weather_df.copy()
    if "timestamp" not in weather.columns:
        return weather
    weather["timestamp"] = pd.to_datetime(weather["timestamp"], errors="coerce")
    return weather[(weather["timestamp"] >= start) & (weather["timestamp"] <= end)].copy()


def run(args: argparse.Namespace) -> int:
    occ_source = load_occupancy_from_db(
        table_name=args.db_table,
        schema=args.db_schema,
        env_path=args.env_path,
    )

    weather_df = None
    if args.weather_table:
        weather_df = load_weather_from_db(
            table_name=args.weather_table,
            schema=args.weather_schema,
            timestamp_col=args.weather_timestamp_col,
            temp_col=args.weather_temp_col,
            env_path=args.env_path,
        )

    # Normalize db shape to preprocessing expectations.
    if "interval_begin" in occ_source.columns and "count" in occ_source.columns:
        occ_source = occ_source.rename(
            columns={"interval_begin": "timestamp", "count": "occupancy_count"}
        )

    if args.zone_id:
        zones = [str(args.zone_id)]
    else:
        zone_col = "zone_id" if "zone_id" in occ_source.columns else "access_point"
        zones = sorted(occ_source[zone_col].astype(str).dropna().unique().tolist())
        if args.max_zones is not None:
            zones = zones[: args.max_zones]

    if not zones:
        raise ValueError("No zones found in occupancy source.")

    metrics_rows = []
    forecast_frames = []
    pass_count = 0

    for zone in zones:
        zone_features = prepare_occupancy_forecast_dataset(
            occ_df=occ_source,
            weather_df=weather_df,
            zone_id=zone,
            freq=args.freq,
            dropna_for_training=True,
        )
        model_df = zone_features.rename(
            columns={"timestamp": "ds", "occupancy_count": "y"}
        )[["ds", "y", "outside_temp"]]

        split_idx = int(len(model_df) * (1.0 - args.test_ratio))
        if split_idx < 1 or split_idx >= len(model_df):
            metrics_rows.append(
                {
                    "zone_id": zone,
                    "status": "insufficient_data",
                    "binary_accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "mae": float("nan"),
                    "pass": False,
                }
            )
            continue

        train_df = model_df.iloc[:split_idx].reset_index(drop=True)
        test_df = model_df.iloc[split_idx:].reset_index(drop=True)

        model = ProphetOccupancyModel(zone_id=zone, freq=args.freq)
        model.fit(train_df)
        eval_metrics = model.evaluate(test_df)

        passed = eval_metrics.get("binary_accuracy", 0.0) >= args.accuracy_threshold
        if passed:
            pass_count += 1

        metrics_rows.append(
            {
                "zone_id": zone,
                **eval_metrics,
                "status": "ok",
                "pass": passed,
            }
        )

        test_start = pd.Timestamp(test_df["ds"].min())
        test_end = pd.Timestamp(test_df["ds"].max())
        test_weather = _weather_for_range(weather_df, test_start, test_end)

        forecast = model.predict_date_range(
            start_ts=test_start,
            end_ts=test_end,
            weather_future_df=test_weather,
        )
        forecast = forecast.rename(columns={"ds": "timestamp"})
        forecast["zone_id"] = zone
        forecast_frames.append(forecast)

    metrics_df = pd.DataFrame(metrics_rows)
    forecasts_df = (
        pd.concat(forecast_frames, ignore_index=True)
        if forecast_frames
        else pd.DataFrame(
            columns=[
                "timestamp",
                "zone_id",
                "pred_occupancy_count",
                "pred_is_occupied",
            ]
        )
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_path = output_dir / f"occupancy_model_metrics_{stamp}.csv"
    forecast_path = output_dir / f"occupancy_model_forecasts_{stamp}.csv"

    metrics_df.to_csv(metrics_path, index=False)
    forecasts_df.to_csv(forecast_path, index=False)

    print(f"Wrote metrics: {metrics_path}")
    print(f"Wrote forecasts: {forecast_path}")
    print("")
    print(metrics_df.to_string(index=False))

    global_pass = pass_count >= args.min_passing_zones
    if global_pass:
        print("")
        print(
            f"PASS: {pass_count} zone(s) met binary_accuracy >= {args.accuracy_threshold:.2f} "
            f"(required: {args.min_passing_zones})."
        )
        return 0

    print("")
    print(
        f"FAIL: only {pass_count} zone(s) met binary_accuracy >= {args.accuracy_threshold:.2f} "
        f"(required: {args.min_passing_zones})."
    )
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/eval occupancy prediction model.")
    parser.add_argument("--env-path", default=".env")
    parser.add_argument("--db-schema", default="public")
    parser.add_argument("--db-table", default="space_occupancy")
    parser.add_argument("--weather-schema", default="public")
    parser.add_argument("--weather-table", default=None)
    parser.add_argument("--weather-timestamp-col", default="timestamp")
    parser.add_argument("--weather-temp-col", default="outside_temp")
    parser.add_argument("--zone-id", default=None)
    parser.add_argument("--max-zones", type=int, default=None)
    parser.add_argument("--freq", default="15min")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--accuracy-threshold", type=float, default=0.8)
    parser.add_argument("--min-passing-zones", type=int, default=1)
    parser.add_argument("--output-dir", default="data/processed")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
