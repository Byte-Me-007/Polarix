"""
Causal Benchmark Baselines for Environmental Forecasting (Polarix SIH26060 - Person C).

Implements:
1. Persistence Forecaster: Forecast equals the latest observed environmental values.
2. Recent Mean Forecaster: Forecast equals the moving average of the lookback window.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd


class PersistenceForecaster:
    """
    Causal baseline predicting that future values equal the latest observed value.
    y_hat(var, t+k) = var(t) for all k in {1h, 6h, 24h}
    """

    def __init__(self) -> None:
        self.name = "Persistence"

    def predict_window(self, window_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Given historical dataframe up to time t, predicts horizons [1h, 6h, 24h]."""
        if len(window_df) == 0:
            raise ValueError("Input dataframe cannot be empty.")
        latest = window_df.iloc[-1]
        return {
            "wind_speed_mps": {
                "1h": float(latest["wind_speed_mps"]),
                "6h": float(latest["wind_speed_mps"]),
                "24h": float(latest["wind_speed_mps"]),
            },
            "pressure_hpa": {
                "1h": float(latest["pressure_hpa"]),
                "6h": float(latest["pressure_hpa"]),
                "24h": float(latest["pressure_hpa"]),
            },
            "humidity_percent": {
                "1h": float(latest["humidity_percent"]),
                "6h": float(latest["humidity_percent"]),
                "24h": float(latest["humidity_percent"]),
            },
        }

    def predict_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Computes persistence predictions for a continuous dataframe.
        Returns array of shape (N, 9) where columns match TARGET_COLS.
        """
        w = df["wind_speed_mps"].to_numpy(dtype=np.float32)
        p = df["pressure_hpa"].to_numpy(dtype=np.float32)
        h = df["humidity_percent"].to_numpy(dtype=np.float32)

        return np.column_stack([w, w, w, p, p, p, h, h, h])


class RecentMeanForecaster:
    """
    Causal baseline predicting that future values equal the moving average over the lookback window.
    """

    def __init__(self, window_size: int = 24) -> None:
        self.window_size = window_size
        self.name = f"RecentMean_{window_size}h"

    def predict_window(self, window_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Given historical dataframe up to time t, predicts horizons [1h, 6h, 24h]."""
        if len(window_df) == 0:
            raise ValueError("Input dataframe cannot be empty.")
        recent = window_df.iloc[-self.window_size :] if len(window_df) >= self.window_size else window_df
        return {
            "wind_speed_mps": {
                "1h": float(recent["wind_speed_mps"].mean()),
                "6h": float(recent["wind_speed_mps"].mean()),
                "24h": float(recent["wind_speed_mps"].mean()),
            },
            "pressure_hpa": {
                "1h": float(recent["pressure_hpa"].mean()),
                "6h": float(recent["pressure_hpa"].mean()),
                "24h": float(recent["pressure_hpa"].mean()),
            },
            "humidity_percent": {
                "1h": float(recent["humidity_percent"].mean()),
                "6h": float(recent["humidity_percent"].mean()),
                "24h": float(recent["humidity_percent"].mean()),
            },
        }

    def predict_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Computes rolling mean predictions for a continuous dataframe.
        Returns array of shape (N, 9) where columns match TARGET_COLS.
        """
        w_m = df["wind_speed_mps"].rolling(window=self.window_size, min_periods=1).mean().to_numpy(dtype=np.float32)
        p_m = df["pressure_hpa"].rolling(window=self.window_size, min_periods=1).mean().to_numpy(dtype=np.float32)
        h_m = df["humidity_percent"].rolling(window=self.window_size, min_periods=1).mean().to_numpy(dtype=np.float32)

        return np.column_stack([w_m, w_m, w_m, p_m, p_m, p_m, h_m, h_m, h_m])
