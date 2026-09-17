"""
Unit and Integration tests for Maitri ML Inference Observability and Audit Diagnostics.
Polarix SIH26060 - Person C.
"""

from __future__ import annotations

import json
import math
import pytest
from datetime import datetime, timezone

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.inference_diagnostics import (
    DIAGNOSTIC_STATUSES,
    InferenceDiagnosticRecord,
)
from ml.inference.maitri_ml_service import MaitriMLService


@pytest.fixture
def service() -> MaitriMLService:
    srv = MaitriMLService(max_diagnostics_history=50)
    srv.reset_all()
    srv.clear_diagnostics()
    return srv


# -----------------------------------------------------------------------------
# 1. Diagnostic Record Schema & Validation Tests
# -----------------------------------------------------------------------------
def test_1_diagnostic_record_valid():
    """Verify that a valid diagnostic record validates without errors."""
    rec = InferenceDiagnosticRecord(
        timestamp="2026-09-18T10:00:00Z",
        station_id="MTR",
        sensor_id="TEMP_001",
        inference_status="SUCCESS",
        anomaly_status="NORMAL",
        anomaly_type="NORMAL",
        anomaly_score=0.0025,
        threshold=0.017674,
        model_version="lstm-ae-v1",
        buffer_length=30,
        processing_time_ms=1.45,
    )
    rec.validate()
    d = rec.to_dict()
    assert d["inference_status"] == "SUCCESS"
    assert d["processing_time_ms"] == 1.45
    assert d["threshold"] == 0.017674
    assert d["model_version"] == "lstm-ae-v1"


def test_2_diagnostic_record_invalid_status():
    """Verify invalid inference_status raises ValueError."""
    rec = InferenceDiagnosticRecord(
        timestamp="2026-09-18T10:00:00Z",
        station_id="MTR",
        sensor_id="TEMP_001",
        inference_status="UNKNOWN_STATUS",
    )
    with pytest.raises(ValueError, match="Invalid inference_status"):
        rec.validate()


def test_3_diagnostic_record_invalid_timing():
    """Verify non-finite or negative processing_time_ms raises ValueError."""
    with pytest.raises(ValueError, match="processing_time_ms"):
        InferenceDiagnosticRecord(
            timestamp="2026-09-18T10:00:00Z",
            station_id="MTR",
            sensor_id="TEMP_001",
            inference_status="SUCCESS",
            processing_time_ms=-0.5,
        ).validate()

    with pytest.raises(ValueError, match="processing_time_ms"):
        InferenceDiagnosticRecord(
            timestamp="2026-09-18T10:00:00Z",
            station_id="MTR",
            sensor_id="TEMP_001",
            inference_status="SUCCESS",
            processing_time_ms=float("nan"),
        ).validate()


# -----------------------------------------------------------------------------
# 2. Service Diagnostic Recording Tests: Warmup & Success
# -----------------------------------------------------------------------------
def test_4_insufficient_data_diagnostics(service: MaitriMLService):
    """Verify observations during warmup record INSUFFICIENT_DATA status."""
    service.process_telemetry(
        TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:01:00Z", -15.0)
    )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.station_id == "MTR"
    assert diag.sensor_id == "TEMP_001"
    assert diag.inference_status == "INSUFFICIENT_DATA"
    assert diag.anomaly_status == "INSUFFICIENT_DATA"
    assert diag.anomaly_score is None
    assert diag.anomaly_type is None
    assert diag.buffer_length == 1
    assert diag.processing_time_ms >= 0.0
    assert math.isfinite(diag.processing_time_ms)
    assert diag.threshold == service.threshold
    assert diag.model_version == "lstm-ae-v1"


def test_5_success_normal_diagnostics(service: MaitriMLService):
    """Verify scored normal inference records SUCCESS status."""
    for step in range(1, 31):
        service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", f"2026-09-18T01:{step:02d}:00Z", -15.0 + 0.1 * (step % 4))
        )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "SUCCESS"
    assert diag.anomaly_status in {"NORMAL", "ANOMALY"}
    assert diag.anomaly_score is not None and math.isfinite(diag.anomaly_score)
    assert diag.buffer_length == 30
    assert diag.processing_time_ms >= 0.0


def test_6_success_anomaly_diagnostics(service: MaitriMLService):
    """Verify scored anomaly inference records SUCCESS with anomaly_status=ANOMALY."""
    for step in range(1, 31):
        service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", f"2026-09-18T02:{step:02d}:00Z", -15.0 + 0.1 * (step % 4))
        )
    # Inject anomaly spike
    service.process_telemetry(
        TelemetryInput("MTR", "TEMP_001", "2026-09-18T02:31:00Z", 25.0)
    )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "SUCCESS"
    assert diag.anomaly_status == "ANOMALY"
    assert diag.anomaly_type == "SPIKE"
    assert diag.anomaly_score is not None and diag.anomaly_score > service.threshold
    assert diag.buffer_length == 30


# -----------------------------------------------------------------------------
# 3. Missing, Duplicate, and Stale Rejection Diagnostics
# -----------------------------------------------------------------------------
def test_7_missing_data_diagnostics(service: MaitriMLService):
    """Verify missing/null data records MISSING_DATA status and resets buffer."""
    service.process_telemetry(
        TelemetryInput("MTR", "TEMP_001", "2026-09-18T03:01:00Z", None, quality="MISSING")
    )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "MISSING_DATA"
    assert diag.anomaly_status == "MISSING_DATA"
    assert diag.anomaly_score is None
    assert diag.anomaly_type is None
    assert diag.buffer_length == 0


