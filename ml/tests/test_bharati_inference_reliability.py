"""
Bharati ML Inference Reliability & Edge-Case Hardening Tests (SIH26060 - Person C).

Comprehensive test suite verifying:
1. NaN values safely handled via MISSING_DATA without entering the LSTM.
2. Positive infinity (+inf) safely handled via MISSING_DATA.
3. Negative infinity (-inf) safely handled via MISSING_DATA.
4. None/null values follow MISSING_DATA path.
5. Invalid/missing observations do not enter the rolling buffer.
6. Fewer than 30 valid observations returns INSUFFICIENT_DATA.
7. Exact 30-point boundary triggers scored inference.
8. Rolling window strictly bounded to 30 observations.
9. Exact duplicate telemetry does not duplicate or advance the window.
10. Out-of-order telemetry cannot corrupt the chronological rolling window.
11. Timezone-aware timestamps normalized and handled with consistent UTC semantics.
12. Invalid/unparseable timestamps are rejected safely.
13. Unsupported station remains rejected.
14. Unsupported sensor remains rejected.
15. Interleaved sensors remain strictly isolated.
16. reset_sensor() isolates the reset without affecting other sensors.
17. reset_all() clears all histories across all sensors.
18. Rejected input preserves valid sensor state.
19. Same input sequence produces deterministic output across fresh services.
20. Tampered model artifact prevents inference instantiation.
21. Missing model artifact prevents inference instantiation.
22. JSON output contains no non-finite values (no NaN or inf).
23. All four inference states serialize losslessly.
24. Valid GOOD quality telemetry continues to work normally.
25. Existing model version remains lstm-ae-bharati-v1 and threshold remains 0.013215307652775843.
26. Maitri artifacts remain completely untouched.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest

from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    BharatiTelemetryInput,
    BharatiTelemetryOutput,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    UnsupportedSensorError,
    UnsupportedStationError,
    parse_iso_timestamp,
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService
from ml.models.model_registry import ModelIntegrityError, compute_file_sha256

FROZEN_BHARATI_MODEL_VERSION = "lstm-ae-bharati-v1"
FROZEN_BHARATI_THRESHOLD = 0.013215307652775843

FROZEN_MAITRI_MODEL_SHA = "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262"
FROZEN_MAITRI_CONFIG_SHA = "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b"
FROZEN_MAITRI_SCALER_SHA = "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224"
FROZEN_MAITRI_THRESHOLD_SHA = "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1"


@pytest.fixture
def service() -> BharatiMLService:
    """Fixture providing a fresh BharatiMLService instance with cleared buffers."""
    srv = BharatiMLService(device="cpu", verify_manifest=True)
    srv.reset_all()
    return srv


# -----------------------------------------------------------------------------
# Test 1: NaN Values Handled Safely
# -----------------------------------------------------------------------------
def test_1_nan_handled_safely(service: BharatiMLService) -> None:
    """Verify NaN value returns MISSING_DATA, clears buffer, and does not enter PyTorch model."""
    inp = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("nan"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_buffer_length("BRT_TEMP_001") == 0


# -----------------------------------------------------------------------------
# Test 2: Positive Infinity Handled Safely
# -----------------------------------------------------------------------------
def test_2_pos_inf_handled_safely(service: BharatiMLService) -> None:
    """Verify +inf value returns MISSING_DATA, clears buffer, and does not corrupt PyTorch tensors."""
    inp = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("inf"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_buffer_length("BRT_TEMP_001") == 0


# -----------------------------------------------------------------------------
# Test 3: Negative Infinity Handled Safely
# -----------------------------------------------------------------------------
def test_3_neg_inf_handled_safely(service: BharatiMLService) -> None:
    """Verify -inf value returns MISSING_DATA, clears buffer, and does not corrupt PyTorch tensors."""
    inp = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-09-18T00:00:00Z",
        value=float("-inf"),
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None
    assert service.get_buffer_length("BRT_TEMP_001") == 0


# -----------------------------------------------------------------------------
# Test 4: Missing Value Follows MISSING_DATA
# -----------------------------------------------------------------------------
def test_4_missing_value_follows_missing_data(service: BharatiMLService) -> None:
    """Verify value=None returns MISSING_DATA."""
    inp = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_PRESS_001",
        timestamp="2026-09-18T00:00:00Z",
        value=None,
        quality="GOOD",
    )
    out = service.process_telemetry(inp)
    assert out.anomaly_status == "MISSING_DATA"
    assert out.anomaly_score is None
    assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 5: Invalid Quality Clears Buffer
# -----------------------------------------------------------------------------
def test_5_invalid_quality_clears_buffer(service: BharatiMLService) -> None:
    """Verify non-GOOD quality observations clear the buffer instead of accumulating."""
    for step in range(1, 11):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_HUM_001",
                timestamp=f"2026-09-18T00:{step:02d}:00Z",
                value=60.0 + step * 0.1,
                quality="GOOD",
            )
        )
    assert service.get_buffer_length("BRT_HUM_001") == 10

    # Feed bad quality
    out_bad = service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_HUM_001",
            timestamp="2026-09-18T00:11:00Z",
            value=61.5,
            quality="BAD",
        )
    )
    assert out_bad.anomaly_status == "MISSING_DATA"
    assert service.get_buffer_length("BRT_HUM_001") == 0


# -----------------------------------------------------------------------------
# Test 6: Insufficient History Under 30 Points
# -----------------------------------------------------------------------------
def test_6_insufficient_history_under_30(service: BharatiMLService) -> None:
    """Verify steps 1 through 29 strictly return INSUFFICIENT_DATA."""
    for step in range(1, 30):
        out = service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_VIB_001",
                timestamp=f"2026-09-18T01:{step:02d}:00Z",
                value=0.90 + 0.01 * step,
                quality="GOOD",
            )
        )
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None
        assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 7: Exact 30-Point Boundary Triggers Scored Inference
# -----------------------------------------------------------------------------
def test_7_exact_30_point_boundary(service: BharatiMLService) -> None:
    """Verify the 30th observation immediately evaluates scored inference."""
    for step in range(1, 30):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_POWER_001",
                timestamp=f"2026-09-18T02:{step:02d}:00Z",
                value=42.0 + 0.1 * step,
                quality="GOOD",
            )
        )
    # 30th observation
    out_30 = service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_POWER_001",
            timestamp="2026-09-18T02:30:00Z",
            value=45.0,
            quality="GOOD",
        )
    )
    assert out_30.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_30.anomaly_score is not None
    assert np.isfinite(out_30.anomaly_score)


# -----------------------------------------------------------------------------
# Test 8: Rolling Window Bounded to 30 Observations
# -----------------------------------------------------------------------------
def test_8_rolling_window_bounded_to_30(service: BharatiMLService) -> None:
    """Verify buffer length stays strictly at 30 when feeding 50 observations."""
    for step in range(1, 51):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-09-18T03:{step:02d}:00Z",
                value=-10.0 + 0.05 * step,
                quality="GOOD",
            )
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 30


# -----------------------------------------------------------------------------
# Test 9: Duplicate Timestamp Rejection
# -----------------------------------------------------------------------------
def test_9_duplicate_timestamp_rejection(service: BharatiMLService) -> None:
    """Verify duplicate timestamp raises DuplicateTelemetryError without advancing buffer."""
    service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_PRESS_001",
            timestamp="2026-09-18T04:00:00Z",
            value=985.0,
            quality="GOOD",
        )
    )
    assert service.get_buffer_length("BRT_PRESS_001") == 1

    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_PRESS_001",
                timestamp="2026-09-18T04:00:00Z",
                value=985.5,
                quality="GOOD",
            )
        )
    assert service.get_buffer_length("BRT_PRESS_001") == 1


# -----------------------------------------------------------------------------
# Test 10: Stale Timestamp Rejection
# -----------------------------------------------------------------------------
def test_10_stale_timestamp_rejection(service: BharatiMLService) -> None:
    """Verify older timestamp raises StaleTelemetryError without corrupting buffer."""
    service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_PRESS_001",
            timestamp="2026-09-18T04:10:00Z",
            value=985.0,
            quality="GOOD",
        )
    )
    with pytest.raises(StaleTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_PRESS_001",
                timestamp="2026-09-18T04:05:00Z",
                value=985.5,
                quality="GOOD",
            )
        )
    assert service.get_buffer_length("BRT_PRESS_001") == 1


# -----------------------------------------------------------------------------
# Test 11: Timezone-Aware Timestamps Handled Consistently
# -----------------------------------------------------------------------------
def test_11_timezone_aware_timestamps_handled_consistently(service: BharatiMLService) -> None:
    """Verify ISO timestamps with mixed timezone offsets (+05:30, Z) are parsed with consistent UTC semantics."""
    # 2026-09-18T10:00:00Z is 2026-09-18T15:30:00+05:30
    service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T10:00:00Z",
            value=-10.0,
            quality="GOOD",
        )
    )

    # Re-sending the same UTC moment with +05:30 offset should be caught as duplicate
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T15:30:00+05:30",
                value=-10.0,
                quality="GOOD",
            )
        )

    # Forward timestamp with offset proceeds
    out = service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T15:31:00+05:30",
            value=-10.1,
            quality="GOOD",
        )
    )
    assert out.anomaly_status == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# Test 12: Malformed Timestamp Rejected
# -----------------------------------------------------------------------------
def test_12_malformed_timestamp_rejected() -> None:
    """Verify invalid timestamp format raises InvalidContractError."""
    with pytest.raises(InvalidContractError):
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="INVALID_DATE_TIME",
            value=-10.0,
        )


# -----------------------------------------------------------------------------
# Test 13: Unsupported Station Rejected
# -----------------------------------------------------------------------------
def test_13_unsupported_station_rejected() -> None:
    """Verify non-BRT stations raise UnsupportedStationError."""
    with pytest.raises(UnsupportedStationError):
        BharatiTelemetryInput(
            station_id="MAITRI",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T10:00:00Z",
            value=-10.0,
        )


# -----------------------------------------------------------------------------
# Test 14: Unsupported Sensor Rejected
# -----------------------------------------------------------------------------
def test_14_unsupported_sensor_rejected() -> None:
    """Verify sensor IDs outside supported 5 raise UnsupportedSensorError."""
    with pytest.raises(UnsupportedSensorError):
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="INVALID_SENSOR",
            timestamp="2026-09-18T10:00:00Z",
            value=-10.0,
        )


# -----------------------------------------------------------------------------
# Test 15: Sensor Isolation Interleaved
# -----------------------------------------------------------------------------
def test_15_sensor_isolation_interleaved(service: BharatiMLService) -> None:
    """Verify interleaved telemetry across sensors maintains strictly isolated buffers."""
    for step in range(1, 31):
        for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
            service.process_telemetry(
                BharatiTelemetryInput(
                    station_id="BRT",
                    sensor_id=s_id,
                    timestamp=f"2026-09-18T05:{step:02d}:00Z",
                    value=10.0 + step,
                    quality="GOOD",
                )
            )

    # All 5 buffers should have exactly 30 observations
    info = service.get_service_info()
    for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
        assert info["active_buffer_lengths"][s_id] == 30


# -----------------------------------------------------------------------------
# Test 16: Reset Sensor Isolation
# -----------------------------------------------------------------------------
def test_16_reset_sensor_isolation(service: BharatiMLService) -> None:
    """Verify reset_sensor clears only the specified sensor."""
    for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
        for step in range(1, 10):
            service.process_telemetry(
                BharatiTelemetryInput(
                    station_id="BRT",
                    sensor_id=s_id,
                    timestamp=f"2026-09-18T06:{step:02d}:00Z",
                    value=10.0 + step,
                    quality="GOOD",
                )
            )

    service.reset_sensor("BRT_TEMP_001")
    assert service.get_buffer_length("BRT_TEMP_001") == 0
    assert service.get_buffer_length("BRT_PRESS_001") == 9
    assert service.get_buffer_length("BRT_HUM_001") == 9


# -----------------------------------------------------------------------------
# Test 17: Reset All Clears All Sensors
# -----------------------------------------------------------------------------
def test_17_reset_all_clears_all_sensors(service: BharatiMLService) -> None:
    """Verify reset_all clears all sensor histories."""
    for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id=s_id,
                timestamp="2026-09-18T07:00:00Z",
                value=15.0,
                quality="GOOD",
            )
        )
    service.reset_all()
    for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
        assert service.get_buffer_length(s_id) == 0


# -----------------------------------------------------------------------------
# Test 18: Rejected Input Preserves Valid Sensor State
# -----------------------------------------------------------------------------
def test_18_rejected_input_preserves_valid_sensor_state(service: BharatiMLService) -> None:
    """Verify that rejected inputs do not mutate or clear existing valid buffer state."""
    for step in range(1, 15):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-09-18T08:{step:02d}:00Z",
                value=-10.0 + step * 0.1,
                quality="GOOD",
            )
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 14

    # Attempt rejected duplicate
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T08:14:00Z",
                value=-10.0,
            )
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 14

    # Attempt rejected stale
    with pytest.raises(StaleTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T08:05:00Z",
                value=-10.0,
            )
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 14


# -----------------------------------------------------------------------------
# Test 19: Deterministic Repeated Inference
# -----------------------------------------------------------------------------
def test_19_deterministic_repeated_inference() -> None:
    """Verify two separate service instances produce bitwise identical outputs for identical sequences."""
    srv1 = BharatiMLService(verify_manifest=True)
    srv2 = BharatiMLService(verify_manifest=True)

    inputs = [
        BharatiTelemetryInput(
            "BRT", "BRT_POWER_001", f"2026-09-18T09:{i:02d}:00Z", 42.0 + 0.1 * np.sin(i), quality="GOOD"
        )
        for i in range(35)
    ]

    out1 = [srv1.process_telemetry(inp).to_dict() for inp in inputs]
    out2 = [srv2.process_telemetry(inp).to_dict() for inp in inputs]

    assert out1 == out2


# -----------------------------------------------------------------------------
# Test 20: Tampered Model Artifact Prevents Init
# -----------------------------------------------------------------------------
def test_20_tampered_model_artifact_prevents_init(tmp_path: Path) -> None:
    """Verify tampered model weights raise ModelIntegrityError on service initialization."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")
    (models_dir / "lstm-ae-bharati-v1.pt").write_bytes(b"CORRUPTED_MODEL")

    with pytest.raises(ModelIntegrityError):
        BharatiMLService(
            model_path=models_dir / "lstm-ae-bharati-v1.pt",
            config_path=models_dir / "lstm-ae-bharati-v1_config.json",
            scaler_path=models_dir / "lstm-ae-bharati-v1_scaler.json",
            threshold_path=results_dir / "bharati_lstm_threshold.json",
            manifest_path=models_dir / "lstm-ae-bharati-v1_manifest.json",
            verify_manifest=True,
        )


