"""
Unit and Integration Tests for Maitri ML Service Boundary (SIH26060 - Person C).

Verifies the MaitriMLService adapter:
1. Service initialization succeeds with valid model artifacts.
2. Valid Maitri telemetry is accepted.
3. First 29 observations return INSUFFICIENT_DATA.
4. The 30th valid observation produces an inference result.
5. Missing telemetry returns MISSING_DATA.
6. Missing data clears the relevant sensor history.
7. Different sensors maintain independent histories.
8. Unsupported station is rejected.
9. Unsupported sensor is rejected.
10. Output is a valid TelemetryInferenceOutput.
11. Model version remains lstm-ae-v1.
12. No retraining occurs during service inference.
13. Model integrity validation remains active.
14. JSON serialization remains lossless.
15. Resetting one sensor does not affect another sensor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    InvalidContractError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.models.model_registry import ModelIntegrityError, validate_model_artifacts


@pytest.fixture
def ml_service() -> MaitriMLService:
    """Fixture providing a freshly initialized MaitriMLService instance."""
    service = MaitriMLService(device="cpu")
    service.reset_all()
    return service


# -----------------------------------------------------------------------------
# Test 1: Service Initialization
# -----------------------------------------------------------------------------
def test_1_service_initialization(ml_service: MaitriMLService) -> None:
    """Verify service initializes successfully and exposes expected diagnostic metadata."""
    info = ml_service.get_service_info()
    assert info["service_name"] == "MaitriMLService"
    assert info["station_id"] == "MTR"
    assert info["model_version"] == "lstm-ae-v1"
    assert info["sequence_length"] == 30
    assert info["reconstruction_threshold"] == pytest.approx(0.017674, rel=1e-4)
    assert info["status"] == "READY"
    assert set(info["supported_sensors"]) == set(SUPPORTED_SENSORS)


# -----------------------------------------------------------------------------
# Test 2: Valid Maitri Telemetry Acceptance
# -----------------------------------------------------------------------------
def test_2_valid_telemetry_accepted(ml_service: MaitriMLService) -> None:
    """Verify valid TelemetryInput instances for all 5 sensors are accepted without error."""
    for sensor in SUPPORTED_SENSORS:
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id=sensor,
            timestamp="2026-09-18T00:00:00Z",
            value=-15.0,
            quality="GOOD",
        )
        out = ml_service.process_telemetry(inp)
        assert isinstance(out, TelemetryInferenceOutput)
        assert out.station_id == "MTR"
        assert out.sensor_id == sensor


# -----------------------------------------------------------------------------
# Test 3: First 29 Observations Return INSUFFICIENT_DATA
# -----------------------------------------------------------------------------
def test_3_first_29_insufficient_data(ml_service: MaitriMLService) -> None:
    """Verify the first 29 observations return INSUFFICIENT_DATA with null score and type."""
    for step in range(1, 30):
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=-15.0 + 0.01 * step,
            quality="GOOD",
        )
        out = ml_service.process_telemetry(inp)
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None
        assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 4: The 30th Observation Produces Inference Result
# -----------------------------------------------------------------------------
def test_4_30th_observation_produces_inference(ml_service: MaitriMLService) -> None:
    """Verify the 30th observation generates a numeric score and valid inference status."""
    for step in range(1, 30):
        ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="PRESS_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=990.0,
            quality="GOOD",
        ))

    step_30 = TelemetryInput(
        station_id="MTR",
        sensor_id="PRESS_001",
        timestamp="2026-09-18T00:30:00Z",
        value=990.0,
        quality="GOOD",
    )
    out = ml_service.process_telemetry(step_30)
    assert out.anomaly_status in {"NORMAL", "ANOMALY"}
    assert isinstance(out.anomaly_score, float)
    assert out.anomaly_type is not None


# -----------------------------------------------------------------------------
# Test 5: Missing Telemetry Returns MISSING_DATA
# -----------------------------------------------------------------------------
def test_5_missing_telemetry_returns_missing_data(ml_service: MaitriMLService) -> None:
    """Verify null values and bad quality tags return MISSING_DATA with null score and type."""
    # Null value
    out_null = ml_service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-09-18T00:00:00Z",
        value=None,
        quality="GOOD",
    ))
    assert out_null.anomaly_status == "MISSING_DATA"
    assert out_null.anomaly_score is None
    assert out_null.anomaly_type is None

    # Bad quality
    out_bad = ml_service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-09-18T00:01:00Z",
        value=55.0,
        quality="BAD",
    ))
    assert out_bad.anomaly_status == "MISSING_DATA"
    assert out_bad.anomaly_score is None
    assert out_bad.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 6: Missing Data Clears Relevant Sensor History
# -----------------------------------------------------------------------------
def test_6_missing_data_clears_sensor_history(ml_service: MaitriMLService) -> None:
    """Verify receiving missing data resets the window buffer, requiring 30 new points."""
    # Feed 30 points to reach scored inference
    for step in range(1, 31):
        ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="VIB_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=0.85,
            quality="GOOD",
        ))

    # Send missing point
    ml_service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="VIB_001",
        timestamp="2026-09-18T00:31:00Z",
        value=None,
        quality="GOOD",
    ))

    # Next valid point must now return INSUFFICIENT_DATA
    next_out = ml_service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="VIB_001",
        timestamp="2026-09-18T00:32:00Z",
        value=0.85,
        quality="GOOD",
    ))
    assert next_out.anomaly_status == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# Test 7: Independent Histories for Different Sensors
# -----------------------------------------------------------------------------
def test_7_different_sensors_maintain_independent_histories(ml_service: MaitriMLService) -> None:
    """Verify interleaving multiple sensors never causes cross-sensor history contamination."""
    # Feed 30 points of POWER_001 and 10 points of TEMP_001
    for step in range(1, 31):
        out_power = ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="POWER_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=35.0,
            quality="GOOD",
        ))
        if step <= 10:
            out_temp = ml_service.process_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id="TEMP_001",
                timestamp=f"2026-09-18T00:{step:02d}:00Z",
                value=-15.0,
                quality="GOOD",
            ))
            assert out_temp.anomaly_status == "INSUFFICIENT_DATA"

    # POWER_001 reached 30 observations and produces inference
    assert out_power.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_power.anomaly_score is not None

    # Check buffer lengths via service diagnostic info
    info = ml_service.get_service_info()
    assert info["active_buffer_lengths"]["POWER_001"] == 30
    assert info["active_buffer_lengths"]["TEMP_001"] == 10


# -----------------------------------------------------------------------------
# Test 8: Unsupported Station Rejection
# -----------------------------------------------------------------------------
def test_8_unsupported_station_rejected(ml_service: MaitriMLService) -> None:
    """Verify station IDs other than 'MTR' are rejected with UnsupportedStationError."""
    for invalid_station in ["BHARATI", "BHT", "STATION_X", "UNKNOWN"]:
        with pytest.raises(UnsupportedStationError):
            ml_service.process_telemetry(TelemetryInput(
                station_id=invalid_station,
                sensor_id="TEMP_001",
                timestamp="2026-09-18T00:00:00Z",
                value=-15.0,
            ))


# -----------------------------------------------------------------------------
# Test 9: Unsupported Sensor Rejection
# -----------------------------------------------------------------------------
def test_9_unsupported_sensor_rejected(ml_service: MaitriMLService) -> None:
    """Verify sensor IDs outside SUPPORTED_SENSORS are rejected with UnsupportedSensorError."""
    for invalid_sensor in ["RADIATION_001", "GPS_001", "TEMP_999", "INVALID"]:
        with pytest.raises(UnsupportedSensorError):
            ml_service.process_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id=invalid_sensor,
                timestamp="2026-09-18T00:00:00Z",
                value=10.0,
            ))


# -----------------------------------------------------------------------------
# Test 10: Output is a Valid TelemetryInferenceOutput
# -----------------------------------------------------------------------------
def test_10_output_contract_type_and_fields(ml_service: MaitriMLService) -> None:
    """Verify returned output adheres strictly to TelemetryInferenceOutput schema and validation."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=-14.8,
        unit="°C",
        quality="GOOD",
        source="SIMULATOR",
    )
    out = ml_service.process_telemetry(inp)

    assert isinstance(out, TelemetryInferenceOutput)
    assert out.station_id == "MTR"
    assert out.sensor_id == "TEMP_001"
    assert out.timestamp == "2026-09-18T00:00:00Z"
    assert out.value == -14.8
    assert out.unit == "°C"
    assert out.quality == "GOOD"
    assert out.source == "SIMULATOR"
    assert out.model_version == "lstm-ae-v1"


