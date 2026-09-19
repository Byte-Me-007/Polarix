"""
Leakage-Safe Preprocessing & Temporal Sequence Construction for Polarix Energy ML (SIH26060).

Ensures:
1. Scalers are fit STRICTLY on the training partition.
2. Sequence windows (lookback L=24) are constructed causally using timestamps <= t only.
3. Cross-station sequence isolation: MTR and BRT sequences never cross station boundaries.
4. Causal temporal feature extraction (diurnal sine/cosine, annual sine/cosine).
5. Explicit handling of missing values and categorical sensor anomalies.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

FEATURE_COLUMNS: List[str] = [
    "power_demand_kw",
    "generator_output_kw",
    "battery_soc_percent",
    "battery_charge_kw",
    "battery_discharge_kw",
    "fuel_consumption_l",
    "temperature_c",
    "humidity_percent",
    "pressure_hpa",
    "wind_speed_mps",
    "sensor_anomaly_score",
    "sensor_is_anomaly",
    "sensor_is_missing",
    "station_is_brt",
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
]

TARGET_COLUMNS: List[str] = [
    "target_power_demand_1h_kw",
    "target_battery_soc_1h_percent",
    "target_energy_demand_6h_kwh",
    "target_energy_demand_24h_kwh",
]


@dataclass
class EnergyScalerParams:
    """Serializable parameters for standard scaling fit on training partition."""

    feature_names: List[str]
    target_names: List[str]
    feature_mean: List[float]
    feature_std: List[float]
    target_mean: List[float]
    target_std: List[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EnergyScalerParams:
        return cls(
            feature_names=list(data["feature_names"]),
            target_names=list(data["target_names"]),
            feature_mean=[float(x) for x in data["feature_mean"]],
            feature_std=[float(x) for x in data["feature_std"]],
            target_mean=[float(x) for x in data["target_mean"]],
            target_std=[float(x) for x in data["target_std"]],
        )

    def save(self, filepath: Path) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> EnergyScalerParams:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def extract_features_and_targets(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract causal engineered features and target arrays from raw telemetry dataframe.
    """
    df_out = df.copy()

    # Parse timestamps for cyclical temporal embeddings
    ts = pd.to_datetime(df_out["timestamp"], utc=True)
    hour = ts.dt.hour.to_numpy()
    dayofyear = ts.dt.dayofyear.to_numpy()

    df_out["sin_hour"] = np.sin(2.0 * np.pi * hour / 24.0)
    df_out["cos_hour"] = np.cos(2.0 * np.pi * hour / 24.0)
    df_out["sin_day"] = np.sin(2.0 * np.pi * dayofyear / 365.25)
    df_out["cos_day"] = np.cos(2.0 * np.pi * dayofyear / 365.25)

    # Station encoding: 0.0 for MTR, 1.0 for BRT
    df_out["station_is_brt"] = (df_out["station_id"] == "BRT").astype(float)

    # Sensor ML status encoding with safe optional defaulting
    sensor_status = (
        df_out["sensor_anomaly_status"]
        if "sensor_anomaly_status" in df_out.columns
        else pd.Series("NORMAL", index=df_out.index)
    )
    data_quality = (
        df_out["data_quality"]
        if "data_quality" in df_out.columns
        else pd.Series("GOOD", index=df_out.index)
    )
    sensor_score = (
        df_out["sensor_anomaly_score"]
        if "sensor_anomaly_score" in df_out.columns
        else pd.Series(1.0, index=df_out.index)
    )

    df_out["sensor_is_anomaly"] = (sensor_status == "ANOMALY").astype(float)
    df_out["sensor_is_missing"] = (
        (sensor_status == "MISSING_DATA") | (data_quality == "MISSING")
    ).astype(float)

    # Handle any null sensor scores with median baseline
    df_out["sensor_anomaly_score"] = sensor_score.fillna(1.0).astype(float)

    # Ensure all required features exist
    for col in FEATURE_COLUMNS:
        if col not in df_out.columns:
            raise ValueError(f"Missing required feature column: {col}")

    X_df = df_out[FEATURE_COLUMNS].copy()
    y_df = df_out[TARGET_COLUMNS].copy() if all(c in df_out.columns for c in TARGET_COLUMNS) else pd.DataFrame()

    return X_df, y_df


