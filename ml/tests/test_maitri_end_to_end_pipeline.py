"""
Comprehensive End-to-End ML Inference Pipeline Tests for Maitri Station (SIH26060 - Person C).

Verifies the entire ML inference lifecycle:
1. Normal telemetry sequence
2. Spike telemetry sequence
3. Drift telemetry sequence
4. Stuck-value telemetry sequence
5. Dropout and missing data handling
6. Insufficient data streaming behavior
7. Malformed telemetry contract rejection
8. Unsupported station rejection
9. Unsupported sensor rejection
10. Interleaved multi-sensor history isolation
11. JSON serialization roundtrip
12. Model version propagation
13. Anomaly type classification propagation
14. Model integrity validation before inference
15. Repeated deterministic execution
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from ml.inference.anomaly_type_classifier import (
    SUPPORTED_ANOMALY_TYPES,
    AnomalyTypeClassifier,
)
from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_STATUSES,
    InvalidContractError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.lstm_inference import LSTMAutoencoderInference
from ml.inference.validate_maitri_pipeline import MaitriPipelineValidator
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    ModelVersionMismatchError,
    validate_model_artifacts,
)


@pytest.fixture(scope="module")
def inference_engine() -> LSTMAutoencoderInference:
    """Fixture providing an initialized LSTM Autoencoder inference engine."""
    return LSTMAutoencoderInference(device="cpu")


@pytest.fixture(scope="module")
def synthetic_df() -> pd.DataFrame:
    """Fixture providing the synthetic telemetry dataset."""
    dataset_path = Path(__file__).resolve().parent.parent / "data" / "maitri_synthetic_telemetry.csv"
    assert dataset_path.exists(), f"Synthetic dataset missing at {dataset_path}"
    return pd.read_csv(dataset_path)


# -----------------------------------------------------------------------------
# Test 1: Normal Telemetry Sequence
# -----------------------------------------------------------------------------
def test_1_normal_sequence(inference_engine: LSTMAutoencoderInference, synthetic_df: pd.DataFrame) -> None:
    """Verify normal telemetry sequence produces INSUFFICIENT_DATA initially, then valid inference."""
    inference_engine.reset_history()
    sub = synthetic_df[(synthetic_df["sensor_id"] == "TEMP_001") & (synthetic_df["anomaly_type"] == "NORMAL")].head(35)
    
    for i, (_, row) in enumerate(sub.iterrows()):
        inp = TelemetryInput(
            station_id=str(row["station_id"]),
            sensor_id=str(row["sensor_id"]),
            timestamp=str(row["timestamp"]),
            value=float(row["value"]),
            unit=str(row["unit"]),
            quality="GOOD",
        )
        out = inference_engine.infer_telemetry(inp)

        if i < 29:
            assert out.anomaly_status == "INSUFFICIENT_DATA"
            assert out.anomaly_score is None
            assert out.anomaly_type is None
        else:
            assert out.anomaly_status in {"NORMAL", "ANOMALY"}
            assert out.anomaly_score is not None
            if out.anomaly_status == "NORMAL":
                assert out.anomaly_type == "NORMAL"


# -----------------------------------------------------------------------------
# Test 2: Spike Sequence
# -----------------------------------------------------------------------------
def test_2_spike_sequence(inference_engine: LSTMAutoencoderInference, synthetic_df: pd.DataFrame) -> None:
    """Verify spike sequence produces SPIKE or UNKNOWN anomaly type when flagged as ANOMALY."""
    inference_engine.reset_history()
    normal_sub = synthetic_df[(synthetic_df["sensor_id"] == "TEMP_001") & (synthetic_df["anomaly_type"] == "NORMAL")].head(30)
    for _, row in normal_sub.iterrows():
        inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=str(row["timestamp"]),
            value=float(row["value"]),
            quality="GOOD",
        ))

    # Send sharp spike pulse
    spike_input = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-02T00:00:00Z",
        value=15.0,  # Extreme jump from ~ -15.0
        quality="GOOD",
    )
    out = inference_engine.infer_telemetry(spike_input)
    assert out.anomaly_status == "ANOMALY"
    assert out.anomaly_score is not None and out.anomaly_score > inference_engine.threshold
    assert out.anomaly_type in {"SPIKE", "UNKNOWN"}


# -----------------------------------------------------------------------------
# Test 3: Drift Sequence
# -----------------------------------------------------------------------------
def test_3_drift_sequence(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify gradual drift sequence produces DRIFT or UNKNOWN anomaly type when flagged as ANOMALY."""
    inference_engine.reset_history()
    # Warm up 30 steps with nominal sinusoidal temperature
    for i in range(30):
        val = -15.0 + 0.1 * np.sin(i)
        inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=float(val),
            quality="GOOD",
        ))

    # Feed steady monotonic drift ramp
    drift_types_observed = set()
    for i in range(30):
        val = -15.0 + 0.30 * i
        out = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T01:{i:02d}:00Z",
            value=float(val),
            quality="GOOD",
        ))
        if out.anomaly_status == "ANOMALY":
            assert out.anomaly_type in {"DRIFT", "UNKNOWN", "SPIKE"}
            drift_types_observed.add(out.anomaly_type)

    assert "DRIFT" in drift_types_observed


