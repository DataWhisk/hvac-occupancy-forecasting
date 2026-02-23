#!/usr/bin/env python3
"""
Build a data dictionary for occupancy CSV files.

Usage:
  python scripts/build_occupancy_data_dictionary.py
"""

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load import load_occupancy  # noqa: E402


def infer_semantic(col: str) -> str:
    c = col.lower()
    if "access_point" in c:
        return "access-point identifier"
    if "interval" in c or "time" in c or "timestamp" in c:
        return "time bucket start"
    if c == "count":
        return "observed occupancy count"
    if "source" in c:
        return "source filename"
    return "unknown"


def main():
    input_dir = PROJECT_ROOT / "data/raw/occupancy/brenhall_ap_15min"
    output_csv = PROJECT_ROOT / "data/interim/occupancy_data_dictionary.csv"
    output_md = PROJECT_ROOT / "docs/occupancy_data_dictionary.md"

    df = load_occupancy(str(input_dir), parse_dates=True)

    rows = []
    for col in df.columns:
        s = df[col]
        rows.append(
            {
                "column_name": col,
                "dtype": str(s.dtype),
                "non_null_count": int(s.notna().sum()),
                "null_count": int(s.isna().sum()),
                "null_pct": float((s.isna().mean() * 100).round(4)),
                "n_unique": int(s.nunique(dropna=True)),
                "sample_values": " | ".join(map(str, s.dropna().head(3).tolist())),
                "semantic_meaning": infer_semantic(col),
            }
        )

    ddf = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    ddf.to_csv(output_csv, index=False)

    min_ts = df["interval_begin"].min()
    max_ts = df["interval_begin"].max()

    md = []
    md.append("# Occupancy Data Dictionary\n")
    md.append("Generated from `data/raw/occupancy/brenhall_ap_15min/*.csv`.\n")
    md.append("## Dataset Summary\n")
    md.append(f"- Rows: **{len(df):,}**")
    md.append(f"- Columns: **{len(df.columns)}**")
    md.append(f"- Source files: **{df['source_file'].nunique()}**")
    md.append(f"- Time range: **{min_ts} -> {max_ts}**\n")

    md.append("## Schema\n")
    md.append("| Column | Dtype | Null % | Unique | Meaning | Example |")
    md.append("|---|---:|---:|---:|---|---|")

    for _, r in ddf.iterrows():
        md.append(
            f"| {r['column_name']} | {r['dtype']} | {r['null_pct']:.4f}% | {r['n_unique']} | {r['semantic_meaning']} | {str(r['sample_values']).replace('|', ', ')} |"
        )

    md.append("\n## Notes\n")
    md.append("- Raw source schemas were normalized to: `access_point`, `interval_begin`, `count`.\n")
    md.append("- `interval_begin_time` and `ap` are mapped to canonical names when present.\n")
    md.append("- `count` is coerced to numeric for analysis readiness.\n")

    output_md.write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote: {output_csv}")
    print(f"Wrote: {output_md}")


if __name__ == "__main__":
    main()
