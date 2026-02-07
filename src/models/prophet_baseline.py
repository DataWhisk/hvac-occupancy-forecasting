"""
Prophet-based baseline model for occupancy forecasting.

Uses Facebook Prophet for time-series forecasting of building occupancy.
Prophet handles seasonality (daily, weekly, yearly) and holidays well,
making it a good baseline for campus building occupancy patterns.
"""

import pandas as pd
from typing import Optional, Dict, Any


class ProphetOccupancyModel:
    """
    Prophet-based occupancy forecasting model.

    Wraps Facebook Prophet to predict future occupancy for a given zone,
    capturing daily patterns (class schedules), weekly patterns (weekdays vs weekends),
    and longer-term seasonality (academic calendar).

    Attributes:
        model: The underlying Prophet model instance.
        zone_id: The zone/room this model is trained for.
        freq: Forecast frequency (e.g., "15min", "1H").

    TODO:
        - Add support for external regressors (weather, events)
        - Implement cross-validation for hyperparameter tuning
        - Add academic calendar as custom seasonality or holidays
    """

    def __init__(
        self,
        zone_id: Optional[str] = None,
        freq: str = "15min",
        **prophet_kwargs: Dict[str, Any],
    ):
        """
        Initialize the Prophet occupancy model.

        Args:
            zone_id: Identifier for the zone/room being modeled.
            freq: Forecast frequency.
            **prophet_kwargs: Additional arguments passed to Prophet().
        """
        self.zone_id = zone_id
        self.freq = freq
        self.prophet_kwargs = prophet_kwargs
        self.model = None

    def fit(self, df: pd.DataFrame) -> "ProphetOccupancyModel":
        """
        Fit the Prophet model on historical occupancy data.

        Args:
            df: DataFrame with columns ['ds', 'y'] where:
                - ds: datetime timestamp
                - y: occupancy count

        Returns:
            self (fitted model)

        TODO:
            - Implement actual Prophet fitting
            - Add data validation
            - Configure seasonalities for campus patterns
        """
        # TODO: Implement Prophet model fitting
        # from prophet import Prophet
        # self.model = Prophet(**self.prophet_kwargs)
        # self.model.fit(df)
        raise NotImplementedError("Implement Prophet model fitting")

    def predict(
        self,
        periods: int,
        include_history: bool = False,
    ) -> pd.DataFrame:
        """
        Generate occupancy forecasts for future periods.

        Args:
            periods: Number of future periods to forecast.
            include_history: Whether to include historical fitted values.

        Returns:
            DataFrame with columns ['ds', 'yhat', 'yhat_lower', 'yhat_upper'].

        TODO:
            - Implement prediction logic
            - Add uncertainty intervals
            - Post-process predictions (e.g., clip negative values to 0)
        """
        if self.model is None:
            raise ValueError("Model must be fitted before prediction")

        # TODO: Implement prediction
        # future = self.model.make_future_dataframe(periods=periods, freq=self.freq)
        # forecast = self.model.predict(future)
        raise NotImplementedError("Implement Prophet prediction")

    def evaluate(
        self,
        test_df: pd.DataFrame,
        metrics: Optional[list] = None,
    ) -> Dict[str, float]:
        """
        Evaluate model performance on test data.

        Args:
            test_df: Test DataFrame with columns ['ds', 'y'].
            metrics: List of metrics to compute (default: MAE, RMSE, MAPE).

        Returns:
            Dictionary of metric names to values.

        TODO:
            - Implement evaluation metrics
            - Add occupancy-specific metrics (e.g., accuracy at zero detection)
        """
        if metrics is None:
            metrics = ["mae", "rmse", "mape"]

        # TODO: Implement evaluation
        raise NotImplementedError("Implement model evaluation")
