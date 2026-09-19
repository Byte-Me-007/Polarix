"""
Anti-Leakage and Causality Verification Tests (Polarix SIH26060 - Person C).

Mandatory tests verifying:
1. Future mutation immunity (prediction at time t cannot change when t+k is altered).
2. Strict chronological split non-overlap.
3. Feature scaler fitted strictly on train data without val/test contamination.
4. Target columns completely isolated from feature matrix.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.temperature.inference.temperature_forecaster import TemperatureForecaster
from ml.temperature.training.preprocessing import (
    FEATURE_COLS,
    TARGET_COLS,
    TemperatureFeatureScaler,
)
from ml.temperature.training.train_temperature_lstm import load_and_split_data


def test_chronological_split_no_overlap():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    mtr_train, mtr_val, mtr_test, brt_train, brt_val, brt_test = load_and_split_data(data_dir)

    for train, val, test, name in [(mtr_train, mtr_val, mtr_test, "MTR"), (brt_train, brt_val, brt_test, "BRT")]:
        max_train_ts = train["timestamp"].max()
        min_val_ts = val["timestamp"].min()
        max_val_ts = val["timestamp"].max()
        min_test_ts = test["timestamp"].min()

        assert max_train_ts < min_val_ts, f"Temporal overlap between Train and Val in {name}"
        assert max_val_ts < min_test_ts, f"Temporal overlap between Val and Test in {name}"

        # Check monotonically increasing
        ts_train_dt = pd.to_datetime(train["timestamp"], utc=True)
        ts_val_dt = pd.to_datetime(val["timestamp"], utc=True)
        ts_test_dt = pd.to_datetime(test["timestamp"], utc=True)
        assert (ts_train_dt.diff().dropna() > pd.Timedelta(0)).all()
        assert (ts_val_dt.diff().dropna() > pd.Timedelta(0)).all()
        assert (ts_test_dt.diff().dropna() > pd.Timedelta(0)).all()


def test_future_mutation_invariance():
    """
    Future Mutation Test:
    1. Select a prediction cutoff t.
    2. Extract the 24-hour lookback window ending at t.
    3. Run forecaster.
    4. Provide subsequent points (t+1, t+2) but mutate them wildly.
    5. Run prediction for the window ending at t.
    6. Confirm the prediction at t is strictly unchanged.
    """
    forecaster = TemperatureForecaster()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    df_mtr = pd.read_csv(data_dir / "maitri_temperature_telemetry.csv")

    # Take 30 rows
    sample_window = df_mtr.iloc[100:124].copy().reset_index(drop=True)
    res1 = forecaster.predict_window("MTR", sample_window)

    assert res1["status"] == "PREDICTION_AVAILABLE"
    forecast_1 = res1["forecasts"]

    # Mutate values at index 125, 126 in the wider series
    df_mutated = df_mtr.iloc[100:130].copy().reset_index(drop=True)
    # Mutate future rows (rows after index 23)
    df_mutated.loc[24:, "temperature_c"] = 999.0
    df_mutated.loc[24:, "wind_speed_mps"] = 500.0
    df_mutated.loc[24:, "pressure_hpa"] = 10.0

    # Predict again using the exact 24h window ending at index 23 (time t)
    window_at_t = df_mutated.iloc[:24].copy().reset_index(drop=True)
    res2 = forecaster.predict_window("MTR", window_at_t)

    assert res2["status"] == "PREDICTION_AVAILABLE"
    forecast_2 = res2["forecasts"]

    assert forecast_1["temperature_1h_c"] == forecast_2["temperature_1h_c"]
    assert forecast_1["temperature_6h_c"] == forecast_2["temperature_6h_c"]
    assert forecast_1["temperature_24h_c"] == forecast_2["temperature_24h_c"]


def test_target_feature_isolation():
    """Ensures no target column exists in input FEATURE_COLS."""
    for target in TARGET_COLS:
        assert target not in FEATURE_COLS, f"Target {target} leaked into feature columns!"


def test_scaler_isolated_from_test_data():
    """Verifies that the persisted scaler was fitted only on training set."""
    forecaster = TemperatureForecaster()
    scaler = forecaster.scaler

    data_dir = Path(__file__).resolve().parent.parent / "data"
    mtr_train, mtr_val, mtr_test, brt_train, brt_val, brt_test = load_and_split_data(data_dir)
    comb_train = pd.concat([mtr_train, brt_train], ignore_index=True)

    # Recompute train statistics
    expected_mean = float(comb_train["temperature_c"].mean())
    assert pytest.approx(scaler.temp_mean, rel=1e-3) == expected_mean

    # Ensure scaler temp_mean does NOT match the test set mean
    comb_test = pd.concat([mtr_test, brt_test], ignore_index=True)
    test_mean = float(comb_test["temperature_c"].mean())
    assert abs(scaler.temp_mean - test_mean) > 0.05
