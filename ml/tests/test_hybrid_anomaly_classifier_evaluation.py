"""
Unit & Integration Tests for Hybrid Anomaly Classifier Re-Evaluation (SIH26060 - Person C).
Step 41: Verifies the re-evaluated downstream anomaly-type classification performance,
STUCK_VALUE active flatline detection, recovery behavior, SPIKE/DRIFT non-regression,
missing telemetry handling, multi-sensor isolation, determinism, and artifact integrity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier
from ml.inference.bharati_anomaly_type_classifier import (
    DEFAULT_BHARATI_SENSOR_NOISE_STD,
    BharatiAnomalyTypeClassifier,
)
from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    BharatiTelemetryInput,
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.lstm_inference import LSTMAutoencoderInference
from ml.training.evaluate_hybrid_anomaly_classifier import evaluate_station_classifier

FROZEN_ARTIFACT_HASHES: Dict[str, str] = {
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
    "ml/models/lstm-ae-v1.pt": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
    "ml/models/lstm-ae-v1_config.json": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
    "ml/models/lstm-ae-v1_scaler.json": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
    "ml/results/lstm_threshold.json": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
}


@pytest.fixture
def brt_classifier() -> BharatiAnomalyTypeClassifier:
    return BharatiAnomalyTypeClassifier()


@pytest.fixture
def mtr_classifier() -> AnomalyTypeClassifier:
    return AnomalyTypeClassifier()


# -----------------------------------------------------------------------------
# 1. STUCK_VALUE & Flatline Detection Tests
# -----------------------------------------------------------------------------
def test_1_exact_flatline_detection(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify long exact constant flatline at tail is detected as STUCK_VALUE."""
    # 15 varying + 15 exact flatline values
    window = [-10.0 + 0.1 * i for i in range(15)] + [-8.5] * 15
    res = brt_classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res == "STUCK_VALUE"


def test_2_near_flatline_within_tolerance(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify near-flatline with sub-micro-variance is classified as STUCK_VALUE."""
    # 15 varying + 15 values within 1e-5 tolerance
    window = [-10.0 + 0.1 * i for i in range(15)] + [-8.5 + (1e-6 * (i % 3)) for i in range(15)]
    res = brt_classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    assert res == "STUCK_VALUE"


def test_3_normal_low_variance_not_stuck(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify normal telemetry with natural low variance is not falsely classified as STUCK_VALUE."""
    # Small natural diurnal oscillations (std ~ 0.05, steps ~ 0.02)
    rng = np.random.default_rng(42)
    window = [-10.0 + 0.05 * np.sin(i / 3.0) + rng.normal(0, 0.01) for i in range(30)]
    res = brt_classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=False)
    assert res == "NORMAL"


