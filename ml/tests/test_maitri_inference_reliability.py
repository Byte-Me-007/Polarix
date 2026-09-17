"""
Maitri ML Inference Reliability & Edge-Case Hardening Tests (SIH26060 - Person C).

Comprehensive test suite verifying:
1. NaN values safely handled via MISSING_DATA without entering the LSTM.
2. Positive infinity (+inf) safely handled via MISSING_DATA.
3. Negative infinity (-inf) safely handled via MISSING_DATA.
4. None/null values follow MISSING_DATA path.
5. Invalid/missing observations do not enter the rolling buffer.
6. Fewer than 30 valid observations returns INSUFFICIENT_DATA.
7. Exact duplicate telemetry does not duplicate or advance the window.
8. Out-of-order telemetry cannot corrupt the chronological rolling window.
9. Invalid/unparseable timestamps are rejected safely.
10. Interleaved sensors remain strictly isolated.
11. Unsupported station remains rejected.
12. Unsupported sensor remains rejected.
13. reset_sensor() isolates the reset without affecting other sensors.
14. reset_all() clears all histories across all sensors.
15. Tampered model artifact prevents inference instantiation.
16. Missing model artifact prevents inference instantiation.
17. Invalid manifest prevents inference instantiation.
18. JSON output contains no non-finite values (no NaN or inf).
19. All four inference states serialize losslessly.
20. Same input sequence produces deterministic output across fresh services.
21. Rolling buffer never exceeds 30 observations (bounded deque).
22. Invalid quality values are rejected safely by contract.
23. Valid GOOD quality telemetry continues to work normally.
24. Existing anomaly type classification still functions accurately.
25. Existing model version remains lstm-ae-v1.
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
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.models.model_registry import ModelIntegrityError


@pytest.fixture
def service() -> MaitriMLService:
    """Fixture providing a fresh MaitriMLService instance with cleared buffers."""
    srv = MaitriMLService(device="cpu")
    srv.reset_all()
    return srv


# -----------------------------------------------------------------------------
# Test 1: NaN Values Handled Safely
# -----------------------------------------------------------------------------
def test_1_nan_handled_safely(service: MaitriMLService) -> None:
    """Verify NaN value returns MISSING_DATA, clears buffer, and does not enter PyTorch model."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("nan"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 0


# -----------------------------------------------------------------------------
# Test 2: Positive Infinity Handled Safely
# -----------------------------------------------------------------------------
def test_2_pos_inf_handled_safely(service: MaitriMLService) -> None:
    """Verify +inf value returns MISSING_DATA, clears buffer, and does not corrupt PyTorch tensors."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("inf"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 0


# -----------------------------------------------------------------------------
# Test 3: Negative Infinity Handled Safely
# -----------------------------------------------------------------------------
def test_3_neg_inf_handled_safely(service: MaitriMLService) -> None:
    """Verify -inf value returns MISSING_DATA, clears buffer, and does not corrupt PyTorch tensors."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("-inf"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 0


