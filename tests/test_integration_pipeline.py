import pandas as pd

from src.data.preprocess import prepare_occupancy_forecast_dataset
from src.models import ProphetOccupancyModel, predict_occupancy


def test_end_to_end_training_eval_and_inference():
    ts = pd.date_range("2025-01-01 00:00:00", periods=14 * 24 * 4, freq="15min")
    occ_values = [0 if t.hour < 8 or t.hour >= 18 else 5 for t in ts]
    occ_df = pd.DataFrame(
        {
            "timestamp": ts,
            "zone_id": ["A"] * len(ts),
            "occupancy_count": occ_values,
        }
    )
    weather_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 00:00:00", periods=14 * 24, freq="1h"),
            "outside_temp": [58 + (i % 24) * 0.2 for i in range(14 * 24)],
        }
    )

    features = prepare_occupancy_forecast_dataset(
        occ_df=occ_df,
        weather_df=weather_df,
        zone_id="A",
        freq="15min",
        dropna_for_training=True,
    )
    model_df = features.rename(columns={"timestamp": "ds", "occupancy_count": "y"})[
        ["ds", "y", "outside_temp"]
    ]
    split_idx = int(len(model_df) * 0.8)

    model = ProphetOccupancyModel(zone_id="A", freq="15min")
    model.fit(model_df.iloc[:split_idx])
    metrics = model.evaluate(model_df.iloc[split_idx:])

    assert {"binary_accuracy", "precision", "recall", "f1", "mae"}.issubset(metrics.keys())

    forecast = predict_occupancy(
        zone_id="A",
        start_ts="2025-01-14 00:00:00",
        end_ts="2025-01-14 23:45:00",
        freq="15min",
        model=model,
    )

    assert len(forecast) == 96
    assert forecast["timestamp"].is_monotonic_increasing
    assert {"zone_id", "pred_occupancy_count", "pred_is_occupied"}.issubset(forecast.columns)