def test_4_recovery_after_flatline_releases_stuck_state(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify that once active variations resume after a flatline, STUCK_VALUE is not triggered."""
    # 15 flatline values in history, followed by 15 active fluctuating normal values at tail
    rng = np.random.default_rng(42)
    recovered_window = [-8.5] * 15 + [-8.5 + 0.2 * i + rng.normal(0, 0.05) for i in range(1, 16)]
    res = brt_classifier.classify(recovered_window, sensor_id="BRT_TEMP_001", is_known_anomaly=False)
    assert res != "STUCK_VALUE"
    assert res == "NORMAL"


# -----------------------------------------------------------------------------
# 2. SPIKE & DRIFT Non-Regression Tests
# -----------------------------------------------------------------------------
def test_5_spike_non_regression(brt_classifier: BharatiAnomalyTypeClassifier, mtr_classifier: AnomalyTypeClassifier):
    """Verify high-magnitude sudden jump reliably classifies as SPIKE."""
    rng = np.random.default_rng(42)
    window = [-10.0 + rng.normal(0, 0.1) for _ in range(29)] + [35.0]

    brt_res = brt_classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True)
    mtr_res = mtr_classifier.classify(window, sensor_id="TEMP_001", is_known_anomaly=True)

    assert brt_res == "SPIKE"
    assert mtr_res == "SPIKE"


def test_6_drift_non_regression(brt_classifier: BharatiAnomalyTypeClassifier, mtr_classifier: AnomalyTypeClassifier):
    """Verify steady monotonic ramp classifies as DRIFT."""
    window = [980.0 + 0.5 * i for i in range(30)]

    brt_res = brt_classifier.classify(window, sensor_id="BRT_PRESS_001", is_known_anomaly=True)
    mtr_res = mtr_classifier.classify(window, sensor_id="PRESS_001", is_known_anomaly=True)

    assert brt_res == "DRIFT"
    assert mtr_res == "DRIFT"


# -----------------------------------------------------------------------------
# 3. Missing Data & Edge Case Tests
# -----------------------------------------------------------------------------
def test_7_missing_and_nonfinite_telemetry(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify NaN, Inf, empty, and short windows are cleanly handled."""
    assert brt_classifier.classify([], sensor_id="BRT_TEMP_001") == "MISSING_DATA"
    assert brt_classifier.classify(None, sensor_id="BRT_TEMP_001") == "MISSING_DATA"
    assert brt_classifier.classify([-10.0] * 29 + [float("nan")], sensor_id="BRT_TEMP_001") == "MISSING_DATA"
    assert brt_classifier.classify([-10.0] * 29 + [float("inf")], sensor_id="BRT_TEMP_001") == "MISSING_DATA"
    assert brt_classifier.classify([-10.0] * 10, sensor_id="BRT_TEMP_001") == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# 4. Multi-Sensor Isolation & Determinism Tests
# -----------------------------------------------------------------------------
def test_8_multi_sensor_isolation(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify noise-floor adaptation operates independently per sensor."""
    # A step jump of 0.20 is a SPIKE for vibration (sigma=0.03) but NORMAL for humidity (sigma=1.0)
    jump_window = [0.75] * 28 + [0.95, 0.95]
    vib_res = brt_classifier.classify(jump_window, sensor_id="BRT_VIB_001", is_known_anomaly=True)
    hum_res = brt_classifier.classify(jump_window, sensor_id="BRT_HUM_001", is_known_anomaly=True)

    assert vib_res == "SPIKE"
    assert hum_res != "SPIKE"


def test_9_repeated_classification_is_deterministic(brt_classifier: BharatiAnomalyTypeClassifier):
    """Verify 100% deterministic outputs across repeated runs."""
    window = [-10.0 + 0.3 * i for i in range(30)]
    results = [brt_classifier.classify(window, sensor_id="BRT_TEMP_001", is_known_anomaly=True) for _ in range(50)]
    assert all(r == "DRIFT" for r in results)


# -----------------------------------------------------------------------------
# 5. Full Evaluation Artifact Integrity & Metric Tests
# -----------------------------------------------------------------------------
def test_10_evaluation_report_artifacts_exist():
    """Verify generated re-evaluation artifacts exist and contain valid content."""
    json_path = Path("ml/results/hybrid_anomaly_classifier_re_evaluation.json")
    md_path = Path("ml/results/hybrid_anomaly_classifier_re_evaluation.md")

    assert json_path.exists(), "Re-evaluation JSON must exist."
    assert md_path.exists(), "Re-evaluation Markdown must exist."

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "stations" in data
    assert "BRT" in data["stations"]
    assert "MTR" in data["stations"]
    assert "stuck_value_comparison" in data

    # Verify Bharati metrics
    brt_metrics = data["stations"]["BRT"]["overall"]["class_metrics"]
    assert brt_metrics["STUCK_VALUE"]["precision"] == 1.0000
    assert brt_metrics["STUCK_VALUE"]["recall"] == 0.7500
    assert brt_metrics["STUCK_VALUE"]["f1_score"] == 0.8571
    assert brt_metrics["SPIKE"]["recall"] == 1.0000
    assert brt_metrics["NORMAL"]["precision"] == 0.9882

    # Verify Maitri metrics
    mtr_metrics = data["stations"]["MTR"]["overall"]["class_metrics"]
    assert mtr_metrics["STUCK_VALUE"]["precision"] == 1.0000
    assert mtr_metrics["STUCK_VALUE"]["recall"] == 0.7500
    assert mtr_metrics["STUCK_VALUE"]["f1_score"] == 0.8571
    assert mtr_metrics["SPIKE"]["recall"] == 1.0000
    assert mtr_metrics["NORMAL"]["precision"] == 0.9863

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "SYNTHETIC DATA DISCLAIMER" in md_text
    assert "FROZEN ARTIFACTS STATEMENT" in md_text
    assert "STUCK_VALUE" in md_text


def test_11_all_8_frozen_artifacts_intact():
    """Cryptographic verification that none of the 8 frozen ML artifacts were modified."""
    for rel_path, expected_hash in FROZEN_ARTIFACT_HASHES.items():
        file_path = Path(rel_path)
        assert file_path.exists(), f"Frozen artifact {rel_path} missing."
        h = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert h == expected_hash, f"Frozen artifact {rel_path} hash mismatch: {h} != {expected_hash}"
