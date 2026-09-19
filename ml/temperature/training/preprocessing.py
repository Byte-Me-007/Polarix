"""
Causal Feature Preprocessing & Windowing for Temperature ML (Polarix SIH26060 - Person C).

Strictly prevents data leakage by fitting normalizers solely on the training partition.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch


FEATURE_COLS = [
    "temperature_c",
    "humidity_percent",
    "pressure_hpa",
    "wind_speed_mps",
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
    "is_bharati",
]

TARGET_COLS = [
    "target_temperature_1h_c",
    "target_temperature_6h_c",
    "target_temperature_24h_c",
]


class TemperatureFeatureScaler:
    """
    Standardizes environmental features and targets using statistics learned
    exclusively from the training chronological split.
    """

    def __init__(self) -> None:
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.feature_cols: List[str] = list(FEATURE_COLS)
        self.target_cols: List[str] = list(TARGET_COLS)
        self.is_fitted: bool = False

    def fit(self, df_train: pd.DataFrame) -> "TemperatureFeatureScaler":
        """Fits mean and std statistics strictly on the train partition."""
        df_processed = self._encode_station(df_train)

        # Scale continuous features
        continuous_features = ["temperature_c", "humidity_percent", "pressure_hpa", "wind_speed_mps"]
        for col in continuous_features:
            val = df_processed[col].to_numpy(dtype=np.float32)
            mean_val = float(np.mean(val))
            std_val = float(np.std(val))
            self.means[col] = mean_val
            self.stds[col] = std_val if std_val > 1e-6 else 1.0

        # Features with fixed bounds [-1, 1] or [0, 1] keep identity scaling (mean 0, std 1)
        identity_features = ["sin_hour", "cos_hour", "sin_day", "cos_day", "is_bharati"]
        for col in identity_features:
            self.means[col] = 0.0
            self.stds[col] = 1.0

        # Target scaling uses the temperature_c statistics to keep multi-horizon outputs on identical scale
        self.temp_mean = self.means["temperature_c"]
        self.temp_std = self.stds["temperature_c"]
        self.is_fitted = True
        return self

    def _encode_station(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adds binary station indicator column without mutating input."""
        df_out = df.copy()
        if "is_bharati" not in df_out.columns:
            df_out["is_bharati"] = (df_out["station_id"] == "BRT").astype(np.float32)
        return df_out

    def transform_features(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms feature matrix according to fitted statistics."""
        if not self.is_fitted:
            raise RuntimeError("TemperatureFeatureScaler must be fitted before transform.")

        df_processed = self._encode_station(df)
        matrix = np.zeros((len(df_processed), len(self.feature_cols)), dtype=np.float32)

        for idx, col in enumerate(self.feature_cols):
            val = df_processed[col].to_numpy(dtype=np.float32)
            matrix[:, idx] = (val - self.means[col]) / self.stds[col]

        return matrix

    def transform_targets(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms target vector using fitted temperature statistics."""
        if not self.is_fitted:
            raise RuntimeError("TemperatureFeatureScaler must be fitted before transform.")

        matrix = np.zeros((len(df), len(self.target_cols)), dtype=np.float32)
        for idx, col in enumerate(self.target_cols):
            val = df[col].to_numpy(dtype=np.float32)
            matrix[:, idx] = (val - self.temp_mean) / self.temp_std

        return matrix

    def inverse_transform_targets(self, targets_norm: np.ndarray) -> np.ndarray:
        """Denormalizes standardized predictions back into degrees Celsius."""
        if not self.is_fitted:
            raise RuntimeError("TemperatureFeatureScaler must be fitted before inverse transform.")

        return targets_norm * self.temp_std + self.temp_mean

    def save_json(self, filepath: Union[str, Path]) -> None:
        """Persists scaler configuration as machine-readable JSON."""
        state = {
            "is_fitted": self.is_fitted,
            "feature_cols": self.feature_cols,
            "target_cols": self.target_cols,
            "means": self.means,
            "stds": self.stds,
            "temp_mean": self.temp_mean,
            "temp_std": self.temp_std,
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> "TemperatureFeatureScaler":
        """Loads scaler from JSON file."""
        with open(filepath, "r") as f:
            state = json.load(f)

        scaler = cls()
        scaler.is_fitted = state["is_fitted"]
        scaler.feature_cols = state["feature_cols"]
        scaler.target_cols = state["target_cols"]
        scaler.means = {k: float(v) for k, v in state["means"].items()}
        scaler.stds = {k: float(v) for k, v in state["stds"].items()}
        scaler.temp_mean = float(state["temp_mean"])
        scaler.temp_std = float(state["temp_std"])
        return scaler


def build_causal_sequences(
    df: pd.DataFrame,
    scaler: TemperatureFeatureScaler,
    lookback: int = 24,
    has_targets: bool = True,
) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
    """
    Constructs causal sliding window tensors (batch_size, lookback, num_features)
    and optional target tensors (batch_size, 3).
    Ensures zero future information leakage into sequences.
    """
    X_mat = scaler.transform_features(df)
    n_samples = len(df) - lookback + 1

    if n_samples <= 0:
        raise ValueError(f"DataFrame length ({len(df)}) is shorter than lookback window ({lookback}).")

    # Build sequence windows
    X_seqs = np.zeros((n_samples, lookback, len(scaler.feature_cols)), dtype=np.float32)
    for i in range(n_samples):
        X_seqs[i] = X_mat[i : i + lookback]

    X_tensor = torch.tensor(X_seqs, dtype=torch.float32)

    if not has_targets:
        return X_tensor, None

    # Targets align with the last timestep of each window: index i + lookback - 1
    # Check if target values exist at these window endpoints
    target_mat = scaler.transform_targets(df)
    y_aligned = target_mat[lookback - 1 :]
    y_tensor = torch.tensor(y_aligned, dtype=torch.float32)

    # Filter out any windows where future target is NaN (e.g. at the very end of time-series)
    valid_mask = ~torch.isnan(y_tensor).any(dim=1)
    return X_tensor[valid_mask], y_tensor[valid_mask]
