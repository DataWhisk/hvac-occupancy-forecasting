import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import matplotlib.pyplot as plt

def prepare_data(df, time_col='interval_begin_time', count_col='count'):
    """Resamples raw interval data into strict 1-hour blocks."""
    df = df.copy()
    
    # Ensure datetime format and set as index
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    
    # Resample to 1-hour intervals, filling missing gaps with 0
    hourly_df = df[count_col].resample('1h').sum().fillna(0).to_frame(name='occupancy')
    return hourly_df

def create_features(df):
    """Generates time-based and lag features for the XGBoost model."""
    df = df.copy()
    
    # Time-based features
    df['hour'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Lag features (past occupancy)
    df['occ_lag_1h'] = df['occupancy'].shift(1)
    df['occ_lag_24h'] = df['occupancy'].shift(24)
    
    # Drop rows with NaN values created by shifting
    return df.dropna()

def train_and_evaluate(df, target_col='occupancy', train_ratio=0.8):
    """Splits data chronologically, trains the model, and generates predictions."""
    # Chronological split
    split_idx = int(len(df) * train_ratio)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    # Define features and target
    features = [col for col in df.columns if col != target_col]
    
    X_train, y_train = train[features], train[target_col]
    X_test, y_test = test[features], test[target_col]
    
    # Initialize and train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=1000,
        learning_rate=0.05,
        early_stopping_rounds=50,
        objective='reg:squarederror'
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False
    )
    
    # Predict and evaluate
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f"Mean Absolute Error: {mae:.2f} people")
    
    return model, X_test, y_test, predictions

def plot_actual_vs_predicted(y_test, predictions):
    """Plots the actual occupancy versus the model's predictions over time."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot actuals
    ax.plot(y_test.index, y_test.values, label='Actual Occupancy', color='#2E86AB', linewidth=2)
    
    # Plot predictions (using a dashed line and distinct color)
    ax.plot(y_test.index, predictions, label='Predicted Occupancy', color='#F24236', linewidth=2, linestyle='--', alpha=0.8)
    
    # Formatting
    ax.set_title("XGBoost Forecasting: Actual vs. Predicted Occupancy", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Date & Time", fontsize=11)
    ax.set_ylabel("Occupancy Count", fontsize=11)
    ax.legend(loc='upper right', frameon=True)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig