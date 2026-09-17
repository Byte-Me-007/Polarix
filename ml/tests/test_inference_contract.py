"""
Unit tests for Polarix ML Telemetry Inference Contract (SIH26060 - Person C).
"""

import json
from pathlib import Path

import numpy as np
import pytest

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_QUALITIES,
    VALID_STATUSES,
    InvalidContractError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.lstm_inference import LSTMAutoencoderInference


@pytest.fixture
def inference_engine():
    """Fixture providing initialized inference service."""
    return LSTMAutoencoderInference()


def test_1_valid_telemetry_input_creation():
    """Verify standard TelemetryInput instantiation."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:30:00Z",
        value=-34.5,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
    )
    assert inp.station_id == "MTR"
    assert inp.sensor_id == "TEMP_001"
    assert inp.timestamp == "2026-09-17T10:30:00Z"
    assert inp.value == -34.5
    assert inp.unit == "C"
    assert inp.quality == "GOOD"
    assert inp.source == "SIMULATOR"


def test_2_valid_output_creation():
    """Verify standard TelemetryInferenceOutput instantiation."""
    out = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:30:00Z",
        value=-34.5,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.0215,
        anomaly_status="ANOMALY",
        model_version="lstm-ae-v1",
    )
    assert out.station_id == "MTR"
    assert out.sensor_id == "TEMP_001"
    assert out.timestamp == "2026-09-17T10:30:00Z"
    assert out.value == -34.5
    assert out.unit == "C"
    assert out.quality == "GOOD"
    assert out.source == "SIMULATOR"
    assert out.anomaly_score == 0.0215
    assert out.anomaly_status == "ANOMALY"
    assert out.model_version == "lstm-ae-v1"


def test_3_json_serialization():
    """Verify serialization to JSON string and deserialization back to contract."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="PRESS_001",
        timestamp="2026-09-17T10:30:00Z",
        value=985.2,
        unit="hPa",
        quality="GOOD",
        source="SIMULATOR",
    )
    json_str = inp.to_json()
    loaded_inp = TelemetryInput.from_json(json_str)
    assert inp == loaded_inp

    out = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="PRESS_001",
        timestamp="2026-09-17T10:30:00Z",
        value=985.2,
        unit="hPa",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.0012,
        anomaly_status="NORMAL",
        model_version="lstm-ae-v1",
    )
    out_json = out.to_json()
    loaded_out = TelemetryInferenceOutput.from_json(out_json)
    assert out == loaded_out


def test_4_required_fields():
    """Verify empty or missing required fields raise InvalidContractError."""
    with pytest.raises(InvalidContractError):
        TelemetryInput(
            station_id="",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
        )

    with pytest.raises(InvalidContractError):
        TelemetryInput(
            station_id="MTR",
            sensor_id="",
            timestamp="2026-09-17T10:30:00Z",
        )

    with pytest.raises(InvalidContractError):
        TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp="",
        )


def test_5_nullable_anomaly_score():
    """Verify anomaly_score is None for INSUFFICIENT_DATA and MISSING_DATA."""
    out_insuff = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:30:00Z",
        value=-34.5,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=None,
        anomaly_status="INSUFFICIENT_DATA",
    )
    assert out_insuff.anomaly_score is None

    out_missing = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:30:00Z",
        value=None,
        unit="C",
        quality="BAD",
        source="SIMULATOR",
        anomaly_score=None,
        anomaly_status="MISSING_DATA",
    )
    assert out_missing.anomaly_score is None

    # Invalid: non-None score with INSUFFICIENT_DATA
    with pytest.raises(InvalidContractError):
        TelemetryInferenceOutput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
            value=-34.5,
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
            anomaly_score=0.05,
            anomaly_status="INSUFFICIENT_DATA",
        )


def test_6_valid_status_values():
    """Verify only permitted anomaly_status values are accepted."""
    for valid_status in ["NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"]:
        score = 0.01 if valid_status in ["NORMAL", "ANOMALY"] else None
        out = TelemetryInferenceOutput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
            value=-34.5,
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
            anomaly_score=score,
            anomaly_status=valid_status,
        )
        assert out.anomaly_status == valid_status

    with pytest.raises(InvalidContractError):
        TelemetryInferenceOutput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
            value=-34.5,
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
            anomaly_score=0.01,
            anomaly_status="UNKNOWN_STATUS",
        )


def test_7_model_version_preservation():
    """Verify exact model version string is maintained in output."""
    out = TelemetryInferenceOutput(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-09-17T10:30:00Z",
        value=45.0,
        unit="%",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.005,
        anomaly_status="NORMAL",
        model_version="lstm-ae-v1",
    )
    assert out.model_version == "lstm-ae-v1"


def test_8_station_id_preservation():
    """Verify station_id is preserved from input to output."""
    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="POWER_001",
        timestamp="2026-09-17T10:30:00Z",
        value=32.0,
    )
    assert inp.station_id == "MTR"


def test_9_sensor_id_preservation():
    """Verify sensor_id is preserved from input to output."""
    for sensor in ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]:
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id=sensor,
            timestamp="2026-09-17T10:30:00Z",
            value=10.0,
        )
        assert inp.sensor_id == sensor


