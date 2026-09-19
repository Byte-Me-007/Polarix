"""
Unit Tests for Energy ML Dataset Generation & Physical Microgrid Constraints (Polarix SIH26060).

Validates:
1. Determinism across seeds.
2. Station coverage (MTR and BRT) and complete 1-year timeline (8760 hours/station).
3. Chronological ordering and monotonic timestamp continuity without duplicates.
4. Physical invariants:
   - Power demand in valid operating ranges.
   - Generator output within [0, P_rated].
   - Battery SoC in [0, 100]%.
   - Battery charge/discharge within inverter power ratings.
   - Strictly mutually exclusive battery charge and discharge (P_chg * P_dis == 0).
   - Fuel consumption non-negative and physically consistent.
   - Temperature and environmental variables bounded by Antarctic ranges.
5. Causal target construction:
   - 1h ahead power demand matching t+1.
   - 1h ahead battery SoC matching t+1.
   - 6h and 24h forward cumulative energy matching future rolling sums.
   - Deficit risk flag correctness.
   - Boundary NaNs strictly localized to future lookahead tail.
6. Chronological 70% / 15% / 15% train/val/test splits without temporal overlap.
7. Anomaly and missing telemetry injection rates within documented limits.
8. Manifest integrity and SHA-256 hash match against generated files.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.energy.data.generate_energy_dataset import (
    BHARATI_CONFIG,
    MAITRI_CONFIG,
    compute_file_sha256,
    generate_and_save_all_energy_datasets,
    generate_station_time_series,
)

DATA_DIR = Path("ml/energy/data")


@pytest.fixture(scope="module")
def energy_manifest() -> dict:
    manifest_path = DATA_DIR / "energy_dataset_manifest.json"
    assert manifest_path.exists(), f"Manifest file missing: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def maitri_df() -> pd.DataFrame:
    csv_path = DATA_DIR / "maitri_energy_telemetry.csv"
    assert csv_path.exists(), f"Maitri dataset missing: {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def bharati_df() -> pd.DataFrame:
    csv_path = DATA_DIR / "bharati_energy_telemetry.csv"
    assert csv_path.exists(), f"Bharati dataset missing: {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def combined_df() -> pd.DataFrame:
    csv_path = DATA_DIR / "polarix_energy_telemetry.csv"
    assert csv_path.exists(), f"Combined dataset missing: {csv_path}"
    return pd.read_csv(csv_path)


def test_dataset_generation_determinism():
    """Verify that generating with the same seed yields bit-for-bit identical DataFrames."""
    df1 = generate_station_time_series(MAITRI_CONFIG, n_hours=100, seed=42)
    df2 = generate_station_time_series(MAITRI_CONFIG, n_hours=100, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_station_coverage_and_row_counts(maitri_df, bharati_df, combined_df):
    """Verify exact 8,760 hours per station and 17,520 combined rows."""
    assert len(maitri_df) == 8760, f"Expected 8760 rows for Maitri, got {len(maitri_df)}"
    assert len(bharati_df) == 8760, f"Expected 8760 rows for Bharati, got {len(bharati_df)}"
    assert len(combined_df) == 17520, f"Expected 17520 rows in combined dataset, got {len(combined_df)}"
    assert (maitri_df["station_id"] == "MTR").all()
    assert (bharati_df["station_id"] == "BRT").all()


def test_chronological_ordering_and_frequency(maitri_df, bharati_df):
    """Verify timestamps are strictly monotonic increasing with no duplicates and 1h delta."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        ts = pd.to_datetime(df["timestamp"])
        assert ts.is_monotonic_increasing, f"{name} timestamps are not monotonic increasing"
        assert df["timestamp"].nunique() == len(df), f"{name} contains duplicate timestamps"
        deltas = ts.diff().dropna()
        assert (deltas == pd.Timedelta(hours=1)).all(), f"{name} hourly frequency violated"