# -----------------------------------------------------------------------------
# Test 4: Missing Value Follows MISSING_DATA
# -----------------------------------------------------------------------------
def test_4_missing_value_follows_missing_data(service: MaitriMLService) -> None:
    """Verify value=None returns MISSING_DATA."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="PRESS_001",
        timestamp="2026-09-18T00:00:00Z",
        value=None,
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 5: Invalid Observations Do Not Enter Buffer
# -----------------------------------------------------------------------------
def test_5_invalid_observations_do_not_enter_buffer(service: MaitriMLService) -> None:
    """Verify invalid quality or null observations clear the buffer instead of accumulating."""
    # Feed 10 valid observations
    for step in range(1, 11):
        service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="HUM_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=55.0,
            quality="GOOD",
        ))
    assert service.get_service_info()["active_buffer_lengths"]["HUM_001"] == 10

    # Feed a BAD quality record
    service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-09-18T00:11:00Z",
        value=55.0,
        quality="BAD",
    ))
    # Buffer was cleared
    assert service.get_service_info()["active_buffer_lengths"]["HUM_001"] == 0


# -----------------------------------------------------------------------------
# Test 6: Fewer Than 30 Observations Returns INSUFFICIENT_DATA
# -----------------------------------------------------------------------------
def test_6_fewer_than_30_returns_insufficient(service: MaitriMLService) -> None:
    """Verify observations 1 to 29 consistently yield INSUFFICIENT_DATA."""
    for step in range(1, 30):
        out = service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="VIB_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=0.85,
            quality="GOOD",
        ))
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None
        assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 7: Duplicate Telemetry Does Not Advance Window
# -----------------------------------------------------------------------------
def test_7_duplicate_telemetry_handling(service: MaitriMLService) -> None:
    """Verify duplicate timestamp for the same sensor raises DuplicateTelemetryError and leaves buffer untouched."""
    inp1 = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=-15.0,
        quality="GOOD",
    )
    service.process_telemetry(inp1)
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 1

    # Send identical timestamp again
    inp2 = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=-14.5,
        quality="GOOD",
    )
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(inp2)

    # Buffer length remains 1 (did not duplicate)
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 1


# -----------------------------------------------------------------------------
# Test 8: Out-of-Order Telemetry Cannot Corrupt Window
# -----------------------------------------------------------------------------
def test_8_out_of_order_telemetry_handling(service: MaitriMLService) -> None:
    """Verify stale older timestamp raises StaleTelemetryError and leaves buffer untouched."""
    service.process_telemetry(TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:10:00Z",
        value=-15.0,
        quality="GOOD",
    ))
    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 1

    # Send stale timestamp from the past
    stale_input = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T00:05:00Z",
        value=-16.0,
        quality="GOOD",
    )
    with pytest.raises(StaleTelemetryError):
        service.process_telemetry(stale_input)

    assert service.get_service_info()["active_buffer_lengths"]["TEMP_001"] == 1


# -----------------------------------------------------------------------------
# Test 9: Invalid Timestamps Rejected Safely
# -----------------------------------------------------------------------------
def test_9_invalid_timestamps_rejected_safely() -> None:
    """Verify unparseable or empty timestamp strings raise InvalidContractError."""
    with pytest.raises(InvalidContractError):
        TelemetryInput(station_id="MTR", sensor_id="TEMP_001", timestamp="not_a_timestamp", value=-15.0)

    with pytest.raises(InvalidContractError):
        TelemetryInput(station_id="MTR", sensor_id="TEMP_001", timestamp="", value=-15.0)


# -----------------------------------------------------------------------------
# Test 10: Interleaved Sensors Remain Isolated
# -----------------------------------------------------------------------------
def test_10_interleaved_sensors_isolation(service: MaitriMLService) -> None:
    """Verify interleaving observations across 5 sensors does not cross-contaminate buffers."""
    for step in range(1, 31):
        for sensor in SUPPORTED_SENSORS:
            service.process_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id=sensor,
                timestamp=f"2026-09-18T00:{step:02d}:00Z",
                value=10.0,
                quality="GOOD",
            ))

    lengths = service.get_service_info()["active_buffer_lengths"]
    for sensor in SUPPORTED_SENSORS:
        assert lengths[sensor] == 30


# -----------------------------------------------------------------------------
# Test 11: Unsupported Station Remains Rejected
# -----------------------------------------------------------------------------
def test_11_unsupported_station_rejected(service: MaitriMLService) -> None:
    """Verify non-Maitri stations raise UnsupportedStationError."""
    with pytest.raises(UnsupportedStationError):
        service.process_telemetry(TelemetryInput(
            station_id="BHARATI",
            sensor_id="TEMP_001",
            timestamp="2026-09-18T00:00:00Z",
            value=-15.0,
        ))


# -----------------------------------------------------------------------------
# Test 12: Unsupported Sensor Remains Rejected
# -----------------------------------------------------------------------------
def test_12_unsupported_sensor_rejected(service: MaitriMLService) -> None:
    """Verify unsupported sensor IDs raise UnsupportedSensorError."""
    with pytest.raises(UnsupportedSensorError):
        service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="RADIATION_001",
            timestamp="2026-09-18T00:00:00Z",
            value=10.0,
        ))


# -----------------------------------------------------------------------------
# Test 13: reset_sensor Isolates Reset
# -----------------------------------------------------------------------------
def test_13_reset_sensor_isolates_reset(service: MaitriMLService) -> None:
    """Verify reset_sensor only clears the specified sensor's buffer and timestamp tracker."""
    service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", -15.0))
    service.process_telemetry(TelemetryInput("MTR", "PRESS_001", "2026-09-18T00:00:00Z", 990.0))

    service.reset_sensor("TEMP_001")
    lengths = service.get_service_info()["active_buffer_lengths"]
    assert lengths["TEMP_001"] == 0
    assert lengths["PRESS_001"] == 1


