#!/usr/bin/env python3
"""
Load Bren Hall weekly HVAC raw CSV exports into one combined dataframe.

Usage:
  python scripts/load_brenhall_hvac.py
  python scripts/load_brenhall_hvac.py --input data/raw/hvac/brenhall_2024_weekly --output data/interim/brenhall_2024_hvac_combined.csv
"""

import argparse
from pathlib import Path
import sys

# Ensure local src/ is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load import load_hvac  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Combine Bren Hall HVAC weekly CSV files")
    parser.add_argument(
        "--input",
        default="data/raw/hvac/brenhall_2024_weekly",
        help="Input directory containing weekly Bren Hall HVAC CSV files",
    )
    parser.add_argument(
        "--output",
        default="data/interim/brenhall_2024_hvac_combined.csv",
        help="Output combined CSV path",
    )
    parser.add_argument(
        "--no-parse-dates",
        action="store_true",
        help="Do not parse Timestamp as datetime",
    )

    args = parser.parse_args()

    input_path = PROJECT_ROOT / args.input
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_hvac(str(input_path), parse_dates=not args.no_parse_dates)
    df.to_csv(output_path, index=False)

    print(f"Saved combined file: {output_path}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    if "Timestamp" in df.columns:
        print(f"Timestamp range: {df['Timestamp'].min()} -> {df['Timestamp'].max()}")


if __name__ == "__main__":
    main()