# -----------------------------------------------------------------------------
# Test 4: Stuck-Value Sequence
# -----------------------------------------------------------------------------
def test_4_stuck_value_sequence(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify flatline sequence produces STUCK_VALUE or UNKNOWN anomaly type when flagged as ANOMALY."""
    inference_engine.reset_history()
    for i in range(30):
        val = -15.0 + 0.1 * np.sin(i)
        inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=float(val),
            quality="GOOD",
        ))

    # Feed repeated constant flatline
    stuck_types_observed = set()
    for i in range(25):
        out = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T02:{i:02d}:00Z",
            value=-28.5,
            quality="GOOD",
        ))
        if out.anomaly_status == "ANOMALY":
            assert out.anomaly_type in {"STUCK_VALUE", "UNKNOWN", "SPIKE"}
            stuck_types_observed.add(out.anomaly_type)

    assert "STUCK_VALUE" in stuck_types_observed


# -----------------------------------------------------------------------------
# Test 5: Missing Data and Quality Handling
# -----------------------------------------------------------------------------
def test_5_missing_data(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify null values and bad quality return MISSING_DATA and clear the buffer."""
    inference_engine.reset_history()
    for i in range(30):
        inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=-15.0,
            quality="GOOD",
        ))

    # 1. None value
    null_out = inference_engine.infer_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:30:00Z",
        value=None,
        quality="GOOD",
    ))
    assert null_out.anomaly_status == "MISSING_DATA"
    assert null_out.anomaly_score is None
    assert null_out.anomaly_type is None

    # Next valid point must be INSUFFICIENT_DATA
    next_out = inference_engine.infer_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:31:00Z",
        value=-15.0,
        quality="GOOD",
    ))
    assert next_out.anomaly_status == "INSUFFICIENT_DATA"

    # 2. Bad quality tag
    bad_q_out = inference_engine.infer_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:32:00Z",
        value=-15.0,
        quality="BAD",
    ))
    assert bad_q_out.anomaly_status == "MISSING_DATA"
    assert bad_q_out.anomaly_score is None
    assert bad_q_out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 6: Insufficient Data Behavior
# -----------------------------------------------------------------------------
def test_6_insufficient_data(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify streaming fewer than 30 observations consistently returns INSUFFICIENT_DATA."""
    inference_engine.reset_history()
    for i in range(29):
        out = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="PRESS_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=990.0 + i * 0.01,
            quality="GOOD",
        ))
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None
        assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 7: Malformed Telemetry Rejection
# -----------------------------------------------------------------------------
def test_7_malformed_telemetry() -> None:
    """Verify invalid contract inputs raise InvalidContractError."""
    with pytest.raises(InvalidContractError):
        TelemetryInput(station_id="MTR", sensor_id="", timestamp="2026-09-17T10:00:00Z", value=10.0)

    with pytest.raises(InvalidContractError):
        TelemetryInput(station_id="MTR", sensor_id="TEMP_001", timestamp="", value=10.0)

    with pytest.raises(InvalidContractError):
        TelemetryInput(station_id="MTR", sensor_id="TEMP_001", timestamp="2026-09-17T10:00:00Z", value="invalid_num")  # type: ignore


# -----------------------------------------------------------------------------
# Test 8: Unsupported Station Rejection
# -----------------------------------------------------------------------------
def test_8_unsupported_station() -> None:
    """Verify station IDs outside SUPPORTED_STATIONS are strictly rejected."""
    for invalid_station in ["BHARATI", "BHT", "STATION_X", ""]:
        with pytest.raises((UnsupportedStationError, InvalidContractError)):
            TelemetryInput(station_id=invalid_station, sensor_id="TEMP_001", timestamp="2026-09-17T10:00:00Z", value=10.0)


# -----------------------------------------------------------------------------
# Test 9: Unsupported Sensor Rejection
# -----------------------------------------------------------------------------
def test_9_unsupported_sensor() -> None:
    """Verify sensor IDs outside SUPPORTED_SENSORS are strictly rejected."""
    for invalid_sensor in ["RADIATION_001", "GPS_001", "TEMP_999", "INVALID"]:
        with pytest.raises(UnsupportedSensorError):
            TelemetryInput(station_id="MTR", sensor_id=invalid_sensor, timestamp="2026-09-17T10:00:00Z", value=10.0)


# -----------------------------------------------------------------------------
# Test 10: Interleaved Multi-Sensor History Isolation
# -----------------------------------------------------------------------------
def test_10_interleaved_multi_sensor_histories(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify interleaved streams from multiple sensors maintain completely isolated sliding buffers."""
    inference_engine.reset_history()

    # Interleave TEMP_001 (30 points) and VIB_001 (15 points)
    for i in range(30):
        out_temp = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=-15.0 + 0.05 * np.sin(i),
            quality="GOOD",
        ))
        if i < 15:
            out_vib = inference_engine.infer_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id="VIB_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=0.85 + 0.01 * np.cos(i),
                quality="GOOD",
            ))
            assert out_vib.anomaly_status == "INSUFFICIENT_DATA"

    # TEMP_001 reached 30 observations
    assert out_temp.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_temp.anomaly_score is not None

    # Clear TEMP_001 with null value
    inference_engine.infer_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:30:00Z",
        value=None,
    ))

    # Add 15 more points to VIB_001; it should reach 30 and output scored inference
    for i in range(15, 30):
        out_vib = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="VIB_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=0.85 + 0.01 * np.cos(i),
            quality="GOOD",
        ))

    assert out_vib.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_vib.anomaly_score is not None


