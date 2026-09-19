"""
Causal Benchmark Baselines for Temperature Forecasting (Polarix SIH26060 - Person C).

Implements:
1. Persistence Forecaster: Forecast equals the most recent observed temperature.
2. Recent Mean Forecaster: Forecast equals the moving average of the lookback window.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


class PersistenceForecaster:
    """
    Causal baseline predicting that future temperature equals the latest observed temperature.
    y_hat(t + 1h) = temperature(t)
    y_hat(t + 6h) = temperature(t)
    y_hat(t + 24h) = temperature(t)
    """

    def __init__(self) -> None:
        self.name = "Persistence"

    def predict_window(self, temp_series: Union[List[float], np.ndarray]) -> Dict[str, float]:
        """Given historical temperatures up to time t, predicts horizons [1h, 6h, 24h]."""
        if len(temp_series) == 0:
            raise ValueError("Input series cannot be empty.")
        latest_val = float(temp_series[-1])
        return {
            "temperature_1h_c": latest_val,
            "temperature_6h_c": latest_val,
            "temperature_24h_c": latest_val,
        }

    def predict_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Computes persistence predictions for a continuous dataframe.
        Returns array of shape (N, 3) where columns are [1h, 6h, 24h].
        """
        temps = df["temperature_c"].to_numpy(dtype=np.float32)
        return np.column_stack([temps, temps, temps])


class RecentMeanForecaster:
    """
    Causal baseline predicting that future temperature equals the mean of the recent lookback window.
    y_hat(t + k) = (1/W) * sum_{i=0}^{W-1} temperature(t - i)
    """

    def __init__(self, window_size: int = 24) -> None:
        self.window_size = window_size
        self.name = f"RecentMean_{window_size}h"

    def predict_window(self, temp_series: Union[List[float], np.ndarray]) -> Dict[str, float]:
        """Given historical temperatures up to time t, predicts horizons [1h, 6h, 24h]."""
        if len(temp_series) == 0:
            raise ValueError("Input series cannot be empty.")
        window = temp_series[-self.window_size :] if len(temp_series) >= self.window_size else temp_series
        mean_val = float(np.mean(window))
        return {
            "temperature_1h_c": mean_val,
            "temperature_6h_c": mean_val,
            "temperature_24h_c": mean_val,
        }

    def predict_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Computes rolling mean predictions for a continuous dataframe.
        Returns array of shape (N, 3) where columns are [1h, 6h, 24h].
        """
        rolling_mean = df["temperature_c"].rolling(window=self.window_size, min_periods=1).mean().to_numpy(dtype=np.float32)
        return np.column_stack([rolling_mean, rolling_mean, rolling_mean])
