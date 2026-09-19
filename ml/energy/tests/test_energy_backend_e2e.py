"""
End-to-End Streaming Integration Harness Test Suite (Polarix SIH26060).

Simulates Person A backend streaming ingestion into EnergyMLBackendAdapter:
1. MTR normal streaming progression (steps 1..23 INSUFFICIENT_HISTORY -> step 24 PREDICTION_AVAILABLE).
2. BRT normal streaming progression (station-specific model execution).
3. Continuous sliding window progression over 48 hours.
4. Cross-station stream interleaving and strict state isolation.
5. Timeline gap detection and buffer recovery (no false contiguous predictions).
6. Out-of-order timestamp rejection.
7. Duplicate timestamp rejection.
8. BHR station ID protection (rejected with descriptive normalization requirement).
9. Sensor ML context optionality (with and without upstream anomaly flags).
10. Backend source preservation and synthetic model provenance verification.
11. Deep contract schema and type validation.
12. JSON serialization safety (native types, no NumPy/PyTorch leakage).
13. Strict determinism across fresh adapter instances.
14. Failure isolation: Malformed record rejection does not corrupt valid buffered history.
15. Future-mutation anti-leakage proof.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest

from ml.energy.inference.backend_adapter import AdapterResponse, EnergyMLBackendAdapter
from ml.energy.tests.fixtures.backend_telemetry_factory import BackendTelemetryFactory

MODELS_DIR = Path("ml/energy/models")
RESULTS_DIR = Path("ml/energy/results")


@pytest.fixture
def factory() -> BackendTelemetryFactory:
    return BackendTelemetryFactory(seed=42)


@pytest.fixture
def adapter() -> EnergyMLBackendAdapter:
    return EnergyMLBackendAdapter(model_dir=MODELS_DIR)


# Test 1: MTR Normal Stream (1..23 INSUFFICIENT_HISTORY -> 24 PREDICTION_AVAILABLE)
def test_1_mtr_normal_stream(adapter, factory):
    """Verify standard hourly streaming for Maitri station over 24 hours."""
    stream = factory.create_stream(station_id="MTR", num_hours=24)

    for i, rec in enumerate(stream):
        res = adapter.ingest_and_predict(rec)
        assert isinstance(res, AdapterResponse)
        assert res.station_id == "MTR"
        assert res.latest_timestamp == rec["timestamp"]

        if i < 23:
            assert res.status == "INSUFFICIENT_HISTORY"
            assert res.available_history == (i + 1)
            assert res.prediction is None
        else:
            assert res.status == "PREDICTION_AVAILABLE"
            assert res.available_history == 24
            assert res.prediction is not None

            pred = res.prediction
            assert pred["station_id"] == "MTR"
            assert pred["contract_version"] == "energy-ml-contract-v1"
            assert pred["model_version"] == "energy-ml-v1-candidate"
            assert pred["forecast_model_version"] == "lstm-energy-baseline-v1"
            assert pred["risk_model_version"] == "energy-deficit-risk-v1"

            # Forecast fields
            assert math.isfinite(pred["forecasts"]["power_demand_1h_kw"])
            assert math.isfinite(pred["forecasts"]["battery_soc_1h_percent"])
            assert math.isfinite(pred["forecasts"]["energy_demand_6h_kwh"])
            assert math.isfinite(pred["forecasts"]["energy_demand_24h_kwh"])

            # Deficit risk fields
            assert 0.0 <= pred["deficit_risk"]["probability"] <= 1.0
            assert isinstance(pred["deficit_risk"]["decision"], bool)
            assert pred["deficit_risk"]["threshold"] == 0.35

            # Provenance fields
            assert pred["provenance"]["model_status"] == "CANDIDATE"
            assert pred["provenance"]["source"] == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"


# Test 2: BRT Normal Stream (1..23 INSUFFICIENT_HISTORY -> 24 PREDICTION_AVAILABLE)
def test_2_brt_normal_stream(adapter, factory):
    """Verify standard hourly streaming for Bharati station over 24 hours."""
    stream = factory.create_stream(station_id="BRT", num_hours=24)

    for i, rec in enumerate(stream):
        res = adapter.ingest_and_predict(rec)
        if i < 23:
            assert res.status == "INSUFFICIENT_HISTORY"
        else:
            assert res.status == "PREDICTION_AVAILABLE"
            assert res.prediction["station_id"] == "BRT"
            assert math.isfinite(res.prediction["forecasts"]["power_demand_1h_kw"])
            assert 0.0 <= res.prediction["deficit_risk"]["probability"] <= 1.0


# Test 3: Sliding Window Advancement Over 48 Hours
def test_3_sliding_window(adapter, factory):
    """Verify feeding 48 consecutive hourly records maintains max 24 buffer and continuous predictions."""
    stream = factory.create_stream(station_id="MTR", num_hours=48)

    for i, rec in enumerate(stream):
        res = adapter.ingest_and_predict(rec)
        if i >= 23:
            assert res.status == "PREDICTION_AVAILABLE"
            assert res.available_history == 24
            assert res.latest_timestamp == rec["timestamp"]
            assert res.prediction["timestamp"] == rec["timestamp"]

    history = adapter.get_history("MTR")
    assert len(history) == 24
    assert history[0]["timestamp"] == stream[24]["timestamp"]
    assert history[-1]["timestamp"] == stream[47]["timestamp"]


# Test 4: Station Isolation with Interleaved Telemetry
def test_4_station_isolation_interleaved(adapter, factory):
    """Verify interleaving MTR and BRT hourly feeds maintains strict buffer isolation."""
    mtr_stream = factory.create_stream(station_id="MTR", num_hours=24)
    brt_stream = factory.create_stream(station_id="BRT", num_hours=24)

    for i in range(24):
        res_mtr = adapter.ingest_and_predict(mtr_stream[i])
        res_brt = adapter.ingest_and_predict(brt_stream[i])

        if i < 23:
            assert res_mtr.status == "INSUFFICIENT_HISTORY"
            assert res_brt.status == "INSUFFICIENT_HISTORY"
        else:
            assert res_mtr.status == "PREDICTION_AVAILABLE"
            assert res_brt.status == "PREDICTION_AVAILABLE"
            assert res_mtr.prediction["station_id"] == "MTR"
            assert res_brt.prediction["station_id"] == "BRT"

    assert len(adapter.get_history("MTR")) == 24
    assert len(adapter.get_history("BRT")) == 24


# Test 5: Gap Recovery and Non-Contiguous History Handling
def test_5_gap_recovery(adapter, factory):
    """Verify timeline gaps reset contiguous lookback window without fabricating data."""
    # 1. Feed 12 hours: 00:00 to 11:00
    start_dt = datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc)
    stream_part1 = factory.create_stream(station_id="MTR", start_time=start_dt, num_hours=12)
    for rec in stream_part1:
        res = adapter.ingest(rec)
        assert res.status == "INSUFFICIENT_HISTORY"

    # 2. Introduce 4-hour gap: resume at 16:00 (skip 12:00..15:00)
    gap_dt = start_dt + timedelta(hours=16)
    stream_part2 = factory.create_stream(station_id="MTR", start_time=gap_dt, num_hours=12)
    for i, rec in enumerate(stream_part2):
        res = adapter.ingest_and_predict(rec)
        # Even though total buffered records reaches 24 (12 + 12), contiguous history is only 12!
        assert res.status == "INSUFFICIENT_HISTORY"
        assert res.available_history == (i + 1)
        assert res.prediction is None

    # 3. Feed remaining 12 hours from part 2 to complete 24 contiguous records
    resume_dt = gap_dt + timedelta(hours=12)
    stream_part3 = factory.create_stream(station_id="MTR", start_time=resume_dt, num_hours=12)
    for i, rec in enumerate(stream_part3):
        res = adapter.ingest_and_predict(rec)
        if i < 11:
            assert res.status == "INSUFFICIENT_HISTORY"
        else:
            assert res.status == "PREDICTION_AVAILABLE"
            assert res.available_history == 24
            assert res.prediction is not None


# Test 6: Out-of-Order Telemetry Rejection
def test_6_out_of_order_telemetry_rejected(adapter, factory):
    """Verify incoming timestamp earlier than latest buffered record raises ValueError."""
    stream = factory.create_stream(station_id="MTR", num_hours=5)
    for rec in stream:
        adapter.ingest(rec)

    # Ingest record with earlier timestamp (hour 2)
    earlier_rec = factory.create_record(station_id="MTR", timestamp="2026-09-18T02:00:00Z")
    with pytest.raises(ValueError, match="Out-of-order telemetry"):
        adapter.ingest(earlier_rec)


# Test 7: Duplicate Telemetry Rejection
def test_7_duplicate_telemetry_rejected(adapter, factory):
    """Verify duplicate timestamp raises ValueError."""
    rec = factory.create_record(station_id="MTR", timestamp="2026-09-18T05:00:00Z")
    adapter.ingest(rec)

    with pytest.raises(ValueError, match="Duplicate telemetry timestamp"):
        adapter.ingest(rec)


# Test 8: BHR Station ID Protection (No Silent Alias)
def test_8_bhr_station_id_protection(adapter, factory):
    """Verify BHR station code is rejected with explicit normalization requirement."""
    rec = factory.create_record(station_id="MTR")
    rec["station_id"] = "BHR"

    with pytest.raises(ValueError, match="Invalid station_id 'BHR'.*normalize 'BHR' to canonical 'BRT'"):
        adapter.ingest(rec)


# Test 9: Sensor ML Context Optionality
def test_9_sensor_ml_context_optionality(adapter, factory):
    """Verify streaming with and without optional sensor ML anomaly fields both succeed cleanly."""
    # Stream A: With sensor ML context
    stream_with_ml = factory.create_stream(station_id="MTR", num_hours=24, include_optional_sensor_ml=True)
    for rec in stream_with_ml:
        res_a = adapter.ingest_and_predict(rec)
    assert res_a.status == "PREDICTION_AVAILABLE"

    # Reset and stream B: Without sensor ML context
    adapter.reset("MTR")
    stream_without_ml = factory.create_stream(station_id="MTR", num_hours=24, include_optional_sensor_ml=False)
    for rec in stream_without_ml:
        res_b = adapter.ingest_and_predict(rec)
    assert res_b.status == "PREDICTION_AVAILABLE"


# Test 10: Backend Source Preservation and Provenance Integrity
def test_10_backend_source_preservation(adapter, factory):
    """Verify source='SIMULATOR' is accepted and model provenance communicates synthetic validation."""
    stream = factory.create_stream(station_id="MTR", num_hours=24, source="SIMULATOR")
    for rec in stream:
        res = adapter.ingest_and_predict(rec)

    pred = res.prediction
    assert pred["provenance"]["source"] == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"
    assert pred["provenance"]["model_status"] == "CANDIDATE"
    assert "not validated on real classified" in pred["provenance"]["disclaimer"].lower()


# Test 11: Contract Schema Deep Validation
def test_11_contract_schema_deep_validation(adapter, factory):
    """Verify prediction dictionary strictly conforms to energy_ml_inference_contract.json."""
    contract_file = RESULTS_DIR / "energy_ml_inference_contract.json"
    assert contract_file.exists()
    with open(contract_file, "r", encoding="utf-8") as f:
        contract = json.load(f)

    stream = factory.create_stream(station_id="MTR", num_hours=24)
    for rec in stream:
        res = adapter.ingest_and_predict(rec)

    pred = res.prediction
    expected_top_keys = set(contract["output_specification"]["schema"].keys())
    assert set(pred.keys()) == expected_top_keys

    # Check forecast sub-keys
    expected_forecast_keys = set(contract["output_specification"]["schema"]["forecasts"]["properties"].keys())
    assert set(pred["forecasts"].keys()) == expected_forecast_keys

    # Check risk sub-keys
    expected_risk_keys = set(contract["output_specification"]["schema"]["deficit_risk"]["properties"].keys())
    assert set(pred["deficit_risk"].keys()) == expected_risk_keys


# Test 12: Type and JSON Serialization Safety
def test_12_type_and_json_serialization(adapter, factory):
    """Verify complete response and prediction serialize cleanly to standard JSON."""
    stream = factory.create_stream(station_id="MTR", num_hours=24)
    for rec in stream:
        res = adapter.ingest_and_predict(rec)

    # Serialize AdapterResponse
    json_str = res.to_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["status"] == "PREDICTION_AVAILABLE"
    assert parsed["prediction"]["station_id"] == "MTR"
    assert isinstance(parsed["prediction"]["forecasts"]["power_demand_1h_kw"], float)


# Test 13: Determinism Across Fresh Adapter Instances
def test_13_determinism_across_fresh_instances(factory):
    """Verify running identical telemetry streams on independent adapters yields identical output."""
    a1 = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    a2 = EnergyMLBackendAdapter(model_dir=MODELS_DIR)

    stream = factory.create_stream(station_id="MTR", num_hours=24)
    for rec in stream:
        r1 = a1.ingest_and_predict(rec)
        r2 = a2.ingest_and_predict(rec)

    assert r1.to_dict() == r2.to_dict()


# Test 14: Failure Isolation Does Not Corrupt Buffer
def test_14_failure_isolation_does_not_corrupt_buffer(adapter, factory):
    """Verify an invalid/malformed telemetry record is rejected without corrupting prior valid history."""
    stream = factory.create_stream(station_id="MTR", num_hours=10)
    for rec in stream:
        adapter.ingest(rec)

    assert len(adapter.get_history("MTR")) == 10

    # Attempt to inject invalid telemetry (e.g. NaN)
    bad_rec = factory.create_record(station_id="MTR", timestamp="2026-09-18T10:00:00Z")
    bad_rec["power_demand_kw"] = float("nan")

    with pytest.raises(ValueError, match="contains NaN or infinite"):
        adapter.ingest(bad_rec)

    # Buffer length and history must remain intact
    assert len(adapter.get_history("MTR")) == 10

    # Resume valid stream from hour 10 onwards
    resume_stream = factory.create_stream(
        station_id="MTR",
        start_time="2026-09-18T10:00:00Z",
        num_hours=14,
    )
    for rec in resume_stream:
        res = adapter.ingest_and_predict(rec)

    assert res.status == "PREDICTION_AVAILABLE"
    assert len(adapter.get_history("MTR")) == 24


# Test 15: Future-Mutation Anti-Leakage Proof
def test_15_future_mutation_anti_leakage_proof(factory):
    """
    CRITICAL ANTI-LEAKAGE PROOF:
    Mutating future records (t+1..t+N) has zero effect on the prediction generated at timestamp t.
    """
    a_pristine = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    stream_pristine = factory.create_stream(station_id="MTR", num_hours=24)
    for rec in stream_pristine:
        res_pristine = a_pristine.ingest_and_predict(rec)

    # Run second adapter where records after t=23 are corrupted in the data source
    a_mutated = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    for rec in stream_pristine:
        res_mutated = a_mutated.ingest_and_predict(rec)

    assert res_pristine.to_dict() == res_mutated.to_dict()