# -----------------------------------------------------------------------------
# Test 11: Model Version Propagation
# -----------------------------------------------------------------------------
def test_11_model_version_preservation(ml_service: MaitriMLService) -> None:
    """Verify the model version 'lstm-ae-v1' is consistently preserved in all outputs."""
    for sensor in SUPPORTED_SENSORS:
        out = ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id=sensor,
            timestamp="2026-09-18T00:00:00Z",
            value=10.0,
        ))
        assert out.model_version == DEFAULT_MODEL_VERSION


# -----------------------------------------------------------------------------
# Test 12: Zero Retraining Occurs During Inference
# -----------------------------------------------------------------------------
def test_12_no_retraining_during_inference(ml_service: MaitriMLService) -> None:
    """Verify model parameters and threshold remain strictly frozen during inference execution."""
    initial_weights = [p.clone().detach() for p in ml_service._engine.model.parameters()]
    initial_threshold = ml_service.threshold

    # Stream 60 observations
    for i in range(60):
        ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T00:{i:02d}:00Z",
            value=-15.0 + 0.5 * np.sin(i),
            quality="GOOD",
        ))

    # Verify model parameters did not mutate
    for p_init, p_curr in zip(initial_weights, ml_service._engine.model.parameters()):
        assert (p_init == p_curr).all()

    # Verify threshold did not mutate
    assert ml_service.threshold == initial_threshold


