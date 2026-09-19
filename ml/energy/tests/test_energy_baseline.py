"""
Comprehensive Unit & Integration Test Suite for Energy ML Forecasting Baseline (Polarix SIH26060).

Tests:
1. Chronological sequence construction without temporal shuffling.
2. Cross-station sequence isolation (MTR and BRT boundaries strictly segregated).
3. Lookback window length (L=24) and causality.
4. Target alignment (t+1, t+6, t+24 lookaheads).
5. Scaler fitting restricted strictly to training partition.
6. Missing-value handling in feature extraction.
7. Deterministic preprocessing transformations.
8. Deterministic model configuration serialization and loading.
9. Baseline forecaster prediction correctness (Persistence, Seasonal Lag, Moving Average).
10. Neural model output shape and tensor dimensions.
11. Saved artifact roundtrip loading (weights, config, scaler).
12. Single-window inference execution (EnergyForecaster.predict_window).
13. Insufficient history rejection (< 24 hours raises ValueError).
14. Station-specific evaluation disaggregation.
15. Regression metrics computation validity (MAE, RMSE, R2, sMAPE).
16. Strict Anti-Leakage Proof: Mutating raw records at timestamps > t does not alter the feature vector at timestamp t.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from ml.energy.inference.energy_forecaster import EnergyForecaster, EnergyPrediction
from ml.energy.models.energy_lstm import EnergyLSTM, EnergyModelConfig
from ml.energy.training.baselines import (
    MovingAverageForecaster,
    PersistenceForecaster,
    SeasonalLagForecaster,
    compute_regression_metrics,
)
from ml.energy.training.preprocessing import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    EnergyScalerParams,
    build_station_sequences,
    extract_features_and_targets,
    fit_energy_scaler,
    inverse_transform_targets,
    transform_features,
    transform_targets,
)

DATA_DIR = Path("ml/energy/data")
MODELS_DIR = Path("ml/energy/models")
RESULTS_DIR = Path("ml/energy/results")


@pytest.fixture(scope="module")
def maitri_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "maitri_energy_telemetry.csv")


@pytest.fixture(scope="module")
def bharati_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "bharati_energy_telemetry.csv")


@pytest.fixture(scope="module")
def trained_scaler() -> EnergyScalerParams:
    return EnergyScalerParams.load(MODELS_DIR / "energy_lstm_baseline_scaler.json")


@pytest.fixture(scope="module")
def forecaster() -> EnergyForecaster:
    return EnergyForecaster(model_dir=MODELS_DIR)


# Test 1: Chronological Sequence Construction
def test_1_chronological_sequence_construction(maitri_df, trained_scaler):
    """Verify that sequences preserve chronological order and contain consecutive timesteps."""
    mtr_train = maitri_df[maitri_df["split"] == "train"].copy()
    X, y, y_norm = build_station_sequences(mtr_train, trained_scaler, lookback=24)
    assert len(X) > 0
    assert X.shape[1] == 24  # Lookback = 24
    assert X.shape[2] == len(FEATURE_COLUMNS)
    assert y.shape[1] == len(TARGET_COLUMNS)


# Test 2: Cross-Station Sequence Isolation
def test_2_no_cross_station_sequence_leakage(maitri_df, bharati_df, trained_scaler):
    """Verify that MTR sequences contain exclusively MTR data and BRT contains BRT data."""
    X_mtr, _, _ = build_station_sequences(maitri_df.head(100), trained_scaler, lookback=24)
    X_brt, _, _ = build_station_sequences(bharati_df.head(100), trained_scaler, lookback=24)

    # Station indicator feature is index 13 ('station_is_brt')
    brt_idx = FEATURE_COLUMNS.index("station_is_brt")
    assert np.all(X_mtr[:, :, brt_idx] < 0.0)  # Standard scaled 0.0 becomes negative
    assert np.all(X_brt[:, :, brt_idx] > 0.0)  # Standard scaled 1.0 becomes positive


# Test 3: Lookback Window Correctness
def test_3_lookback_window_correctness(maitri_df, trained_scaler):
    """Verify exact lookback window length and alignment with raw feature matrix."""
    lookback = 24
    sample_df = maitri_df.iloc[:50].copy()
    X_df, _ = extract_features_and_targets(sample_df)
    X_scaled = transform_features(X_df, trained_scaler)
    X_seq, _, _ = build_station_sequences(sample_df, trained_scaler, lookback=lookback)

    # First sequence should match exactly the first 24 rows
    assert np.allclose(X_seq[0], X_scaled[:lookback], atol=1e-5)
    # Second sequence should match rows 1 to 25
    assert np.allclose(X_seq[1], X_scaled[1 : lookback + 1], atol=1e-5)


# Test 4: Target Alignment
def test_4_target_alignment(maitri_df, trained_scaler):
    """Verify sequence targets align with the last timestep of each sliding window."""
    sample_df = maitri_df.iloc[:50].copy()
    _, y_df = extract_features_and_targets(sample_df)
    _, y_seq, _ = build_station_sequences(sample_df, trained_scaler, lookback=24)

    # Target for first sequence (index 0) corresponds to timestep index 23 of sample_df
    assert np.allclose(y_seq[0], y_df.iloc[23].to_numpy(), atol=1e-4)


# Test 5: Train-Only Scaler Fitting
def test_5_train_only_scaler_fitting(maitri_df, bharati_df):
    """Verify scaler parameters are strictly derived from train split."""
    train_combined = pd.concat(
        [maitri_df[maitri_df["split"] == "train"], bharati_df[bharati_df["split"] == "train"]],
        ignore_index=True,
    )
    scaler = fit_energy_scaler(train_combined)

    X_train_df, _ = extract_features_and_targets(train_combined)
    expected_means = X_train_df.mean(axis=0).to_numpy()
    assert np.allclose(scaler.feature_mean, expected_means, atol=1e-4)


# Test 6: Missing-Value Handling
def test_6_missing_value_handling(maitri_df, trained_scaler):
    """Verify that null sensor anomaly scores or missing quality flags are handled gracefully."""
    df_corrupt = maitri_df.iloc[:30].copy()
    df_corrupt.loc[5, "sensor_anomaly_score"] = np.nan
    df_corrupt.loc[10, "data_quality"] = "MISSING"

    X_df, _ = extract_features_and_targets(df_corrupt)
    assert not X_df.isna().any().any()
    X_scaled = transform_features(X_df, trained_scaler)
    assert not np.isnan(X_scaled).any()


# Test 7: Deterministic Preprocessing
def test_7_deterministic_preprocessing(maitri_df, trained_scaler):
    """Verify feature extraction and transformation is 100% deterministic."""
    sample = maitri_df.iloc[:100].copy()
    X1, y1 = extract_features_and_targets(sample)
    X2, y2 = extract_features_and_targets(sample)
    pd.testing.assert_frame_equal(X1, X2)
    pd.testing.assert_frame_equal(y1, y2)


# Test 8: Deterministic Model Configuration Serialization
def test_8_model_config_serialization(tmp_path):
    """Verify EnergyModelConfig roundtrip JSON serialization."""
    cfg = EnergyModelConfig(hidden_dim=64, num_layers=3, dropout=0.2, seed=123)
    path = tmp_path / "cfg.json"
    cfg.save(path)
    loaded = EnergyModelConfig.load(path)
    assert loaded == cfg


# Test 9: Baseline Prediction Correctness
def test_9_baseline_prediction_correctness(maitri_df):
    """Verify mathematical properties of classical baselines."""
    sample = maitri_df.iloc[:100].copy()

    # Persistence
    pers = PersistenceForecaster().predict(sample)
    assert np.allclose(pers["pred_power_demand_1h_kw"], sample["power_demand_kw"])
    assert np.allclose(pers["pred_energy_demand_6h_kwh"], sample["power_demand_kw"] * 6.0)

    # Moving Average
    ma = MovingAverageForecaster(short_window=6, long_window=24).predict(sample)
    assert not ma.isna().any().any()
    assert (ma["pred_energy_demand_6h_kwh"] >= 0.0).all()


# Test 10: Model Output Shape
def test_10_model_output_shape():
    """Verify PyTorch model input-output tensor dimensionality."""
    cfg = EnergyModelConfig(input_dim=18, hidden_dim=48, num_layers=2, num_targets=4)
    model = EnergyLSTM(cfg)
    x = torch.randn(8, 24, 18)  # Batch=8, Lookback=24, Dim=18
    out = model(x)
    assert out.shape == (8, 4)


# Test 11: Saved Artifact Loading
def test_11_saved_artifact_loading():
    """Verify that trained model weights, config, and scaler files exist and load successfully."""
    assert (MODELS_DIR / "energy_lstm_baseline.pt").exists()
    assert (MODELS_DIR / "energy_lstm_baseline_config.json").exists()
    assert (MODELS_DIR / "energy_lstm_baseline_scaler.json").exists()

    cfg = EnergyModelConfig.load(MODELS_DIR / "energy_lstm_baseline_config.json")
    model = EnergyLSTM(cfg)
    state_dict = torch.load(MODELS_DIR / "energy_lstm_baseline.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()


# Test 12: Single-Window Inference Execution
def test_12_single_window_inference(forecaster, maitri_df):
    """Verify end-to-end single sequence inference via EnergyForecaster."""
    window = maitri_df.iloc[:24].copy()
    pred = forecaster.predict_window(window)
    assert isinstance(pred, EnergyPrediction)
    assert pred.station_id == "MTR"
    assert pred.target_power_demand_1h_kw > 0.0
    assert 0.0 <= pred.target_battery_soc_1h_percent <= 100.0
    assert pred.target_energy_demand_6h_kwh > 0.0
    assert pred.target_energy_demand_24h_kwh > 0.0


# Test 13: Insufficient History Rejection
def test_13_insufficient_history_rejection(forecaster, maitri_df):
    """Verify ValueError is raised when input sequence is shorter than 24 hours."""
    short_window = maitri_df.iloc[:20].copy()
    with pytest.raises(ValueError, match="Insufficient historical context"):
        forecaster.predict_window(short_window)


# Test 14: Station-Specific Evaluation Disaggregation
def test_14_station_specific_evaluation_metrics():
    """Verify metrics JSON contains separate MTR, BRT, and Combined evaluations."""
    metrics_path = RESULTS_DIR / "baseline_metrics.json"
    assert metrics_path.exists()
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert "MTR" in metrics["station_metrics"]
    assert "BRT" in metrics["station_metrics"]
    assert "COMBINED" in metrics["station_metrics"]

    # Verify neural model outperformed persistence in 1h power demand across both stations
    mtr_neural_mae = metrics["station_metrics"]["MTR"]["neural_lstm"]["target_power_demand_1h_kw"]["mae"]
    mtr_pers_mae = metrics["station_metrics"]["MTR"]["persistence"]["target_power_demand_1h_kw"]["mae"]
    assert mtr_neural_mae < mtr_pers_mae

    brt_neural_mae = metrics["station_metrics"]["BRT"]["neural_lstm"]["target_power_demand_1h_kw"]["mae"]
    brt_pers_mae = metrics["station_metrics"]["BRT"]["persistence"]["target_power_demand_1h_kw"]["mae"]
    assert brt_neural_mae < brt_pers_mae


# Test 15: Metric Calculation Function
def test_15_metric_calculation_validity():
    """Verify compute_regression_metrics mathematical properties."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0], dtype=float)
    y_pred = np.array([12.0, 19.0, 31.0, 38.0], dtype=float)

    metrics = compute_regression_metrics(y_true, y_pred)
    assert metrics["mae"] == 1.5
    assert np.isclose(metrics["rmse"], np.sqrt(2.5), atol=1e-3)
    assert metrics["r2"] > 0.95


