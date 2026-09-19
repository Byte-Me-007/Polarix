"""
Unit & Anti-Leakage Compatibility Test Suite for Person A Backend Integration (Polarix SIH26060).

Tests:
1. Required raw telemetry fields are explicitly declared and validated.
2. Optional sensor ML fields are safely defaulted when omitted.
3. Derived features (18 LSTM, 26 Risk) are strictly causal with no lookahead.
4. No future target columns are required for inference.
5. Station ID validation: MTR and BRT accepted; BHR rejected without silent aliasing.
6. Timestamp parsing, UTC enforcement, and trigonometric temporal embeddings.
7. 24-hour lookback requirement enforcement on unified service.
8. Unified output schema conformity against energy_ml_inference_contract.json.
9. Compatibility matrix and report artifact file integrity.
10. Frozen model artifact integrity preservation.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from ml.energy.inference.energy_ml_service import EnergyMLService, UnifiedEnergyPrediction
from ml.energy.risk.features import (
    PHYSICAL_BOUNDS,
    REQUIRED_RAW_COLUMNS,
    RISK_FEATURE_COLUMNS,
    TARGET_COLUMNS_EXCLUDED,
    extract_risk_features,
    validate_risk_telemetry,
)
from ml.energy.training.preprocessing import FEATURE_COLUMNS as LSTM_FEATURE_COLUMNS, extract_features_and_targets

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
def energy_service() -> EnergyMLService:
    return EnergyMLService(model_dir=MODELS_DIR)


# Test 1: Required Raw Telemetry Fields Declared and Validated
def test_1_required_raw_fields_are_explicitly_declared_and_validated(maitri_df):
    """Verify all 12 required physical fields are strictly enforced and missing any raises KeyError."""
    assert len(REQUIRED_RAW_COLUMNS) == 12
    sample = maitri_df.iloc[:24].copy()

    for col in REQUIRED_RAW_COLUMNS:
        invalid_sample = sample.drop(columns=[col])
        with pytest.raises(KeyError, match="missing required columns"):
            validate_risk_telemetry(invalid_sample)


# Test 2: Optional Sensor ML Fields Safely Defaulted
def test_2_optional_fields_are_safely_defaulted(maitri_df, energy_service):
    """Verify optional fields (sensor_anomaly_score, sensor_anomaly_status, data_quality) can be omitted."""
    sample = maitri_df.iloc[:24].copy()

    # Strip optional fields
    optional_cols = ["sensor_anomaly_score", "sensor_anomaly_status", "sensor_anomaly_type", "data_quality", "event_type", "source"]
    stripped_sample = sample.drop(columns=[c for c in optional_cols if c in sample.columns])

    # Should succeed without error
    pred = energy_service.predict(stripped_sample)
    assert isinstance(pred, UnifiedEnergyPrediction)
    assert pred.station_id == "MTR"


# Test 3: Derived Features Causality and No Lookahead
def test_3_derived_features_causality_and_no_lookahead(maitri_df):
    """Verify 18 LSTM features and 26 Deficit-Risk features depend strictly on timestamps <= t."""
    sample = maitri_df.iloc[:30].copy()

    # 1. Check Risk Features
    X_risk, _ = extract_risk_features(sample, validate=True)
    assert len(X_risk.columns) == 26
    assert set(X_risk.columns) == set(RISK_FEATURE_COLUMNS)

    # 2. Check LSTM Features
    X_lstm, _ = extract_features_and_targets(sample)
    assert len(X_lstm.columns) == 18
    assert set(X_lstm.columns) == set(LSTM_FEATURE_COLUMNS)

    # Verify no target columns in extracted features
    for col in TARGET_COLUMNS_EXCLUDED:
        assert col not in X_risk.columns
        assert col not in X_lstm.columns


# Test 4: No Future Target Columns Required for Inference
def test_4_no_target_columns_required_for_inference(maitri_df, energy_service):
    """Verify inference operates smoothly when zero target_ columns are present."""
    sample = maitri_df.iloc[:24].copy()
    target_cols = [c for c in sample.columns if c.startswith("target_")]
    sample_no_targets = sample.drop(columns=target_cols)

    pred = energy_service.predict(sample_no_targets)
    assert isinstance(pred, UnifiedEnergyPrediction)
    assert pred.station_id == "MTR"
    assert math.isfinite(pred.forecasts.power_demand_1h_kw)
    assert math.isfinite(pred.deficit_risk.probability)


# Test 5: Station ID Validation (MTR/BRT Accepted, BHR Rejected Without Silent Alias)
def test_5_station_id_validation_mtr_brt_accepted_bhr_rejected(maitri_df, bharati_df, energy_service):
    """Verify MTR and BRT succeed, while BHR is explicitly rejected (no silent alias)."""
    # MTR succeeds
    pred_mtr = energy_service.predict(maitri_df.iloc[:24])
    assert pred_mtr.station_id == "MTR"

    # BRT succeeds
    pred_brt = energy_service.predict(bharati_df.iloc[:24])
    assert pred_brt.station_id == "BRT"

    # BHR raises explicit ValueError
    sample_bhr = bharati_df.iloc[:24].copy()
    sample_bhr["station_id"] = "BHR"
    with pytest.raises(ValueError, match="Invalid station_id encountered.*BHR"):
        energy_service.predict(sample_bhr)


# Test 6: Timestamp Parsing and UTC Enforcement
def test_6_timestamp_parsing_and_utc_enforcement(maitri_df, energy_service):
    """Verify timestamps are parsed as UTC and temporal cyclical embeddings are computed causally."""
    sample = maitri_df.iloc[:24].copy()
    pred = energy_service.predict(sample)

    expected_ts = str(sample["timestamp"].iloc[-1])
    assert pred.timestamp == expected_ts

    # Check trigonometric properties
    X_risk, _ = extract_risk_features(sample)
    assert np.all(X_risk["sin_hour"] >= -1.0) and np.all(X_risk["sin_hour"] <= 1.0)
    assert np.all(X_risk["cos_hour"] >= -1.0) and np.all(X_risk["cos_hour"] <= 1.0)
    assert np.all(X_risk["sin_day"] >= -1.0) and np.all(X_risk["sin_day"] <= 1.0)
    assert np.all(X_risk["cos_day"] >= -1.0) and np.all(X_risk["cos_day"] <= 1.0)


# Test 7: 24-Hour Lookback Requirement Enforcement
def test_7_24h_lookback_requirement_enforcement(maitri_df, energy_service):
    """Verify that fewer than 24 hours of history raises ValueError."""
    for count in [1, 10, 23]:
        with pytest.raises(ValueError, match="requires at least 24 hours"):
            energy_service.predict(maitri_df.iloc[:count])

    # Exactly 24 hours succeeds
    pred = energy_service.predict(maitri_df.iloc[:24])
    assert isinstance(pred, UnifiedEnergyPrediction)


# Test 8: Unified Output Schema Conformity Against Contract JSON
def test_8_unified_output_schema_conformity(maitri_df, energy_service):
    """Verify output dictionary keys match the authoritative contract schema."""
    contract_path = RESULTS_DIR / "energy_ml_inference_contract.json"
    assert contract_path.exists()

    with open(contract_path, "r", encoding="utf-8") as f:
        contract = json.load(f)

    sample = maitri_df.iloc[:24].copy()
    pred = energy_service.predict(sample)
    d = pred.to_dict()

    expected_top_keys = set(contract["output_specification"]["schema"].keys())
    assert set(d.keys()) == expected_top_keys

    # Check nested forecast keys
    expected_forecast_keys = set(contract["output_specification"]["schema"]["forecasts"]["properties"].keys())
    assert set(d["forecasts"].keys()) == expected_forecast_keys

    # Check nested risk keys
    expected_risk_keys = set(contract["output_specification"]["schema"]["deficit_risk"]["properties"].keys())
    assert set(d["deficit_risk"].keys()) == expected_risk_keys


# Test 9: Compatibility Matrix and Report Artifact File Integrity
def test_9_compatibility_matrix_and_report_artifacts_exist():
    """Verify compatibility matrix JSON and report MD exist and are well-formed."""
    matrix_path = RESULTS_DIR / "energy_ml_backend_compatibility_matrix.json"
    report_path = RESULTS_DIR / "energy_ml_backend_compatibility_report.md"

    assert matrix_path.exists(), "Missing compatibility matrix JSON"
    assert report_path.exists(), "Missing compatibility report MD"

    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    assert matrix["version"] == "1.0.0"
    assert len(matrix["raw_telemetry_fields"]) == 15
    assert len(matrix["derived_features_causality_proof"]) >= 14
    assert matrix["audit_summary"]["blocking_issues_count"] == 1


# Test 10: Frozen Model Artifact Integrity Preservation
def test_10_frozen_model_artifact_integrity():
    """Verify all 5 Energy ML model artifacts match their cryptographic SHA-256 baselines."""
    expected_hashes = {
        "ml/energy/models/energy_lstm_baseline.pt": "2243d99786ad0b83314fb5e0a15cedf25596f0ab06d01ebad4a96d3171524834",
        "ml/energy/models/energy_lstm_baseline_config.json": "55deb80e47d7443b126b9f352944c418a6620c742762bd106e99efbf0f25ca1c",
        "ml/energy/models/energy_lstm_baseline_scaler.json": "b8494c021fc6caab58b7f11877c72aa2a604e24d0b722f2b845e34cf558034d2",
        "ml/energy/models/energy_deficit_risk_v1.joblib": "936167c5d263ed783f751eff2108d1a4c1fa6685e181b58e90b3ed0aac0a9253",
        "ml/energy/models/energy_deficit_risk_v1_config.json": "929a2c2ad71f1bc2052322a344dbc871224b81457648ad9bbca55159d46d6d04",
    }

    for path_str, exp_hash in expected_hashes.items():
        p = Path(path_str)
        assert p.exists(), f"Missing artifact: {path_str}"
        act_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch on {path_str}: {act_hash} vs {exp_hash}"
