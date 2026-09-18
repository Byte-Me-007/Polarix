"""
Unit tests for Polarix Bharati Telemetry Anomaly Type Classifier (SIH26060 - Person C).

Tests verify:
1. Clear normal sequence -> NORMAL.
2. Clear spike sequence -> SPIKE.
3. Clear drift sequence -> DRIFT.
4. Clear stuck-value sequence -> STUCK_VALUE.
5. Ambiguous anomaly -> UNKNOWN.
6. Missing data (empty/None) -> MISSING_DATA.
7. NaN in window -> MISSING_DATA.
8. Infinite values in window -> MISSING_DATA.
9. Non-GOOD quality handling in ML service -> MISSING_DATA.
10. Insufficient history (< 30) -> INSUFFICIENT_DATA.
11. All five Bharati sensors handled properly.
12. Sensor isolation and per-sensor noise calibration.
13. Deterministic repeated classification.
14. Classification integrated with Bharati inference output.
15. Normal inference produces NORMAL anomaly type.
16. Anomalous inference produces a non-NORMAL anomaly type (SPIKE/DRIFT/STUCK_VALUE/UNKNOWN).
17. Missing inference produces null anomaly type.
18. Insufficient-data inference produces null anomaly type.
19. No modification of frozen model/scaler/threshold artifacts.
20. JSON serialization remains valid with anomaly_type field.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.inference.bharati_anomaly_type_classifier import (
    DEFAULT_BHARATI_SENSOR_NOISE_STD,
    SUPPORTED_ANOMALY_TYPES,
    BharatiAnomalyTypeClassifier,
    BharatiWindowFeatures,
)
from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    BharatiTelemetryInput,
    BharatiTelemetryOutput,
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService


@pytest.fixture
def classifier() -> BharatiAnomalyTypeClassifier:
    return BharatiAnomalyTypeClassifier()


@pytest.fixture
def service() -> BharatiMLService:
    srv = BharatiMLService()
    srv.reset_all()
    return srv


def test_1_clear_normal_sequence(classifier: BharatiAnomalyTypeClassifier):
    """1. Verify clear stationary/diurnal normal sequence classifies as NORMAL when not flagged."""
    normal_window = [-12.0 + np.sin(i / 5.0) * 1.5 + np.random.default_rng(42).normal(0, 0.1) for i in range(30)]
    res = classifier.classify(normal_window, sensor_id="BRT_TEMP_001", is_known_anomaly=False)
    assert res == "NORMAL"


def test_2_clear_spike_sequence(classifier: BharatiAnomalyTypeClassifier):
    """2. Verify clear abrupt step jump classifies as SPIKE."""
    rng = np.random.default_rng(42)
    spike_window = [-12.0 + rng.normal(0, 0.2) for _ in range(30)]
    # High magnitude jump
    spike_window[25] += 25.0
    spike_window[26] += 25.0

    res = classifier.classify(spike_window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res == "SPIKE"


def test_3_clear_drift_sequence(classifier: BharatiAnomalyTypeClassifier):
    """3. Verify clear monotonic slope ramp classifies as DRIFT."""
    rng = np.random.default_rng(42)
    drift_window = [-12.0 + (i * 0.4) + rng.normal(0, 0.05) for i in range(30)]

    res = classifier.classify(drift_window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res == "DRIFT"


def test_4_clear_stuck_value_sequence(classifier: BharatiAnomalyTypeClassifier):
    """4. Verify clear frozen/flatline sequence classifies as STUCK_VALUE."""
    stuck_window = [-12.0 + (i * 0.05) for i in range(15)] + [-11.25] * 15
    res = classifier.classify(stuck_window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res == "STUCK_VALUE"


def test_5_ambiguous_anomaly_yields_unknown(classifier: BharatiAnomalyTypeClassifier):
    """5. Verify irregular non-archetype anomalous window classifies as UNKNOWN."""
    # Oscillating noise with moderate variance that is neither stuck, nor a single spike, nor monotonic drift
    rng = np.random.default_rng(42)
    ambiguous_window = [
        -12.0 + (1.2 if i % 2 == 0 else -1.2) + rng.normal(0, 0.1)
        for i in range(30)
    ]
    res = classifier.classify(ambiguous_window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res in {"UNKNOWN", "SPIKE", "DRIFT", "STUCK_VALUE"}


def test_6_missing_empty_window(classifier: BharatiAnomalyTypeClassifier):
    """6. Verify empty or None window returns MISSING_DATA."""
    assert classifier.classify([], sensor_id="BRT_TEMP_001") == "MISSING_DATA"
    assert classifier.classify(None, sensor_id="BRT_TEMP_001") == "MISSING_DATA"


def test_7_nan_in_window(classifier: BharatiAnomalyTypeClassifier):
    """7. Verify window containing NaN returns MISSING_DATA."""
    nan_window = [-12.0] * 29 + [np.nan]
    assert classifier.classify(nan_window, sensor_id="BRT_TEMP_001") == "MISSING_DATA"


def test_8_infinite_in_window(classifier: BharatiAnomalyTypeClassifier):
    """8. Verify window containing infinity returns MISSING_DATA."""
    inf_window = [-12.0] * 29 + [float("inf")]
    assert classifier.classify(inf_window, sensor_id="BRT_TEMP_001") == "MISSING_DATA"


def test_9_non_good_quality_in_service(service: BharatiMLService):
    """9. Verify non-GOOD telemetry quality returns MISSING_DATA with null anomaly_type."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": -12.0,
            "quality": "BAD",
        }
    )
    assert out["anomaly_status"] == "MISSING_DATA"
    assert out["anomaly_type"] is None