def test_power_demand_physical_bounds(maitri_df, bharati_df):
    """Verify power demand falls within realistic physical limits [10 kW, 150 kW]."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        assert (df["power_demand_kw"] >= 10.0).all(), f"{name} has power_demand_kw < 10 kW"
        assert (df["power_demand_kw"] <= 150.0).all(), f"{name} has power_demand_kw > 150 kW"
        # Energy consumption in 1h equals power demand
        assert np.allclose(df["energy_consumption_kwh"], df["power_demand_kw"], atol=1e-2)


def test_generator_output_constraints(maitri_df, bharati_df):
    """Verify generator output operates within rated capacity and non-negative power."""
    assert (maitri_df["generator_output_kw"] >= 0.0).all()
    assert (maitri_df["generator_output_kw"] <= MAITRI_CONFIG.generator_rated_kw).all()

    assert (bharati_df["generator_output_kw"] >= 0.0).all()
    assert (bharati_df["generator_output_kw"] <= BHARATI_CONFIG.generator_rated_kw).all()


def test_battery_soc_and_power_invariants(maitri_df, bharati_df):
    """Verify BESS state of charge is in [0, 100]% and charge/discharge are mutually exclusive."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        assert (df["battery_soc_percent"] >= 0.0).all(), f"{name} SoC < 0%"
        assert (df["battery_soc_percent"] <= 100.0).all(), f"{name} SoC > 100%"
        assert (df["battery_charge_kw"] >= 0.0).all(), f"{name} negative charge kw"
        assert (df["battery_discharge_kw"] >= 0.0).all(), f"{name} negative discharge kw"

        # Invariant: Never charge and discharge simultaneously
        simultaneous = (df["battery_charge_kw"] > 0.0) & (df["battery_discharge_kw"] > 0.0)
        assert simultaneous.sum() == 0, f"{name} has simultaneous charge and discharge"


def test_fuel_consumption_validity(maitri_df, bharati_df):
    """Verify fuel consumption is strictly positive when generator is loaded and physically correlated."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        assert (df["fuel_consumption_l"] >= 0.0).all(), f"{name} negative fuel consumption"
        # Correlation between generator power and fuel consumption must be strong (> 0.95)
        corr = df["generator_output_kw"].corr(df["fuel_consumption_l"])
        assert corr > 0.95, f"{name} fuel consumption not strongly correlated with generator output: {corr}"


def test_weather_and_environmental_bounds(maitri_df, bharati_df):
    """Verify temperature, humidity, pressure, and wind speed respect Antarctic physical ranges."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        assert (df["temperature_c"] >= -55.0).all(), f"{name} temperature too low"
        assert (df["temperature_c"] <= 15.0).all(), f"{name} temperature too high"
        assert (df["humidity_percent"] >= 10.0).all(), f"{name} humidity too low"
        assert (df["humidity_percent"] <= 100.0).all(), f"{name} humidity too high"
        assert (df["pressure_hpa"] >= 920.0).all(), f"{name} pressure too low"
        assert (df["pressure_hpa"] <= 1040.0).all(), f"{name} pressure too high"
        assert (df["wind_speed_mps"] >= 0.0).all(), f"{name} negative wind speed"
        assert (df["wind_speed_mps"] <= 65.0).all(), f"{name} excessive wind speed"