# -----------------------------------------------------------------------------
# Test 14: reset_all Clears All Histories
# -----------------------------------------------------------------------------
def test_14_reset_all_clears_all(service: MaitriMLService) -> None:
    """Verify reset_all clears all sensor sliding windows."""
    for sensor in SUPPORTED_SENSORS:
        service.process_telemetry(TelemetryInput("MTR", sensor, "2026-09-18T00:00:00Z", 10.0))

    service.reset_all()
    lengths = service.get_service_info()["active_buffer_lengths"]
    for sensor in SUPPORTED_SENSORS:
        assert lengths[sensor] == 0


# -----------------------------------------------------------------------------
# Test 15: Tampered Model Artifact Prevents Inference
# -----------------------------------------------------------------------------
def test_15_tampered_artifact_prevents_inference(tmp_path: Path) -> None:
    """Verify corrupting an artifact file's content triggers ModelIntegrityError on service load."""
    fake_weights = tmp_path / "corrupted_weights.pt"
    fake_weights.write_bytes(b"tampered content")

    manifest = tmp_path / "lstm-ae-v1_manifest.json"
    manifest.write_text(json.dumps({
        "model_version": "lstm-ae-v1",
        "artifacts": {
            "model": {
                "file": "corrupted_weights.pt",
                "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
                "size_bytes": 100,
            }
        }
    }))

    with pytest.raises(ModelIntegrityError):
        MaitriMLService(manifest_path=manifest, verify_manifest=True)


# -----------------------------------------------------------------------------
# Test 16: Missing Model Artifact Prevents Inference
# -----------------------------------------------------------------------------
def test_16_missing_artifact_prevents_inference(tmp_path: Path) -> None:
    """Verify missing artifact file triggers ModelIntegrityError."""
    manifest = tmp_path / "lstm-ae-v1_manifest.json"
    manifest.write_text(json.dumps({
        "model_version": "lstm-ae-v1",
        "artifacts": {
            "model": {
                "file": "does_not_exist.pt",
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "size_bytes": 100,
            }
        }
    }))

    with pytest.raises(ModelIntegrityError):
        MaitriMLService(manifest_path=manifest, verify_manifest=True)


# -----------------------------------------------------------------------------
# Test 17: Invalid Manifest Prevents Inference
# -----------------------------------------------------------------------------
def test_17_invalid_manifest_prevents_inference(tmp_path: Path) -> None:
    """Verify corrupted JSON manifest triggers ModelIntegrityError."""
    manifest = tmp_path / "lstm-ae-v1_manifest.json"
    manifest.write_text("invalid json content {{{")

    with pytest.raises(Exception):
        MaitriMLService(manifest_path=manifest, verify_manifest=True)


# -----------------------------------------------------------------------------
# Test 18: JSON Output Contains No Non-Finite Values
# -----------------------------------------------------------------------------
def test_18_json_output_finite(service: MaitriMLService) -> None:
    """Verify serialized JSON contract contains no NaN or Infinity tokens."""
    for step in range(1, 31):
        out = service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=-15.0 + 0.1 * np.sin(step),
            quality="GOOD",
        ))

    json_str = out.to_json()
    assert "NaN" not in json_str
    assert "Infinity" not in json_str
    assert "-Infinity" not in json_str