# -----------------------------------------------------------------------------
# Test 13: Model Integrity Validation Remains Active
# -----------------------------------------------------------------------------
def test_13_model_integrity_validation_active(tmp_path: Path) -> None:
    """Verify corrupting a model manifest prevents service instantiation."""
    # Validate existing registry passes
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    assert report.overall_status == "VALID"

    # Corrupt manifest pointing to invalid file
    bad_manifest = tmp_path / "bad_manifest.json"
    bad_manifest.write_text(json.dumps({
        "model_version": "lstm-ae-v1",
        "artifacts": {
            "model": {
                "file": "non_existent_weights.pt",
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "size_bytes": 100,
            }
        }
    }))

    with pytest.raises(ModelIntegrityError):
        MaitriMLService(manifest_path=bad_manifest, verify_manifest=True)


# -----------------------------------------------------------------------------
# Test 14: Lossless JSON Serialization
# -----------------------------------------------------------------------------
def test_14_json_serialization_lossless(ml_service: MaitriMLService) -> None:
    """Verify JSON-string-in/out and dataclass serialization preserves all metadata losslessly."""
    json_in = json.dumps({
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": "2026-09-18T00:00:00Z",
        "value": -14.5,
        "unit": "°C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    })

    json_out = ml_service.process_json(json_in, indent=2)
    deserialized = TelemetryInferenceOutput.from_json(json_out)

    assert deserialized.station_id == "MTR"
    assert deserialized.sensor_id == "TEMP_001"
    assert deserialized.value == -14.5
    assert deserialized.unit == "°C"
    assert deserialized.model_version == "lstm-ae-v1"


# -----------------------------------------------------------------------------
# Test 15: Per-Sensor Reset Isolation
# -----------------------------------------------------------------------------
def test_15_reset_sensor_isolation(ml_service: MaitriMLService) -> None:
    """Verify resetting one sensor's buffer does not affect any other sensor's buffer."""
    # Fill 30 observations for PRESS_001 and 20 for VIB_001
    for step in range(1, 31):
        ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="PRESS_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=990.0,
            quality="GOOD",
        ))
        if step <= 20:
            ml_service.process_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id="VIB_001",
                timestamp=f"2026-09-18T00:{step:02d}:00Z",
                value=0.85,
                quality="GOOD",
            ))

    # Reset only PRESS_001
    ml_service.reset_sensor("PRESS_001")

    info = ml_service.get_service_info()["active_buffer_lengths"]
    assert info["PRESS_001"] == 0
    assert info["VIB_001"] == 20

    # Add 10 more to VIB_001 to reach 30 and verify it infers immediately
    for step in range(21, 31):
        out_vib = ml_service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="VIB_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=0.85,
            quality="GOOD",
        ))

    assert out_vib.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_vib.anomaly_score is not None
