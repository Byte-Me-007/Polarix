"""
Recovery-Aware Sequence Preparation Pipeline for Sensor ML V2 (Polarix SIH26060 - Person C).

Features:
1. Chronological 70/15/15 train/val/test partitioning per sensor without leakage.
2. Scalers fitted strictly on normal non-null training records.
3. Explicit window classification:
   - CLEAN_NORMAL: target is normal and all 30 steps in window are normal.
   - CONTAMINATED_NORMAL: target is normal but window contains historical anomaly in past steps.
   - ACTIVE_ANOMALY: target is an anomaly.
4. Normal-only training policy uses exclusively CLEAN_NORMAL sequences from training partition.
5. Unified implementation supporting both Maitri ('MTR') and Bharati ('BRT').
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class SensorScalerSpec:
    """Scaler specification for a telemetry sensor."""

    sensor_id: str
    station_id: str
    mean: float
    std: float
    unit: str

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / self.std

    def inverse_transform(self, normalized: np.ndarray) -> np.ndarray:
        return (normalized * self.std) + self.mean

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorScalerSpec":
        return cls(
            sensor_id=data["sensor_id"],
            station_id=data.get("station_id", "MTR"),
            mean=float(data["mean"]),
            std=float(data["std"]),
            unit=data.get("unit", ""),
        )


class RecoveryAwareDataset(Dataset):
    """PyTorch Dataset for recovery-aware sequences."""

    def __init__(self, sequences: np.ndarray) -> None:
        # sequences: shape (N, seq_len, 1) float32
        self.sequences = torch.from_numpy(sequences).float()

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.sequences[idx]


def fit_recovery_aware_scalers(
    train_df: pd.DataFrame, station_id: str, min_std: float = 1e-6
) -> Dict[str, SensorScalerSpec]:
    """Fit mean and std strictly on NORMAL non-null training records."""
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
        scalers[sensor_id] = SensorScalerSpec(
            sensor_id=sensor_id,
            station_id=station_id,
            mean=mean_val,
            std=std_val,
            unit=unit,
        )
    return scalers


def extract_recovery_aware_windows(
    sensor_df: pd.DataFrame,
    scaler: SensorScalerSpec,
    seq_len: int = 30,
    clean_normal_only: bool = False,
    split_name: str = "train",
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Extract sliding sequences and classify each window into CLEAN_NORMAL, CONTAMINATED_NORMAL, or ACTIVE_ANOMALY.
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
    station_id = scaler.station_id
    sensor_id = scaler.sensor_id

    sequences = []
    metadata = []
    n = len(values)

    for i in range(n - seq_len + 1):
        window_vals = values[i : i + seq_len]
        window_anom = is_anom[i : i + seq_len]

        # Skip window if it contains missing / NaN values (e.g. sensor dropout)
        if np.isnan(window_vals).any():
            continue

        target_idx = i + seq_len - 1
        target_is_anom = int(is_anom[target_idx])
        window_has_anomaly = int(np.any(window_anom != 0))

        # Determine window state
        if target_is_anom == 1:
            window_state = "ACTIVE_ANOMALY"
        elif window_has_anomaly == 1:
            window_state = "CONTAMINATED_NORMAL"
        else:
            window_state = "CLEAN_NORMAL"

        # Training policy: only clean normal windows are used for normal autoencoder training
        if clean_normal_only and window_state != "CLEAN_NORMAL":
            continue

        norm_window = scaler.transform(window_vals)

        meta = {
            "station_id": station_id,
            "sensor_id": sensor_id,
            "timestamp": timestamps[target_idx],
            "window_start_timestamp": timestamps[i],
            "window_end_timestamp": timestamps[target_idx],
            "target_value": float(values[target_idx]),
            "is_anomaly": target_is_anom,
            "anomaly_type": anom_types[target_idx],
            "window_contains_anomaly": window_has_anomaly,
            "window_state": window_state,
            "split": split_name,
        }

        sequences.append(norm_window)
        metadata.append(meta)

    if len(sequences) == 0:
        return np.empty((0, seq_len, 1), dtype=np.float32), []

    seq_arr = np.array(sequences, dtype=np.float32)[:, :, np.newaxis]
    return seq_arr, metadata


def prepare_recovery_aware_dataset(
    station_id: str,
    csv_path: str,
    seq_len: int = 30,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Dict[str, Any]:
    """
    Prepare chronologically partitioned recovery-aware dataset for a station.
    """
    csv_file = Path(csv_path)
    if not csv_file.is_absolute():
        csv_file = REPO_ROOT / csv_path

    df = pd.read_csv(csv_file)

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

    for _, sensor_group in df.groupby("sensor_id"):
        n_total = len(sensor_group)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)

        train_subsets.append(sensor_group.iloc[:n_train])
        val_subsets.append(sensor_group.iloc[n_train : n_train + n_val])
        test_subsets.append(sensor_group.iloc[n_train + n_val :])

    train_df = pd.concat(train_subsets, ignore_index=True)
    val_df = pd.concat(val_subsets, ignore_index=True)
    test_df = pd.concat(test_subsets, ignore_index=True)

    # Scalers fitted strictly on training normal non-null records
    scalers = fit_recovery_aware_scalers(train_df, station_id=station_id)

    train_seqs_list, train_meta_list = [], []
    val_seqs_list, val_meta_list = [], []
    test_seqs_list, test_meta_list = [], []

    for sensor_id, scaler in scalers.items():
        s_train = train_df[train_df["sensor_id"] == sensor_id]
        s_val = val_df[val_df["sensor_id"] == sensor_id]
        s_test = test_df[test_df["sensor_id"] == sensor_id]

        # Training sequences: strictly CLEAN_NORMAL
        t_seqs, t_meta = extract_recovery_aware_windows(
            s_train, scaler, seq_len=seq_len, clean_normal_only=True, split_name="train"
        )
        if len(t_seqs) > 0:
            train_seqs_list.append(t_seqs)
            train_meta_list.extend(t_meta)

        # Validation sequences: all valid windows for evaluation
        v_seqs, v_meta = extract_recovery_aware_windows(
            s_val, scaler, seq_len=seq_len, clean_normal_only=False, split_name="val"
        )
        if len(v_seqs) > 0:
            val_seqs_list.append(v_seqs)
            val_meta_list.extend(v_meta)

        # Test sequences: all valid windows for evaluation
        te_seqs, te_meta = extract_recovery_aware_windows(
            s_test, scaler, seq_len=seq_len, clean_normal_only=False, split_name="test"
        )
        if len(te_seqs) > 0:
            test_seqs_list.append(te_seqs)
            test_meta_list.extend(te_meta)

    train_sequences = np.concatenate(train_seqs_list, axis=0) if train_seqs_list else np.empty((0, seq_len, 1), dtype=np.float32)
    val_sequences = np.concatenate(val_seqs_list, axis=0) if val_seqs_list else np.empty((0, seq_len, 1), dtype=np.float32)
    test_sequences = np.concatenate(test_seqs_list, axis=0) if test_seqs_list else np.empty((0, seq_len, 1), dtype=np.float32)

    # Window count statistics
    def get_state_counts(meta_list: List[Dict[str, Any]]) -> Dict[str, int]:
        c_clean = sum(1 for m in meta_list if m["window_state"] == "CLEAN_NORMAL")
        c_contam = sum(1 for m in meta_list if m["window_state"] == "CONTAMINATED_NORMAL")
        c_active = sum(1 for m in meta_list if m["window_state"] == "ACTIVE_ANOMALY")
        return {
            "total": len(meta_list),
            "CLEAN_NORMAL": c_clean,
            "CONTAMINATED_NORMAL": c_contam,
            "ACTIVE_ANOMALY": c_active,
        }

    stats = {
        "station_id": station_id,
        "train_window_counts": get_state_counts(train_meta_list),
        "val_window_counts": get_state_counts(val_meta_list),
        "test_window_counts": get_state_counts(test_meta_list),
    }

    return {
        "station_id": station_id,
        "scalers": scalers,
        "train_sequences": train_sequences,
        "train_metadata": train_meta_list,
        "val_sequences": val_sequences,
        "val_metadata": val_meta_list,
        "test_sequences": test_sequences,
        "test_metadata": test_meta_list,
        "stats": stats,
    }