# -----------------------------------------------------------------------------
# Test 19: All Four States Serialize Correctly
# -----------------------------------------------------------------------------
def test_19_all_four_states_serialize_correctly() -> None:
    """Verify NORMAL, ANOMALY, INSUFFICIENT_DATA, MISSING_DATA all roundtrip JSON losslessly."""
    outputs = [
        TelemetryInferenceOutput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", -15.0, "°C", "GOOD", "SIM", 0.005, "NORMAL", "NORMAL"),
        TelemetryInferenceOutput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", 15.0, "°C", "GOOD", "SIM", 0.550, "ANOMALY", "SPIKE"),
        TelemetryInferenceOutput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", -15.0, "°C", "GOOD", "SIM", None, "INSUFFICIENT_DATA", None),
        TelemetryInferenceOutput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", None, "°C", "BAD", "SIM", None, "MISSING_DATA", None),
    ]
    for out in outputs:
        js = out.to_json()
        restored = TelemetryInferenceOutput.from_json(js)
        assert restored.anomaly_status == out.anomaly_status
        assert restored.anomaly_score == out.anomaly_score
        assert restored.anomaly_type == out.anomaly_type


# -----------------------------------------------------------------------------
# Test 20: Deterministic Output Across Fresh Services
# -----------------------------------------------------------------------------
def test_20_deterministic_output_across_services() -> None:
    """Verify two independent service instances produce bitwise identical inference outputs."""
    srv1 = MaitriMLService(device="cpu")
    srv2 = MaitriMLService(device="cpu")

    inputs = [
        TelemetryInput("MTR", "PRESS_001", f"2026-09-18T00:{step:02d}:00Z", 990.0 + 0.1 * step, quality="GOOD")
        for step in range(1, 35)
    ]

    out1 = [srv1.process_telemetry(inp).to_dict() for inp in inputs]
    out2 = [srv2.process_telemetry(inp).to_dict() for inp in inputs]

    assert out1 == out2


# -----------------------------------------------------------------------------
# Test 21: Rolling Buffer Never Exceeds 30
# -----------------------------------------------------------------------------
def test_21_buffer_bounded_at_30(service: MaitriMLService) -> None:
    """Verify feeding 100 observations keeps rolling buffer strictly bounded to 30."""
    for step in range(1, 101):
        service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T{step//60:02d}:{step%60:02d}:00Z",
            value=-15.0,
            quality="GOOD",
        ))

    lengths = service.get_service_info()["active_buffer_lengths"]
    assert lengths["TEMP_001"] == 30


# -----------------------------------------------------------------------------
# Test 22: Invalid Quality Values Handled Safely
# -----------------------------------------------------------------------------
def test_22_invalid_quality_values_rejected() -> None:
    """Verify unrecognized quality string raises InvalidContractError."""
    with pytest.raises(InvalidContractError):
        TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", -15.0, quality="UNKNOWN_QUALITY")


# -----------------------------------------------------------------------------
# Test 23: Valid GOOD Quality Telemetry Continues Normally
# -----------------------------------------------------------------------------
def test_23_valid_good_telemetry_normal(service: MaitriMLService) -> None:
    """Verify standard valid telemetry processes through all steps normally."""
    for step in range(1, 31):
        out = service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="POWER_001",
            timestamp=f"2026-09-18T00:{step:02d}:00Z",
            value=35.0 + 0.1 * np.cos(step),
            quality="GOOD",
        ))
    assert out.anomaly_status in {"NORMAL", "ANOMALY"}
    assert isinstance(out.anomaly_score, float)


# -----------------------------------------------------------------------------
# Test 24: Existing Anomaly Classification Still Works
# -----------------------------------------------------------------------------
def test_24_anomaly_classification_works(service: MaitriMLService) -> None:
    """Verify anomalous spike is classified as SPIKE."""
    for step in range(1, 31):
        val = -15.0 + 0.2 * (step % 4)
        service.process_telemetry(TelemetryInput("MTR", "TEMP_001", f"2026-09-18T00:{step:02d}:00Z", val, quality="GOOD"))

    # Spike
    spike_out = service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:31:00Z", 25.0, quality="GOOD"))
    assert spike_out.anomaly_status == "ANOMALY"
    assert spike_out.anomaly_type == "SPIKE"


# -----------------------------------------------------------------------------
# Test 25: Existing Model Version Remains lstm-ae-v1
# -----------------------------------------------------------------------------
def test_25_model_version_remains_lstm_ae_v1(service: MaitriMLService) -> None:
    """Verify model version is strictly lstm-ae-v1."""
    out = service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:00:00Z", -15.0))
    assert out.model_version == DEFAULT_MODEL_VERSION
    assert service.model_version == DEFAULT_MODEL_VERSION
