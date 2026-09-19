"""
Production-Ready Inference Forecaster for Polarix Energy Microgrid (SIH26060).

Provides:
1. Unified inference engine loading frozen PyTorch weights, config, and scaler parameters.
2. Stepwise single-sequence prediction and batch DataFrame forecasting.
3. Input validation, shape assertions, and insufficient history handling (< 24h).
4. Deterministic inverse scaling back to physical microgrid units (kW, %, kWh).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch

from ml.energy.models.energy_lstm import EnergyLSTM, EnergyModelConfig
from ml.energy.training.preprocessing import (
    EnergyScalerParams,
    extract_features_and_targets,
    inverse_transform_targets,
    transform_features,
)


@dataclass
class EnergyPrediction:
    """Structured container for multi-horizon energy forecasts."""

    station_id: str
    prediction_timestamp: str
    target_power_demand_1h_kw: float
    target_battery_soc_1h_percent: float
    target_energy_demand_6h_kwh: float
    target_energy_demand_24h_kwh: float
    model_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnergyForecaster:
    """Inference engine for Polarix Energy ML forecasting baseline."""

    def __init__(
        self,
        model_dir: Union[str, Path] = Path("ml/energy/models"),
        model_name: str = "energy_lstm_baseline",
    ):
        self.model_dir = Path(model_dir)
        self.model_name = model_name

        self.model_path = self.model_dir / f"{model_name}.pt"
        self.config_path = self.model_dir / f"{model_name}_config.json"
        self.scaler_path = self.model_dir / f"{model_name}_scaler.json"

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights missing: {self.model_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config missing: {self.config_path}")
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler parameters missing: {self.scaler_path}")

        # Load config and scaler
        self.config = EnergyModelConfig.load(self.config_path)
        self.scaler = EnergyScalerParams.load(self.scaler_path)

        # Initialize model and load weights
        self.model = EnergyLSTM(self.config)
        state_dict = torch.load(self.model_path, map_location=torch.device("cpu"), weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def predict_window(self, window_df: pd.DataFrame) -> EnergyPrediction:
        """
        Generate a multi-horizon forecast given an input dataframe containing >= lookback history.
        Uses exactly the last lookback (24) rows.
        """
        if len(window_df) < self.config.lookback:
            raise ValueError(
                f"Insufficient historical context: provided {len(window_df)} rows, "
                f"required minimum lookback is {self.config.lookback} hours."
            )

        # Take last lookback rows
        recent_df = window_df.iloc[-self.config.lookback :].copy()
        station_id = str(recent_df["station_id"].iloc[-1])
        ts_now = str(recent_df["timestamp"].iloc[-1])

        X_df, _ = extract_features_and_targets(recent_df)
        X_scaled = transform_features(X_df, self.scaler)

        # Shape: (1, lookback, input_dim)
        x_tensor = torch.tensor(X_scaled[np.newaxis, :, :], dtype=torch.float32)

        with torch.no_grad():
            y_norm = self.model(x_tensor).numpy()

        y_raw = inverse_transform_targets(y_norm, self.scaler)[0]

        return EnergyPrediction(
            station_id=station_id,
            prediction_timestamp=ts_now,
            target_power_demand_1h_kw=round(float(y_raw[0]), 2),
            target_battery_soc_1h_percent=round(float(np.clip(y_raw[1], 0.0, 100.0)), 2),
            target_energy_demand_6h_kwh=round(float(max(0.0, y_raw[2])), 2),
            target_energy_demand_24h_kwh=round(float(max(0.0, y_raw[3])), 2),
            model_version=self.config.model_name,
        )

    def predict_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate continuous sliding-window predictions over an entire station timeline.
        """
        if len(df) < self.config.lookback:
            raise ValueError(f"Dataframe length {len(df)} is less than required lookback {self.config.lookback}")

        X_df, _ = extract_features_and_targets(df)
        X_scaled = transform_features(X_df, self.scaler)

        N = len(df)
        sequences = []
        valid_indices = []

        for i in range(self.config.lookback - 1, N):
            seq = X_scaled[i - self.config.lookback + 1 : i + 1]
            sequences.append(seq)
            valid_indices.append(i)

        x_tensor = torch.tensor(np.array(sequences, dtype=np.float32), dtype=torch.float32)
        with torch.no_grad():
            preds_norm = self.model(x_tensor).numpy()

        preds_raw = inverse_transform_targets(preds_norm, self.scaler)

        pred_df = pd.DataFrame(index=valid_indices)
        pred_df["timestamp"] = df["timestamp"].iloc[valid_indices].values
        pred_df["station_id"] = df["station_id"].iloc[valid_indices].values
        pred_df["pred_power_demand_1h_kw"] = np.round(preds_raw[:, 0], 2)
        pred_df["pred_battery_soc_1h_percent"] = np.round(np.clip(preds_raw[:, 1], 0.0, 100.0), 2)
        pred_df["pred_energy_demand_6h_kwh"] = np.round(np.maximum(0.0, preds_raw[:, 2]), 2)
        pred_df["pred_energy_demand_24h_kwh"] = np.round(np.maximum(0.0, preds_raw[:, 3]), 2)

        return pred_df