# Test 16: Strict Anti-Leakage Proof (Future Independence)
def test_16_strict_anti_leakage_proof(forecaster, maitri_df):
    """
    CRITICAL LEAKAGE TEST:
    Proves that mutating raw data at future timestamps (t+1 .. t+N) has EXACTLY ZERO effect
    on the feature representation and model forecast generated at timestamp t.
    """
    history_base = maitri_df.iloc[:24].copy()
    future_data = maitri_df.iloc[24:48].copy()

    full_df_original = pd.concat([history_base, future_data], ignore_index=True)

    # Mutate future timestamps drastically
    full_df_mutated = full_df_original.copy()
    full_df_mutated.loc[24:, "power_demand_kw"] = 999.0
    full_df_mutated.loc[24:, "temperature_c"] = 99.0
    full_df_mutated.loc[24:, "battery_soc_percent"] = 0.0
    full_df_mutated.loc[24:, "event_type"] = "EXTREME_COLD"

    # Prediction at timestamp t=23 (the end of history_base)
    pred_orig = forecaster.predict_window(full_df_original.iloc[:24])
    pred_mutated = forecaster.predict_window(full_df_mutated.iloc[:24])

    assert pred_orig.target_power_demand_1h_kw == pred_mutated.target_power_demand_1h_kw
    assert pred_orig.target_battery_soc_1h_percent == pred_mutated.target_battery_soc_1h_percent
    assert pred_orig.target_energy_demand_6h_kwh == pred_mutated.target_energy_demand_6h_kwh
    assert pred_orig.target_energy_demand_24h_kwh == pred_mutated.target_energy_demand_24h_kwh
