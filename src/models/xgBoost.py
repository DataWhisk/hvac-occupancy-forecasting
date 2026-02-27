import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import matplotlib.pyplot as plt


class occupancy_predictor:
    """
    A class to handle occupancy forecasting using XGBoost.
    
    Manages data preparation, feature engineering, model training,
    evaluation, and visualization of predictions.
    """
    
    def __init__(self):
        """Initialize the occupancy predictor with empty state."""
        self.df = None
        self.model = None
        self.X_test = None
        self.y_test = None
        self.predictions = None
        self.features = None
        self.target_col = 'occupancy'
    
    def prepare_data(self, df, time_col='interval_begin', count_col='count'):
        """
        Resamples raw interval data into strict 1-hour blocks.
        
        Args:
            df (pd.DataFrame): Raw interval data
            time_col (str): Name of the timestamp column
            count_col (str): Name of the count column
        
        Returns:
            self: For method chaining
        """
        df = df.copy()
        
        # Ensure datetime format and set as index
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
        
        # Resample to 1-hour intervals, filling missing gaps with 0
        hourly_df = df[count_col].resample('1h').sum().fillna(0).to_frame(name='occupancy')
        self.df = hourly_df
        return self
    
    def create_features(self, weather_df=None):
        """
        Generates time-based and lag features for the XGBoost model, 
        and integrates external weather data if provided.
        
        Args:
            weather_df (pd.DataFrame, optional): External weather data with datetime index
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not prepared. Call prepare_data() first.")
        
        df = self.df.copy()
        
        # Merge external weather data
        if weather_df is not None:
            # Join the weather data onto the occupancy data using the datetime index
            df = df.join(weather_df, how='left')
            
            # If there are any missing temperature values (e.g., an API hiccup), 
            # forward-fill them using the previous hour's temperature
            df['outside_temp'] = df['outside_temp'].ffill()
        
        # Generate engineered features
        # Time-based features
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Lag features (past occupancy)
        df['occ_lag_1h'] = df['occupancy'].shift(1)
        df['occ_lag_24h'] = df['occupancy'].shift(24)
        
        # Drop the first 24 rows which now have NaN values because of the lag shifting
        self.df = df.dropna()
        return self
    
    def train_and_evaluate(self, target_col='occupancy', train_ratio=0.8):
        """
        Splits data chronologically, trains the model, and generates predictions.
        
        Args:
            target_col (str): Name of the target column
            train_ratio (float): Proportion of data to use for training
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not prepared. Call prepare_data() and create_features() first.")
        
        df = self.df
        self.target_col = target_col
        
        # Chronological split
        split_idx = int(len(df) * train_ratio)
        train = df.iloc[:split_idx]
        test = df.iloc[split_idx:]
        
        # Define features and target
        self.features = [col for col in df.columns if col != target_col]
        
        X_train, y_train = train[self.features], train[target_col]
        self.X_test, self.y_test = test[self.features], test[target_col]
        
        # Initialize and train XGBoost
        self.model = xgb.XGBRegressor(
            n_estimators=1000,
            learning_rate=0.05,
            early_stopping_rounds=50,
            objective='reg:squarederror'
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (self.X_test, self.y_test)],
            verbose=False
        )
        
        # Predict and evaluate
        self.predictions = self.model.predict(self.X_test)
        mae = mean_absolute_error(self.y_test, self.predictions)
        print(f"Mean Absolute Error: {mae:.2f} people")
        
        return self
    
    def plot_actual_vs_predicted(self, start_time=None, end_time=None):
        """
        Plots the actual occupancy versus the model's predictions over time.
        Includes optional parameters to zoom in on a specific date range.
        
        Args:
            start_time (str, optional): Start date for zoomed view
            end_time (str, optional): End date for zoomed view
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if self.y_test is None or self.predictions is None:
            raise ValueError("Model not trained. Call train_and_evaluate() first.")
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Plot actuals
        ax.plot(self.y_test.index, self.y_test.values, label='Actual Occupancy', 
                color='#2E86AB', linewidth=2)
        
        # Plot predictions 
        ax.plot(self.y_test.index, self.predictions, label='Predicted Occupancy', 
                color='#F24236', linewidth=2, linestyle='--', alpha=0.8)
        
        # Apply zoom limits if provided
        if start_time:
            ax.set_xlim(left=pd.to_datetime(start_time))
        if end_time:
            ax.set_xlim(right=pd.to_datetime(end_time))
            
        # Formatting
        ax.set_title("XGBoost Forecasting: Actual vs. Predicted Occupancy", 
                     fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel("Date & Time", fontsize=11)
        ax.set_ylabel("Occupancy Count", fontsize=11)
        ax.legend(loc='upper right', frameon=True)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return fig
    
    def print_predictions(self):
        """
        Prints predictions alongside their corresponding timestamps.
        
        Displays the timestamp and predicted occupancy count for each 
        prediction in the test set in a formatted table.
        """
        if self.predictions is None:
            raise ValueError("Model not trained. Call train_and_evaluate() first.")
        
        # Create a DataFrame with timestamps and predictions
        results_df = pd.DataFrame({
            'Timestamp': self.y_test.index,
            'Predicted Occupancy': self.predictions
        })
        
        print("\n" + "="*60)
        print("PREDICTIONS WITH TIMESTAMPS")
        print("="*60)
        print(results_df.to_string(index=False))
        print("="*60 + "\n")