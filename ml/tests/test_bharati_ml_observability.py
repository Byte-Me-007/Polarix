"""
Unit and Integration tests for Bharati ML Inference Observability and Structured Audit Diagnostics.
Polarix SIH26060 - Person C.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
import pytest

from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    BharatiTelemetryInput,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.bharati_ml_observability import (
    SUPPORTED_EVENT_TYPES,
    BharatiInferenceAuditRecord,
    summarize_audit_records,
)
from ml.inference.bharati_ml_service import BharatiMLService


@pytest.fixture
def service() -> BharatiMLService:
    srv = BharatiMLService(max_diagnostics_history=50)
    srv.reset_all()
    srv.clear_diagnostics()
    return srv


# -----------------------------------------------------------------------------
# 1. Audit Record Schema & Validation Tests
# -----------------------------------------------------------------------------
def test_1_audit_record_valid():
    """Verify that a valid audit record validates without errors and serializes deterministically."""
    rec = BharatiInferenceAuditRecord(
        timestamp="2026-09-18T10:00:00Z",
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        input_value_present=True,
        input_quality="GOOD",
        input_accepted=True,
        event_type="INFERENCE",
        anomaly_status="NORMAL",
        anomaly_type="NORMAL",
        anomaly_score=0.0025,
        threshold=0.013215307652775843,
        model_version="lstm-ae-bharati-v1",
        history_size_before=29,
        history_size_after=30,
        inference_eligible=True,
        state_changed=True,
        processing_time_ms=1.45,
    )
    rec.validate()
    d = rec.to_dict()
    assert d["event_type"] == "INFERENCE"
    assert d["processing_time_ms"] == 1.45
    assert d["threshold"] == 0.013215
    assert d["model_version"] == "lstm-ae-bharati-v1"
    assert d["history_size_before"] == 29
    assert d["history_size_after"] == 30
    assert d["inference_eligible"] is True
    assert d["state_changed"] is True


def test_2_audit_record_invalid_event_type():
    """Verify invalid event_type raises ValueError."""
    rec = BharatiInferenceAuditRecord(
        timestamp="2026-09-18T10:00:00Z",
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        input_value_present=True,
        input_quality="GOOD",
        input_accepted=True,
        event_type="UNSUPPORTED_EVENT",
    )
    with pytest.raises(ValueError, match="Invalid event_type"):
        rec.validate()


def test_3_audit_record_invalid_timing():
    """Verify non-finite or negative processing_time_ms raises ValueError."""
    with pytest.raises(ValueError, match="processing_time_ms"):
        BharatiInferenceAuditRecord(
            timestamp="2026-09-18T10:00:00Z",
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            input_value_present=True,
            input_quality="GOOD",
            input_accepted=True,
            event_type="INFERENCE",
            processing_time_ms=-0.5,
        ).validate()

    with pytest.raises(ValueError, match="processing_time_ms"):
        BharatiInferenceAuditRecord(
            timestamp="2026-09-18T10:00:00Z",
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            input_value_present=True,
            input_quality="GOOD",
            input_accepted=True,
            event_type="INFERENCE",
            processing_time_ms=float("nan"),
        ).validate()


# -----------------------------------------------------------------------------
# 2. Service Audit Recording: Warmup, Normal, and Anomaly
# -----------------------------------------------------------------------------
def test_4_insufficient_data_audit(service: BharatiMLService):
    """Verify telemetry during warmup creates INSUFFICIENT_DATA event and tracks buffer evolution."""
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T00:01:00Z", -12.0)
    )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.station_id == "BRT"
    assert rec.sensor_id == "BRT_TEMP_001"
    assert rec.event_type == "INSUFFICIENT_DATA"
    assert rec.anomaly_status == "INSUFFICIENT_DATA"
    assert rec.anomaly_score is None
    assert rec.anomaly_type is None
    assert rec.history_size_before == 0
    assert rec.history_size_after == 1
    assert rec.inference_eligible is False
    assert rec.state_changed is True
    assert rec.processing_time_ms >= 0.0
    assert math.isfinite(rec.processing_time_ms)
    assert rec.threshold == service.threshold
    assert rec.model_version == "lstm-ae-bharati-v1"


def test_5_successful_normal_inference_audit(service: BharatiMLService):
    """Verify 30 sequential observations trigger scored NORMAL INFERENCE audit record."""
    for step in range(1, 31):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T01:{step:02d}:00Z", -12.0 + 0.05 * (step % 3))
        )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "INFERENCE"
    assert rec.anomaly_status == "NORMAL"
    assert rec.anomaly_type == "NORMAL"
    assert rec.anomaly_score is not None and rec.anomaly_score <= service.threshold
    assert rec.history_size_before == 29
    assert rec.history_size_after == 30
    assert rec.inference_eligible is True
    assert rec.state_changed is True
    assert rec.processing_time_ms >= 0.0


def test_6_successful_anomaly_inference_audit(service: BharatiMLService):
    """Verify anomaly spike injection records INFERENCE audit with ANOMALY status and classified type."""
    for step in range(1, 31):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T02:{step:02d}:00Z", -12.0 + 0.05 * (step % 3))
        )
    # Inject large anomalous spike
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T02:31:00Z", 45.0)
    )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "INFERENCE"
    assert rec.anomaly_status == "ANOMALY"
    assert rec.anomaly_type in {"SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
    assert rec.anomaly_score is not None and rec.anomaly_score > service.threshold
    assert rec.history_size_before == 30
    assert rec.history_size_after == 30
    assert rec.inference_eligible is True
    assert rec.state_changed is True


# -----------------------------------------------------------------------------
# 3. Missing, Stale, Duplicate, and Invalid-Input Diagnostics
# -----------------------------------------------------------------------------
def test_7_missing_data_audit(service: BharatiMLService):
    """Verify null or MISSING telemetry creates MISSING_DATA event and resets buffer."""
    # Add 5 points first
    for step in range(1, 6):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T03:{step:02d}:00Z", -12.0)
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 5

    # Send MISSING observation
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T03:06:00Z", None, quality="MISSING")
    )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "MISSING_DATA"
    assert rec.anomaly_status == "MISSING_DATA"
    assert rec.anomaly_score is None
    assert rec.anomaly_type is None
    assert rec.history_size_before == 5
    assert rec.history_size_after == 0
    assert rec.state_changed is True
    assert rec.inference_eligible is False


def test_8_nan_value_missing_data_audit(service: BharatiMLService):
    """Verify NaN telemetry value triggers MISSING_DATA event and resets buffer."""
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T03:10:00Z", 985.0)
    )
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T03:11:00Z", float("nan"))
    )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "MISSING_DATA"
    assert rec.anomaly_status == "MISSING_DATA"
    assert rec.history_size_after == 0


def test_9_duplicate_rejection_audit(service: BharatiMLService):
    """Verify duplicate timestamp raises DuplicateTelemetryError and logs DUPLICATE event."""
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T04:00:00Z", 70.0)
    )
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T04:00:00Z", 70.0)
        )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "DUPLICATE"
    assert rec.input_accepted is False
    assert rec.error_code == "DuplicateTelemetryError"
    assert rec.rejection_reason is not None and "Duplicate timestamp" in rec.rejection_reason
    assert rec.state_changed is False


def test_10_stale_rejection_audit(service: BharatiMLService):
    """Verify out-of-order timestamp raises StaleTelemetryError and logs STALE event."""
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T05:00:00Z", 70.0)
    )
    with pytest.raises(StaleTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T04:59:00Z", 70.0)
        )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "STALE"
    assert rec.input_accepted is False
    assert rec.error_code == "StaleTelemetryError"
    assert rec.rejection_reason is not None and "Stale out-of-order telemetry" in rec.rejection_reason
    assert rec.state_changed is False


def test_11_invalid_station_and_sensor_audit(service: BharatiMLService):
    """Verify invalid station or sensor records INVALID_INPUT event."""
    with pytest.raises(UnsupportedStationError):
        service.process_telemetry(
            {"station_id": "UNKNOWN_STATION", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-09-18T06:00:00Z", "value": -12.0}
        )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.event_type == "INVALID_INPUT"
    assert rec.input_accepted is False
    assert rec.station_id == "UNKNOWN_STATION"

    with pytest.raises(UnsupportedSensorError):
        service.process_telemetry(
            {"station_id": "BRT", "sensor_id": "INVALID_SENSOR", "timestamp": "2026-09-18T06:01:00Z", "value": -12.0}
        )
    rec2 = service.get_last_audit_record()
    assert rec2 is not None
    assert rec2.event_type == "INVALID_INPUT"
    assert rec2.input_accepted is False
    assert rec2.sensor_id == "INVALID_SENSOR"


# -----------------------------------------------------------------------------
# 4. Model Traceability, History Visibility, and Sensor Isolation
# -----------------------------------------------------------------------------
def test_12_model_version_and_threshold_traceability(service: BharatiMLService):
    """Verify model_version and threshold in audit match frozen configuration exactly."""
    service.process_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T07:00:00Z", -10.0)
    )
    rec = service.get_last_audit_record()
    assert rec is not None
    assert rec.model_version == "lstm-ae-bharati-v1"
    assert rec.threshold == 0.013215307652775843


def test_13_sensor_state_isolation(service: BharatiMLService):
    """Verify audit logs for different sensors reflect independent buffer lengths and state changes."""
    service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T08:00:00Z", -12.0))
    service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T08:01:00Z", -12.1))
    service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T08:00:00Z", 980.0))

    recs = service.get_recent_audit_records()
    assert len(recs) == 3

    # BRT_TEMP_001 step 2
    assert recs[1].sensor_id == "BRT_TEMP_001"
    assert recs[1].history_size_before == 1
    assert recs[1].history_size_after == 2

    # BRT_PRESS_001 step 1
    assert recs[2].sensor_id == "BRT_PRESS_001"
    assert recs[2].history_size_before == 0
    assert recs[2].history_size_after == 1


# -----------------------------------------------------------------------------
# 5. Serialization, Sanitization, and Aggregation Tests
# -----------------------------------------------------------------------------
def test_14_json_roundtrip_serialization(service: BharatiMLService):
    """Verify audit record JSON serialization roundtrips accurately."""
    service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_VIB_001", "2026-09-18T09:00:00Z", 0.04))
    rec = service.get_last_audit_record()
    assert rec is not None

    json_str = rec.to_json(indent=2)
    assert "BRT_VIB_001" in json_str
    assert "INSUFFICIENT_DATA" in json_str

    parsed = json.loads(json_str)
    assert parsed["station_id"] == "BRT"
    assert parsed["sensor_id"] == "BRT_VIB_001"
    assert parsed["event_type"] == "INSUFFICIENT_DATA"

    reconstructed = BharatiInferenceAuditRecord.from_json(json_str)
    assert reconstructed.station_id == rec.station_id
    assert reconstructed.sensor_id == rec.sensor_id
    assert reconstructed.event_type == rec.event_type


def test_15_aggregate_diagnostics_summary(service: BharatiMLService):
    """Verify summary computation aggregates counts, events, and latency percentiles."""
    for step in range(1, 35):
        val = 50.0 if step == 32 else (-12.0 + 0.02 * step)
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T10:{step:02d}:00Z", val)
        )

    # Add duplicate to create rejected event
    with pytest.raises(DuplicateTelemetryError):
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T10:34:00Z", -12.0)
        )

    summary = service.get_diagnostics_summary()
    assert summary["total_events"] == 35
    assert summary["accepted_events"] == 34
    assert summary["rejected_events"] == 1
    assert summary["event_counts"]["DUPLICATE"] == 1
    assert summary["event_counts"]["INSUFFICIENT_DATA"] == 29
    assert summary["event_counts"]["INFERENCE"] == 5
    assert summary["latency_stats"]["count"] == 35
    assert summary["latency_stats"]["avg_latency_ms"] >= 0.0
    assert summary["latency_stats"]["p50_latency_ms"] >= 0.0
    assert summary["latency_stats"]["p95_latency_ms"] >= summary["latency_stats"]["p50_latency_ms"]


def test_16_deterministic_repeated_sequence():
    """Verify running an identical telemetry sequence on fresh services produces identical audit semantics."""
    s1 = BharatiMLService()
    s2 = BharatiMLService()

    seq = [
        BharatiTelemetryInput("BRT", "BRT_POWER_001", f"2026-09-18T11:{step:02d}:00Z", 25.0 + (step % 2))
        for step in range(1, 32)
    ]

    for item in seq:
        s1.process_telemetry(item)
        s2.process_telemetry(item)

    recs1 = s1.get_recent_audit_records()
    recs2 = s2.get_recent_audit_records()

    assert len(recs1) == len(recs2)
    for r1, r2 in zip(recs1, recs2):
        assert r1.event_type == r2.event_type
        assert r1.anomaly_status == r2.anomaly_status
        assert r1.anomaly_type == r2.anomaly_type
        assert r1.anomaly_score == r2.anomaly_score
        assert r1.history_size_before == r2.history_size_before
        assert r1.history_size_after == r2.history_size_after