# -----------------------------------------------------------------------------
# Test 21: Missing Artifact Prevents Init
# -----------------------------------------------------------------------------
def test_21_missing_artifact_prevents_init(tmp_path: Path) -> None:
    """Verify missing threshold file raises ModelIntegrityError."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1.pt", models_dir / "lstm-ae-bharati-v1.pt")
    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    with pytest.raises(ModelIntegrityError):
        BharatiMLService(
            model_path=models_dir / "lstm-ae-bharati-v1.pt",
            config_path=models_dir / "lstm-ae-bharati-v1_config.json",
            scaler_path=models_dir / "lstm-ae-bharati-v1_scaler.json",
            threshold_path=tmp_path / "nonexistent_thresh.json",
            manifest_path=models_dir / "lstm-ae-bharati-v1_manifest.json",
            verify_manifest=True,
        )


# -----------------------------------------------------------------------------
# Test 22: JSON Output Zero Non-Finite Values
# -----------------------------------------------------------------------------
def test_22_json_output_zero_non_finite_values(service: BharatiMLService) -> None:
    """Verify JSON output never produces NaN or Infinity tokens."""
    out = service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T10:00:00Z",
            value=float("nan"),
            quality="GOOD",
        )
    )
    json_str = out.to_json()
    assert "NaN" not in json_str
    assert "Infinity" not in json_str


# -----------------------------------------------------------------------------
# Test 23: All Four Inference States Serialize Losslessly
# -----------------------------------------------------------------------------
def test_23_all_four_statuses_lossless_serialization(service: BharatiMLService) -> None:
    """Verify NORMAL, ANOMALY, INSUFFICIENT_DATA, and MISSING_DATA all serialize and deserialize losslessly."""
    states = ["NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"]
    for status in states:
        score = 0.005 if status in {"NORMAL", "ANOMALY"} else None
        anom_type = "NORMAL" if status == "NORMAL" else ("SPIKE" if status == "ANOMALY" else None)
        out = BharatiTelemetryOutput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T10:00:00Z",
            value=-10.0 if status != "MISSING_DATA" else None,
            unit="C",
            quality="GOOD" if status != "MISSING_DATA" else "BAD",
            source="SIMULATOR",
            anomaly_score=score,
            anomaly_status=status,
            anomaly_type=anom_type,
            model_version=FROZEN_BHARATI_MODEL_VERSION,
        )
        j_str = out.to_json()
        restored = BharatiTelemetryOutput.from_json(j_str)
        assert restored == out


# -----------------------------------------------------------------------------
# Test 24: Valid GOOD Quality Telemetry Continues Normally
# -----------------------------------------------------------------------------
def test_24_valid_good_quality_telemetry_continues_normally(service: BharatiMLService) -> None:
    """Verify standard continuous telemetry streams cleanly."""
    for step in range(1, 35):
        out = service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_PRESS_001",
                timestamp=f"2026-09-18T11:{step:02d}:00Z",
                value=985.0 + 0.05 * (step % 5),
                quality="GOOD",
            )
        )
    assert out.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out.anomaly_score is not None


# -----------------------------------------------------------------------------
# Test 25: Model Version and Threshold Invariants
# -----------------------------------------------------------------------------
def test_25_model_version_and_threshold_invariants(service: BharatiMLService) -> None:
    """Verify model version is strictly lstm-ae-bharati-v1 and threshold is 0.013215307652775843."""
    assert service.model_version == FROZEN_BHARATI_MODEL_VERSION
    assert abs(service.threshold - FROZEN_BHARATI_THRESHOLD) < 1e-12


# -----------------------------------------------------------------------------
# Test 26: Maitri Artifacts Untouched
# -----------------------------------------------------------------------------
def test_26_maitri_artifacts_untouched() -> None:
    """Verify all Maitri artifacts remain intact with exact unaltered SHA-256 hashes."""
    assert compute_file_sha256("ml/models/lstm-ae-v1.pt") == FROZEN_MAITRI_MODEL_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_config.json") == FROZEN_MAITRI_CONFIG_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_scaler.json") == FROZEN_MAITRI_SCALER_SHA
    assert compute_file_sha256("ml/results/lstm_threshold.json") == FROZEN_MAITRI_THRESHOLD_SHA
