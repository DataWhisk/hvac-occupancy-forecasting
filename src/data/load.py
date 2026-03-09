"""
Data loading utilities for HVAC occupancy forecasting.

DB-only source of truth:
- PostgreSQL loading via .env credentials
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd

try:
    import psycopg2
except ImportError:  # pragma: no cover - handled at runtime
    psycopg2 = None


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
    CSV loading is disabled. Use `load_occupancy_from_db`.
    """
    raise NotImplementedError(
        "CSV loading is disabled. Use PostgreSQL loaders (load_occupancy_from_db)."
    )


def load_hvac(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    CSV loading is disabled. Use `load_hvac_from_db`.
    """
    raise NotImplementedError(
        "CSV loading is disabled. Use PostgreSQL loaders (load_hvac_from_db)."
    )


def load_weather(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    CSV loading is disabled. Use `load_weather_from_db`.
    """
    raise NotImplementedError(
        "CSV loading is disabled. Use PostgreSQL loaders (load_weather_from_db)."
    )


def fetch_historical_weather(
    lat: float = 33.6695,
    lon: float = -117.8231,
    start_date: str = "2017-08-28",
    end_date: str = "2018-01-05",
) -> pd.DataFrame:
    """
    Disabled in DB-only mode.
    """
    raise NotImplementedError(
        "Weather API loading is disabled in DB-only mode. Use load_weather_from_db."
    )


def load_tou(path: str, parse_dates: bool = True) -> pd.DataFrame:
    """
    CSV loading is disabled. Use `load_tou_from_db`.
    """
    raise NotImplementedError(
        "CSV loading is disabled. Use PostgreSQL loaders (load_tou_from_db)."
    )


def load_space_metadata(path: str) -> pd.DataFrame:
    """
    CSV loading is disabled. Use `load_space_metadata_from_db`.
    """
    raise NotImplementedError(
        "CSV loading is disabled. Use PostgreSQL loaders (load_space_metadata_from_db)."
    )


def _read_env_file(path: str = ".env") -> Dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    parsed: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        parsed[key] = value
    return parsed


def get_db_config(env_path: str = ".env", **overrides) -> Dict[str, str]:
    """
    Build DB config from environment variables + .env + explicit overrides.
    """
    file_values = _read_env_file(env_path)
    merged = {**file_values, **os.environ, **overrides}

    config = {
        "host": merged.get("DB_HOST", merged.get("PGHOST", "")),
        "port": str(merged.get("DB_PORT", merged.get("PGPORT", "5432"))),
        "dbname": merged.get("DB_NAME", merged.get("PGDATABASE", "")),
        "user": merged.get("DB_USER", merged.get("PGUSER", "")),
        "password": merged.get("DB_PASSWORD", merged.get("PGPASSWORD", "")),
    }

    missing = [k for k, v in config.items() if not v]
    if missing:
        raise ValueError(
            "Missing DB config values: "
            f"{missing}. Set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."
        )
    return config


def get_postgres_connection(env_path: str = ".env", **overrides):
    """
    Create a psycopg2 connection from .env/environment config.
    """
    if psycopg2 is None:
        raise ImportError(
            "psycopg2 is not installed. Install 'psycopg2-binary' to enable DB loading."
        )
    config = get_db_config(env_path=env_path, **overrides)
    return psycopg2.connect(**config)


def _query_dataframe(conn, query: str, params: Optional[Sequence] = None) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(query, params if params is not None else [])
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def _validate_identifier(identifier: str, label: str) -> None:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", identifier):
        raise ValueError(f"Invalid {label}: {identifier!r}")


def load_table_from_db(
    table_name: str,
    schema: str = "public",
    columns: Optional[Sequence[str]] = None,
    where_clause: Optional[str] = None,
    limit: Optional[int] = None,
    parse_dates: Optional[Sequence[str]] = None,
    env_path: str = ".env",
) -> pd.DataFrame:
    """
    Load a database table into a DataFrame.

    Note:
      where_clause is inserted as-is. Prefer trusted static SQL only.
    """
    _validate_identifier(schema, "schema")
    _validate_identifier(table_name, "table_name")
    if columns:
        for col in columns:
            _validate_identifier(col, "column")

    cols_sql = ", ".join(columns) if columns else "*"
    query = f'SELECT {cols_sql} FROM "{schema}"."{table_name}"'
    if where_clause:
        query += f" WHERE {where_clause}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"

    with get_postgres_connection(env_path=env_path) as conn:
        df = _query_dataframe(conn, query=query)

    if parse_dates:
        for col in parse_dates:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_schema_dictionary(schema: str = "public", env_path: str = ".env") -> pd.DataFrame:
    """
    Load schema metadata with column comments and estimated row counts.
    """
    query = """
    SELECT
      c.table_schema,
      c.table_name,
      c.column_name,
      c.ordinal_position,
      c.data_type,
      c.is_nullable,
      c.column_default,
      pgd.description AS column_comment,
      COALESCE(st.n_live_tup, 0)::bigint AS estimated_row_count
    FROM information_schema.columns c
    LEFT JOIN pg_catalog.pg_namespace ns
      ON ns.nspname = c.table_schema
    LEFT JOIN pg_catalog.pg_class cls
      ON cls.relnamespace = ns.oid
     AND cls.relname = c.table_name
    LEFT JOIN pg_catalog.pg_description pgd
      ON pgd.objoid = cls.oid
     AND pgd.objsubid = c.ordinal_position
    LEFT JOIN pg_catalog.pg_stat_user_tables st
      ON st.schemaname = c.table_schema
     AND st.relname = c.table_name
    WHERE c.table_schema = %s
    ORDER BY c.table_name, c.ordinal_position;
    """
    with get_postgres_connection(env_path=env_path) as conn:
        return _query_dataframe(conn, query=query, params=[schema])


def load_occupancy_from_db(
    table_name: str = "space_occupancy",
    schema: str = "public",
    env_path: str = ".env",
    zone_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load occupancy series from a PostgreSQL table and normalize to:
    [zone_id, interval_begin, count].
    """
    _validate_identifier(schema, "schema")
    _validate_identifier(table_name, "table_name")

    params = None
    if table_name == "space_occupancy":
        query = (
            f'SELECT space_id::text AS zone_id, beginning AS interval_begin, '
            f"occupancy::double precision AS count "
            f'FROM "{schema}"."space_occupancy"'
        )
        if zone_id is not None:
            query += " WHERE space_id::text = %s"
            params = [str(zone_id)]
    else:
        query = f'SELECT * FROM "{schema}"."{table_name}"'

    with get_postgres_connection(env_path=env_path) as conn:
        df = _query_dataframe(conn, query=query, params=params)

    if "interval_begin" in df.columns:
        df["interval_begin"] = pd.to_datetime(df["interval_begin"], errors="coerce")
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce")
    return df


def load_weather_from_db(
    table_name: str,
    schema: str = "public",
    timestamp_col: str = "timestamp",
    temp_col: str = "outside_temp",
    env_path: str = ".env",
) -> pd.DataFrame:
    """
    Load weather series from PostgreSQL and normalize to:
    [timestamp, outside_temp].
    """
    _validate_identifier(schema, "schema")
    _validate_identifier(table_name, "table_name")
    _validate_identifier(timestamp_col, "timestamp_col")
    _validate_identifier(temp_col, "temp_col")

    query = (
        f'SELECT {timestamp_col} AS timestamp, '
        f"{temp_col}::double precision AS outside_temp "
        f'FROM "{schema}"."{table_name}"'
    )
    with get_postgres_connection(env_path=env_path) as conn:
        df = _query_dataframe(conn, query=query)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["outside_temp"] = pd.to_numeric(df["outside_temp"], errors="coerce")
    return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def load_hvac_from_db(
    table_name: str = "hvac",
    schema: str = "public",
    env_path: str = ".env",
) -> pd.DataFrame:
    """
    Load HVAC table from PostgreSQL.
    """
    return load_table_from_db(
        table_name=table_name,
        schema=schema,
        env_path=env_path,
        parse_dates=["timestamp"],
    )


def load_tou_from_db(
    table_name: str,
    schema: str = "public",
    env_path: str = ".env",
) -> pd.DataFrame:
    """
    Load TOU table from PostgreSQL.
    """
    return load_table_from_db(
        table_name=table_name,
        schema=schema,
        env_path=env_path,
    )


def load_space_metadata_from_db(
    table_name: str = "space_metadata",
    schema: str = "public",
    env_path: str = ".env",
) -> pd.DataFrame:
    """
    Load space metadata table from PostgreSQL.
    """
    return load_table_from_db(
        table_name=table_name,
        schema=schema,
        env_path=env_path,
    )
