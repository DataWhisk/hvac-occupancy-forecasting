from datetime import datetime

import pytest

from src.viz import dashboard_data


class FakeCursor:
    def __init__(self, columns, rows):
        self.description = [(col, None, None, None, None, None, None) for col in columns]
        self._rows = rows
        self.last_query = ""
        self.last_params = None

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _patch_connection(monkeypatch, fake_cursor):
    monkeypatch.setattr(
        dashboard_data,
        "get_postgres_connection",
        lambda env_path=".env": FakeConnection(fake_cursor),
    )


def test_fetch_occupancy_daily_uses_parameterized_time_filters(monkeypatch):
    cursor = FakeCursor(
        columns=["day", "avg_occ", "peak_occ", "samples"],
        rows=[],
    )
    _patch_connection(monkeypatch, cursor)

    dashboard_data.fetch_occupancy_daily(
        schema="public",
        env_path=".env",
        start_ts="2024-01-01 00:00:00",
        end_ts="2024-01-31 23:59:59",
    )

    assert "beginning >= %s" in cursor.last_query
    assert "beginning <= %s" in cursor.last_query
    assert isinstance(cursor.last_params[0], datetime)
    assert isinstance(cursor.last_params[1], datetime)
    assert cursor.last_params[0] <= cursor.last_params[1]


def test_fetch_hvac_zone_stats_param_order(monkeypatch):
    cursor = FakeCursor(
        columns=[
            "space_id",
            "avg_temp",
            "std_temp",
            "min_temp",
            "max_temp",
            "comfort_exceedance_pct",
            "samples",
        ],
        rows=[("Zone-A", 72.0, 2.0, 68.0, 78.0, 10.0, 100)],
    )
    _patch_connection(monkeypatch, cursor)

    df = dashboard_data.fetch_hvac_zone_stats(
        schema="public",
        env_path=".env",
        comfort_low=69.0,
        comfort_high=75.0,
        start_ts="2024-07-01 00:00:00",
        end_ts="2024-07-15 23:59:59",
    )

    assert cursor.last_params[0] == 69.0
    assert cursor.last_params[1] == 75.0
    assert isinstance(cursor.last_params[2], datetime)
    assert isinstance(cursor.last_params[3], datetime)
    assert list(df.columns) == [
        "space_id",
        "avg_temp",
        "std_temp",
        "min_temp",
        "max_temp",
        "comfort_exceedance_pct",
        "samples",
    ]


def test_invalid_schema_is_rejected():
    with pytest.raises(ValueError):
        dashboard_data.fetch_hvac_kpis(schema="public;drop table hvac", env_path=".env")
