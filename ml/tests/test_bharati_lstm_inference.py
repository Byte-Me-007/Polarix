"""Unit tests for Polarix Bharati LSTM Inference Layer & Service Adapter (SIH26060 - Person C).

Tests verify:
1. Supported Bharati sensor.
2. All five Bharati sensors supported.
3. Fewer than 30 valid points -> INSUFFICIENT_DATA.
4. Exactly 30 valid points -> inference occurs.
5. Subsequent rolling inference.
6. Normal telemetry path.
7. Anomaly telemetry path.
8. Missing/null value -> MISSING_DATA.
9. NaN handling -> MISSING_DATA.
10. Infinite value handling -> MISSING_DATA.
11. Non-GOOD quality handling -> MISSING_DATA.
12. Missing data clears sensor history buffer.
13. Sensor history isolation between different sensors.
14. Duplicate timestamp rejection.
15. Stale/out-of-order timestamp rejection.
16. Unsupported sensor rejection.
17. Wrong station rejection.
18. Output preserves telemetry metadata.
19. Output contains correct model version (lstm-ae-bharati-v1).
20. Score is finite whenever inference succeeds.
21. Score is null for non-inference statuses.
22. Frozen threshold (0.013215307652775843) is actually used.
23. Frozen artifacts are properly loaded.
24. Inference is strictly deterministic.
25. Multiple sensors can be processed independently in interleaved streams.
26. Serialization / deserialization of contracts to JSON and Dict.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

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
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService


@pytest.fixture
def service() -> BharatiMLService:
    """Fixture providing a fresh BharatiMLService instance with clean buffers."""
    srv = BharatiMLService()
    srv.reset_all()
    return srv


@pytest.fixture
def engine() -> BharatiLSTMInference:
    """Fixture providing a fresh BharatiLSTMInference engine."""
    eng = BharatiLSTMInference()
    eng.reset_history()
    return eng


def test_1_supported_bharati_sensor(service: BharatiMLService):
    """1. Verify single supported Bharati sensor is accepted."""
    out = service.process_telemetry(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": -12.5,
            "unit": "°C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
    )
    assert out.station_id == "BRT"
    assert out.sensor_id == "BRT_TEMP_001"
    assert out.anomaly_status == "INSUFFICIENT_DATA"


def test_2_all_five_bharati_sensors(service: BharatiMLService):
    """2. Verify all five distinct Bharati sensors are supported and configured."""
    expected_sensors = {
        "BRT_TEMP_001",
        "BRT_PRESS_001",
        "BRT_HUM_001",
        "BRT_VIB_001",
        "BRT_POWER_001",
    }
    assert set(service.supported_sensors) == expected_sensors
    for s_id in expected_sensors:
        res = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": s_id,
                "timestamp": "2026-03-01T00:00:00Z",
                "value": 10.0,
                "quality": "GOOD",
            }
        )
        assert res["sensor_id"] == s_id
        assert res["anomaly_status"] == "INSUFFICIENT_DATA"


def test_3_insufficient_data_under_30_points(service: BharatiMLService):
    """3. Verify feeding fewer than 30 observations returns INSUFFICIENT_DATA."""
    for i in range(29):
        out = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": -12.0,
                "quality": "GOOD",
            }
        )
        assert out["anomaly_status"] == "INSUFFICIENT_DATA"
        assert out["anomaly_score"] is None
    assert service.get_buffer_length("BRT_TEMP_001") == 29


def test_4_exactly_30_points_triggers_inference(service: BharatiMLService):
    """4. Verify exactly 30 points triggers scored model inference."""
    for i in range(29):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_PRESS_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 985.0,
                "quality": "GOOD",
            }
        )
    # 30th point
    out30 = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_PRESS_001",
            "timestamp": "2026-03-01T00:29:00Z",
            "value": 985.0,
            "quality": "GOOD",
        }
    )
    assert out30["anomaly_status"] in {"NORMAL", "ANOMALY"}
    assert out30["anomaly_score"] is not None
    assert isinstance(out30["anomaly_score"], float)
    assert service.get_buffer_length("BRT_PRESS_001") == 30


def test_5_subsequent_rolling_inference(service: BharatiMLService):
    """5. Verify points 31..35 continue rolling inference with 30-length window."""
    for i in range(35):
        out = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_HUM_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 70.0,
                "quality": "GOOD",
            }
        )
        if i >= 29:
            assert out["anomaly_status"] in {"NORMAL", "ANOMALY"}
            assert out["anomaly_score"] is not None
    assert service.get_buffer_length("BRT_HUM_001") == 30


def test_6_normal_telemetry_path(service: BharatiMLService):
    """6. Verify steady normal telemetry yields NORMAL status."""
    for i in range(30):
        out = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_POWER_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 48.0,
                "quality": "GOOD",
            }
        )
    assert out["anomaly_status"] == "NORMAL"
    assert out["anomaly_score"] <= service.threshold


def test_7_anomaly_telemetry_path(service: BharatiMLService):
    """7. Verify anomalous spike yields ANOMALY status."""
    for i in range(29):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_VIB_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 1.5,
                "quality": "GOOD",
            }
        )
    # 30th point is a large spike
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_VIB_001",
            "timestamp": "2026-03-01T00:29:00Z",
            "value": 50.0,
            "quality": "GOOD",
        }
    )
    assert out["anomaly_status"] == "ANOMALY"
    assert out["anomaly_score"] > service.threshold


def test_8_missing_null_value(service: BharatiMLService):
    """8. Verify value == None returns MISSING_DATA and anomaly_score == None."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": None,
            "quality": "GOOD",
        }
    )
    assert out["anomaly_status"] == "MISSING_DATA"
    assert out["anomaly_score"] is None


