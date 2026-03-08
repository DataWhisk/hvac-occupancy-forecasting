#!/usr/bin/env python3
"""
Build a DB schema dictionary from PostgreSQL metadata.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data import load_schema_dictionary  # noqa: E402


def infer_meaning(table: str, column: str) -> str:
    c = column.lower()
    t = table.lower()
    if c in {"beginning", "end", "timestamp", "timestamp"}:
        return "time boundary / observation timestamp"
    if "occupancy" in c:
        return "observed occupancy count"
    if c in {"space_id", "roomid", "typeid", "region_id", "wapcov_id"}:
        return "entity identifier"
    if c in {"user", "mac"}:
        return "anonymized user/device identifier"
    if "temp" in c:
        return "temperature measurement"
    if c in {"access_point", "wap", "sensor", "sensor_id"}:
        return "network/sensor source identifier"
    if c == "payload":
        return "raw payload or event value"
    if t == "space" and c == "parent_space_id":
        return "hierarchical parent reference"
    return "domain-specific field; confirm with data owner"


def main():
    out_csv = PROJECT_ROOT / "data/interim/db_schema_dictionary.csv"
    out_md = PROJECT_ROOT / "docs/db_data_dictionary.md"

    schema_df = load_schema_dictionary(schema="public", env_path=".env")
    if schema_df.empty:
        raise RuntimeError("No schema metadata returned from DB.")

    schema_df = schema_df.copy()
    schema_df["semantic_meaning"] = schema_df.apply(
        lambda r: infer_meaning(r["table_name"], r["column_name"]),
        axis=1,
    )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    schema_df.to_csv(out_csv, index=False)

    lines = []
    lines.append("# Database Data Dictionary\n")
    lines.append("Generated from PostgreSQL metadata (`information_schema` + `pg_catalog`).\n")
    tables = sorted(schema_df["table_name"].unique().tolist())
    lines.append(f"- Tables discovered: **{len(tables)}**\n")

    for table in tables:
        tdf = schema_df[schema_df["table_name"] == table].copy()
        est_rows = int(tdf["estimated_row_count"].iloc[0]) if len(tdf) else 0
        lines.append(f"## {table}\n")
        lines.append(f"- Estimated rows: **{est_rows:,}**\n")
        lines.append("| Column | Type | Nullable | Meaning | Comment |")
        lines.append("|---|---|---|---|---|")
        for _, r in tdf.iterrows():
            comment = "" if pd.isna(r["column_comment"]) else str(r["column_comment"])
            lines.append(
                f"| {r['column_name']} | {r['data_type']} | {r['is_nullable']} | "
                f"{r['semantic_meaning']} | {comment} |"
            )
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_md}")


if __name__ == "__main__":
    main()