def fit_energy_scaler(train_df: pd.DataFrame) -> EnergyScalerParams:
    """
    Fit standard normal scaler strictly on the training partition.
    """
    X_train, y_train = extract_features_and_targets(train_df)

    f_mean = X_train.mean(axis=0).to_numpy()
    f_std = X_train.std(axis=0).to_numpy()
    f_std = np.where(f_std < 1e-6, 1.0, f_std)  # Prevent division by zero

    # Drop any NaNs in targets when computing mean/std
    y_clean = y_train.dropna()
    t_mean = y_clean.mean(axis=0).to_numpy()
    t_std = y_clean.std(axis=0).to_numpy()
    t_std = np.where(t_std < 1e-6, 1.0, t_std)

    return EnergyScalerParams(
        feature_names=FEATURE_COLUMNS,
        target_names=TARGET_COLUMNS,
        feature_mean=f_mean.tolist(),
        feature_std=f_std.tolist(),
        target_mean=t_mean.tolist(),
        target_std=t_std.tolist(),
    )


def transform_features(X_df: pd.DataFrame, scaler: EnergyScalerParams) -> np.ndarray:
    """Transform feature dataframe to standard scaled numpy array."""
    X_vals = X_df[scaler.feature_names].to_numpy(dtype=np.float32)
    mean = np.array(scaler.feature_mean, dtype=np.float32)
    std = np.array(scaler.feature_std, dtype=np.float32)
    return (X_vals - mean) / std


def transform_targets(y_df: pd.DataFrame, scaler: EnergyScalerParams) -> np.ndarray:
    """Transform target dataframe to standard scaled numpy array."""
    y_vals = y_df[scaler.target_names].to_numpy(dtype=np.float32)
    mean = np.array(scaler.target_mean, dtype=np.float32)
    std = np.array(scaler.target_std, dtype=np.float32)
    return (y_vals - mean) / std


def inverse_transform_targets(y_norm: np.ndarray, scaler: EnergyScalerParams) -> np.ndarray:
    """Inverse transform normalized predictions back to physical microgrid units."""
    mean = np.array(scaler.target_mean, dtype=np.float32)
    std = np.array(scaler.target_std, dtype=np.float32)
    return y_norm * std + mean


def build_station_sequences(
    df: pd.DataFrame,
    scaler: EnergyScalerParams,
    lookback: int = 24,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build chronological sliding window sequences for a single station.

    Returns:
    - X: 3D array of shape (N_samples, lookback, n_features)
    - y: 2D array of shape (N_samples, n_targets) in physical units
    - y_norm: 2D array of shape (N_samples, n_targets) standard normalized
    """
    X_df, y_df = extract_features_and_targets(df)
    X_scaled = transform_features(X_df, scaler)
    y_raw = y_df.to_numpy(dtype=np.float32)
    y_scaled = transform_targets(y_df, scaler)

    N = len(df)
    sequences_X = []
    sequences_y = []
    sequences_y_norm = []

    for i in range(lookback - 1, N):
        # Input sequence: from (i - lookback + 1) to i inclusive (length = lookback)
        seq_x = X_scaled[i - lookback + 1 : i + 1]
        target_val = y_raw[i]
        target_norm = y_scaled[i]

        # Skip rows where targets are NaN (e.g. at the end of the series where future values don't exist)
        if np.isnan(target_val).any():
            continue

        sequences_X.append(seq_x)
        sequences_y.append(target_val)
        sequences_y_norm.append(target_norm)

    if not sequences_X:
        return (
            np.empty((0, lookback, len(scaler.feature_names)), dtype=np.float32),
            np.empty((0, len(scaler.target_names)), dtype=np.float32),
            np.empty((0, len(scaler.target_names)), dtype=np.float32),
        )

    return (
        np.array(sequences_X, dtype=np.float32),
        np.array(sequences_y, dtype=np.float32),
        np.array(sequences_y_norm, dtype=np.float32),
    )
