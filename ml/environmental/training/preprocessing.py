"""
Causal Feature Preprocessing & Windowing for Environmental ML (Polarix SIH26060 - Person C).

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
    "wind_speed_mps",
    "pressure_hpa",
    "humidity_percent",
    "temperature_c",
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
    "is_bharati",
]

TARGET_COLS = [
    "target_wind_speed_1h_mps",
    "target_wind_speed_6h_mps",
    "target_wind_speed_24h_mps",
    "target_pressure_1h_hpa",
    "target_pressure_6h_hpa",
    "target_pressure_24h_hpa",
    "target_humidity_1h_percent",
    "target_humidity_6h_percent",
    "target_humidity_24h_percent",
]


class EnvironmentalFeatureScaler:
    """
    Standardizes multivariate environmental features and targets using statistics learned
    exclusively from the training chronological split.
    """

    def __init__(self) -> None:
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.feature_cols: List[str] = list(FEATURE_COLS)
        self.target_cols: List[str] = list(TARGET_COLS)
        self.is_fitted: bool = False

    def fit(self, df_train: pd.DataFrame) -> "EnvironmentalFeatureScaler":
        """Fits mean and std statistics strictly on the train partition."""
        df_processed = self._encode_station(df_train)

        # Scale continuous features
        continuous_features = ["wind_speed_mps", "pressure_hpa", "humidity_percent", "temperature_c"]
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

        # Target statistics align with their source continuous variables
        target_map = {
            "target_wind_speed_1h_mps": "wind_speed_mps",
            "target_wind_speed_6h_mps": "wind_speed_mps",
            "target_wind_speed_24h_mps": "wind_speed_mps",
            "target_pressure_1h_hpa": "pressure_hpa",
            "target_pressure_6h_hpa": "pressure_hpa",
            "target_pressure_24h_hpa": "pressure_hpa",
            "target_humidity_1h_percent": "humidity_percent",
            "target_humidity_6h_percent": "humidity_percent",
            "target_humidity_24h_percent": "humidity_percent",
        }
        self.target_means: Dict[str, float] = {t: self.means[v] for t, v in target_map.items()}
        self.target_stds: Dict[str, float] = {t: self.stds[v] for t, v in target_map.items()}

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
            raise RuntimeError("EnvironmentalFeatureScaler must be fitted before transform.")

        df_processed = self._encode_station(df)
        matrix = np.zeros((len(df_processed), len(self.feature_cols)), dtype=np.float32)

        for idx, col in enumerate(self.feature_cols):
            val = df_processed[col].to_numpy(dtype=np.float32)
            matrix[:, idx] = (val - self.means[col]) / self.stds[col]

        return matrix

    def transform_targets(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms target vector using fitted statistics."""
        if not self.is_fitted:
            raise RuntimeError("EnvironmentalFeatureScaler must be fitted before transform.")

        matrix = np.zeros((len(df), len(self.target_cols)), dtype=np.float32)
        for idx, col in enumerate(self.target_cols):
            val = df[col].to_numpy(dtype=np.float32)
            matrix[:, idx] = (val - self.target_means[col]) / self.target_stds[col]

        return matrix

    def inverse_transform_targets(self, targets_norm: np.ndarray) -> np.ndarray:
        """Denormalizes standardized predictions back into physical units."""
        if not self.is_fitted:
            raise RuntimeError("EnvironmentalFeatureScaler must be fitted before inverse transform.")

        targets_denorm = np.zeros_like(targets_norm, dtype=np.float32)
        for idx, col in enumerate(self.target_cols):
            targets_denorm[:, idx] = targets_norm[:, idx] * self.target_stds[col] + self.target_means[col]

        return targets_denorm

    def save_json(self, filepath: Union[str, Path]) -> None:
        """Persists scaler configuration as machine-readable JSON."""
        state = {
            "is_fitted": self.is_fitted,
            "feature_cols": self.feature_cols,
            "target_cols": self.target_cols,
            "means": self.means,
            "stds": self.stds,
            "target_means": self.target_means,
            "target_stds": self.target_stds,
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> "EnvironmentalFeatureScaler":
        """Loads scaler from JSON file."""
        with open(filepath, "r") as f:
            state = json.load(f)

        scaler = cls()
        scaler.is_fitted = state["is_fitted"]
        scaler.feature_cols = state["feature_cols"]
        scaler.target_cols = state["target_cols"]
        scaler.means = {k: float(v) for k, v in state["means"].items()}
        scaler.stds = {k: float(v) for k, v in state["stds"].items()}
        scaler.target_means = {k: float(v) for k, v in state["target_means"].items()}
        scaler.target_stds = {k: float(v) for k, v in state["target_stds"].items()}
        return scaler


def build_causal_sequences(
    df: pd.DataFrame,
    scaler: EnvironmentalFeatureScaler,
    lookback: int = 24,
    has_targets: bool = True,
) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
    """
    Constructs causal sliding window tensors (batch_size, lookback, num_features)
    and optional target tensors (batch_size, 9).
    Ensures zero future information leakage into sequences.
    """
    X_mat = scaler.transform_features(df)
    n_samples = len(df) - lookback + 1

    if n_samples <= 0:
        raise ValueError(f"DataFrame length ({len(df)}) is shorter than lookback window ({lookback}).")

    X_seqs = np.zeros((n_samples, lookback, len(scaler.feature_cols)), dtype=np.float32)
    for i in range(n_samples):
        X_seqs[i] = X_mat[i : i + lookback]

    X_tensor = torch.tensor(X_seqs, dtype=torch.float32)

    if not has_targets:
        return X_tensor, None

    target_mat = scaler.transform_targets(df)
    y_aligned = target_mat[lookback - 1 :]
    y_tensor = torch.tensor(y_aligned, dtype=torch.float32)

    valid_mask = ~torch.isnan(y_tensor).any(dim=1)
    return X_tensor[valid_mask], y_tensor[valid_mask]