# -----------------------------------------------------------------------------
# Test 11: JSON Serialization Roundtrip
# -----------------------------------------------------------------------------
def test_11_json_serialization(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify all TelemetryInferenceOutput variants serialize to JSON and deserialize identically."""
    inference_engine.reset_history()
    for i in range(30):
        out = inference_engine.infer_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="HUM_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=55.0,
            unit="%",
            quality="GOOD",
        ))

    json_str = out.to_json(indent=2)
    deserialized = TelemetryInferenceOutput.from_json(json_str)

    assert deserialized.station_id == out.station_id
    assert deserialized.sensor_id == out.sensor_id
    assert deserialized.timestamp == out.timestamp
    assert deserialized.value == out.value
    assert deserialized.unit == out.unit
    assert deserialized.quality == out.quality
    assert deserialized.anomaly_score == out.anomaly_score
    assert deserialized.anomaly_status == out.anomaly_status
    assert deserialized.anomaly_type == out.anomaly_type
    assert deserialized.model_version == out.model_version


# -----------------------------------------------------------------------------
# Test 12: Model Version Propagation
# -----------------------------------------------------------------------------
def test_12_model_version_propagation(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify model version 'lstm-ae-v1' is consistently propagated to all outputs."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="POWER_001",
        timestamp="2026-03-01T00:00:00Z",
        value=35.0,
        quality="GOOD",
    )
    out = inference_engine.infer_telemetry(inp)
    assert out.model_version == "lstm-ae-v1"


# -----------------------------------------------------------------------------
# Test 13: Anomaly Type Propagation
# -----------------------------------------------------------------------------
def test_13_anomaly_type_propagation(inference_engine: LSTMAutoencoderInference) -> None:
    """Verify anomaly_type is correctly typed and matches valid domain constraints."""
    inference_engine.reset_history()
    
    # 1. Insufficient data -> None
    out_insuf = inference_engine.infer_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-03-01T00:00:00Z", -15.0))
    assert out_insuf.anomaly_type is None

    # 2. Missing data -> None
    out_miss = inference_engine.infer_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-03-01T00:01:00Z", None))
    assert out_miss.anomaly_type is None

    # 3. Scored data -> one of SUPPORTED_ANOMALY_TYPES
    for i in range(30):
        out_scored = inference_engine.infer_telemetry(TelemetryInput("MTR", "TEMP_001", f"2026-03-01T01:{i:02d}:00Z", -15.0 + i * 0.3))

    assert out_scored.anomaly_type in SUPPORTED_ANOMALY_TYPES


# -----------------------------------------------------------------------------
# Test 14: Model Integrity Validation
# -----------------------------------------------------------------------------
def test_14_model_integrity_validation() -> None:
    """Verify model artifact SHA-256 and byte size integrity validation passes."""
    report = validate_model_artifacts(model_version=DEFAULT_MODEL_VERSION, raise_on_error=True)
    assert report.overall_status == "VALID"
    assert len(report.errors) == 0
    assert len(report.artifact_results) == 4
    for key, spec in report.artifact_results.items():
        assert spec["status"] == "VALID"
        assert spec["actual_sha256"] == spec["expected_sha256"]
        assert spec["actual_size"] == spec["expected_size"]


# -----------------------------------------------------------------------------
# Test 15: Repeated Deterministic Execution
# -----------------------------------------------------------------------------
def test_15_repeated_deterministic_execution() -> None:
    """Verify two independent inference instances produce bitwise identical outputs for identical inputs."""
    engine1 = LSTMAutoencoderInference(device="cpu")
    engine2 = LSTMAutoencoderInference(device="cpu")

    inputs = [
        TelemetryInput("MTR", "PRESS_001", f"2026-03-01T00:{i:02d}:00Z", 990.0 + 0.2 * np.sin(i), quality="GOOD")
        for i in range(35)
    ]

    outputs1 = [engine1.infer_telemetry(inp).to_dict() for inp in inputs]
    outputs2 = [engine2.infer_telemetry(inp).to_dict() for inp in inputs]

    assert outputs1 == outputs2
