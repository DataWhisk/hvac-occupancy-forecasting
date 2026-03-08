import pandas as pd

from src.data.preprocess import prepare_occupancy_forecast_dataset


def test_feature_alignment_no_future_leakage():
    ts = pd.date_range("2025-01-01 00:00:00", periods=12, freq="15min")
    occ = pd.DataFrame(
        {
            "timestamp": ts,
            "zone_id": ["A"] * len(ts),
            "occupancy_count": list(range(len(ts))),
        }
    )
    weather = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 00:00:00", periods=4, freq="1h"),
            "outside_temp": [60, 61, 62, 63],
        }
    )

    features = prepare_occupancy_forecast_dataset(
        occ_df=occ,
        weather_df=weather,
        zone_id="A",
        lag_periods=[1, 4],
        dropna_for_training=False,
    )

    # lag(1) at index i must equal occupancy_count at i-1.
    assert features.loc[2, "occupancy_lag_1"] == features.loc[1, "occupancy_count"]
    assert features.loc[5, "occupancy_lag_4"] == features.loc[1, "occupancy_count"]
