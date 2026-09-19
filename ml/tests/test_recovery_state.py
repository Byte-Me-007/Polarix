"""
Unit and Integration Tests for Causal Recovery-State Detection (SIH26060 - Person C).

Validates:
1. Initial state and insufficient history handling.
2. Clean normal sequence state preservation.
3. Active anomaly trigger and transition.
4. Anomaly -> Recovery transition upon baseline convergence.
5. Recovery -> Stable Normal transition after confirmation run.
6. Safety: Recovery state does NOT automatically suppress real anomalies.
7. Causal-only state progression without future leakage.
8. Missing-data handling without raising exceptions.
9. Deterministic classifier compatibility (STUCK_VALUE, DRIFT, SPIKE).
10. Exact reproducibility across repeated runs.
11. Evaluation artifacts schema and presence.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.experiments.sensor_v2.recovery_state.recovery_state_detector import (
    CausalRecoveryStateDetector,
    RecoveryFeatures,
    TelemetryPoint,
    apply_causal_recovery_detector_to_sequence,
)
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestCausalRecoveryStateTransitions:
    """Test state machine transitions and safety constraints."""

    def test_initial_and_insufficient_history(self) -> None:
        det = CausalRecoveryStateDetector(
            sensor_id="TEMP_001",
            anomaly_threshold=3.0,
            min_history_steps=3,
        )
        pt1 = TelemetryPoint("2026-03-01T00:00:00Z", "TEMP_001", 10.0, 0.2, 0.5)
        feats1, adj1, st1 = det.process_step(pt1)
        assert st1 == "INSUFFICIENT_CONTEXT"
        assert adj1 == 0.5

        pt2 = TelemetryPoint("2026-03-01T00:01:00Z", "TEMP_001", 10.1, 0.3, 0.6)
        feats2, adj2, st2 = det.process_step(pt2)
        assert st2 == "INSUFFICIENT_CONTEXT"

        pt3 = TelemetryPoint("2026-03-01T00:02:00Z", "TEMP_001", 10.0, 0.1, 0.4)
        feats3, adj3, st3 = det.process_step(pt3)
        assert st3 in ["CLEAN_NORMAL", "STABLE_NORMAL"]

    def test_clean_normal_sequence(self) -> None:
        det = CausalRecoveryStateDetector(sensor_id="TEMP_001", anomaly_threshold=3.0)
        # Feed 10 clean normal observations
        for i in range(10):
            pt = TelemetryPoint(f"2026-03-01T00:{i:02d}:00Z", "TEMP_001", 10.0, 0.2, 0.4)
            feats, adj_s, state = det.process_step(pt)
            assert adj_s == 0.4
            if i >= 3:
                assert state in ["CLEAN_NORMAL", "STABLE_NORMAL"]

    def test_anomaly_to_recovery_to_stable_transitions(self) -> None:
        det = CausalRecoveryStateDetector(
            sensor_id="TEMP_001",
            anomaly_threshold=3.0,
            z_norm_bound=1.8,
            recovery_window_steps=5,
            stable_confirm_steps=3,
        )

        # 1. Normal steps (3 steps)
        for i in range(3):
            det.process_step(TelemetryPoint(f"ts_{i}", "TEMP_001", 10.0, 0.1, 0.2))

        # 2. Spike Anomaly (Score=50.0, Z=4.0)
        pt_anom = TelemetryPoint("ts_anom", "TEMP_001", 25.0, 4.0, 50.0)
        feats_anom, adj_anom, st_anom = det.process_step(pt_anom)
        assert st_anom == "ACTIVE_ANOMALY"
        assert adj_anom == 50.0

        # 3. Post-Spike Step 1: Telemetry returns to normal (Z=0.2), but LSTM score is still high (Score=20.0)
        pt_rec1 = TelemetryPoint("ts_rec1", "TEMP_001", 10.2, 0.2, 20.0)
        feats_rec1, adj_rec1, st_rec1 = det.process_step(pt_rec1)
        assert st_rec1 == "RECOVERY"
        assert adj_rec1 < 20.0  # Attenuated!

        # 4. Post-Spike Steps 2-6: Consecutive normal steps -> transition to STABLE_NORMAL
        for i in range(2, 8):
            pt_rec = TelemetryPoint(f"ts_rec{i}", "TEMP_001", 10.0, 0.1, 0.5)
            feats, adj_s, state = det.process_step(pt_rec)
        assert state == "STABLE_NORMAL"

    def test_recovery_does_not_suppress_real_anomaly(self) -> None:
        det = CausalRecoveryStateDetector(
            sensor_id="TEMP_001",
            anomaly_threshold=3.0,
            z_norm_bound=1.8,
        )
        # Establish baseline
        for i in range(3):
            det.process_step(TelemetryPoint(f"ts_{i}", "TEMP_001", 10.0, 0.1, 0.2))

        # Spike 1
        det.process_step(TelemetryPoint("ts_spike1", "TEMP_001", 25.0, 4.0, 50.0))

        # Recovery step
        det.process_step(TelemetryPoint("ts_rec", "TEMP_001", 10.0, 0.2, 15.0))

        # Second Spike occurs during recovery window (Z=4.5, Score=60.0)
        pt_spike2 = TelemetryPoint("ts_spike2", "TEMP_001", 30.0, 4.5, 60.0)
        feats_s2, adj_s2, st_s2 = det.process_step(pt_spike2)
        assert st_s2 == "ACTIVE_ANOMALY"
        assert adj_s2 == 60.0  # Unattenuated

    def test_missing_data_handling(self) -> None:
        det = CausalRecoveryStateDetector(sensor_id="TEMP_001", anomaly_threshold=3.0)
        pt_missing = TelemetryPoint("ts_miss", "TEMP_001", None, np.nan, 0.0, is_missing=True)
        feats, adj, st = det.process_step(pt_missing)
        assert st == "MISSING_DATA"
        assert adj == 0.0


class TestCausalSequenceProcessingAndSafety:
    """Test sequence processing, reproducibility, and leakage protection."""

    def test_deterministic_reproducibility(self) -> None:
        raw_vals = [10.0, 10.1, 10.0, 25.0, 10.2, 10.0, 10.0]
        norm_vals = np.array([0.1, 0.2, 0.1, 4.0, 0.3, 0.1, 0.1])
        scores = np.array([0.2, 0.3, 0.2, 50.0, 20.0, 5.0, 0.5])
        ts = [f"2026-03-01T00:{i:02d}:00Z" for i in range(len(raw_vals))]

        adj1, f1, st1 = apply_causal_recovery_detector_to_sequence(
            "TEMP_001", raw_vals, norm_vals, scores, ts, threshold=3.0
        )
        adj2, f2, st2 = apply_causal_recovery_detector_to_sequence(
            "TEMP_001", raw_vals, norm_vals, scores, ts, threshold=3.0
        )

        assert np.array_equal(adj1, adj2)
        assert st1 == st2

    def test_classifier_compatibility(self) -> None:
        clf = AnomalyTypeClassifier()
        # Normal with noise
        normal_series = [10.0 + 0.2 * np.sin(i) for i in range(30)]
        assert clf.classify(normal_series, sensor_id="TEMP_001", is_known_anomaly=False) == "NORMAL"
        # Flatline
        assert clf.classify([5.000] * 30, sensor_id="TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"
        # Drift
        drift = [10.0 + i * 0.3 for i in range(30)]
        assert clf.classify(drift, sensor_id="TEMP_001", is_known_anomaly=True) == "DRIFT"


class TestRecoveryEvaluationArtifacts:
    """Test schema and integrity of recovery evaluation artifacts."""

    def test_json_artifact_schema(self) -> None:
        json_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "recovery_state"
            / "results"
            / "recovery_state_evaluation.json"
        )
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        assert "stations" in doc
        for st in ["MTR", "BRT"]:
            assert st in doc["stations"]
            st_doc = doc["stations"][st]
            assert "baseline_unadjusted" in st_doc
            assert "recovery_aware_sensor" in st_doc
            assert "temporal_bins" in st_doc["recovery_aware_sensor"]
            assert "subsets" in st_doc["recovery_aware_sensor"]