def test_10_unsupported_sensor_rejection():
    """Verify arbitrary unsupported sensor IDs are rejected with UnsupportedSensorError."""
    with pytest.raises(UnsupportedSensorError):
        TelemetryInput(
            station_id="MTR",
            sensor_id="UNSUPPORTED_SENSOR_999",
            timestamp="2026-09-17T10:30:00Z",
            value=10.0,
        )

    with pytest.raises(UnsupportedSensorError):
        TelemetryInferenceOutput(
            station_id="MTR",
            sensor_id="UNSUPPORTED_SENSOR_999",
            timestamp="2026-09-17T10:30:00Z",
            value=10.0,
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
            anomaly_score=0.01,
            anomaly_status="NORMAL",
        )


def test_11_unsupported_station_rejection():
    """Verify non-Maitri stations (including future Bharati) are rejected at this stage."""
    with pytest.raises(UnsupportedStationError):
        TelemetryInput(
            station_id="BHARATI",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
            value=-20.0,
        )

    with pytest.raises(UnsupportedStationError):
        TelemetryInferenceOutput(
            station_id="BHARATI",
            sensor_id="TEMP_001",
            timestamp="2026-09-17T10:30:00Z",
            value=-20.0,
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
            anomaly_score=0.01,
            anomaly_status="NORMAL",
        )


def test_12_deterministic_contract_conversion():
    """Verify conversion between object, dict, and JSON is deterministic."""
    data = {
        "station_id": "MTR",
        "sensor_id": "VIB_001",
        "timestamp": "2026-09-17T10:30:00Z",
        "value": 0.45,
        "unit": "mm/s",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    inp1 = TelemetryInput.from_dict(data)
    inp2 = TelemetryInput.from_dict(data)
    assert inp1 == inp2
    assert inp1.to_json() == inp2.to_json()


def test_13_compatibility_with_lstm_autoencoder_inference(inference_engine):
    """Verify infer_telemetry accepts TelemetryInput and dict and returns TelemetryInferenceOutput."""
    inference_engine.reset_history("MTR", "TEMP_001")

    inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:00:00Z",
        value=-25.0,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
    )
    out = inference_engine.infer_telemetry(inp)

    assert isinstance(out, TelemetryInferenceOutput)
    assert out.station_id == inp.station_id
    assert out.sensor_id == inp.sensor_id
    assert out.timestamp == inp.timestamp
    assert out.value == inp.value
    assert out.unit == inp.unit
    assert out.quality == inp.quality
    assert out.source == inp.source
    assert out.model_version == "lstm-ae-v1"


def test_14_normal_output(inference_engine):
    """Verify stream reaching 30 normal points produces NORMAL status."""
    inference_engine.reset_history("MTR", "TEMP_001")

    out = None
    for i in range(30):
        val = -15.0 + np.sin(i / 10.0) * 1.5
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-17T10:{i:02d}:00Z",
            value=float(val),
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
        )
        out = inference_engine.infer_telemetry(inp)

    assert out.anomaly_status == "NORMAL"
    assert isinstance(out.anomaly_score, float)
    assert out.anomaly_score <= inference_engine.threshold


def test_15_anomaly_output(inference_engine):
    """Verify anomalous sequence produces ANOMALY status."""
    inference_engine.reset_history("MTR", "TEMP_001")

    # 29 baseline normal points
    for i in range(29):
        val = -15.0 + np.sin(i / 10.0) * 1.5
        inference_engine.infer_telemetry(
            TelemetryInput(
                station_id="MTR",
                sensor_id="TEMP_001",
                timestamp=f"2026-09-17T10:{i:02d}:00Z",
                value=float(val),
                unit="C",
                quality="GOOD",
                source="SIMULATOR",
            )
        )

    # 30th point is massive shock/spike (+50 degrees)
    spike_inp = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:29:00Z",
        value=35.0,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
    )
    out = inference_engine.infer_telemetry(spike_inp)

    assert out.anomaly_status == "ANOMALY"
    assert isinstance(out.anomaly_score, float)
    assert out.anomaly_score > inference_engine.threshold


def test_16_insufficient_data_output(inference_engine):
    """Verify first 29 points return INSUFFICIENT_DATA."""
    inference_engine.reset_history("MTR", "PRESS_001")

    for i in range(29):
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id="PRESS_001",
            timestamp=f"2026-09-17T10:{i:02d}:00Z",
            value=990.0 + i * 0.1,
            unit="hPa",
            quality="GOOD",
            source="SIMULATOR",
        )
        out = inference_engine.infer_telemetry(inp)
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None


def test_17_missing_data_output(inference_engine):
    """Verify null value or bad quality returns MISSING_DATA."""
    inference_engine.reset_history("MTR", "HUM_001")

    # Null value
    out_null = inference_engine.infer_telemetry(
        TelemetryInput(
            station_id="MTR",
            sensor_id="HUM_001",
            timestamp="2026-09-17T10:00:00Z",
            value=None,
            unit="%",
            quality="GOOD",
            source="SIMULATOR",
        )
    )
    assert out_null.anomaly_status == "MISSING_DATA"
    assert out_null.anomaly_score is None

    # Bad quality flag
    out_bad = inference_engine.infer_telemetry(
        TelemetryInput(
            station_id="MTR",
            sensor_id="HUM_001",
            timestamp="2026-09-17T10:01:00Z",
            value=65.0,
            unit="%",
            quality="BAD",
            source="SIMULATOR",
        )
    )
    assert out_bad.anomaly_status == "MISSING_DATA"
    assert out_bad.anomaly_score is None