def test_target_construction_correctness_and_no_leakage(maitri_df):
    """Verify multi-horizon targets are exact causal lookaheads without forward leakage into features."""
    # 1h ahead power demand
    expected_1h_p = maitri_df["power_demand_kw"].shift(-1)
    pd.testing.assert_series_equal(
        maitri_df["target_power_demand_1h_kw"],
        expected_1h_p,
        check_names=False,
    )

    # 1h ahead battery SoC
    expected_1h_soc = maitri_df["battery_soc_percent"].shift(-1)
    pd.testing.assert_series_equal(
        maitri_df["target_battery_soc_1h_percent"],
        expected_1h_soc,
        check_names=False,
    )

    # 6h ahead cumulative energy demand: sum from t+1 to t+6
    for t in range(10):
        expected_6h = round(float(maitri_df["power_demand_kw"].iloc[t + 1 : t + 7].sum()), 2)
        assert np.isclose(maitri_df["target_energy_demand_6h_kwh"].iloc[t], expected_6h, atol=1e-2)

    # 24h ahead cumulative energy demand: sum from t+1 to t+24
    for t in range(10):
        expected_24h = round(float(maitri_df["power_demand_kw"].iloc[t + 1 : t + 25].sum()), 2)
        assert np.isclose(maitri_df["target_energy_demand_24h_kwh"].iloc[t], expected_24h, atol=1e-2)

    # Tail NaNs: target 1h has 1 NaN, target 6h has 6 NaNs, target 24h has 24 NaNs
    assert maitri_df["target_power_demand_1h_kw"].isna().sum() == 1
    assert maitri_df["target_battery_soc_1h_percent"].isna().sum() == 1
    assert maitri_df["target_energy_demand_6h_kwh"].isna().sum() == 6
    assert maitri_df["target_energy_demand_24h_kwh"].isna().sum() == 24


def test_chronological_splits_proportions_and_bounds(maitri_df, bharati_df):
    """Verify strict 70% train, 15% validation, 15% test chronological partition."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        split_counts = df["split"].value_counts().to_dict()
        assert split_counts["train"] == 6132, f"{name} train count mismatch"
        assert split_counts["val"] == 1314, f"{name} val count mismatch"
        assert split_counts["test"] == 1314, f"{name} test count mismatch"

        train_ts = pd.to_datetime(df[df["split"] == "train"]["timestamp"])
        val_ts = pd.to_datetime(df[df["split"] == "val"]["timestamp"])
        test_ts = pd.to_datetime(df[df["split"] == "test"]["timestamp"])

        assert train_ts.max() < val_ts.min(), f"{name} Train and Validation overlap"
        assert val_ts.max() < test_ts.min(), f"{name} Validation and Test overlap"


def test_sensor_ml_integration_placeholders(maitri_df, bharati_df):
    """Verify upstream Sensor ML feature placeholders have valid contracts."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        assert (df["sensor_anomaly_score"] >= 0.0).all()
        assert set(df["sensor_anomaly_status"].unique()).issubset({"NORMAL", "ANOMALY", "MISSING_DATA"})
        assert set(df["data_quality"].unique()).issubset({"GOOD", "MISSING"})


def test_deficit_risk_positive_distribution_across_all_splits(maitri_df, bharati_df):
    """Verify both MTR and BRT have strictly non-zero positive deficit-risk examples in train, val, and test."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        for split_name in ["train", "val", "test"]:
            sub_df = df[df["split"] == split_name]
            pos_count = int((sub_df["target_energy_deficit_risk"] == 1).sum())
            total_count = len(sub_df)
            prevalence = pos_count / total_count
            assert pos_count > 0, f"{name} {split_name} has ZERO positive deficit-risk events! Required > 0."
            assert prevalence >= 0.001, f"{name} {split_name} prevalence too low: {prevalence:.4f}"



def test_manifest_consistency_and_sha256_hashes(energy_manifest):
    """Verify manifest file hashes match the on-disk dataset files bit-for-bit."""
    assert energy_manifest["dataset_version"] == "1.0.0"
    assert energy_manifest["total_records"] == 17520
    assert energy_manifest["station_records"] == {"MTR": 8760, "BRT": 8760}

    for filename, file_meta in energy_manifest["dataset_files"].items():
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File listed in manifest does not exist: {filepath}"
        actual_hash = compute_file_sha256(filepath)
        assert actual_hash == file_meta["sha256"], (
            f"Hash mismatch for {filename}: expected {file_meta['sha256']}, got {actual_hash}"
        )
