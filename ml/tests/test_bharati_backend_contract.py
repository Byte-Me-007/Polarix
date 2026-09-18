"""
Unit and Integration tests for Bharati ML Backend Integration Contract (SIH26060 - Person C).

Validates the contract between Person A's backend and Person C's Bharati ML service.
"""

from __future__ import annotations

import json
import math
import pytest

from ml.inference.bharati_backend_contract import (
    EXAMPLE_BHARATI_BACKEND_INFERENCE_OUTPUT_ANOMALY,
    EXAMPLE_BHARATI_BACKEND_INFERENCE_OUTPUT_NORMAL,
    EXAMPLE_BHARATI_BACKEND_TELEMETRY_INPUT,
    adapt_backend_input,
    adapt_backend_output,
    process_backend_payload,
)
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
)
from ml.inference.bharati_ml_service import BharatiMLService
from ml.models.model_registry import compute_file_sha256

FROZEN_BHARATI_MODEL_VERSION = "lstm-ae-bharati-v1"
FROZEN_BHARATI_THRESHOLD = 0.013215307652775843

FROZEN_MAITRI_MODEL_SHA = "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262"
FROZEN_MAITRI_CONFIG_SHA = "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b"
FROZEN_MAITRI_SCALER_SHA = "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224"
FROZEN_MAITRI_THRESHOLD_SHA = "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1"


@pytest.fixture
def service() -> BharatiMLService:
    srv = BharatiMLService(verify_manifest=True)
    srv.reset_all()
    return srv


# -----------------------------------------------------------------------------
# 1. Canonical Examples & Input Adapter Tests
# -----------------------------------------------------------------------------
def test_1_canonical_examples_valid():
    """Verify that predefined canonical example payloads pass contract validation."""
    inp = adapt_backend_input(EXAMPLE_BHARATI_BACKEND_TELEMETRY_INPUT)
    assert inp.station_id == "BRT"
    assert inp.sensor_id == "BRT_TEMP_001"
    assert inp.quality == "GOOD"

    out_norm = adapt_backend_output(EXAMPLE_BHARATI_BACKEND_INFERENCE_OUTPUT_NORMAL)
    assert out_norm["station_id"] == "BRT"
    assert out_norm["anomaly_status"] == "NORMAL"
    assert out_norm["model_version"] == FROZEN_BHARATI_MODEL_VERSION

    out_anom = adapt_backend_output(EXAMPLE_BHARATI_BACKEND_INFERENCE_OUTPUT_ANOMALY)
    assert out_anom["station_id"] == "BRT"
    assert out_anom["anomaly_status"] == "ANOMALY"
    assert out_anom["anomaly_type"] == "SPIKE"


def test_2_adapt_backend_input_json_string():
    """Verify adapt_backend_input correctly parses and validates raw JSON strings."""
    raw_json = json.dumps(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_PRESS_001",
            "timestamp": "2026-09-18T12:00:00Z",
            "value": 985.4,
            "unit": "hPa",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
    )
    inp = adapt_backend_input(raw_json)
    assert isinstance(inp, BharatiTelemetryInput)
    assert inp.station_id == "BRT"
    assert inp.sensor_id == "BRT_PRESS_001"
    assert inp.value == 985.4


def test_3_adapt_backend_input_dict():
    """Verify adapt_backend_input correctly parses and validates dictionary inputs."""
    d = {
        "station_id": "BRT",
        "sensor_id": "BRT_HUM_001",
        "timestamp": "2026-09-18T12:00:00Z",
        "value": 62.5,
        "unit": "%",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    inp = adapt_backend_input(d)
    assert isinstance(inp, BharatiTelemetryInput)
    assert inp.sensor_id == "BRT_HUM_001"


def test_4_adapt_backend_input_invalid_types():
    """Verify adapt_backend_input raises InvalidContractError for non-dict/string types."""
    with pytest.raises(InvalidContractError):
        adapt_backend_input(12345)  # type: ignore

    with pytest.raises(InvalidContractError):
        adapt_backend_input(["station_id", "BRT"])  # type: ignore


# -----------------------------------------------------------------------------
# 2. Output Adaptation & Metadata Preservation Tests
# -----------------------------------------------------------------------------
def test_5_adapt_backend_output_metadata_preservation():
    """Verify that adapt_backend_output strictly preserves all metadata and fields."""
    infer_out = BharatiTelemetryOutput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-09-18T10:30:00Z",
        value=-10.5,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.0025,
        anomaly_status="NORMAL",
        anomaly_type="NORMAL",
        model_version=DEFAULT_BHARATI_MODEL_VERSION,
    )
    d = adapt_backend_output(infer_out)

    assert d["station_id"] == "BRT"
    assert d["sensor_id"] == "BRT_TEMP_001"
    assert d["timestamp"] == "2026-09-18T10:30:00Z"
    assert d["value"] == -10.5
    assert d["unit"] == "C"
    assert d["quality"] == "GOOD"
    assert d["source"] == "SIMULATOR"
    assert d["anomaly_score"] == 0.0025
    assert d["anomaly_status"] == "NORMAL"
    assert d["anomaly_type"] == "NORMAL"
    assert d["model_version"] == FROZEN_BHARATI_MODEL_VERSION


