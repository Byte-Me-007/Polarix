"""
Sequence Preparation & Normalization Pipeline for Polarix Bharati LSTM Autoencoder (SIH26060 - Person C).

Features:
- Chronological per-sensor 70/15/15 split.
- Strict leakage prevention: Normalization parameters (mean, std) computed strictly from NORMAL training records.
- Sliding window sequence creation (seq_len=30).
- Explicit missing / dropout handling: NaN sequences are never used for training.
- Complete metadata tracking (station_id='BRT', sensor_id, timestamp, is_anomaly, anomaly_type).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

STATION_ID = "BRT"


@dataclass
class BharatiSensorScaler:
    sensor_id: str
    mean: float
    std: float
    unit: str

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / self.std

    def inverse_transform(self, normalized: np.ndarray) -> np.ndarray:
        return (normalized * self.std) + self.mean

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "mean": float(self.mean),
            "std": float(self.std),
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BharatiSensorScaler":
        return cls(
            sensor_id=data["sensor_id"],
            mean=float(data["mean"]),
            std=float(data["std"]),
            unit=data.get("unit", ""),
        )


class BharatiSequenceDataset(Dataset):
    """PyTorch Dataset for Bharati time-series sequences."""

    def __init__(self, sequences: np.ndarray) -> None:
        # sequences: (N, seq_len, 1) float32
        self.sequences = torch.from_numpy(sequences).float()

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.sequences[idx]


def fit_bharati_sensor_scalers(
    train_df: pd.DataFrame, min_std: float = 1e-6
) -> Dict[str, BharatiSensorScaler]:
    """
    Compute normalization parameters (mean, std) ONLY from NORMAL training records for Bharati.

    Parameters:
    -----------
    train_df : pd.DataFrame
        Training partition of Bharati telemetry data.
    min_std : float
        Numerical epsilon to avoid divide-by-zero on low variance sensors.

    Returns:
    --------
    Dict[str, BharatiSensorScaler]: Scaler mapping per sensor_id.
    """
    scalers = {}
    for sensor_id, group in train_df.groupby("sensor_id"):
        if "is_anomaly" in group.columns:
            normal_records = group[(group["is_anomaly"] == 0) & (group["value"].notna())]
        else:
            normal_records = group[group["value"].notna()]

        vals = normal_records["value"].to_numpy(dtype=float)
        if len(vals) == 0:
            mean_val = 0.0
            std_val = 1.0
        else:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 1.0
            if std_val < min_std or np.isnan(std_val):
                std_val = min_std

        unit = str(group["unit"].iloc[0]) if "unit" in group.columns and len(group) > 0 else ""
        scalers[sensor_id] = BharatiSensorScaler(
            sensor_id=sensor_id,
            mean=mean_val,
            std=std_val,
            unit=unit,
        )
    return scalers


def save_bharati_scalers(scalers: Dict[str, BharatiSensorScaler], output_path: Path) -> None:
    """Persist scalers to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v.to_dict() for k, v in scalers.items()}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_bharati_scalers(input_path: Path) -> Dict[str, BharatiSensorScaler]:
    """Load scalers from a JSON file."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: BharatiSensorScaler.from_dict(v) for k, v in data.items()}


def extract_sliding_windows(
    sensor_df: pd.DataFrame,
    scaler: BharatiSensorScaler,
    seq_len: int = 30,
    normal_only: bool = False,
    split_name: str = "train",
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Generate sliding windows for a single Bharati sensor.

    Parameters:
    -----------
    sensor_df : pd.DataFrame
        Chronologically sorted telemetry for a single sensor.
    scaler : BharatiSensorScaler
        Scaler fitted on training data.
    seq_len : int
        Window length in time steps.
    normal_only : bool
        If True, only windows where ALL points are normal (is_anomaly == 0, not null) are kept.
    split_name : str
        Partition identifier ('train', 'val', 'test').

    Returns:
    --------
    Tuple[np.ndarray, List[Dict]]:
        - Array of shape (M, seq_len, 1) containing normalized values.
        - Metadata list of length M corresponding to each window.
    """
    values = sensor_df["value"].to_numpy(dtype=float)
    timestamps = sensor_df["timestamp"].tolist()
    is_anom = (
        sensor_df["is_anomaly"].to_numpy(dtype=int)
        if "is_anomaly" in sensor_df.columns
        else np.zeros(len(sensor_df), dtype=int)
    )
    anom_types = (
        sensor_df["anomaly_type"].tolist()
        if "anomaly_type" in sensor_df.columns
        else ["NORMAL"] * len(sensor_df)
    )
    station_id = (
        str(sensor_df["station_id"].iloc[0])
        if "station_id" in sensor_df.columns and len(sensor_df) > 0
        else STATION_ID
    )
    sensor_id = scaler.sensor_id

    sequences = []
    metadata = []

    n = len(values)
    for i in range(n - seq_len + 1):
        window_vals = values[i : i + seq_len]
        window_anom = is_anom[i : i + seq_len]

        # Check for missing / NaN in window
        if np.isnan(window_vals).any():
            continue

        if normal_only:
            if np.any(window_anom != 0):
                continue

        norm_window = scaler.transform(window_vals)

        target_idx = i + seq_len - 1
        seq_meta = {
            "station_id": station_id,
            "sensor_id": sensor_id,
            "timestamp": timestamps[target_idx],
            "target_value": float(values[target_idx]),
            "is_anomaly": int(is_anom[target_idx]),
            "anomaly_type": anom_types[target_idx],
            "any_anomaly_in_window": int(np.any(window_anom != 0)),
            "split": split_name,
        }

        sequences.append(norm_window)
        metadata.append(seq_meta)

    if len(sequences) == 0:
        return np.empty((0, seq_len, 1), dtype=np.float32), []

    seq_arr = np.array(sequences, dtype=np.float32)[:, :, np.newaxis]
    return seq_arr, metadata


