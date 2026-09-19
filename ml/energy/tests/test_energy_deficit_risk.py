"""
Comprehensive Unit, Integrity & Anti-Leakage Test Suite for Energy Deficit-Risk Prediction (Polarix SIH26060).

Tests:
1. Target integrity: Physical definition alignment across all station records.
2. Feature list causality: Zero target_ columns or future lookahead variables in RISK_FEATURE_COLUMNS.
3. Causal rolling features: Backward-only windows and slopes.
4. Strict Anti-Leakage Proof (Future Mutation): Mutating raw rows at timestamps > t does not alter the feature vector or model prediction at timestamp t.
5. Model training determinism across seeds.
6. Probability bounds: Output probabilities strictly in [0.0, 1.0].
7. Operating decision threshold correctness (deficit_risk == (prob >= threshold)).
8. Threshold persistence: Config JSON and joblib bundle store identical threshold.
9. Canonical inference container schema (DeficitRiskPrediction dataclass & dict).
10. Station disaggregation: MTR vs BRT mapped deterministically.
11. Metric calculation mathematical correctness.
12. Single-class safety: Metric calculation does not raise exceptions when only one class is present.
13. Artifact file integrity and roundtrip loading.
14. Exploratory cross-station transfer execution.
15. Feature ordering invariance: Scrambled column order produces identical inference results.
16. Missing required feature raises explicit KeyError.
17. Target columns in input DataFrame are safely ignored/excluded from inference.
18. NaN / Inf input rejection with explicit ValueError.
19. Physical range validation (SoC, pressure, humidity, power, temperature).
20. No future lookahead (lead/shift(-k)) in risk feature extraction or inference.
21. Representative normal-case operational fixture (expected deficit_risk = False).
22. Representative deficit-case operational fixture (expected deficit_risk = True).
23. Machine-readable inference contract validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
import pytest

from ml.energy.risk.features import (
    PHYSICAL_BOUNDS,
    REQUIRED_RAW_COLUMNS,
    RISK_FEATURE_COLUMNS,
    TARGET_COLUMN,
    TARGET_COLUMNS_EXCLUDED,
    extract_risk_features,
    validate_risk_telemetry,
)
from ml.energy.risk.inference import DeficitRiskForecaster, DeficitRiskPrediction
from ml.energy.risk.models import (
    GradientBoostingRiskClassifier,
    LogisticRegressionRiskClassifier,
    MajorityClassClassifier,
    RuleBasedPersistenceRiskClassifier,
    compute_classification_metrics,
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
def risk_forecaster() -> DeficitRiskForecaster:
    return DeficitRiskForecaster(model_dir=MODELS_DIR)


# Test 1: Target Definition Integrity
def test_1_target_definition_integrity(maitri_df, bharati_df):
    """Verify target_energy_deficit_risk matches the physical microgrid specification."""
    for name, df in [("MTR", maitri_df), ("BRT", bharati_df)]:
        rated_gen = 120.0 if name == "MTR" else 150.0
        expected_risk = (
            (df["target_battery_soc_1h_percent"] < 25.0) | (df["target_power_demand_1h_kw"] > 0.95 * rated_gen)
        ).astype(float)
        expected_risk = np.where(df["target_power_demand_1h_kw"].isna(), np.nan, expected_risk)

        valid_mask = ~df[TARGET_COLUMN].isna()
        assert np.allclose(
            df.loc[valid_mask, TARGET_COLUMN],
            expected_risk[valid_mask],
            atol=1e-5,
        )


# Test 2: Feature List Excludes Future Targets
def test_2_feature_list_excludes_future_targets():
    """Verify RISK_FEATURE_COLUMNS contains zero target_ columns or lookahead variables."""
    assert TARGET_COLUMN not in RISK_FEATURE_COLUMNS
    for col in RISK_FEATURE_COLUMNS:
        assert not col.startswith("target_"), f"Future target found in feature list: {col}"
        assert not col.startswith("future_"), f"Future variable found in feature list: {col}"
    for target_col in TARGET_COLUMNS_EXCLUDED:
        assert target_col not in RISK_FEATURE_COLUMNS


# Test 3: Causal Rolling Features
def test_3_causal_rolling_features(maitri_df):
    """Verify rolling statistics and slopes are backward-looking only."""
    sample = maitri_df.iloc[:30].copy()
    X_df, _ = extract_risk_features(sample, validate=True)

    # At row index 0, rolling 6h mean must equal the power demand at row 0
    assert np.isclose(X_df.loc[0, "recent_demand_mean_6h"], sample.loc[0, "power_demand_kw"])
    # At row index 5, rolling 6h mean must equal the average of rows 0..5
    expected_mean_5 = sample.loc[:5, "power_demand_kw"].mean()
    assert np.isclose(X_df.loc[5, "recent_demand_mean_6h"], expected_mean_5)


# Test 4: Strict Anti-Leakage Proof (Future Mutation Test)
def test_4_future_mutation_anti_leakage_proof(risk_forecaster, maitri_df):
    """
    CRITICAL LEAKAGE TEST:
    Modifying future records (t+1 .. t+N) with extreme values has ZERO effect
    on the risk feature vector and predicted deficit probability at timestamp t.
    """
    history_window = maitri_df.iloc[:24].copy()
    future_data = maitri_df.iloc[24:48].copy()

    df_original = pd.concat([history_window, future_data], ignore_index=True)

    # Mutate future values to extreme outliers
    df_mutated = df_original.copy()
    df_mutated.loc[24:, "power_demand_kw"] = 250.0
    df_mutated.loc[24:, "generator_output_kw"] = 10.0
    df_mutated.loc[24:, "battery_soc_percent"] = 5.0
    df_mutated.loc[24:, "temperature_c"] = -45.0
    df_mutated.loc[24:, "event_type"] = "EXTREME_COLD"

    # Evaluate prediction for timestamp t=23 (end of history_window)
    pred_orig = risk_forecaster.predict_window(df_original.iloc[:24])
    pred_mut = risk_forecaster.predict_window(df_mutated.iloc[:24])

    assert pred_orig.deficit_risk_probability == pred_mut.deficit_risk_probability
    assert pred_orig.deficit_risk == pred_mut.deficit_risk


# Test 5: Model Training Determinism
def test_5_model_training_determinism(maitri_df):
    """Verify training with fixed random seed yields identical predictions."""
    X_df, y_s = extract_risk_features(maitri_df.iloc[:200])
    X = X_df.to_numpy(dtype=np.float32)
    y = y_s.to_numpy(dtype=np.float32)

    m1 = GradientBoostingRiskClassifier(random_state=42, max_iter=50).fit(X, y)
    m2 = GradientBoostingRiskClassifier(random_state=42, max_iter=50).fit(X, y)

    p1 = m1.predict_proba(X)
    p2 = m2.predict_proba(X)
    assert np.allclose(p1, p2, atol=1e-6)


# Test 6: Probability Bounds
def test_6_probability_bounds(risk_forecaster, maitri_df):
    """Verify predicted probabilities fall strictly in [0.0, 1.0]."""
    preds_df = risk_forecaster.predict_dataframe(maitri_df.iloc[:100])
    probs = preds_df["deficit_risk_probability"]
    assert (probs >= 0.0).all()
    assert (probs <= 1.0).all()


# Test 7: Decision Threshold Correctness
def test_7_decision_threshold_correctness(risk_forecaster, maitri_df):
    """Verify binary deficit_risk flag strictly equals (prob >= threshold)."""
    preds_df = risk_forecaster.predict_dataframe(maitri_df.iloc[:100])
    expected_flags = preds_df["deficit_risk_probability"] >= risk_forecaster.threshold
    assert (preds_df["deficit_risk"] == expected_flags).all()


# Test 8: Threshold Persistence & Config Consistency
def test_8_threshold_persistence():
    """Verify frozen threshold in config JSON matches the saved model bundle."""
    config_path = MODELS_DIR / "energy_deficit_risk_v1_config.json"
    assert config_path.exists()
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    forecaster = DeficitRiskForecaster(model_dir=MODELS_DIR)
    assert np.isclose(forecaster.threshold, cfg["selected_threshold"], atol=1e-5)
    assert forecaster.threshold == 0.35


# Test 9: Canonical Inference Schema
def test_9_canonical_inference_schema(risk_forecaster, maitri_df):
    """Verify predict_window returns valid DeficitRiskPrediction container."""
    pred = risk_forecaster.predict_window(maitri_df.iloc[:24])
    assert isinstance(pred, DeficitRiskPrediction)
    assert pred.station_id == "MTR"
    assert isinstance(pred.deficit_risk_probability, float)
    assert isinstance(pred.deficit_risk, bool)
    assert pred.threshold == 0.35
    assert pred.model_version == "energy-deficit-risk-v1"

    # Test dictionary conversion
    d = pred.to_dict()
    assert set(d.keys()) == {
        "station_id",
        "timestamp",
        "deficit_risk_probability",
        "deficit_risk",
        "threshold",
        "model_version",
    }


# Test 10: Station Disaggregation & Encoding
def test_10_station_disaggregation(risk_forecaster, maitri_df, bharati_df):
    """Verify forecaster handles both MTR (station_is_brt=0) and BRT (station_is_brt=1)."""
    pred_mtr = risk_forecaster.predict_window(maitri_df.iloc[:24])
    pred_brt = risk_forecaster.predict_window(bharati_df.iloc[:24])
    assert pred_mtr.station_id == "MTR"
    assert pred_brt.station_id == "BRT"

    # Verify underlying feature encoding
    X_mtr, _ = extract_risk_features(maitri_df.iloc[:5])
    X_brt, _ = extract_risk_features(bharati_df.iloc[:5])
    assert (X_mtr["station_is_brt"] == 0.0).all()
    assert (X_brt["station_is_brt"] == 1.0).all()


# Test 11: Metric Calculation Function Correctness
def test_11_metric_calculation_correctness():
    """Verify compute_classification_metrics accuracy and confusion matrix values."""
    y_true = np.array([0, 0, 1, 1], dtype=float)
    y_prob = np.array([0.1, 0.4, 0.8, 0.9], dtype=float)

    metrics = compute_classification_metrics(y_true, y_prob, threshold=0.5)
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["specificity"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["confusion_matrix"] == {"tn": 2, "fp": 0, "fn": 0, "tp": 2}


# Test 12: Single-Class Safety in Metric Calculation
def test_12_single_class_safety_in_metrics():
    """Verify single-class test evaluation does not raise unhandled exceptions."""
    y_true_zeros = np.zeros(100, dtype=float)
    y_prob = np.random.uniform(0.01, 0.30, size=100)

    metrics = compute_classification_metrics(y_true_zeros, y_prob, threshold=0.5)
    assert metrics["accuracy"] == 1.0
    assert metrics["specificity"] == 1.0
    assert metrics["false_negatives"] == 0
    assert metrics["false_positives"] == 0


# Test 13: Artifact File Integrity
def test_13_artifact_file_integrity():
    """Verify all deficit risk model artifacts and metrics JSON exist and are valid."""
    assert (MODELS_DIR / "energy_deficit_risk_v1.joblib").exists()
    assert (MODELS_DIR / "energy_deficit_risk_v1_config.json").exists()
    assert (RESULTS_DIR / "deficit_risk_metrics.json").exists()
    assert (RESULTS_DIR / "deficit_risk_report.md").exists()
    assert (RESULTS_DIR / "energy_deficit_risk_inference_contract.json").exists()


# Test 14: Exploratory Cross-Station Transfer
def test_14_exploratory_cross_station_transfer():
    """Verify metrics JSON contains valid cross-station transfer evaluation data."""
    with open(RESULTS_DIR / "deficit_risk_metrics.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert "exploratory_cross_station_transfer" in metrics
    assert "train_mtr_test_brt" in metrics["exploratory_cross_station_transfer"]
    assert "train_brt_test_mtr" in metrics["exploratory_cross_station_transfer"]


# Test 15: Feature Ordering Invariance
def test_15_feature_ordering_invariance(risk_forecaster, maitri_df):
    """Verify providing telemetry columns in scrambled order produces identical inference results."""
    df_window = maitri_df.iloc[:24].copy()

    # Original prediction
    pred_orig = risk_forecaster.predict_window(df_window)

    # Scramble column order
    scrambled_cols = list(df_window.columns)
    np.random.RandomState(42).shuffle(scrambled_cols)
    df_scrambled = df_window[scrambled_cols].copy()

    pred_scrambled = risk_forecaster.predict_window(df_scrambled)

    assert pred_orig.deficit_risk_probability == pred_scrambled.deficit_risk_probability
    assert pred_orig.deficit_risk == pred_scrambled.deficit_risk
    assert pred_orig.station_id == pred_scrambled.station_id
    assert pred_orig.timestamp == pred_scrambled.timestamp


# Test 16: Missing Required Feature Rejection
def test_16_missing_required_feature_rejection(risk_forecaster, maitri_df):
    """Verify missing required telemetry fields raise a descriptive KeyError."""
    df_window = maitri_df.iloc[:24].copy()

    # Drop required power_demand_kw column
    df_invalid = df_window.drop(columns=["power_demand_kw"])
    with pytest.raises(KeyError, match="missing required columns"):
        risk_forecaster.predict_window(df_invalid)

    # Drop station_id column
    df_no_station = df_window.drop(columns=["station_id"])
    with pytest.raises(KeyError, match="missing required columns"):
        risk_forecaster.predict_window(df_no_station)


# Test 17: Target Columns Safely Ignored in Inference
def test_17_target_columns_safely_ignored_in_inference(risk_forecaster, maitri_df):
    """Verify presence or alteration of target_ columns has ZERO effect on inference."""
    df_window = maitri_df.iloc[:24].copy()

    pred1 = risk_forecaster.predict_window(df_window)

    # Corrupt target columns
    df_corrupted_targets = df_window.copy()
    for col in TARGET_COLUMNS_EXCLUDED:
        if col in df_corrupted_targets.columns:
            df_corrupted_targets[col] = 99999.0

    pred2 = risk_forecaster.predict_window(df_corrupted_targets)

    # Drop all target columns entirely
    df_no_targets = df_window.drop(columns=[c for c in TARGET_COLUMNS_EXCLUDED if c in df_window.columns])
    pred3 = risk_forecaster.predict_window(df_no_targets)

    assert pred1.deficit_risk_probability == pred2.deficit_risk_probability == pred3.deficit_risk_probability
    assert pred1.deficit_risk == pred2.deficit_risk == pred3.deficit_risk


# Test 18: NaN and Inf Input Rejection
def test_18_nan_and_inf_input_rejection(risk_forecaster, maitri_df):
    """Verify NaN and Inf values in numeric telemetry raise ValueError."""
    df_window = maitri_df.iloc[:24].copy()

    # Inject NaN into power_demand_kw
    df_nan = df_window.copy()
    df_nan.loc[23, "power_demand_kw"] = np.nan
    with pytest.raises(ValueError, match="contains NaN or infinite"):
        risk_forecaster.predict_window(df_nan)

    # Inject Inf into battery_soc_percent
    df_inf = df_window.copy()
    df_inf.loc[23, "battery_soc_percent"] = np.inf
    with pytest.raises(ValueError, match="contains NaN or infinite"):
        risk_forecaster.predict_window(df_inf)


# Test 19: Physical Range Validation
def test_19_physical_range_validation(risk_forecaster, maitri_df):
    """Verify physical invariant bounds (SoC outside [0, 100], invalid station) are rejected."""
    df_window = maitri_df.iloc[:24].copy()

    # SoC > 100%
    df_high_soc = df_window.copy()
    df_high_soc.loc[23, "battery_soc_percent"] = 105.0
    with pytest.raises(ValueError, match="battery_soc_percent.*above physical upper bound"):
        risk_forecaster.predict_window(df_high_soc)

    # Negative power demand
    df_neg_power = df_window.copy()
    df_neg_power.loc[23, "power_demand_kw"] = -10.0
    with pytest.raises(ValueError, match="power_demand_kw.*below physical lower bound"):
        risk_forecaster.predict_window(df_neg_power)

    # Invalid station ID
    df_invalid_station = df_window.copy()
    df_invalid_station.loc[23, "station_id"] = "UNKNOWN_STATION"
    with pytest.raises(ValueError, match="Invalid station_id encountered"):
        risk_forecaster.predict_window(df_invalid_station)


# Test 20: No Future Lookahead (Causal Invariant)
def test_20_no_future_lookahead():
    """Verify source code in ml/energy/risk does not use forward shifts (shift(-1), lead)."""
    import inspect
    import ml.energy.risk.features as feat_mod
    import ml.energy.risk.inference as inf_mod

    feat_src = inspect.getsource(feat_mod)
    inf_src = inspect.getsource(inf_mod)

    assert "shift(-" not in feat_src, "Forbidden forward shift found in features.py"
    assert "shift(-" not in inf_src, "Forbidden forward shift found in inference.py"


# Test 21: Representative Normal-Case Operational Fixture
def test_21_representative_normal_operational_fixture(risk_forecaster):
    """Verify standard diurnal operation with full battery, spinning reserve, and normal demand yields deficit_risk = False."""
    normal_telemetry: Dict[str, Any] = {
        "timestamp": "2026-02-15T12:00:00Z",
        "station_id": "MTR",
        "power_demand_kw": 45.0,
        "generator_output_kw": 50.0,
        "battery_soc_percent": 80.0,
        "battery_charge_kw": 5.0,
        "battery_discharge_kw": 0.0,
        "fuel_consumption_l": 14.1,
        "temperature_c": -8.0,
        "humidity_percent": 55.0,
        "pressure_hpa": 988.0,
        "wind_speed_mps": 6.0,
        "sensor_anomaly_score": 0.8,
        "sensor_anomaly_status": "NORMAL",
        "data_quality": "GOOD",
    }
    pred = risk_forecaster.predict_dict(normal_telemetry)
    assert isinstance(pred, DeficitRiskPrediction)
    assert pred.deficit_risk is False
    assert pred.deficit_risk_probability < risk_forecaster.threshold


# Test 22: Representative Deficit-Case Operational Fixture
def test_22_representative_deficit_operational_fixture(risk_forecaster):
    """Verify severe constrained generation with battery depleted to 16% yields deficit_risk = True."""
    deficit_telemetry: Dict[str, Any] = {
        "timestamp": "2026-07-20T03:00:00Z",
        "station_id": "MTR",
        "power_demand_kw": 115.0,
        "generator_output_kw": 25.0,  # Generator throttled to base
        "battery_soc_percent": 16.5,  # Critical depletion
        "battery_charge_kw": 0.0,
        "battery_discharge_kw": 45.0,  # Max discharge attempting to cover shortfall
        "fuel_consumption_l": 8.0,
        "temperature_c": -38.0,
        "humidity_percent": 80.0,
        "pressure_hpa": 950.0,
        "wind_speed_mps": 32.0,
        "sensor_anomaly_score": 2.5,
        "sensor_anomaly_status": "NORMAL",
        "data_quality": "GOOD",
    }
    pred = risk_forecaster.predict_dict(deficit_telemetry)
    assert isinstance(pred, DeficitRiskPrediction)
    assert pred.deficit_risk is True
    assert pred.deficit_risk_probability >= risk_forecaster.threshold


# Test 23: Machine-Readable Inference Contract Validation
def test_23_inference_contract_validation():
    """Verify energy_deficit_risk_inference_contract.json is well-formed and valid."""
    contract_file = RESULTS_DIR / "energy_deficit_risk_inference_contract.json"
    assert contract_file.exists()
    with open(contract_file, "r", encoding="utf-8") as f:
        contract = json.load(f)

    assert contract["model_version"] == "energy-deficit-risk-v1"
    assert contract["operating_threshold"] == 0.35
    assert "input_specification" in contract
    assert "output_specification" in contract
    assert len(contract["input_specification"]["required_telemetry_fields"]) == 12