def test_6_adapt_backend_output_no_non_finite_values():
    """Verify that adapt_backend_output sanitizes non-finite values into None for clean JSON."""
    infer_out = BharatiTelemetryOutput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
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
def test_7_process_backend_payload_normal(service: BharatiMLService):
    """Verify full end-to-end normal pipeline with dictionary payload."""
    res = None
    for step in range(1, 31):
        payload = {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": f"2026-09-18T00:{step:02d}:00Z",
            "value": -10.0 + 0.1 * (step % 4),
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        res = process_backend_payload(service, payload)

    assert res is not None
    assert res["station_id"] == "BRT"
    assert res["sensor_id"] == "BRT_TEMP_001"
    assert res["anomaly_status"] in {"NORMAL", "ANOMALY"}
    assert res["anomaly_score"] is not None and math.isfinite(res["anomaly_score"])
    assert res["model_version"] == FROZEN_BHARATI_MODEL_VERSION


def test_8_process_backend_payload_anomaly(service: BharatiMLService):
    """Verify full end-to-end anomaly pipeline producing ANOMALY status."""
    for step in range(1, 31):
        service.process_telemetry(
            BharatiTelemetryInput(
                "BRT", "BRT_TEMP_001", f"2026-09-18T01:{step:02d}:00Z", -10.0 + 0.1 * (step % 4)
            )
        )
    # Inject spike
    spike_payload = {
        "station_id": "BRT",
        "sensor_id": "BRT_TEMP_001",
        "timestamp": "2026-09-18T01:31:00Z",
        "value": 25.0,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    res = process_backend_payload(service, spike_payload)
    assert res["anomaly_status"] == "ANOMALY"
    assert res["anomaly_type"] in {"SPIKE", "UNKNOWN"}
    assert res["anomaly_score"] is not None and res["anomaly_score"] > service.threshold


def test_9_process_backend_payload_insufficient_and_missing(service: BharatiMLService):
    """Verify handling of insufficient and missing telemetry payloads."""
    # Insufficient
    ins_payload = {
        "station_id": "BRT",
        "sensor_id": "BRT_HUM_001",
        "timestamp": "2026-09-18T02:01:00Z",
        "value": 60.0,
    }
    res_ins = process_backend_payload(service, ins_payload)
    assert res_ins["anomaly_status"] == "INSUFFICIENT_DATA"
    assert res_ins["anomaly_score"] is None
    assert res_ins["anomaly_type"] is None

    # Missing
    mis_payload = {
        "station_id": "BRT",
        "sensor_id": "BRT_HUM_001",
        "timestamp": "2026-09-18T02:02:00Z",
        "value": None,
        "quality": "MISSING",
    }
    res_mis = process_backend_payload(service, mis_payload)
    assert res_mis["anomaly_status"] == "MISSING_DATA"
    assert res_mis["anomaly_score"] is None
    assert res_mis["anomaly_type"] is None


def test_10_process_backend_payload_duplicate_rejection(service: BharatiMLService):
    """Verify duplicate telemetry raises DuplicateTelemetryError."""
    p1 = {
        "station_id": "BRT",
        "sensor_id": "BRT_VIB_001",
        "timestamp": "2026-09-18T03:00:00Z",
        "value": 0.05,
    }
    process_backend_payload(service, p1)
    with pytest.raises(DuplicateTelemetryError):
        process_backend_payload(service, p1)


def test_11_process_backend_payload_stale_rejection(service: BharatiMLService):
    """Verify stale out-of-order telemetry raises StaleTelemetryError."""
    p1 = {
        "station_id": "BRT",
        "sensor_id": "BRT_VIB_001",
        "timestamp": "2026-09-18T03:10:00Z",
        "value": 0.05,
    }
    process_backend_payload(service, p1)

    p_stale = {
        "station_id": "BRT",
        "sensor_id": "BRT_VIB_001",
        "timestamp": "2026-09-18T03:05:00Z",
        "value": 0.05,
    }
    with pytest.raises(StaleTelemetryError):
        process_backend_payload(service, p_stale)


def test_12_process_backend_payload_unsupported_station(service: BharatiMLService):
    """Verify unsupported station is rejected."""
    p_bad_st = {
        "station_id": "MAITRI",
        "sensor_id": "BRT_VIB_001",
        "timestamp": "2026-09-18T04:00:00Z",
        "value": 0.05,
    }
    with pytest.raises((UnsupportedStationError, InvalidContractError)):
        process_backend_payload(service, p_bad_st)


def test_13_process_backend_payload_unsupported_sensor(service: BharatiMLService):
    """Verify unsupported sensor is rejected."""
    p_bad_sens = {
        "station_id": "BRT",
        "sensor_id": "INVALID_SENSOR",
        "timestamp": "2026-09-18T04:00:00Z",
        "value": 0.05,
    }
    with pytest.raises(UnsupportedSensorError):
        process_backend_payload(service, p_bad_sens)


def test_14_multi_sensor_interleaved_backend_traffic(service: BharatiMLService):
    """Verify concurrent interleaved backend payloads across 5 sensors do not mix state."""
    for step in range(1, 31):
        for s_id in sorted(list(SUPPORTED_BHARATI_SENSORS)):
            payload = {
                "station_id": "BRT",
                "sensor_id": s_id,
                "timestamp": f"2026-09-18T05:{step:02d}:00Z",
                "value": 10.0 + step,
                "quality": "GOOD",
            }
            res = process_backend_payload(service, payload)
            if step < 30:
                assert res["anomaly_status"] == "INSUFFICIENT_DATA"
            else:
                assert res["anomaly_status"] in {"NORMAL", "ANOMALY"}
                assert res["anomaly_score"] is not None


def test_15_full_json_roundtrip_all_statuses(service: BharatiMLService):
    """Verify full JSON string serialization and deserialization roundtrip."""
    payloads = [
        # Insufficient
        {"station_id": "BRT", "sensor_id": "BRT_POWER_001", "timestamp": "2026-09-18T06:01:00Z", "value": 40.0},
        # Missing
        {"station_id": "BRT", "sensor_id": "BRT_POWER_001", "timestamp": "2026-09-18T06:02:00Z", "value": None, "quality": "BAD"},
    ]

    for p in payloads:
        res = process_backend_payload(service, json.dumps(p))
        json_res = json.dumps(res)
        parsed = json.loads(json_res)
        assert parsed["station_id"] == "BRT"
        assert parsed["model_version"] == FROZEN_BHARATI_MODEL_VERSION
        assert set(parsed.keys()) == {
            "station_id",
            "sensor_id",
            "timestamp",
            "value",
            "unit",
            "quality",
            "source",
            "anomaly_score",
            "anomaly_status",
            "anomaly_type",
            "model_version",
        }


def test_16_model_version_transparency(service: BharatiMLService):
    """Verify model version is explicitly lstm-ae-bharati-v1 in all outputs."""
    p = {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-09-18T07:00:00Z", "value": -10.0}
    res = process_backend_payload(service, p)
    assert res["model_version"] == FROZEN_BHARATI_MODEL_VERSION


def test_17_frozen_threshold_invariant(service: BharatiMLService):
    """Verify reconstruction threshold is strictly 0.013215307652775843."""
    assert abs(service.threshold - FROZEN_BHARATI_THRESHOLD) < 1e-12


def test_18_maitri_artifacts_untouched():
    """Verify Maitri artifacts are completely untouched."""
    assert compute_file_sha256("ml/models/lstm-ae-v1.pt") == FROZEN_MAITRI_MODEL_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_config.json") == FROZEN_MAITRI_CONFIG_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_scaler.json") == FROZEN_MAITRI_SCALER_SHA
    assert compute_file_sha256("ml/results/lstm_threshold.json") == FROZEN_MAITRI_THRESHOLD_SHA
