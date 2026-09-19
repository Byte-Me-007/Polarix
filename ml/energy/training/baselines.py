"""
Classical Time-Series Forecasting Baselines for Polarix Energy Microgrid (SIH26060).

Provides non-neural benchmarks against which all ML models must be evaluated:
1. Persistence Forecaster (Random Walk / Naive):
   - 1h Ahead Demand: P(t)
   - 1h Ahead SoC: SoC(t)
   - 6h Ahead Energy: 6 * P(t)
   - 24h Ahead Energy: 24 * P(t)
2. Seasonal / 24-Hour Lag Forecaster (Diurnal Cyclical):
   - 1h Ahead Demand: P(t - 23) (same hour of preceding day)
   - 1h Ahead SoC: SoC(t - 23)
   - 6h Ahead Energy: sum(P(t - 24 + k)) for k in 1..6
   - 24h Ahead Energy: sum(P(t - k)) for k in 0..23 (preceding 24h actual energy)
3. Moving Average Forecaster (Causal Rolling Window):
   - Uses historical backward-looking rolling windows only.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


class PersistenceForecaster:
    """Naive persistence baseline assuming future state equals current state."""

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        preds = pd.DataFrame(index=df.index)
        preds["pred_power_demand_1h_kw"] = df["power_demand_kw"]
        preds["pred_battery_soc_1h_percent"] = df["battery_soc_percent"]
        preds["pred_energy_demand_6h_kwh"] = df["power_demand_kw"] * 6.0
        preds["pred_energy_demand_24h_kwh"] = df["power_demand_kw"] * 24.0
        return preds


class SeasonalLagForecaster:
    """Diurnal 24-hour lag baseline using prior day's corresponding operational state."""

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        preds = pd.DataFrame(index=df.index)
        # Power demand 24h lag aligned for t+1
        preds["pred_power_demand_1h_kw"] = df["power_demand_kw"].shift(23)
        preds["pred_battery_soc_1h_percent"] = df["battery_soc_percent"].shift(23)

        # 6h forward energy approximated by prior day's 6h window
        p_roll_6h = df["power_demand_kw"].rolling(window=6, min_periods=6).sum()
        preds["pred_energy_demand_6h_kwh"] = p_roll_6h.shift(18)

        # 24h forward energy approximated by prior 24h total energy
        p_roll_24h = df["power_demand_kw"].rolling(window=24, min_periods=24).sum()
        preds["pred_energy_demand_24h_kwh"] = p_roll_24h

        # Backfill initial lookback rows with persistence
        p_base = PersistenceForecaster().predict(df)
        for col in preds.columns:
            preds[col] = preds[col].fillna(p_base[col])

        return preds


class MovingAverageForecaster:
    """Moving average baseline using backward historical windows."""

    def __init__(self, short_window: int = 6, long_window: int = 24):
        self.short_window = short_window
        self.long_window = long_window

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        preds = pd.DataFrame(index=df.index)
        ma_short = df["power_demand_kw"].rolling(window=self.short_window, min_periods=1).mean()
        ma_long = df["power_demand_kw"].rolling(window=self.long_window, min_periods=1).mean()
        ma_soc = df["battery_soc_percent"].rolling(window=self.short_window, min_periods=1).mean()

        preds["pred_power_demand_1h_kw"] = ma_short
        preds["pred_battery_soc_1h_percent"] = ma_soc
        preds["pred_energy_demand_6h_kwh"] = ma_short * 6.0
        preds["pred_energy_demand_24h_kwh"] = ma_long * 24.0
        return preds


def compute_regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:
    """
    Compute MAE, RMSE, R2, and safe sMAPE between true and predicted arrays.
    """
    # Filter out NaNs
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not np.any(mask):
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "smape": 0.0}

    t = y_true[mask]
    p = y_pred[mask]

    mae = float(np.mean(np.abs(p - t)))
    rmse = float(np.sqrt(np.mean((p - t) ** 2)))

    ss_res = np.sum((t - p) ** 2)
    ss_tot = np.sum((t - np.mean(t)) ** 2)
    r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))

    # Symmetric MAPE (sMAPE): 200 * |p - t| / (|t| + |p| + eps)
    denom = np.abs(t) + np.abs(p) + 1e-6
    smape = float(np.mean(200.0 * np.abs(p - t) / denom))

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "smape": round(smape, 4),
    }
