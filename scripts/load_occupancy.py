#!/usr/bin/env python3
"""Combine occupancy CSV files into one normalized dataset."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load import load_occupancy  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Combine occupancy CSVs")
    parser.add_argument(
        "--input",
        default="data/raw/occupancy/brenhall_ap_15min",
        help="Input directory containing occupancy CSV files",
    )
    parser.add_argument(
        "--output",
        default="data/interim/occupancy_15min_combined.csv",
        help="Output combined CSV path",
    )
    args = parser.parse_args()

    in_path = PROJECT_ROOT / args.input
    out_path = PROJECT_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_occupancy(str(in_path), parse_dates=True)
    df.to_csv(out_path, index=False)

    print(f"Saved combined file: {out_path}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Time range: {df['interval_begin'].min()} -> {df['interval_begin'].max()}")


if __name__ == "__main__":
    main()
