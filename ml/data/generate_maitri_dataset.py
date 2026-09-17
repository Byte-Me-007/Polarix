#!/usr/bin/env python3
"""
Maitri Synthetic Telemetry Dataset Generator for Polarix ML (SIH26060).

Generates reproducible synthetic sensor telemetry for Maitri station ('MTR').
Supports normal structured telemetry and injected anomaly types:
- NORMAL
- SPIKE
- DRIFT
- DROPOUT (missing values)
- STUCK_VALUE (flatline / constant sensor output)

NOTE: This dataset uses purely SYNTHETIC data for ML development and validation.
It does NOT use or assume real historical Maitri sensor data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

STATION_ID = "MTR"
DATA_SOURCE = "SYNTHETIC_ML_DATASET"


@dataclass(frozen=True)
class MaitriSensorConfig:
    sensor_id: str
    sensor_type: str
    unit: str
    baseline_mean: float
    diurnal_amplitude: float
    noise_std: float
    min_val: float
    max_val: float


SENSOR_CONFIGS: Dict[str, MaitriSensorConfig] = {
    "TEMP_001": MaitriSensorConfig(
        sensor_id="TEMP_001",
        sensor_type="temperature",
        unit="°C",
        baseline_mean=-15.0,
        diurnal_amplitude=4.5,
        noise_std=0.35,
        min_val=-45.0,
        max_val=10.0,
    ),
    "PRESS_001": MaitriSensorConfig(
        sensor_id="PRESS_001",
        sensor_type="pressure",
        unit="hPa",
        baseline_mean=990.0,
        diurnal_amplitude=2.0,
        noise_std=0.25,
        min_val=930.0,
        max_val=1040.0,
    ),
    "HUM_001": MaitriSensorConfig(
        sensor_id="HUM_001",
        sensor_type="humidity",
        unit="%",
        baseline_mean=55.0,
        diurnal_amplitude=8.0,
        noise_std=1.2,
        min_val=10.0,
        max_val=98.0,
    ),
    "VIB_001": MaitriSensorConfig(
        sensor_id="VIB_001",
        sensor_type="vibration",
        unit="mm/s",
        baseline_mean=0.85,
        diurnal_amplitude=0.15,
        noise_std=0.04,
        min_val=0.0,
        max_val=15.0,
    ),
    "POWER_001": MaitriSensorConfig(
        sensor_id="POWER_001",
        sensor_type="power consumption",
        unit="kW",
        baseline_mean=35.0,
        diurnal_amplitude=6.0,
        noise_std=0.8,
        min_val=5.0,
        max_val=100.0,
    ),
}


def generate_normal_telemetry(
    config: MaitriSensorConfig,
    n_points: int,
    rng: np.random.Generator,
    sample_interval_sec: int = 60,
) -> np.ndarray:
    """
    Generate smooth, structured normal telemetry for a given sensor config.

    Combines:
    - Diurnal sinusoidal variation (simulating daily thermal/operational cycles)
    - Autoregressive smooth drift (AR(1) process for physical inertia)
    - Gaussian sensor measurement noise
    """
    time_steps = np.arange(n_points)
    day_period = (24 * 3600) / sample_interval_sec

    # Diurnal cycle
    diurnal = config.diurnal_amplitude * np.sin(2 * np.pi * time_steps / day_period)

    # Autoregressive smooth variation (AR(1))
    ar_noise = np.zeros(n_points)
    phi = 0.96
    sigma_innov = config.noise_std * np.sqrt(1 - phi**2)
    innovations = rng.normal(0, sigma_innov, size=n_points)
    for t in range(1, n_points):
        ar_noise[t] = phi * ar_noise[t - 1] + innovations[t]

    # White measurement noise
    white_noise = rng.normal(0, config.noise_std * 0.4, size=n_points)

    raw_values = config.baseline_mean + diurnal + ar_noise + white_noise
    return np.clip(raw_values, config.min_val, config.max_val)


def inject_spike(
    values: np.ndarray,
    anomaly_types: List[str],
    is_anomaly: np.ndarray,
    qualities: List[str],
    start_idx: int,
    duration: int,
    magnitude: float,
    positive: bool = True,
) -> None:
    """Inject a short-lived abnormal deviation / spike."""
    end_idx = min(start_idx + duration, len(values))
    direction = 1.0 if positive else -1.0
    for idx in range(start_idx, end_idx):
        values[idx] += direction * magnitude
        anomaly_types[idx] = "SPIKE"
        is_anomaly[idx] = 1
        qualities[idx] = "BAD"


def inject_drift(
    values: np.ndarray,
    anomaly_types: List[str],
    is_anomaly: np.ndarray,
    qualities: List[str],
    start_idx: int,
    duration: int,
    drift_rate: float,
) -> None:
    """Inject a gradual deviation / ramp from the normal baseline."""
    end_idx = min(start_idx + duration, len(values))
    for step, idx in enumerate(range(start_idx, end_idx), start=1):
        values[idx] += step * drift_rate
        anomaly_types[idx] = "DRIFT"
        is_anomaly[idx] = 1
        qualities[idx] = "BAD"


def inject_dropout(
    values: np.ndarray,
    anomaly_types: List[str],
    is_anomaly: np.ndarray,
    qualities: List[str],
    start_idx: int,
    duration: int,
) -> None:
    """Inject sensor dropout / missing telemetry (represented as np.nan / MISSING)."""
    end_idx = min(start_idx + duration, len(values))
    for idx in range(start_idx, end_idx):
        values[idx] = np.nan
        anomaly_types[idx] = "DROPOUT"
        is_anomaly[idx] = 1
        qualities[idx] = "MISSING"


def inject_stuck_value(
    values: np.ndarray,
    anomaly_types: List[str],
    is_anomaly: np.ndarray,
    qualities: List[str],
    start_idx: int,
    duration: int,
) -> None:
    """Freeze the sensor output to a constant value for a contiguous interval."""
    end_idx = min(start_idx + duration, len(values))
    stuck_val = values[max(0, start_idx - 1)]
    if np.isnan(stuck_val):
        stuck_val = 0.0
    for idx in range(start_idx, end_idx):
        values[idx] = stuck_val
        anomaly_types[idx] = "STUCK_VALUE"
        is_anomaly[idx] = 1
        qualities[idx] = "BAD"


def generate_sensor_series(
    config: MaitriSensorConfig,
    n_points: int,
    rng: np.random.Generator,
    start_timestamp: pd.Timestamp,
    sample_interval_sec: int = 60,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """Generate complete telemetry time-series for a single sensor."""
    values = generate_normal_telemetry(config, n_points, rng, sample_interval_sec)
    anomaly_types: List[str] = ["NORMAL"] * n_points
    is_anomaly = np.zeros(n_points, dtype=int)
    qualities: List[str] = ["GOOD"] * n_points

    if inject_anomalies and n_points >= 200:
        # Structured anomaly placement across time windows
        # 1. Spike at ~15% into the series
        spike_start = int(n_points * 0.15)
        spike_dur = int(rng.integers(3, 8))
        spike_mag = config.diurnal_amplitude * 2.5 + config.noise_std * 6.0
        inject_spike(values, anomaly_types, is_anomaly, qualities, spike_start, spike_dur, spike_mag, positive=True)

        # 2. Drift at ~35% into the series
        drift_start = int(n_points * 0.35)
        drift_dur = int(min(45, max(15, n_points * 0.08)))
        drift_rate = (config.diurnal_amplitude * 1.5) / drift_dur
        inject_drift(values, anomaly_types, is_anomaly, qualities, drift_start, drift_dur, drift_rate)

        # 3. Dropout at ~60% into the series
        dropout_start = int(n_points * 0.60)
        dropout_dur = int(rng.integers(5, 12))
        inject_dropout(values, anomaly_types, is_anomaly, qualities, dropout_start, dropout_dur)

        # 4. Stuck value at ~80% into the series
        stuck_start = int(n_points * 0.80)
        stuck_dur = int(min(35, max(12, n_points * 0.06)))
        inject_stuck_value(values, anomaly_types, is_anomaly, qualities, stuck_start, stuck_dur)

    timestamps = [
        (start_timestamp + pd.Timedelta(seconds=i * sample_interval_sec)).isoformat()
        for i in range(n_points)
    ]

    df = pd.DataFrame(
        {
            "station_id": STATION_ID,
            "sensor_id": config.sensor_id,
            "timestamp": timestamps,
            "value": values,
            "unit": config.unit,
            "quality": qualities,
            "source": DATA_SOURCE,
            "anomaly_type": anomaly_types,
            "is_anomaly": is_anomaly,
        }
    )
    return df


def generate_maitri_dataset(
    seed: int = 42,
    points_per_sensor: int = 1000,
    start_time: str = "2026-03-01T00:00:00Z",
    sample_interval_sec: int = 60,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """
    Generate deterministic synthetic telemetry dataset across all Maitri sensors.

    Parameters:
    -----------
    seed : int
        Random seed for full reproducibility.
    points_per_sensor : int
        Number of timestamps per sensor (total rows = points_per_sensor * len(sensors)).
    start_time : str
        ISO-8601 start timestamp.
    sample_interval_sec : int
        Sampling interval in seconds (default: 60s).
    inject_anomalies : bool
        Whether to inject synthetic anomaly windows.

    Returns:
    --------
    pd.DataFrame: Sorted, multi-sensor synthetic telemetry DataFrame.
    """
    start_dt = pd.to_datetime(start_time, utc=True)
    sensor_dfs: List[pd.DataFrame] = []

    # Use independent deterministic seed streams per sensor
    for idx, (sensor_id, config) in enumerate(SENSOR_CONFIGS.items()):
        sensor_seed = seed + idx * 1000
        sensor_rng = np.random.default_rng(sensor_seed)
        df_sensor = generate_sensor_series(
            config=config,
            n_points=points_per_sensor,
            rng=sensor_rng,
            start_timestamp=start_dt,
            sample_interval_sec=sample_interval_sec,
            inject_anomalies=inject_anomalies,
        )
        sensor_dfs.append(df_sensor)

    combined_df = pd.concat(sensor_dfs, ignore_index=True)
    # Sort deterministically by timestamp then sensor_id
    combined_df.sort_values(by=["timestamp", "sensor_id"], inplace=True)
    combined_df.reset_index(drop=True, inplace=True)
    return combined_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic telemetry dataset for Maitri station (Polarix SIH 2026 Person C ML)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--points-per-sensor",
        type=int,
        default=1000,
        help="Number of sequential records per sensor (default: 1000, total rows = 5000).",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Optional total row target across all 5 sensors (overrides points-per-sensor).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ml/data/maitri_synthetic_telemetry.csv",
        help="Output CSV path (default: ml/data/maitri_synthetic_telemetry.csv).",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default="2026-03-01T00:00:00Z",
        help="Start timestamp in ISO-8601 format (default: 2026-03-01T00:00:00Z).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Interval between successive samples in seconds (default: 60).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    points_per_sensor = args.points_per_sensor
    if args.rows is not None:
        points_per_sensor = max(1, args.rows // len(SENSOR_CONFIGS))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Polarix Person C ML] Generating Maitri synthetic dataset (seed={args.seed}, points_per_sensor={points_per_sensor})...")
    df = generate_maitri_dataset(
        seed=args.seed,
        points_per_sensor=points_per_sensor,
        start_time=args.start_time,
        sample_interval_sec=args.interval_seconds,
        inject_anomalies=True,
    )

    df.to_csv(output_path, index=False)
    print(f"[Polarix Person C ML] Saved dataset to {output_path} ({len(df)} rows).")

    # Print summary statistics
    print("\n--- Dataset Summary ---")
    print(f"Total Rows: {len(df)}")
    print(f"Station ID: {df['station_id'].unique().tolist()}")
    print(f"Sensors ({len(df['sensor_id'].unique())}): {df['sensor_id'].unique().tolist()}")
    print(f"Total Anomalies: {df['is_anomaly'].sum()} ({(df['is_anomaly'].mean() * 100):.2f}%)")
    print(f"Missing / Dropout Count: {df['value'].isna().sum()}")
    print("\nAnomaly Breakdown:")
    print(df["anomaly_type"].value_counts().to_string())
    print("\nPer-Sensor Record Count:")
    print(df["sensor_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
