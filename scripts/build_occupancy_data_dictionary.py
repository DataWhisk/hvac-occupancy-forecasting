#!/usr/bin/env python3
"""
Deprecated compatibility wrapper.

CSV occupancy dictionary generation was removed in DB-only mode.
This command now delegates to `build_db_data_dictionary.py`.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "build_db_data_dictionary.py"
    runpy.run_path(str(target), run_name="__main__")
