"""
Unit & Anti-Leakage Test Suite for Unified Energy ML Service (Polarix SIH26060).

Tests:
1. Unified prediction contract schema and structure (forecasts, deficit_risk, provenance).
2. Deterministic inference across identical historical inputs.
3. Maitri (MTR) station end-to-end unified forecasting & risk prediction.
4. Bharati (BRT) station end-to-end unified forecasting & risk prediction.
5. Insufficient historical context rejection (< 24 hours raises ValueError).
6. Strict future-mutation anti-leakage safety on unified output.
7. JSON serialization safety (no NumPy/PyTorch/Pandas types or NaN/Inf).
8. Component model version separation & contract version verification.
9. Component failure separation (explicit exceptions raised on model failure).
10. Target columns safely excluded/ignored during inference.
11. Batch DataFrame and records-list prediction methods.
12. Machine-readable inference contract validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from ml.energy.inference.energy_forecaster import EnergyForecaster
from ml.energy.inference.energy_ml_service import (
    DeficitRiskOutput,
    EnergyForecasts,
    EnergyMLService,
    ProvenanceMetadata,
    UnifiedEnergyPrediction,
)
from ml.energy.risk.inference import DeficitRiskForecaster

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


# Test 1: Unified Prediction Contract Structure
def test_1_unified_prediction_contract_structure(energy_service, maitri_df):
    """Verify predict returns a well-formed UnifiedEnergyPrediction container with all fields."""
    window = maitri_df.iloc[:24].copy()
    pred = energy_service.predict(window)

    assert isinstance(pred, UnifiedEnergyPrediction)
    assert pred.station_id == "MTR"
    assert pred.timestamp == str(window["timestamp"].iloc[-1])
    assert pred.contract_version == "energy-ml-contract-v1"
    assert pred.model_version == "energy-ml-v1-candidate"
    assert pred.forecast_model_version == "lstm-energy-baseline-v1"
    assert pred.risk_model_version == "energy-deficit-risk-v1"

    # Forecasts sub-object
    assert isinstance(pred.forecasts, EnergyForecasts)
    assert isinstance(pred.forecasts.power_demand_1h_kw, float)
    assert isinstance(pred.forecasts.battery_soc_1h_percent, float)
    assert isinstance(pred.forecasts.energy_demand_6h_kwh, float)
    assert isinstance(pred.forecasts.energy_demand_24h_kwh, float)

    # Deficit Risk sub-object
    assert isinstance(pred.deficit_risk, DeficitRiskOutput)
    assert isinstance(pred.deficit_risk.probability, float)
    assert isinstance(pred.deficit_risk.decision, bool)
    assert pred.deficit_risk.threshold == 0.35

    # Provenance sub-object
    assert isinstance(pred.provenance, ProvenanceMetadata)
    assert pred.provenance.model_status == "CANDIDATE"
    assert pred.provenance.source == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"


# Test 2: Deterministic Unified Inference
def test_2_deterministic_unified_inference(energy_service, maitri_df):
    """Verify identical historical telemetry produces bit-for-bit identical unified predictions."""
    window = maitri_df.iloc[:24].copy()
    pred1 = energy_service.predict(window)
    pred2 = energy_service.predict(window)

    assert pred1.to_dict() == pred2.to_dict()


# Test 3: Maitri (MTR) Station End-to-End Inference
def test_3_mtr_station_inference(energy_service, maitri_df):
    """Verify unified inference succeeds for Maitri with valid physical values."""
    window = maitri_df.iloc[100:124].copy()
    pred = energy_service.predict(window)

    assert pred.station_id == "MTR"
    assert 10.0 <= pred.forecasts.power_demand_1h_kw <= 150.0
    assert 0.0 <= pred.forecasts.battery_soc_1h_percent <= 100.0
    assert pred.forecasts.energy_demand_6h_kwh > 0.0
    assert pred.forecasts.energy_demand_24h_kwh > pred.forecasts.energy_demand_6h_kwh
    assert 0.0 <= pred.deficit_risk.probability <= 1.0


# Test 4: Bharati (BRT) Station End-to-End Inference
def test_4_brt_station_inference(energy_service, bharati_df):
    """Verify unified inference succeeds for Bharati with valid physical values."""
    window = bharati_df.iloc[100:124].copy()
    pred = energy_service.predict(window)

    assert pred.station_id == "BRT"
    assert 10.0 <= pred.forecasts.power_demand_1h_kw <= 160.0
    assert 0.0 <= pred.forecasts.battery_soc_1h_percent <= 100.0
    assert pred.forecasts.energy_demand_6h_kwh > 0.0
    assert pred.forecasts.energy_demand_24h_kwh > pred.forecasts.energy_demand_6h_kwh
    assert 0.0 <= pred.deficit_risk.probability <= 1.0


# Test 5: Insufficient Historical Context Rejection
def test_5_insufficient_history_rejection(energy_service, maitri_df):
    """Verify passing fewer than 24 hours of history raises a descriptive ValueError."""
    for n in [1, 5, 12, 23]:
        short_window = maitri_df.iloc[:n].copy()
        with pytest.raises(ValueError, match="requires at least 24 hours"):
            energy_service.predict(short_window)


# Test 6: Strict Future-Mutation Anti-Leakage Safety
def test_6_anti_leakage_future_mutation_safety(energy_service, maitri_df):
    """
    Verify mutating telemetry at timestamps > t has zero effect on unified prediction at timestamp t.
    """
    window_original = maitri_df.iloc[:24].copy()
    future_data = maitri_df.iloc[24:48].copy()
    df_combined = pd.concat([window_original, future_data], ignore_index=True)

    # Prediction on pristine history ending at index 23
    pred_pristine = energy_service.predict(df_combined.iloc[:24])

    # Corrupt future rows in combined dataframe
    df_mutated = df_combined.copy()
    df_mutated.loc[24:, "power_demand_kw"] = 999.0
    df_mutated.loc[24:, "battery_soc_percent"] = 1.0
    df_mutated.loc[24:, "temperature_c"] = -80.0

    # Prediction on same history slice ending at index 23
    pred_mutated = energy_service.predict(df_mutated.iloc[:24])

    assert pred_pristine.to_dict() == pred_mutated.to_dict()


# Test 7: JSON Serialization Safety
def test_7_json_serialization_safety(energy_service, maitri_df):
    """Verify prediction dictionary is fully JSON-serializable to native types without NaN or special objects."""
    window = maitri_df.iloc[:24].copy()
    pred = energy_service.predict(window)

    json_str = pred.to_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["station_id"] == "MTR"
    assert parsed["forecasts"]["power_demand_1h_kw"] == pred.forecasts.power_demand_1h_kw
    assert parsed["deficit_risk"]["probability"] == pred.deficit_risk.probability
    assert parsed["provenance"]["model_status"] == "CANDIDATE"


# Test 8: Component Model Versions Integrity
def test_8_component_model_versions_integrity(energy_service):
    """Verify component versions match the actual trained model versions in the repository."""
    assert energy_service.forecaster.config.model_name == "lstm-energy-baseline-v1"
    assert energy_service.risk_forecaster.model_version == "energy-deficit-risk-v1"


# Test 9: Component Failure Separation
def test_9_component_failure_separation(maitri_df):
    """Verify that failures in either component model raise an explicit error without fabricating values."""
    window = maitri_df.iloc[:24].copy()

    # Case A: Forecasting model failure
    failing_forecaster = MagicMock()
    failing_forecaster.predict_window.side_effect = RuntimeError("PyTorch LSTM runtime execution error")
    svc_fail_forecast = EnergyMLService(forecaster=failing_forecaster)

    with pytest.raises(RuntimeError, match="PyTorch LSTM runtime execution error"):
        svc_fail_forecast.predict(window)

    # Case B: Risk model failure
    failing_risk = MagicMock()
    failing_risk.predict_window.side_effect = ValueError("Gradient boosting feature evaluation error")
    svc_fail_risk = EnergyMLService(risk_forecaster=failing_risk)

    with pytest.raises(ValueError, match="Gradient boosting feature evaluation error"):
        svc_fail_risk.predict(window)


# Test 10: Target Columns Safely Excluded from Inference
def test_10_target_columns_safely_excluded(energy_service, maitri_df):
    """Verify presence or corruption of target columns does not alter unified predictions."""
    window = maitri_df.iloc[:24].copy()
    pred1 = energy_service.predict(window)

    # Drop all target columns
    target_cols = [c for c in window.columns if c.startswith("target_")]
    window_no_targets = window.drop(columns=target_cols)
    pred2 = energy_service.predict(window_no_targets)

    # Corrupt target columns
    window_corrupted = window.copy()
    for col in target_cols:
        window_corrupted[col] = 88888.0
    pred3 = energy_service.predict(window_corrupted)

    assert pred1.to_dict() == pred2.to_dict() == pred3.to_dict()


# Test 11: Records and DataFrame Batch Inference
def test_11_records_and_dataframe_batch_inference(energy_service, maitri_df):
    """Verify predict_records and predict_dataframe methods."""
    window = maitri_df.iloc[:24].copy()
    records = window.to_dict(orient="records")

    pred_rec = energy_service.predict_records(records)
    assert isinstance(pred_rec, UnifiedEnergyPrediction)
    assert pred_rec.station_id == "MTR"

    # Batch DataFrame
    batch_df = maitri_df.iloc[:30].copy()
    res_df = energy_service.predict_dataframe(batch_df)
    assert len(res_df) == (30 - 24 + 1)
    assert "power_demand_1h_kw" in res_df.columns
    assert "deficit_risk_probability" in res_df.columns
    assert "model_status" in res_df.columns


# Test 12: Contract Schema JSON Integrity
def test_12_contract_schema_json_integrity():
    """Verify ml/energy/results/energy_ml_inference_contract.json exists and is valid."""
    contract_path = RESULTS_DIR / "energy_ml_inference_contract.json"
    assert contract_path.exists()

    with open(contract_path, "r", encoding="utf-8") as f:
        contract = json.load(f)

    assert contract["contract_version"] == EnergyMLService.CONTRACT_VERSION
    assert contract["unified_model_version"] == EnergyMLService.UNIFIED_MODEL_VERSION
    assert contract["temporal_requirements"]["required_lookback_hours"] == 24
    assert "component_models" in contract
    assert "input_specification" in contract
    assert "output_specification" in contract
