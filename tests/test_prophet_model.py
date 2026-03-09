import pandas as pd

from src.models.prophet_baseline import ProphetOccupancyModel


def test_date_range_inference_returns_full_coverage():
    train = pd.DataFrame(
        {
            "ds": pd.date_range("2025-01-01 00:00:00", periods=200, freq="15min"),
            "y": [0, 1, 2, 3] * 50,
        }
    )
    model = ProphetOccupancyModel(zone_id="A", freq="15min")
    model.fit(train)

    start = pd.Timestamp("2025-01-03 00:00:00")
    end = pd.Timestamp("2025-01-03 03:45:00")
    forecast = model.predict_date_range(start_ts=start, end_ts=end)

    assert forecast["ds"].min() == start
    assert forecast["ds"].max() == end
    assert len(forecast) == 16
    assert {"pred_occupancy_count", "pred_is_occupied"}.issubset(set(forecast.columns))


def test_binary_conversion_definition_threshold():
    model = ProphetOccupancyModel(zone_id="A", freq="15min")
    model.backend = "seasonal_naive"
    model._seasonal = None  # Not used by this patched path.
    model._fitted_df = pd.DataFrame({"ds": [pd.Timestamp("2025-01-01")], "y": [0]})

    def fake_predict_core(_future_df):
        return pd.DataFrame(
            {
                "ds": pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:15:00"]),
                "yhat": [0.8, 1.2],
                "yhat_lower": [0.8, 1.2],
                "yhat_upper": [0.8, 1.2],
                "pred_occupancy_count": [0.8, 1.2],
                "pred_is_occupied": [False, True],
            }
        )

    model.predict_dataframe = fake_predict_core  # type: ignore[method-assign]

    test_df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:15:00"]),
            "y": [0.0, 2.0],  # true binary => [False, True]
        }
    )
    metrics = model.evaluate(test_df)
    assert metrics["binary_accuracy"] == 1.0
