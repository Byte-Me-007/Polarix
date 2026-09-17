#!/usr/bin/env python3
"""
Bharati Synthetic Telemetry Dataset Generator for Polarix ML (SIH26060 - Person C).

Generates reproducible synthetic sensor telemetry for Bharati station ('BRT').
Supports normal diurnal structured baseline telemetry and injected anomaly types:
- NORMAL
- SPIKE
- DRIFT
- DROPOUT (missing values / sensor offline)
- STUCK_VALUE (flatline sensor output)

DATASET NOTICE:
This dataset uses purely SYNTHETIC data for ML development, testing, demonstration,
and validation. It does NOT use, assume, or claim real historical Bharati sensor data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

STATION_ID = "BRT"
DATA_SOURCE = "SYNTHETIC_ML_DATASET"
DEFAULT_DAY_PERIOD = 288  # Multi-cycle stationary diurnal period in samples


@dataclass(frozen=True)
class BharatiSensorConfig:
    sensor_id: str
    sensor_type: str
    unit: str
    baseline_mean: float
    diurnal_amplitude: float
    noise_std: float
    min_val: float
    max_val: float


SENSOR_CONFIGS: Dict[str, BharatiSensorConfig] = {
    "BRT_TEMP_001": BharatiSensorConfig(
        sensor_id="BRT_TEMP_001",
        sensor_type="temperature",
        unit="C",
        baseline_mean=-10.0,
        diurnal_amplitude=3.5,
        noise_std=0.30,
        min_val=-35.0,
        max_val=15.0,
    ),
    "BRT_PRESS_001": BharatiSensorConfig(
        sensor_id="BRT_PRESS_001",
        sensor_type="pressure",
        unit="hPa",
        baseline_mean=985.0,
        diurnal_amplitude=2.5,
        noise_std=0.20,
        min_val=920.0,
        max_val=1035.0,
    ),
    "BRT_HUM_001": BharatiSensorConfig(
        sensor_id="BRT_HUM_001",
        sensor_type="humidity",
        unit="%",
        baseline_mean=60.0,
        diurnal_amplitude=7.0,
        noise_std=1.0,
        min_val=15.0,
        max_val=98.0,
    ),
    "BRT_VIB_001": BharatiSensorConfig(
        sensor_id="BRT_VIB_001",
        sensor_type="vibration",
        unit="mm/s",
        baseline_mean=0.75,
        diurnal_amplitude=0.12,
        noise_std=0.03,
        min_val=0.0,
        max_val=12.0,
    ),
    "BRT_POWER_001": BharatiSensorConfig(
        sensor_id="BRT_POWER_001",
        sensor_type="power consumption",
        unit="kW",
        baseline_mean=42.0,
        diurnal_amplitude=5.5,
        noise_std=0.70,
        min_val=10.0,
        max_val=110.0,
    ),
}


def generate_normal_telemetry(
    config: BharatiSensorConfig,
    n_points: int,
    rng: np.random.Generator,
    day_period: int = DEFAULT_DAY_PERIOD,
) -> np.ndarray:
    """
    Generate smooth, structured normal telemetry for a given sensor config.

    Combines:
    - Diurnal sinusoidal variation across multiple stationary complete cycles
    - Autoregressive smooth drift (AR(1) process for physical thermal/mechanical inertia)
    - Gaussian sensor measurement noise
    """
    time_steps = np.arange(n_points)

    # Multi-cycle stationary diurnal variation
    diurnal = config.diurnal_amplitude * np.sin(2 * np.pi * time_steps / day_period)

    # Autoregressive smooth variation (AR(1))
    ar_noise = np.zeros(n_points)
    phi = 0.95
    sigma_innov = config.noise_std * np.sqrt(1 - phi**2)
    innovations = rng.normal(0, sigma_innov, size=n_points)
    for t in range(1, n_points):
        ar_noise[t] = phi * ar_noise[t - 1] + innovations[t]

    # White measurement noise
    white_noise = rng.normal(0, config.noise_std * 0.35, size=n_points)

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
    config: BharatiSensorConfig,
    n_points: int,
    rng: np.random.Generator,
    start_timestamp: pd.Timestamp,
    sample_interval_sec: int = 60,
    day_period: int = DEFAULT_DAY_PERIOD,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """
    Generate complete telemetry time-series for a single Bharati sensor.

    Anomalies are injected in Validation (70-85%) and Test (85-100%) partitions,
    keeping Training (0-70%) as pure normal baseline operations.
    """
    values = generate_normal_telemetry(config, n_points, rng, day_period=day_period)
    anomaly_types: List[str] = ["NORMAL"] * n_points
    is_anomaly = np.zeros(n_points, dtype=int)
    qualities: List[str] = ["GOOD"] * n_points

    if inject_anomalies and n_points >= 400:
        # 1. Validation Partition Anomalies (70% - 85% of time series)
        # Val Spike at ~72%
        val_spike_start = int(n_points * 0.72)
        val_spike_dur = int(rng.integers(3, 7))
        spike_mag = config.diurnal_amplitude * 2.5 + config.noise_std * 6.0
        inject_spike(values, anomaly_types, is_anomaly, qualities, val_spike_start, val_spike_dur, spike_mag, positive=True)

        # Val Drift at ~75%
        val_drift_start = int(n_points * 0.75)
        val_drift_dur = int(min(35, max(15, n_points * 0.015)))
        drift_rate = (config.diurnal_amplitude * 1.5) / val_drift_dur
        inject_drift(values, anomaly_types, is_anomaly, qualities, val_drift_start, val_drift_dur, drift_rate)

        # Val Dropout at ~79%
        val_dropout_start = int(n_points * 0.79)
        val_dropout_dur = int(rng.integers(4, 9))
        inject_dropout(values, anomaly_types, is_anomaly, qualities, val_dropout_start, val_dropout_dur)

        # Val Stuck Value at ~82%
        val_stuck_start = int(n_points * 0.82)
        val_stuck_dur = int(min(25, max(12, n_points * 0.012)))
        inject_stuck_value(values, anomaly_types, is_anomaly, qualities, val_stuck_start, val_stuck_dur)

        # 2. Test Partition Anomalies (85% - 100% of time series)
        # Test Spike at ~87%
        test_spike_start = int(n_points * 0.87)
        test_spike_dur = int(rng.integers(3, 7))
        inject_spike(values, anomaly_types, is_anomaly, qualities, test_spike_start, test_spike_dur, spike_mag, positive=False)

        # Test Drift at ~90%
        test_drift_start = int(n_points * 0.90)
        test_drift_dur = int(min(35, max(15, n_points * 0.015)))
        inject_drift(values, anomaly_types, is_anomaly, qualities, test_drift_start, test_drift_dur, -drift_rate)

        # Test Dropout at ~94%
        test_dropout_start = int(n_points * 0.94)
        test_dropout_dur = int(rng.integers(4, 9))
        inject_dropout(values, anomaly_types, is_anomaly, qualities, test_dropout_start, test_dropout_dur)

        # Test Stuck Value at ~97%
        test_stuck_start = int(n_points * 0.97)
        test_stuck_dur = int(min(25, max(12, n_points * 0.012)))
        inject_stuck_value(values, anomaly_types, is_anomaly, qualities, test_stuck_start, test_stuck_dur)

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


def generate_bharati_dataset(
    seed: int = 42,
    points_per_sensor: int = 2000,
    start_time: str = "2026-03-01T00:00:00Z",
    sample_interval_sec: int = 60,
    day_period: int = DEFAULT_DAY_PERIOD,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """
    Generate deterministic synthetic telemetry dataset across all Bharati sensors.

    Parameters:
    -----------
    seed : int
        Random seed for full reproducibility.
    points_per_sensor : int
        Number of sequential timestamps per sensor (default: 2000, total rows = 10,000 across 5 sensors).
    start_time : str
        ISO-8601 start timestamp.
    sample_interval_sec : int
        Sampling interval in seconds (default: 60s).
    day_period : int
        Stationary diurnal cycle period in samples.
    inject_anomalies : bool
        Whether to inject synthetic anomaly windows into validation and test partitions.

    Returns:
    --------
    pd.DataFrame: Chronologically sorted, multi-sensor synthetic telemetry DataFrame.
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
            day_period=day_period,
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
        description="Generate synthetic telemetry dataset for Bharati station (Polarix SIH 2026 Person C ML)."
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
        default=2000,
        help="Number of sequential records per sensor (default: 2000, total rows = 10000).",
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
        default="ml/data/bharati_synthetic_telemetry.csv",
        help="Output CSV path (default: ml/data/bharati_synthetic_telemetry.csv).",
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
    parser.add_argument(
        "--day-period",
        type=int,
        default=DEFAULT_DAY_PERIOD,
        help=f"Diurnal period in samples (default: {DEFAULT_DAY_PERIOD}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    points_per_sensor = args.points_per_sensor
    if args.rows is not None:
        points_per_sensor = max(1, args.rows // len(SENSOR_CONFIGS))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Polarix Person C ML] Generating Bharati synthetic dataset (seed={args.seed}, points_per_sensor={points_per_sensor})...")
    df = generate_bharati_dataset(
        seed=args.seed,
        points_per_sensor=points_per_sensor,
        start_time=args.start_time,
        sample_interval_sec=args.interval_seconds,
        day_period=args.day_period,
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
