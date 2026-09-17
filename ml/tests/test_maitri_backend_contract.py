"""
Unit and Integration tests for Maitri ML Backend Integration Contract.
Polarix SIH26060 - Person C.
"""

from __future__ import annotations

import json
import math
import pytest

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.maitri_backend_contract import (
    EXAMPLE_BACKEND_INFERENCE_OUTPUT_ANOMALY,
    EXAMPLE_BACKEND_INFERENCE_OUTPUT_NORMAL,
    EXAMPLE_BACKEND_TELEMETRY_INPUT,
    adapt_backend_input,
    adapt_backend_output,
    process_backend_payload,
)
from ml.inference.maitri_ml_service import MaitriMLService


@pytest.fixture
def service() -> MaitriMLService:
    srv = MaitriMLService()
    srv.reset_all()
    srv.clear_diagnostics()
    return srv


# -----------------------------------------------------------------------------
# 1. Canonical Examples & Input Adapter Tests
# -----------------------------------------------------------------------------
def test_1_canonical_examples_valid():
    """Verify that predefined canonical example payloads pass contract validation."""
    inp = adapt_backend_input(EXAMPLE_BACKEND_TELEMETRY_INPUT)
    assert inp.station_id == "MTR"
    assert inp.sensor_id == "TEMP_001"
    assert inp.quality == "GOOD"

    out_norm = adapt_backend_output(EXAMPLE_BACKEND_INFERENCE_OUTPUT_NORMAL)
    assert out_norm["anomaly_status"] == "NORMAL"
    assert out_norm["model_version"] == "lstm-ae-v1"

    out_anom = adapt_backend_output(EXAMPLE_BACKEND_INFERENCE_OUTPUT_ANOMALY)
    assert out_anom["anomaly_status"] == "ANOMALY"
    assert out_anom["anomaly_type"] == "SPIKE"


def test_2_adapt_backend_input_json_string():
    """Verify adapt_backend_input correctly parses and validates raw JSON strings."""
    raw_json = json.dumps({
        "station_id": "MTR",
        "sensor_id": "PRESS_001",
        "timestamp": "2026-09-18T12:00:00Z",
        "value": 985.4,
        "unit": "hPa",
        "quality": "GOOD",
        "source": "SIMULATOR",
    })
    inp = adapt_backend_input(raw_json)
    assert isinstance(inp, TelemetryInput)
    assert inp.station_id == "MTR"
    assert inp.sensor_id == "PRESS_001"
    assert inp.value == 985.4


def test_3_adapt_backend_input_invalid_types():
    """Verify adapt_backend_input raises InvalidContractError for non-dict/string types."""
    with pytest.raises(InvalidContractError):
        adapt_backend_input(12345)  # type: ignore

    with pytest.raises(InvalidContractError):
        adapt_backend_input(["station_id", "MTR"])  # type: ignore


# -----------------------------------------------------------------------------
# 2. Output Adaptation & Metadata Preservation Tests
# -----------------------------------------------------------------------------
def test_4_adapt_backend_output_metadata_preservation():
    """Verify that adapt_backend_output strictly preserves all metadata and fields."""
    infer_out = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T10:30:00Z",
        value=-34.5,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.0125,
        anomaly_status="NORMAL",
        anomaly_type="NORMAL",
        model_version=DEFAULT_MODEL_VERSION,
    )
    d = adapt_backend_output(infer_out)

    assert d["station_id"] == "MTR"
    assert d["sensor_id"] == "TEMP_001"
    assert d["timestamp"] == "2026-09-18T10:30:00Z"
    assert d["value"] == -34.5
    assert d["unit"] == "C"
    assert d["quality"] == "GOOD"
    assert d["source"] == "SIMULATOR"
    assert d["anomaly_score"] == 0.0125
    assert d["anomaly_status"] == "NORMAL"
    assert d["anomaly_type"] == "NORMAL"
    assert d["model_version"] == "lstm-ae-v1"