def prepare_bharati_datasets(
    csv_path: str = "ml/data/bharati_synthetic_telemetry.csv",
    seq_len: int = 30,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Dict[str, Any]:
    """
    Complete dataset preparation pipeline for Bharati.

    - Chronologically partitions per sensor: 70% train, 15% val, 15% test.
    - Fits scalers strictly on NORMAL training records.
    - Extracts training sequences (normal only).
    - Extracts validation & test sequences (all valid windows for evaluation).
    """
    df = pd.read_csv(csv_path)

    # Sort chronologically per sensor
    try:
        df["_parsed_ts"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
    except Exception:
        try:
            df["_parsed_ts"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
        except Exception:
            try:
                df["_parsed_ts"] = pd.to_datetime(df["timestamp"], utc=True)
            except Exception:
                df["_parsed_ts"] = np.arange(len(df))
    df.sort_values(by=["sensor_id", "_parsed_ts"], inplace=True)
    df.drop(columns=["_parsed_ts"], inplace=True)

    train_subsets = []
    val_subsets = []
    test_subsets = []

    for sensor_id, group in df.groupby("sensor_id", sort=False):
        n_sensor = len(group)
        n_train = int(n_sensor * train_ratio)
        n_val = int(n_sensor * val_ratio)

        train_subsets.append(group.iloc[:n_train])
        val_subsets.append(group.iloc[n_train : n_train + n_val])
        test_subsets.append(group.iloc[n_train + n_val :])

    train_df = pd.concat(train_subsets, ignore_index=True)
    val_df = pd.concat(val_subsets, ignore_index=True)
    test_df = pd.concat(test_subsets, ignore_index=True)

    # Fit scalers strictly on training NORMAL data
    scalers = fit_bharati_sensor_scalers(train_df)

    train_seqs, train_metas = [], []
    val_seqs, val_metas = [], []
    test_seqs, test_metas = [], []

    for sensor_id, scaler in scalers.items():
        s_train = train_df[train_df["sensor_id"] == sensor_id]
        s_val = val_df[val_df["sensor_id"] == sensor_id]
        s_test = test_df[test_df["sensor_id"] == sensor_id]

        t_seq, t_meta = extract_sliding_windows(
            s_train, scaler, seq_len=seq_len, normal_only=True, split_name="train"
        )
        v_seq, v_meta = extract_sliding_windows(
            s_val, scaler, seq_len=seq_len, normal_only=False, split_name="val"
        )
        te_seq, te_meta = extract_sliding_windows(
            s_test, scaler, seq_len=seq_len, normal_only=False, split_name="test"
        )

        if len(t_seq) > 0:
            train_seqs.append(t_seq)
            train_metas.extend(t_meta)
        if len(v_seq) > 0:
            val_seqs.append(v_seq)
            val_metas.extend(v_meta)
        if len(te_seq) > 0:
            test_seqs.append(te_seq)
            test_metas.extend(te_meta)

    return {
        "train_sequences": np.concatenate(train_seqs, axis=0) if train_seqs else np.empty((0, seq_len, 1)),
        "val_sequences": np.concatenate(val_seqs, axis=0) if val_seqs else np.empty((0, seq_len, 1)),
        "test_sequences": np.concatenate(test_seqs, axis=0) if test_seqs else np.empty((0, seq_len, 1)),
        "train_metadata": train_metas,
        "val_metadata": val_metas,
        "test_metadata": test_metas,
        "scalers": scalers,
        "train_df_records": len(train_df),
        "val_df_records": len(val_df),
        "test_df_records": len(test_df),
    }
