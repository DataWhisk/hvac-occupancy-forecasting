"""
Prophet-based baseline model for occupancy forecasting.

If Prophet is unavailable in the runtime environment, this module falls back
to a deterministic seasonal naive model so the pipeline remains runnable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover - depends on runtime environment
    Prophet = None

from src.data.preprocess import prepare_occupancy_forecast_dataset


@dataclass
class _SeasonalProfile:
    profile: pd.Series
    global_mean: float


class ProphetOccupancyModel:
    """
    Occupancy forecasting model with Prophet primary backend and
    seasonal-naive fallback backend.
    """

    def __init__(
        self,
        zone_id: Optional[str] = None,
        freq: str = "15min",
        **prophet_kwargs: Dict[str, Any],
    ):
        self.zone_id = zone_id
        self.freq = freq
        self.prophet_kwargs = prophet_kwargs

        self.model = None
        self.backend = "unfitted"
        self._uses_temp = False
        self._fitted_df: Optional[pd.DataFrame] = None
        self._seasonal: Optional[_SeasonalProfile] = None
        self._temp_median: Optional[float] = None

    @staticmethod
    def _normalize_fit_df(df: pd.DataFrame) -> pd.DataFrame:
        if "ds" not in df.columns or "y" not in df.columns:
            raise ValueError("Fit dataframe must contain columns ['ds', 'y'].")

        out = df.copy()
        out["ds"] = pd.to_datetime(out["ds"], errors="coerce")
        out["y"] = pd.to_numeric(out["y"], errors="coerce")
        if "outside_temp" in out.columns:
            out["outside_temp"] = pd.to_numeric(out["outside_temp"], errors="coerce")

        out = out.dropna(subset=["ds", "y"]).sort_values("ds").reset_index(drop=True)
        if out.empty:
            raise ValueError("No valid training rows after parsing ['ds', 'y'].")
        return out

    @staticmethod
    def _slot_key(ts: pd.Series) -> pd.MultiIndex:
        minutes = ts.dt.hour * 60 + ts.dt.minute
        return pd.MultiIndex.from_arrays([ts.dt.dayofweek, minutes], names=["dow", "slot"])

    def _build_seasonal_fallback(self, df: pd.DataFrame) -> None:
        keyed = df.copy()
        keyed["dow"] = keyed["ds"].dt.dayofweek
        keyed["slot"] = keyed["ds"].dt.hour * 60 + keyed["ds"].dt.minute
        profile = keyed.groupby(["dow", "slot"])["y"].mean()
        global_mean = float(keyed["y"].mean()) if len(keyed) else 0.0
        self._seasonal = _SeasonalProfile(profile=profile, global_mean=global_mean)
        self.backend = "seasonal_naive"

    def fit(self, df: pd.DataFrame) -> "ProphetOccupancyModel":
        train = self._normalize_fit_df(df)
        self._fitted_df = train
        self._uses_temp = "outside_temp" in train.columns and train["outside_temp"].notna().any()
        self._temp_median = (
            float(train["outside_temp"].median()) if self._uses_temp else None
        )

        if Prophet is None:
            self._build_seasonal_fallback(train)
            self.model = None
            return self

        defaults: Dict[str, Any] = {
            "daily_seasonality": True,
            "weekly_seasonality": True,
            "yearly_seasonality": False,
        }
        defaults.update(self.prophet_kwargs)

        model = Prophet(**defaults)
        fit_cols = ["ds", "y"]
        if self._uses_temp:
            model.add_regressor("outside_temp")
            fit_cols.append("outside_temp")
            train = train.copy()
            train["outside_temp"] = train["outside_temp"].fillna(self._temp_median)

        model.fit(train[fit_cols])
        self.model = model
        self.backend = "prophet"
        return self

    @staticmethod
    def _normalize_future_df(future_df: pd.DataFrame) -> pd.DataFrame:
        if "ds" not in future_df.columns:
            raise ValueError("Future dataframe must include 'ds'.")

        out = future_df.copy()
        out["ds"] = pd.to_datetime(out["ds"], errors="coerce")
        if "outside_temp" in out.columns:
            out["outside_temp"] = pd.to_numeric(out["outside_temp"], errors="coerce")
        out = out.dropna(subset=["ds"]).sort_values("ds").reset_index(drop=True)
        if out.empty:
            raise ValueError("No valid future rows after datetime parsing.")
        return out

    def _fill_missing_future_temp(self, future_df: pd.DataFrame) -> pd.DataFrame:
        out = future_df.copy()
        if not self._uses_temp:
            return out
        if "outside_temp" not in out.columns:
            out["outside_temp"] = self._temp_median
        else:
            out["outside_temp"] = out["outside_temp"].fillna(self._temp_median)
        return out

    @staticmethod
    def _post_process(forecast_df: pd.DataFrame) -> pd.DataFrame:
        out = forecast_df.copy()
        for col in ["yhat", "yhat_lower", "yhat_upper"]:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).clip(lower=0.0)
        out["pred_occupancy_count"] = out["yhat"]
        out["pred_is_occupied"] = out["pred_occupancy_count"] >= 1.0
        return out

    def _predict_core(self, future_df: pd.DataFrame) -> pd.DataFrame:
        if self.backend == "unfitted":
            raise ValueError("Model must be fitted before prediction.")

        future = self._fill_missing_future_temp(self._normalize_future_df(future_df))

        if self.backend == "prophet":
            assert self.model is not None
            pred_cols = ["ds"] + (["outside_temp"] if self._uses_temp else [])
            forecast = self.model.predict(future[pred_cols])
            out = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
            return self._post_process(out)

        assert self._seasonal is not None
        keys = self._slot_key(future["ds"])
        yhat = np.array(
            [self._seasonal.profile.get(key, self._seasonal.global_mean) for key in keys],
            dtype=float,
        )
        out = pd.DataFrame(
            {
                "ds": future["ds"],
                "yhat": yhat,
                "yhat_lower": yhat,
                "yhat_upper": yhat,
            }
        )
        return self._post_process(out)

    def predict(
        self,
        periods: int,
        include_history: bool = False,
    ) -> pd.DataFrame:
        if self._fitted_df is None:
            raise ValueError("Model must be fitted before prediction.")
        if periods <= 0:
            raise ValueError("periods must be > 0")

        last_ds = self._fitted_df["ds"].max()
        future_index = pd.date_range(
            start=last_ds + pd.tseries.frequencies.to_offset(self.freq),
            periods=periods,
            freq=self.freq,
        )
        future = pd.DataFrame({"ds": future_index})

        if include_history:
            history = self._fitted_df[["ds"]].copy()
            if self._uses_temp and "outside_temp" in self._fitted_df.columns:
                history["outside_temp"] = self._fitted_df["outside_temp"]
            if self._uses_temp and "outside_temp" not in future.columns:
                future["outside_temp"] = self._temp_median
            future = pd.concat([history, future], ignore_index=True)

        return self._predict_core(future)

    def predict_date_range(
        self,
        start_ts: datetime | str,
        end_ts: datetime | str,
        weather_future_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_ts)
        end = pd.Timestamp(end_ts)
        if end < start:
            raise ValueError("end_ts must be >= start_ts")

        index = pd.date_range(start=start, end=end, freq=self.freq)
        future = pd.DataFrame({"ds": index})

        if weather_future_df is not None and len(weather_future_df):
            weather = weather_future_df.copy()
            if "timestamp" in weather.columns and "ds" not in weather.columns:
                weather = weather.rename(columns={"timestamp": "ds"})
            if "temperature" in weather.columns and "outside_temp" not in weather.columns:
                weather = weather.rename(columns={"temperature": "outside_temp"})
            weather = weather[["ds", "outside_temp"]].copy()
            weather["ds"] = pd.to_datetime(weather["ds"], errors="coerce")
            weather["outside_temp"] = pd.to_numeric(weather["outside_temp"], errors="coerce")
            future = future.merge(weather, on="ds", how="left")

        return self._predict_core(future)

    def predict_dataframe(self, future_df: pd.DataFrame) -> pd.DataFrame:
        return self._predict_core(future_df)

    def evaluate(
        self,
        test_df: pd.DataFrame,
        metrics: Optional[list] = None,
    ) -> Dict[str, float]:
        if metrics is None:
            metrics = ["binary_accuracy", "precision", "recall", "f1", "mae"]
        if "ds" not in test_df.columns or "y" not in test_df.columns:
            raise ValueError("test_df must contain ['ds', 'y'].")

        eval_df = test_df.copy()
        eval_df["ds"] = pd.to_datetime(eval_df["ds"], errors="coerce")
        eval_df["y"] = pd.to_numeric(eval_df["y"], errors="coerce")
        eval_df = eval_df.dropna(subset=["ds", "y"]).sort_values("ds")

        predict_cols = ["ds"] + (["outside_temp"] if "outside_temp" in eval_df.columns else [])
        forecast = self.predict_dataframe(eval_df[predict_cols])
        merged = eval_df.merge(
            forecast[["ds", "pred_occupancy_count", "pred_is_occupied"]],
            on="ds",
            how="inner",
        )
        if merged.empty:
            raise ValueError("No overlapping rows between test data and predictions.")

        y_true = merged["y"].to_numpy(dtype=float)
        y_pred = merged["pred_occupancy_count"].to_numpy(dtype=float)
        y_true_bin = y_true > 0
        y_pred_bin = merged["pred_is_occupied"].astype(bool).to_numpy()

        tp = int(np.sum(y_true_bin & y_pred_bin))
        tn = int(np.sum(~y_true_bin & ~y_pred_bin))
        fp = int(np.sum(~y_true_bin & y_pred_bin))
        fn = int(np.sum(y_true_bin & ~y_pred_bin))

        total = max(len(merged), 1)
        accuracy = (tp + tn) / total
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
        mae = float(np.mean(np.abs(y_true - y_pred)))

        all_metrics = {
            "binary_accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "mae": float(mae),
            "n_eval_rows": float(len(merged)),
        }
        return {name: all_metrics[name] for name in metrics if name in all_metrics}


def predict_occupancy(
    zone_id: str,
    start_ts: datetime | str,
    end_ts: datetime | str,
    freq: str = "15min",
    model: Optional[ProphetOccupancyModel] = None,
    historical_df: Optional[pd.DataFrame] = None,
    weather_history_df: Optional[pd.DataFrame] = None,
    weather_future_df: Optional[pd.DataFrame] = None,
    train_ratio: float = 0.8,
    **prophet_kwargs: Dict[str, Any],
) -> pd.DataFrame:
    """
    Service-style interface for single-zone occupancy prediction.

    If model is not provided, the function trains a model from historical_df.
    """
    if model is None:
        if historical_df is None:
            raise ValueError("historical_df is required when model is not provided.")
        ds = prepare_occupancy_forecast_dataset(
            occ_df=historical_df,
            weather_df=weather_history_df,
            zone_id=zone_id,
            freq=freq,
            dropna_for_training=True,
        )
        fit_df = ds.rename(columns={"timestamp": "ds", "occupancy_count": "y"})[
            ["ds", "y", "outside_temp"]
        ].copy()
        split_idx = int(len(fit_df) * float(train_ratio))
        if split_idx < 1:
            raise ValueError("Not enough rows to train model.")

        model = ProphetOccupancyModel(zone_id=zone_id, freq=freq, **prophet_kwargs)
        model.fit(fit_df.iloc[:split_idx].reset_index(drop=True))

    forecast = model.predict_date_range(
        start_ts=start_ts,
        end_ts=end_ts,
        weather_future_df=weather_future_df,
    )
    out = forecast.rename(columns={"ds": "timestamp"}).copy()
    out["zone_id"] = str(zone_id)
    return out[["timestamp", "zone_id", "pred_occupancy_count", "pred_is_occupied"]]