def test_9_nan_value_handling(service: BharatiMLService):
    """9. Verify NaN value returns MISSING_DATA."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": float("nan"),
            "quality": "GOOD",
        }
    )
    assert out["anomaly_status"] == "MISSING_DATA"
    assert out["anomaly_score"] is None


def test_10_infinite_value_handling(service: BharatiMLService):
    """10. Verify +Inf / -Inf values return MISSING_DATA."""
    out_pos = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": float("inf"),
            "quality": "GOOD",
        }
    )
    assert out_pos["anomaly_status"] == "MISSING_DATA"

    out_neg = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:01:00Z",
            "value": float("-inf"),
            "quality": "GOOD",
        }
    )
    assert out_neg["anomaly_status"] == "MISSING_DATA"


def test_11_non_good_quality_handling(service: BharatiMLService):
    """11. Verify quality != GOOD returns MISSING_DATA."""
    for bad_q in ["BAD", "MISSING", "UNCERTAIN"]:
        out = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": "2026-03-01T00:00:00Z",
                "value": -12.0,
                "quality": bad_q,
            }
        )
        assert out["anomaly_status"] == "MISSING_DATA"
        assert out["anomaly_score"] is None


def test_12_missing_data_clears_buffer(service: BharatiMLService):
    """12. Verify missing/bad observation clears sensor history buffer."""
    # Feed 25 points
    for i in range(25):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": -12.0,
                "quality": "GOOD",
            }
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 25

    # Missing reading arriving
    service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:25:00Z",
            "value": None,
            "quality": "MISSING",
        }
    )
    # Buffer must be cleared to 0
    assert service.get_buffer_length("BRT_TEMP_001") == 0


def test_13_sensor_history_isolation(service: BharatiMLService):
    """13. Verify rolling history buffers remain strictly isolated across sensors."""
    # Feed 20 points to TEMP
    for i in range(20):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": -12.0,
                "quality": "GOOD",
            }
        )
    # Feed 10 points to PRESS
    for i in range(10):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_PRESS_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 985.0,
                "quality": "GOOD",
            }
        )
    assert service.get_buffer_length("BRT_TEMP_001") == 20
    assert service.get_buffer_length("BRT_PRESS_001") == 10


def test_14_duplicate_timestamp_rejection(service: BharatiMLService):
    """14. Verify duplicate timestamp raises DuplicateTelemetryError."""
    service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": -12.0,
            "quality": "GOOD",
        }
    )
    with pytest.raises(DuplicateTelemetryError):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": "2026-03-01T00:00:00Z",
                "value": -12.0,
                "quality": "GOOD",
            }
        )


def test_15_stale_timestamp_rejection(service: BharatiMLService):
    """15. Verify out-of-order/stale timestamp raises StaleTelemetryError."""
    service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:10:00Z",
            "value": -12.0,
            "quality": "GOOD",
        }
    )
    with pytest.raises(StaleTelemetryError):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": "2026-03-01T00:05:00Z",
                "value": -12.0,
                "quality": "GOOD",
            }
        )


def test_16_unsupported_sensor_rejection(service: BharatiMLService):
    """16. Verify unsupported sensor raises UnsupportedSensorError."""
    with pytest.raises(UnsupportedSensorError):
        service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "UNKNOWN_SENSOR_001",
                "timestamp": "2026-03-01T00:00:00Z",
                "value": 10.0,
                "quality": "GOOD",
            }
        )


def test_17_wrong_station_rejection(service: BharatiMLService):
    """17. Verify wrong station raises UnsupportedStationError."""
    with pytest.raises(UnsupportedStationError):
        service.process_dict(
            {
                "station_id": "MTR",  # Maitri sent to Bharati service
                "sensor_id": "BRT_TEMP_001",
                "timestamp": "2026-03-01T00:00:00Z",
                "value": 10.0,
                "quality": "GOOD",
            }
        )


def test_18_output_preserves_metadata(service: BharatiMLService):
    """18. Verify output contract preserves all input metadata fields."""
    out = service.process_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T12:34:56Z",
            value=-15.25,
            unit="°C",
            quality="GOOD",
            source="CUSTOM_SIMULATOR",
        )
    )
    assert out.station_id == "BRT"
    assert out.sensor_id == "BRT_TEMP_001"
    assert out.timestamp == "2026-03-01T12:34:56Z"
    assert out.value == -15.25
    assert out.unit == "°C"
    assert out.quality == "GOOD"
    assert out.source == "CUSTOM_SIMULATOR"


def test_19_output_model_version(service: BharatiMLService):
    """19. Verify model version in output matches lstm-ae-bharati-v1."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": -12.0,
            "quality": "GOOD",
        }
    )
    assert out["model_version"] == "lstm-ae-bharati-v1"