def test_8_non_finite_nan_diagnostics(service: MaitriMLService):
    """Verify NaN value records MISSING_DATA status."""
    service.process_telemetry(
        TelemetryInput("MTR", "PRESS_001", "2026-09-18T03:10:00Z", float("nan"))
    )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "MISSING_DATA"
    assert diag.buffer_length == 0


def test_9_duplicate_rejection_diagnostics(service: MaitriMLService):
    """Verify duplicate timestamp raises DuplicateTelemetryError and logs REJECTED_DUPLICATE."""
    service.process_telemetry(
        TelemetryInput("MTR", "HUM_001", "2026-09-18T04:00:00Z", 65.0)
    )
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            TelemetryInput("MTR", "HUM_001", "2026-09-18T04:00:00Z", 65.0)
        )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "REJECTED_DUPLICATE"
    assert diag.sensor_id == "HUM_001"
    assert diag.error_message is not None
    assert "Duplicate timestamp" in diag.error_message


def test_10_stale_rejection_diagnostics(service: MaitriMLService):
    """Verify out-of-order timestamp raises StaleTelemetryError and logs REJECTED_STALE."""
    service.process_telemetry(
        TelemetryInput("MTR", "HUM_001", "2026-09-18T05:00:00Z", 65.0)
    )
    with pytest.raises(StaleTelemetryError):
        service.process_telemetry(
            TelemetryInput("MTR", "HUM_001", "2026-09-18T04:59:00Z", 65.0)
        )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "REJECTED_STALE"
    assert diag.sensor_id == "HUM_001"
    assert diag.error_message is not None
    assert "Stale out-of-order telemetry" in diag.error_message


def test_11_invalid_contract_rejection_diagnostics(service: MaitriMLService):
    """Verify invalid station or sensor logs REJECTED_INVALID."""
    with pytest.raises(UnsupportedStationError):
        service.process_telemetry(
            {"station_id": "BHARATI", "sensor_id": "TEMP_001", "timestamp": "2026-09-18T06:00:00Z", "value": -15.0}
        )
    diag = service.get_last_diagnostic()
    assert diag is not None
    assert diag.inference_status == "REJECTED_INVALID"
    assert diag.station_id == "BHARATI"

    with pytest.raises(UnsupportedSensorError):
        service.process_telemetry(
            {"station_id": "MTR", "sensor_id": "INVALID_SENSOR", "timestamp": "2026-09-18T06:01:00Z", "value": -15.0}
        )
    diag2 = service.get_last_diagnostic()
    assert diag2 is not None
    assert diag2.inference_status == "REJECTED_INVALID"
    assert diag2.sensor_id == "INVALID_SENSOR"


# -----------------------------------------------------------------------------
# 4. History Management, Bounded Deque, and Immutability
# -----------------------------------------------------------------------------
def test_12_bounded_diagnostics_history():
    """Verify diagnostics deque does not exceed max_diagnostics_history limit."""
    small_service = MaitriMLService(max_diagnostics_history=10)
    for step in range(1, 25):
        small_service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", f"2026-09-18T07:{step:02d}:00Z", -15.0)
        )
    records = small_service.get_recent_diagnostics()
    assert len(records) == 10
    info = small_service.get_service_info()
    assert info["diagnostics_count"] == 10
    assert info["diagnostics_history_limit"] == 10


def test_13_defensive_copying_and_clear(service: MaitriMLService):
    """Verify get_recent_diagnostics returns a list copy that doesn't mutate internal state."""
    service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T08:01:00Z", -15.0))
    service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T08:02:00Z", -15.0))

    recs = service.get_recent_diagnostics()
    assert len(recs) == 2
    recs.clear()
    assert len(service.get_recent_diagnostics()) == 2

    # Query with limit
    lim_recs = service.get_recent_diagnostics(limit=1)
    assert len(lim_recs) == 1
    assert lim_recs[0].timestamp == "2026-09-18T08:02:00Z"

    # Clear diagnostics
    service.clear_diagnostics()
    assert service.get_last_diagnostic() is None
    assert len(service.get_recent_diagnostics()) == 0


# -----------------------------------------------------------------------------
# 5. Serialization & Roundtrip Tests
# -----------------------------------------------------------------------------
def test_14_json_roundtrip_serialization(service: MaitriMLService):
    """Verify diagnostic record serializes to JSON without non-finite values."""
    service.process_telemetry(TelemetryInput("MTR", "VIB_001", "2026-09-18T09:00:00Z", 0.05))
    diag = service.get_last_diagnostic()
    assert diag is not None

    json_str = diag.to_json(indent=2)
    assert "VIB_001" in json_str
    assert "INSUFFICIENT_DATA" in json_str

    parsed = json.loads(json_str)
    assert parsed["station_id"] == "MTR"
    assert parsed["sensor_id"] == "VIB_001"
    assert parsed["inference_status"] == "INSUFFICIENT_DATA"

    reconstructed = InferenceDiagnosticRecord.from_json(json_str)
    assert reconstructed == diag