def test_5_adapt_backend_output_no_non_finite_values():
    """Verify that adapt_backend_output sanitizes non-finite values into None for clean JSON."""
    infer_out = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T10:30:00Z",
        value=float("nan"),
        unit="C",
        quality="BAD",
        source="SIMULATOR",
        anomaly_score=None,
        anomaly_status="MISSING_DATA",
        anomaly_type=None,
    )
    d = adapt_backend_output(infer_out)
    assert d["value"] is None
    assert d["anomaly_score"] is None
    assert d["anomaly_status"] == "MISSING_DATA"

    # Must serialize cleanly to pure standard JSON
    json_str = json.dumps(d)
    assert "NaN" not in json_str


# -----------------------------------------------------------------------------
# 3. End-to-End process_backend_payload Flow Tests
# -----------------------------------------------------------------------------
def test_6_process_backend_payload_normal(service: MaitriMLService):
    """Verify full end-to-end normal pipeline with dictionary payload."""
    for step in range(1, 31):
        payload = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": f"2026-09-18T00:{step:02d}:00Z",
            "value": -15.0 + 0.1 * (step % 4),
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        res = process_backend_payload(service, payload)

    assert res["station_id"] == "MTR"
    assert res["sensor_id"] == "TEMP_001"
    assert res["anomaly_status"] in {"NORMAL", "ANOMALY"}
    assert res["anomaly_score"] is not None and math.isfinite(res["anomaly_score"])


def test_7_process_backend_payload_anomaly(service: MaitriMLService):
    """Verify full end-to-end anomaly pipeline producing ANOMALY status."""
    for step in range(1, 31):
        service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", f"2026-09-18T01:{step:02d}:00Z", -15.0 + 0.1 * (step % 4))
        )
    # Inject spike
    spike_payload = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": "2026-09-18T01:31:00Z",
        "value": 25.0,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    res = process_backend_payload(service, spike_payload)
    assert res["anomaly_status"] == "ANOMALY"
    assert res["anomaly_type"] == "SPIKE"
    assert res["anomaly_score"] is not None and res["anomaly_score"] > service.threshold


def test_8_process_backend_payload_insufficient_and_missing(service: MaitriMLService):
    """Verify handling of insufficient and missing telemetry payloads."""
    # Insufficient
    ins_payload = {
        "station_id": "MTR",
        "sensor_id": "HUM_001",
        "timestamp": "2026-09-18T02:01:00Z",
        "value": 60.0,
    }
    res_ins = process_backend_payload(service, ins_payload)
    assert res_ins["anomaly_status"] == "INSUFFICIENT_DATA"
    assert res_ins["anomaly_score"] is None

    # Missing
    mis_payload = {
        "station_id": "MTR",
        "sensor_id": "HUM_001",
        "timestamp": "2026-09-18T02:02:00Z",
        "value": None,
        "quality": "MISSING",
    }
    res_mis = process_backend_payload(service, mis_payload)
    assert res_mis["anomaly_status"] == "MISSING_DATA"
    assert res_mis["anomaly_score"] is None


def test_9_process_backend_payload_rejections(service: MaitriMLService):
    """Verify rejections for duplicate, stale, and unsupported parameters."""
    # Duplicate
    p1 = {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": "2026-09-18T03:00:00Z", "value": 0.05}
    process_backend_payload(service, p1)
    with pytest.raises(DuplicateTelemetryError):
        process_backend_payload(service, p1)

    # Stale
    p_stale = {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": "2026-09-18T02:59:00Z", "value": 0.05}
    with pytest.raises(StaleTelemetryError):
        process_backend_payload(service, p_stale)

    # Unsupported Station
    p_bad_st = {"station_id": "BHARATI", "sensor_id": "VIB_001", "timestamp": "2026-09-18T04:00:00Z", "value": 0.05}
    with pytest.raises(UnsupportedStationError):
        process_backend_payload(service, p_bad_st)

    # Unsupported Sensor
    p_bad_sens = {"station_id": "MTR", "sensor_id": "INVALID", "timestamp": "2026-09-18T04:00:00Z", "value": 0.05}
    with pytest.raises(UnsupportedSensorError):
        process_backend_payload(service, p_bad_sens)
