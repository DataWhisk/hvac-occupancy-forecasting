"""
Transformer-based model for occupancy forecasting.

Uses a transformer architecture for time-series forecasting of building occupancy.
Can capture complex temporal dependencies and potentially outperform Prophet
for longer forecast horizons or when external features are important.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple


class TransformerOccupancyModel:
    """
    Transformer-based occupancy forecasting model.

    Uses attention mechanisms to capture temporal patterns in occupancy data.
    This is a more flexible architecture that can incorporate multiple
    input features (weather, time features, etc.).

    Attributes:
        model: The underlying PyTorch transformer model.
        zone_id: The zone/room this model is trained for.
        seq_length: Input sequence length for the transformer.
        pred_length: Prediction horizon length.

    TODO:
        - Implement actual transformer architecture (or use existing library)
        - Add support for multi-zone forecasting
        - Integrate with existing code from previous student
        - Consider using libraries like pytorch-forecasting or darts
    """

    def __init__(
        self,
        zone_id: Optional[str] = None,
        seq_length: int = 96,  # 1 day at 15min intervals
        pred_length: int = 96,  # Predict 1 day ahead
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        **kwargs: Dict[str, Any],
    ):
        """
        Initialize the transformer occupancy model.

        Args:
            zone_id: Identifier for the zone/room being modeled.
            seq_length: Number of historical timesteps as input.
            pred_length: Number of future timesteps to predict.
            d_model: Transformer model dimension.
            n_heads: Number of attention heads.
            n_layers: Number of transformer layers.
            **kwargs: Additional model configuration.
        """
        self.zone_id = zone_id
        self.seq_length = seq_length
        self.pred_length = pred_length
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kwargs = kwargs
        self.model = None
        self.scaler = None

    def _build_model(self):
        """
        Build the transformer model architecture.

        TODO:
            - Implement transformer encoder-decoder or encoder-only architecture
            - Add positional encoding
            - Configure for time-series forecasting
        """
        # TODO: Implement model building
        # import torch
        # import torch.nn as nn
        raise NotImplementedError("Implement transformer architecture")

    def _prepare_sequences(
        self,
        df: pd.DataFrame,
        target_col: str = "occupancy_count",
        feature_cols: Optional[list] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare input/output sequences for training.

        Args:
            df: DataFrame with timestamp index and features.
            target_col: Column name for the target variable.
            feature_cols: List of feature columns to include.

        Returns:
            Tuple of (X, y) arrays for training.

        TODO:
            - Implement sliding window sequence creation
            - Handle multiple features
            - Add proper train/val/test splitting
        """
        # TODO: Implement sequence preparation
        raise NotImplementedError("Implement sequence preparation")

    def fit(
        self,
        df: pd.DataFrame,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 1e-3,
        val_split: float = 0.2,
    ) -> "TransformerOccupancyModel":
        """
        Train the transformer model on historical occupancy data.

        Args:
            df: DataFrame with occupancy and feature columns.
            epochs: Number of training epochs.
            batch_size: Training batch size.
            learning_rate: Optimizer learning rate.
            val_split: Fraction of data for validation.

        Returns:
            self (fitted model)

        TODO:
            - Implement training loop
            - Add early stopping
            - Add learning rate scheduling
            - Log training metrics
        """
        # TODO: Implement training
        raise NotImplementedError("Implement transformer training")

    def predict(
        self,
        df: pd.DataFrame,
        horizon: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Generate occupancy forecasts.

        Args:
            df: Recent historical data for conditioning.
            horizon: Number of steps to forecast (default: pred_length).

        Returns:
            DataFrame with forecasted occupancy values.

        TODO:
            - Implement autoregressive prediction
            - Add uncertainty estimation
            - Handle variable forecast horizons
        """
        if self.model is None:
            raise ValueError("Model must be fitted before prediction")

        # TODO: Implement prediction
        raise NotImplementedError("Implement transformer prediction")

    def evaluate(
        self,
        test_df: pd.DataFrame,
        metrics: Optional[list] = None,
    ) -> Dict[str, float]:
        """
        Evaluate model performance on test data.

        Args:
            test_df: Test DataFrame.
            metrics: List of metrics to compute.

        Returns:
            Dictionary of metric names to values.

        TODO:
            - Implement evaluation metrics
            - Add visualization of predictions vs actuals
        """
        if metrics is None:
            metrics = ["mae", "rmse", "mape"]

        # TODO: Implement evaluation
        raise NotImplementedError("Implement model evaluation")