def test_20_score_finite_on_inference(service: BharatiMLService):
    """20. Verify anomaly score is finite float on scored inference."""
    for i in range(30):
        out = service.process_dict(
            {
                "station_id": "BRT",
                "sensor_id": "BRT_POWER_001",
                "timestamp": f"2026-03-01T00:{i:02d}:00Z",
                "value": 48.0,
                "quality": "GOOD",
            }
        )
    assert np.isfinite(out["anomaly_score"])


def test_21_score_null_on_non_inference(service: BharatiMLService):
    """21. Verify score is None for INSUFFICIENT_DATA and MISSING_DATA."""
    out_insuf = service.process_dict(
        {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-03-01T00:00:00Z", "value": -12.0}
    )
    assert out_insuf["anomaly_score"] is None

    out_miss = service.process_dict(
        {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-03-01T00:01:00Z", "value": None}
    )
    assert out_miss["anomaly_score"] is None


def test_22_frozen_threshold_used(service: BharatiMLService):
    """22. Verify the exact frozen threshold is used."""
    expected_threshold = 0.013215307652775843
    assert pytest.approx(service.threshold, rel=1e-6) == expected_threshold


def test_23_frozen_artifacts_loaded(engine: BharatiLSTMInference):
    """23. Verify all frozen artifacts exist and are loaded properly."""
    assert engine.model is not None
    assert engine.scalers is not None
    assert len(engine.scalers) == 5
    assert engine.config.seq_len == 30
    assert engine.config.model_version == "lstm-ae-bharati-v1"


def test_24_deterministic_inference():
    """24. Verify identical window sequences produce identical anomaly scores."""
    eng1 = BharatiLSTMInference()
    eng2 = BharatiLSTMInference()
    window = [-12.0 + (i * 0.05) for i in range(30)]

    out1 = eng1.infer_window("BRT", "BRT_TEMP_001", "2026-03-01T00:30:00Z", window)
    out2 = eng2.infer_window("BRT", "BRT_TEMP_001", "2026-03-01T00:30:00Z", window)

    assert out1.anomaly_score == out2.anomaly_score
    assert out1.anomaly_status == out2.anomaly_status


def test_25_interleaved_multi_sensor_processing(service: BharatiMLService):
    """25. Verify multiple sensors can be fed in interleaved manner without state pollution."""
    sensors = ["BRT_TEMP_001", "BRT_PRESS_001", "BRT_HUM_001", "BRT_VIB_001", "BRT_POWER_001"]
    base_values = {"BRT_TEMP_001": -12.0, "BRT_PRESS_001": 985.0, "BRT_HUM_001": 70.0, "BRT_VIB_001": 1.5, "BRT_POWER_001": 48.0}

    for step in range(30):
        for s in sensors:
            res = service.process_dict(
                {
                    "station_id": "BRT",
                    "sensor_id": s,
                    "timestamp": f"2026-03-01T00:{step:02d}:00Z",
                    "value": base_values[s],
                    "quality": "GOOD",
                }
            )
            if step < 29:
                assert res["anomaly_status"] == "INSUFFICIENT_DATA"
            else:
                assert res["anomaly_status"] in {"NORMAL", "ANOMALY"}
                assert res["anomaly_score"] is not None


def test_26_serialization_and_deserialization():
    """26. Verify JSON string serialization and deserialization of contracts."""
    inp = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-03-01T00:00:00Z",
        value=-12.0,
        unit="°C",
        quality="GOOD",
        source="TEST",
    )
    json_str = inp.to_json()
    reconstructed = BharatiTelemetryInput.from_json(json_str)
    assert inp == reconstructed

    service = BharatiMLService()
    json_out = service.process_json(json_str)
    output_obj = BharatiTelemetryOutput.from_json(json_out)
    assert output_obj.station_id == "BRT"
    assert output_obj.sensor_id == "BRT_TEMP_001"
    assert output_obj.anomaly_status == "INSUFFICIENT_DATA"