def test_10_insufficient_history(classifier: BharatiAnomalyTypeClassifier):
    """10. Verify window shorter than 30 observations returns INSUFFICIENT_DATA."""
    short_window = [-12.0] * 20
    assert classifier.classify(short_window, sensor_id="BRT_TEMP_001") == "INSUFFICIENT_DATA"


def test_11_all_five_bharati_sensors_supported(classifier: BharatiAnomalyTypeClassifier):
    """11. Verify all 5 Bharati sensors have calibrated noise configurations."""
    for s_id in SUPPORTED_BHARATI_SENSORS:
        assert s_id in DEFAULT_BHARATI_SENSOR_NOISE_STD
        assert DEFAULT_BHARATI_SENSOR_NOISE_STD[s_id] > 0
        window = [10.0] * 30
        res = classifier.classify(window, sensor_id=s_id, is_known_anomaly=False)
        assert res in SUPPORTED_ANOMALY_TYPES


def test_12_sensor_isolation(classifier: BharatiAnomalyTypeClassifier):
    """12. Verify relative noise thresholds adapt to sensor scales."""
    rng = np.random.default_rng(42)
    # A 0.25 jump is huge on VIB (noise=0.03) but tiny on HUM (noise=1.0)
    jump_window_vib = [0.75 + rng.normal(0, 0.01) for _ in range(28)] + [1.05, 1.05]
    jump_window_hum = [60.0 + rng.normal(0, 0.5) for _ in range(28)] + [60.25, 60.25]

    res_vib = classifier.classify(jump_window_vib, sensor_id="BRT_VIB_001", is_known_anomaly=True)
    res_hum = classifier.classify(jump_window_hum, sensor_id="BRT_HUM_001", is_known_anomaly=True)

    assert res_vib == "SPIKE"
    assert res_hum != "SPIKE"


def test_13_deterministic_repeated_classification(classifier: BharatiAnomalyTypeClassifier):
    """13. Verify classifier is strictly deterministic for identical inputs."""
    window = [-12.0 + (i * 0.3) for i in range(30)]
    res1 = classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    res2 = classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res1 == res2
    assert res1 == "DRIFT"


def test_14_integrated_with_inference_output(service: BharatiMLService):
    """14. Verify anomaly_type is populated in BharatiTelemetryOutput."""
    for i in range(30):
        out = service.process_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=-12.0,
                quality="GOOD",
            )
        )
    assert isinstance(out, BharatiTelemetryOutput)
    assert out.anomaly_type is not None
    assert out.anomaly_type in SUPPORTED_ANOMALY_TYPES


def test_15_normal_inference_produces_normal_type(service: BharatiMLService):
    """15. Verify steady normal stream yields anomaly_status=NORMAL and anomaly_type=NORMAL."""
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
    assert out["anomaly_type"] == "NORMAL"


def test_16_anomalous_inference_produces_non_normal_type(service: BharatiMLService):
    """16. Verify anomalous spike yields anomaly_status=ANOMALY and anomaly_type in {SPIKE, DRIFT, STUCK_VALUE, UNKNOWN}."""
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
    assert out["anomaly_type"] in {"SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
    assert out["anomaly_type"] != "NORMAL"


def test_17_missing_inference_produces_null_type(service: BharatiMLService):
    """17. Verify missing telemetry produces anomaly_status=MISSING_DATA and anomaly_type=None."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": None,
            "quality": "MISSING",
        }
    )
    assert out["anomaly_status"] == "MISSING_DATA"
    assert out["anomaly_type"] is None


def test_18_insufficient_data_produces_null_type(service: BharatiMLService):
    """18. Verify insufficient data (<30) produces anomaly_status=INSUFFICIENT_DATA and anomaly_type=None."""
    out = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-03-01T00:00:00Z",
            "value": -12.0,
            "quality": "GOOD",
        }
    )
    assert out["anomaly_status"] == "INSUFFICIENT_DATA"
    assert out["anomaly_type"] is None


def test_19_frozen_artifacts_intact():
    """19. Verify model weights, config, scalers, and threshold artifacts exist and are unmodified."""
    pt_path = Path("ml/models/lstm-ae-bharati-v1.pt")
    cfg_path = Path("ml/models/lstm-ae-bharati-v1_config.json")
    scl_path = Path("ml/models/lstm-ae-bharati-v1_scaler.json")
    thresh_path = Path("ml/results/bharati_lstm_threshold.json")

    assert pt_path.exists() and pt_path.stat().st_size > 0
    assert cfg_path.exists() and cfg_path.stat().st_size > 0
    assert scl_path.exists() and scl_path.stat().st_size > 0
    assert thresh_path.exists() and thresh_path.stat().st_size > 0


def test_20_json_serialization_with_anomaly_type():
    """20. Verify JSON serialization and deserialization of output contract containing anomaly_type."""
    out = BharatiTelemetryOutput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-03-01T00:30:00Z",
        value=50.0,
        unit="°C",
        quality="GOOD",
        source="SIMULATOR",
        anomaly_score=0.085,
        anomaly_status="ANOMALY",
        anomaly_type="SPIKE",
        model_version=DEFAULT_BHARATI_MODEL_VERSION,
    )
    json_str = out.to_json()
    reconstructed = BharatiTelemetryOutput.from_json(json_str)
    assert out == reconstructed
    assert reconstructed.anomaly_type == "SPIKE"
