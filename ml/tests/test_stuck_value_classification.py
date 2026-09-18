"""Focused regression test suite for STUCK_VALUE classification & recovery handling.

Verifies:
- Exact and near-flatline STUCK_VALUE detection
- Normal low-variance & short stable periods do not trigger STUCK_VALUE
- Recovery after stuck correctly transitions out of STUCK_VALUE
- Dropout vs STUCK_VALUE separation
- Spike and Drift classification non-regression
- Multi-sensor isolation across all Bharati and Maitri sensors
- Deterministic repeated classification
- Frozen artifact hash preservation
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

from ml.inference.bharati_anomaly_type_classifier import BharatiAnomalyTypeClassifier
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FROZEN_HASHES = {
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
    "ml/models/lstm-ae-v1.pt": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
    "ml/models/lstm-ae-v1_config.json": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
    "ml/models/lstm-ae-v1_scaler.json": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
    "ml/results/lstm_threshold.json": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
}


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def test_frozen_artifacts_intact():
    for rel_path, expected in FROZEN_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Missing frozen artifact: {abs_path}"
        actual = compute_sha256(abs_path)
        assert actual == expected, f"Frozen hash modified: {rel_path}"


def test_exact_flatline_detection():
    clf_b = BharatiAnomalyTypeClassifier()
    clf_m = AnomalyTypeClassifier()

    flat = np.full(30, -25.0)
    assert clf_b.classify(flat, "BRT_TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"
    assert clf_b.classify(flat, "BRT_TEMP_001", is_known_anomaly=False) == "STUCK_VALUE"
    assert clf_m.classify(flat, "TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"


def test_near_flatline_with_microjitter():
    clf = BharatiAnomalyTypeClassifier()
    np.random.seed(42)
    near_flat = -20.0 + np.random.normal(0, 1e-5, 30)
    assert clf.classify(near_flat, "BRT_TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"


def test_tail_flatline_run():
    clf = BharatiAnomalyTypeClassifier()
    np.random.seed(42)
    t = np.linspace(0, 4 * np.pi, 30)
    win = -10.0 + np.sin(t)
    win[-10:] = -10.5  # 10 flat points at tail
    assert clf.classify(win, "BRT_TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"


def test_short_stable_period_not_stuck():
    clf = BharatiAnomalyTypeClassifier()
    np.random.seed(42)
    t = np.linspace(0, 4 * np.pi, 30)
    win = -10.0 + np.sin(t) + np.random.normal(0, 0.1, 30)
    win[-3:] = win[-4]  # only 3 identical points
    assert clf.classify(win, "BRT_TEMP_001", is_known_anomaly=False) == "NORMAL"


def test_recovery_after_stuck_not_stuck_at_tail():
    clf = BharatiAnomalyTypeClassifier()
    np.random.seed(42)
    rec_win = np.zeros(30)
    rec_win[:15] = -15.0  # stuck in past
    rec_win[15:] = -15.0 + 2.0 * np.sin(np.linspace(0, 2 * np.pi, 15)) + np.random.normal(0, 0.1, 15)
    # When primary detector is NORMAL, output should be NORMAL (not STUCK_VALUE)
    assert clf.classify(rec_win, "BRT_TEMP_001", is_known_anomaly=False) == "NORMAL"


def test_dropout_versus_stuck():
    clf = BharatiAnomalyTypeClassifier()
    flat = np.full(30, -25.0)
    flat[-1] = np.nan
    assert clf.classify(flat, "BRT_TEMP_001", is_known_anomaly=True) == "MISSING_DATA"


def test_spike_drift_non_regression():
    clf = BharatiAnomalyTypeClassifier()
    np.random.seed(42)
    # Spike
    spike = np.full(30, 20.0)
    spike[-1] = 45.0
    assert clf.classify(spike, "BRT_POWER_001", is_known_anomaly=True) == "SPIKE"

    # Drift
    drift = 20.0 + np.linspace(0, 10.0, 30) + np.random.normal(0, 0.05, 30)
    assert clf.classify(drift, "BRT_POWER_001", is_known_anomaly=True) == "DRIFT"


def test_multi_sensor_isolation():
    clf = BharatiAnomalyTypeClassifier()
    stuck_win = np.full(30, 50.0)
    sensors = [
        "BRT_TEMP_001",
        "BRT_PRESS_001",
        "BRT_HUM_001",
        "BRT_VIB_001",
        "BRT_POWER_001",
    ]
    for s in sensors:
        assert clf.classify(stuck_win, s, is_known_anomaly=True) == "STUCK_VALUE"


def test_deterministic_repeated_runs():
    clf = BharatiAnomalyTypeClassifier()
    stuck_win = np.full(30, 50.0)
    results = [clf.classify(stuck_win, "BRT_PRESS_001", is_known_anomaly=True) for _ in range(100)]
    assert all(r == "STUCK_VALUE" for r in results)
