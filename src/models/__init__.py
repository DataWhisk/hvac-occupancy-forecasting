"""Forecasting models for occupancy prediction."""

from .prophet_baseline import ProphetOccupancyModel, predict_occupancy
from .transformer_baseline import TransformerOccupancyModel
try:
    from .xgBoost import occupancy_predictor
except Exception:  # pragma: no cover - optional dependency (xgboost)
    occupancy_predictor = None


__all__ = [
    "ProphetOccupancyModel",
    "predict_occupancy",
    "TransformerOccupancyModel",
    "occupancy_predictor",
]
