"""
PostgreSQL query helpers for the Streamlit HVAC/occupancy dashboard.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Optional, Sequence

# Make `src.*` imports work even when module is run from outside repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data import get_postgres_connection

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(identifier: str, label: str) -> None:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Invalid {label}: {identifier!r}")


def _to_datetime(value: Optional[datetime | str]) -> Optional[datetime]:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def _build_time_filter(
    column_name: str,
    start_ts: Optional[datetime | str],
    end_ts: Optional[datetime | str],
) -> tuple[str, List[datetime]]:
    start_dt = _to_datetime(start_ts)
    end_dt = _to_datetime(end_ts)
    if start_dt is not None and end_dt is not None and start_dt > end_dt:
        raise ValueError("start_ts must be <= end_ts")

    clauses: List[str] = []
    params: List[datetime] = []
    if start_dt is not None:
        clauses.append(f"{column_name} >= %s")
        params.append(start_dt)
    if end_dt is not None:
        clauses.append(f"{column_name} <= %s")
        params.append(end_dt)

    return (" AND ".join(clauses) if clauses else "TRUE"), params


def _query_dataframe(
    query: str,
    params: Optional[Sequence] = None,
    env_path: str = ".env",
) -> pd.DataFrame:
    with get_postgres_connection(env_path=env_path) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params if params is not None else [])
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def fetch_occupancy_kpis(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("beginning", start_ts, end_ts)
    query = f"""
    SELECT
      COUNT(*)::bigint AS rows,
      COUNT(DISTINCT space_id)::int AS spaces,
      MIN(beginning) AS min_ts,
      MAX(beginning) AS max_ts,
      ROUND(AVG(occupancy)::numeric, 2) AS avg_occ,
      ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY occupancy)::numeric, 2) AS median_occ,
      MAX(occupancy) AS peak_occ
    FROM "{schema}"."space_occupancy"
    WHERE {where_sql};
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_occupancy_daily(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("beginning", start_ts, end_ts)
    query = f"""
    SELECT
      DATE(beginning) AS day,
      ROUND(AVG(occupancy)::numeric, 2) AS avg_occ,
      MAX(occupancy) AS peak_occ,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."space_occupancy"
    WHERE {where_sql}
    GROUP BY DATE(beginning)
    ORDER BY day;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_occupancy_heatmap(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("beginning", start_ts, end_ts)
    query = f"""
    SELECT
      EXTRACT(DOW FROM beginning)::int AS day_of_week,
      EXTRACT(HOUR FROM beginning)::int AS hour_of_day,
      ROUND(AVG(occupancy)::numeric, 2) AS avg_occ,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."space_occupancy"
    WHERE {where_sql}
    GROUP BY 1, 2
    ORDER BY 1, 2;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_occupancy_space_stats(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("o.beginning", start_ts, end_ts)
    query = f"""
    SELECT
      o.space_id::text AS space_id,
      COALESCE(s.building_room, s.space_name, '(unknown)') AS space_label,
      ROUND(AVG(o.occupancy)::numeric, 2) AS avg_occ,
      MAX(o.occupancy) AS peak_occ,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."space_occupancy" o
    LEFT JOIN "{schema}"."space" s
      ON s.space_id = o.space_id
    WHERE {where_sql}
    GROUP BY o.space_id, space_label
    ORDER BY avg_occ DESC, samples DESC;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_hvac_kpis(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("timestamp", start_ts, end_ts)
    query = f"""
    SELECT
      COUNT(*)::bigint AS rows,
      COUNT(DISTINCT space_id)::int AS zones,
      MIN(timestamp) AS min_ts,
      MAX(timestamp) AS max_ts,
      ROUND(AVG(zone_temp)::numeric, 2) AS avg_temp,
      ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY zone_temp)::numeric, 2) AS median_temp,
      ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY zone_temp)::numeric, 2) AS p95_temp
    FROM "{schema}"."hvac"
    WHERE {where_sql};
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_hvac_daily(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("timestamp", start_ts, end_ts)
    query = f"""
    SELECT
      DATE(timestamp) AS day,
      ROUND(AVG(zone_temp)::numeric, 2) AS avg_temp,
      ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY zone_temp)::numeric, 2) AS p95_temp,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."hvac"
    WHERE {where_sql}
    GROUP BY DATE(timestamp)
    ORDER BY day;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_hvac_hourly(
    schema: str = "public",
    env_path: str = ".env",
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, params = _build_time_filter("timestamp", start_ts, end_ts)
    query = f"""
    SELECT
      EXTRACT(HOUR FROM timestamp)::int AS hour_of_day,
      ROUND(AVG(zone_temp)::numeric, 2) AS avg_temp,
      ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY zone_temp)::numeric, 2) AS p90_temp,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."hvac"
    WHERE {where_sql}
    GROUP BY 1
    ORDER BY 1;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_hvac_zone_stats(
    schema: str = "public",
    env_path: str = ".env",
    comfort_low: float = 70.0,
    comfort_high: float = 76.0,
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, time_params = _build_time_filter("timestamp", start_ts, end_ts)
    params: List[object] = [comfort_low, comfort_high]
    params.extend(time_params)
    query = f"""
    SELECT
      space_id,
      ROUND(AVG(zone_temp)::numeric, 2) AS avg_temp,
      ROUND(STDDEV_POP(zone_temp)::numeric, 2) AS std_temp,
      ROUND(MIN(zone_temp)::numeric, 2) AS min_temp,
      ROUND(MAX(zone_temp)::numeric, 2) AS max_temp,
      ROUND(
        100.0 * AVG(CASE WHEN zone_temp < %s OR zone_temp > %s THEN 1.0 ELSE 0.0 END)::numeric,
        2
      ) AS comfort_exceedance_pct,
      COUNT(*)::bigint AS samples
    FROM "{schema}"."hvac"
    WHERE {where_sql}
    GROUP BY space_id
    ORDER BY avg_temp DESC, samples DESC;
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)


def fetch_hvac_comfort_summary(
    schema: str = "public",
    env_path: str = ".env",
    comfort_low: float = 70.0,
    comfort_high: float = 76.0,
    start_ts: Optional[datetime | str] = None,
    end_ts: Optional[datetime | str] = None,
) -> pd.DataFrame:
    _validate_identifier(schema, "schema")
    where_sql, time_params = _build_time_filter("timestamp", start_ts, end_ts)
    params: List[object] = [comfort_low, comfort_high, comfort_low, comfort_high]
    params.extend(time_params)
    query = f"""
    SELECT
      ROUND(100.0 * AVG(CASE WHEN zone_temp < %s THEN 1.0 ELSE 0.0 END)::numeric, 2) AS below_band_pct,
      ROUND(100.0 * AVG(CASE WHEN zone_temp > %s THEN 1.0 ELSE 0.0 END)::numeric, 2) AS above_band_pct,
      ROUND(
        100.0 * AVG(CASE WHEN zone_temp < %s OR zone_temp > %s THEN 1.0 ELSE 0.0 END)::numeric,
        2
      ) AS out_of_band_pct
    FROM "{schema}"."hvac"
    WHERE {where_sql};
    """
    return _query_dataframe(query=query, params=params, env_path=env_path)
