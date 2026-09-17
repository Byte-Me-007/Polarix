"""Unit tests for Polarix Maitri Synthetic ML Dataset Generation."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.generate_maitri_dataset import (
    DATA_SOURCE,
    SENSOR_CONFIGS,
    STATION_ID,
    generate_maitri_dataset,
    generate_normal_telemetry,
    inject_drift,
    inject_dropout,
    inject_spike,
    inject_stuck_value,
)

EXPECTED_COLUMNS = [
    "station_id",
    "sensor_id",
    "timestamp",
    "value",
    "unit",
    "quality",
    "source",
    "anomaly_type",
    "is_anomaly",
]

EXPECTED_SENSORS = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]


def test_expected_columns():
    """Verify that generated dataset contains all required schema columns."""
    df = generate_maitri_dataset(seed=42, points_per_sensor=100)
    assert list(df.columns) == EXPECTED_COLUMNS


def test_maitri_station_and_source():
    """Verify station_id is strictly MTR and source is SYNTHETIC_ML_DATASET."""
    df = generate_maitri_dataset(seed=42, points_per_sensor=100)
    assert (df["station_id"] == STATION_ID).all()
    assert (df["station_id"] == "MTR").all()
    assert (df["source"] == DATA_SOURCE).all()
    assert (df["source"] == "SYNTHETIC_ML_DATASET").all()


def test_all_maitri_sensors_present():
    """Verify all 5 target Maitri sensors exist with correct record counts."""
    points = 250
    df = generate_maitri_dataset(seed=42, points_per_sensor=points)
    unique_sensors = sorted(df["sensor_id"].unique().tolist())
    assert unique_sensors == sorted(EXPECTED_SENSORS)

    for sensor in EXPECTED_SENSORS:
        sensor_rows = df[df["sensor_id"] == sensor]
        assert len(sensor_rows) == points
        expected_unit = SENSOR_CONFIGS[sensor].unit
        assert (sensor_rows["unit"] == expected_unit).all()


def test_reproducibility_with_seed():
    """Verify identical seeds produce identical datasets and different seeds produce different values."""
    df1 = generate_maitri_dataset(seed=123, points_per_sensor=200)
    df2 = generate_maitri_dataset(seed=123, points_per_sensor=200)
    df3 = generate_maitri_dataset(seed=999, points_per_sensor=200)

    pd.testing.assert_frame_equal(df1, df2)

    # Compare non-dropout numerical values for different seeds
    val1 = df1.dropna(subset=["value"])["value"].values
    val3 = df3.dropna(subset=["value"])["value"].values
    assert not np.array_equal(val1, val3)


def test_no_duplicate_timestamps_per_sensor():
    """Verify there are no duplicate timestamps for the same sensor."""
    df = generate_maitri_dataset(seed=42, points_per_sensor=300)
    duplicates = df.duplicated(subset=["sensor_id", "timestamp"])
    assert not duplicates.any(), "Found duplicate timestamps for a single sensor."


def test_normal_telemetry_properties():
    """Verify normal records are labeled with is_anomaly=0, NORMAL, and GOOD."""
    df = generate_maitri_dataset(seed=42, points_per_sensor=300, inject_anomalies=False)
    assert (df["is_anomaly"] == 0).all()
    assert (df["anomaly_type"] == "NORMAL").all()
    assert (df["quality"] == "GOOD").all()
    assert not df["value"].isna().any()


def test_spike_injection():
    """Verify spike injection alters values and sets anomaly flags."""
    values = np.array([10.0, 10.0, 10.0, 10.0, 10.0])
    anomaly_types = ["NORMAL"] * 5
    is_anomaly = np.zeros(5, dtype=int)
    qualities = ["GOOD"] * 5

    inject_spike(values, anomaly_types, is_anomaly, qualities, start_idx=2, duration=2, magnitude=15.0)

    assert values[2] == 25.0
    assert values[3] == 25.0
    assert anomaly_types[2] == "SPIKE"
    assert anomaly_types[3] == "SPIKE"
    assert is_anomaly[2] == 1
    assert is_anomaly[3] == 1
    assert qualities[2] == "BAD"
    assert qualities[3] == "BAD"

    # Pre/post unaffected
    assert values[1] == 10.0
    assert anomaly_types[1] == "NORMAL"
    assert is_anomaly[1] == 0


def test_drift_injection():
    """Verify drift injection adds a progressive ramp and sets anomaly flags."""
    values = np.array([20.0, 20.0, 20.0, 20.0, 20.0])
    anomaly_types = ["NORMAL"] * 5
    is_anomaly = np.zeros(5, dtype=int)
    qualities = ["GOOD"] * 5

    inject_drift(values, anomaly_types, is_anomaly, qualities, start_idx=1, duration=3, drift_rate=2.0)

    assert values[1] == 22.0  # 20 + 1 * 2
    assert values[2] == 24.0  # 20 + 2 * 2
    assert values[3] == 26.0  # 20 + 3 * 2
    assert anomaly_types[1:4] == ["DRIFT", "DRIFT", "DRIFT"]
    assert (is_anomaly[1:4] == 1).all()
    assert (np.array(qualities[1:4]) == "BAD").all()
    assert values[0] == 20.0
    assert values[4] == 20.0


def test_dropout_injection():
    """Verify dropout sets values to NaN and quality to MISSING."""
    values = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    anomaly_types = ["NORMAL"] * 5
    is_anomaly = np.zeros(5, dtype=int)
    qualities = ["GOOD"] * 5

    inject_dropout(values, anomaly_types, is_anomaly, qualities, start_idx=2, duration=2)

    assert np.isnan(values[2])
    assert np.isnan(values[3])
    assert anomaly_types[2] == "DROPOUT"
    assert anomaly_types[3] == "DROPOUT"
    assert is_anomaly[2] == 1
    assert is_anomaly[3] == 1
    assert qualities[2] == "MISSING"
    assert qualities[3] == "MISSING"

    assert not np.isnan(values[1])
    assert qualities[1] == "GOOD"


def test_stuck_value_injection():
    """Verify stuck value freezes sensor reading to a constant flatline."""
    values = np.array([12.0, 14.5, 18.0, 22.0, 26.0])
    anomaly_types = ["NORMAL"] * 5
    is_anomaly = np.zeros(5, dtype=int)
    qualities = ["GOOD"] * 5

    inject_stuck_value(values, anomaly_types, is_anomaly, qualities, start_idx=2, duration=3)

    assert values[2] == 14.5
    assert values[3] == 14.5
    assert values[4] == 14.5
    assert anomaly_types[2:5] == ["STUCK_VALUE", "STUCK_VALUE", "STUCK_VALUE"]
    assert (is_anomaly[2:5] == 1).all()
    assert (np.array(qualities[2:5]) == "BAD").all()


def test_cli_generation_execution(tmp_path: Path):
    """Verify the CLI entry point generates a valid CSV file with expected structure."""
    out_file = tmp_path / "cli_test_telemetry.csv"
    cmd = [
        sys.executable,
        "ml/data/generate_maitri_dataset.py",
        "--seed",
        "42",
        "--points-per-sensor",
        "150",
        "--output",
        str(out_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI execution failed: {res.stderr}"
    assert out_file.exists()

    df_cli = pd.read_csv(out_file)
    assert len(df_cli) == 150 * 5
    assert list(df_cli.columns) == EXPECTED_COLUMNS
    assert set(df_cli["sensor_id"].unique()) == set(EXPECTED_SENSORS)
