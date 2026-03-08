import pandas as pd

from src.viz.dashboard_insights import derive_hvac_insights, derive_occupancy_insights


def test_derive_occupancy_insights_expected_values():
    heatmap = pd.DataFrame(
        {
            "day_of_week": [1, 1, 2, 2],
            "hour_of_day": [9, 10, 9, 10],
            "avg_occ": [15.0, 20.0, 10.0, 11.0],
            "samples": [100, 100, 100, 100],
        }
    )
    spaces = pd.DataFrame(
        {
            "space_id": ["1", "2", "3", "4"],
            "space_label": ["DBH 1001", "DBH 1002", "DBH 1003", "DBH 1004"],
            "avg_occ": [12.0, 8.5, 3.2, 2.4],
            "peak_occ": [40, 32, 10, 8],
            "samples": [100, 100, 100, 100],
        }
    )

    insights = derive_occupancy_insights(heatmap, spaces, low_space_count=2)

    assert insights["busiest_day"] == "Monday"
    assert insights["busiest_hour"] == "10:00"
    assert insights["busiest_hour_avg_occ"] == "20.00"
    assert insights["highest_util_space"] == "DBH 1001"
    assert insights["highest_util_avg_occ"] == "12.00"
    assert insights["low_util_spaces"] == ["DBH 1004", "DBH 1003"]


def test_derive_hvac_insights_uses_comfort_summary_and_variability():
    zones = pd.DataFrame(
        {
            "space_id": ["Zone-A", "Zone-B", "Zone-C"],
            "avg_temp": [74.0, 70.5, 78.2],
            "std_temp": [1.2, 3.1, 2.0],
            "comfort_exceedance_pct": [8.0, 12.0, 25.0],
            "samples": [1000, 1000, 1000],
        }
    )
    comfort_summary = pd.DataFrame(
        {
            "below_band_pct": [5.0],
            "above_band_pct": [9.0],
            "out_of_band_pct": [14.0],
        }
    )

    insights = derive_hvac_insights(zones, comfort_summary)

    assert insights["high_variability_zone"] == "Zone-B"
    assert insights["high_variability_std_temp"] == "3.10"
    assert insights["hottest_zone"] == "Zone-C"
    assert insights["coldest_zone"] == "Zone-B"
    assert insights["overall_out_of_band_pct"] == "14.00"


def test_derive_insights_empty_frames_are_safe():
    occ = derive_occupancy_insights(pd.DataFrame(), pd.DataFrame())
    hvac = derive_hvac_insights(pd.DataFrame(), pd.DataFrame())

    assert occ["busiest_day"] == "N/A"
    assert occ["low_util_spaces"] == []
    assert hvac["high_variability_zone"] == "N/A"
    assert hvac["overall_out_of_band_pct"] == "N/A"
