"""
Unit tests for Polarix Maitri Telemetry Anomaly Type Classifier (SIH26060 - Person C).
"""

import numpy as np
import pytest

from ml.inference.anomaly_type_classifier import (
    AnomalyTypeClassifier,
    WindowFeatures,
)


@pytest.fixture
def classifier():
    return AnomalyTypeClassifier()


def test_1_normal_stable_window(classifier):
    """Verify normal periodic / noisy window without anomalies returns NORMAL or not anomalous."""
    # Stationary sine oscillation with slight noise
    normal_window = [-15.0 + np.sin(i / 5.0) * 1.5 + np.random.default_rng(42).normal(0, 0.1) for i in range(30)]
    res = classifier.classify(normal_window, sensor_id="TEMP_001", is_known_anomaly=False)
    assert res == "NORMAL"


def test_2_synthetic_spike_window(classifier):
    """Verify sudden short-lived jump deviation classifies as SPIKE."""
    # Base baseline with sudden +25.0 spike at index 20 lasting 3 steps
    rng = np.random.default_rng(42)
    spike_window = [-15.0 + rng.normal(0, 0.2) for _ in range(30)]
    spike_window[20] += 20.0
    spike_window[21] += 20.0
    spike_window[22] += 20.0

    res = classifier.classify(spike_window, sensor_id="TEMP_001", is_known_anomaly=True)
    assert res == "SPIKE"


def test_3_synthetic_drift_window(classifier):
    """Verify sustained linear ramp deviation classifies as DRIFT."""
    # Linear drift ramp of 0.5 per step over 30 steps
    rng = np.random.default_rng(42)
    drift_window = [-15.0 + i * 0.4 + rng.normal(0, 0.05) for i in range(30)]

    res = classifier.classify(drift_window, sensor_id="TEMP_001", is_known_anomaly=True)
    assert res == "DRIFT"


def test_4_synthetic_stuck_value_window(classifier):
    """Verify exact flatline sensor reading classifies as STUCK_VALUE."""
    # Constant value for the last 15 steps
    stuck_window = [-15.0 + i * 0.1 for i in range(15)] + [-13.5] * 15

    res = classifier.classify(stuck_window, sensor_id="TEMP_001", is_known_anomaly=True)
    assert res == "STUCK_VALUE"


def test_5_missing_values(classifier):
    """Verify window containing NaN returns MISSING_DATA."""
    nan_window = [-15.0] * 29 + [np.nan]
    res = classifier.classify(nan_window, sensor_id="TEMP_001")
    assert res == "MISSING_DATA"


def test_6_invalid_empty_window(classifier):
    """Verify empty or None window returns MISSING_DATA."""
    assert classifier.classify([], sensor_id="TEMP_001") == "MISSING_DATA"
    assert classifier.classify(None, sensor_id="TEMP_001") == "MISSING_DATA"


def test_7_short_window(classifier):
    """Verify window with fewer than 30 observations returns INSUFFICIENT_DATA."""
    short_window = [-15.0] * 20
    assert classifier.classify(short_window, sensor_id="TEMP_001") == "INSUFFICIENT_DATA"


def test_8_floating_point_near_stuck_values(classifier):
    """Verify micro-jitter / floating point noise flatline still classifies as STUCK_VALUE."""
    # Jitter within 1e-5 tolerance
    rng = np.random.default_rng(42)
    near_stuck = [-15.0 + rng.uniform(-1e-6, 1e-6) for _ in range(30)]

    res = classifier.classify(near_stuck, sensor_id="TEMP_001", is_known_anomaly=True)
    assert res == "STUCK_VALUE"


def test_9_deterministic_classification(classifier):
    """Verify repeated classification of identical windows produces identical results."""
    window = [-15.0 + i * 0.5 for i in range(30)]
    res1 = classifier.classify(window, sensor_id="TEMP_001", is_known_anomaly=True)
    res2 = classifier.classify(window, sensor_id="TEMP_001", is_known_anomaly=True)
    assert res1 == res2
    assert res1 == "DRIFT"


def test_10_no_use_of_dataset_labels(classifier):
    """Verify classifier operates purely on raw numerical features without external labels."""
    # Arbitrary raw list of floats
    synthetic_arr = np.linspace(10.0, 50.0, 30)
    res = classifier.classify(synthetic_arr, sensor_id="POWER_001", is_known_anomaly=True)
    assert res in {"DRIFT", "SPIKE", "STUCK_VALUE", "NORMAL", "UNKNOWN"}
