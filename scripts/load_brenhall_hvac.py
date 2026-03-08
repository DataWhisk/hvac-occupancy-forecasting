#!/usr/bin/env python3
"""
Deprecated: CSV loading was removed in DB-only mode.
"""

if __name__ == "__main__":
    raise SystemExit(
        "CSV HVAC loading is disabled. Use PostgreSQL loaders via src.data.load_hvac_from_db."
    )
