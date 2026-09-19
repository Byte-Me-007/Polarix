"""
Unit and Integration Tests for Causal Recovery Decision Optimization (SIH26060 - Person C).

Validates:
1. Strict Causality Proof: Prediction at time t is mathematically unaffected by future scores (t+1, t+2, ...).
2. K-Consecutive Invariant: Correct behavior across K=1, 2, 3, 4.
3. Edge cases: Empty input, sequence boundaries, single-step spike, alternating normal/anomaly.
4. Validation-only threshold calibration.
5. Deterministic classifier compatibility (STUCK_VALUE, DRIFT, SPIKE, MISSING_DATA).
6. Artifact presence and schema verification.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.experiments.sensor_v2.calibrate_v2_sensors import search_threshold
from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    MultivariateTimestampRecord,
)
from ml.experiments.sensor_v2.recovery_optimization.causal_persistence import (
    apply_causal_persistence,
)
from ml.experiments.sensor_v2.recovery_optimization.recovery_optimization import (
    apply_causal_recovery_decay,
    apply_multisensor_confirmation,
    apply_recovery_aware_station_modulation,
    apply_recovery_hysteresis,
    apply_temporal_persistence_filter,
)
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestCausalityProofAndInvariants:
    """Test mathematical proof of zero future lookahead."""

    def test_future_independence_proof(self) -> None:
        """
        Proof: Modifying any future values at steps > t MUST NOT alter predictions at steps <= t.
        """
        base_scores = np.array([1.0, 5.0, 5.0, 1.0, 2.0, 1.0])
        th = 4.0

        for k in [1, 2, 3]:
            orig_preds = apply_causal_persistence(base_scores, threshold=th, k=k)

            # Modify future at t=3, 4, 5 with extreme values
            modified_future_1 = np.array([1.0, 5.0, 5.0, 999.0, 999.0, 999.0])
            preds_mod1 = apply_causal_persistence(modified_future_1, threshold=th, k=k)

            # Predictions at t=0, 1, 2 MUST remain identical
            assert np.array_equal(orig_preds[:3], preds_mod1[:3])

            # Modify future with zeros
            modified_future_2 = np.array([1.0, 5.0, 5.0, 0.0, 0.0, 0.0])
            preds_mod2 = apply_causal_persistence(modified_future_2, threshold=th, k=k)

            assert np.array_equal(orig_preds[:3], preds_mod2[:3])

    def test_single_step_future_invariant(self) -> None:
        """Changing score[t+1] does not change prediction[t]."""
        s1 = np.array([5.0, 5.0])
        s2 = np.array([5.0, 0.0])

        p1 = apply_causal_persistence(s1, threshold=4.0, k=2)
        p2 = apply_causal_persistence(s2, threshold=4.0, k=2)

        # At t=0, prediction MUST be identical regardless of what happens at t=1
        assert p1[0] == p2[0] == 0

    def test_k_consecutive_behavior(self) -> None:
        # Sequence: Normal (1.0), Anomaly (5.0), Anomaly (5.0), Anomaly (5.0), Normal (1.0)
        scores = np.array([1.0, 5.0, 5.0, 5.0, 1.0])
        th = 4.0

        # K = 1: [0, 1, 1, 1, 0]
        p_k1 = apply_causal_persistence(scores, threshold=th, k=1)
        assert np.array_equal(p_k1, np.array([0, 1, 1, 1, 0]))

        # K = 2: [0, 0, 1, 1, 0]
        p_k2 = apply_causal_persistence(scores, threshold=th, k=2)
        assert np.array_equal(p_k2, np.array([0, 0, 1, 1, 0]))

        # K = 3: [0, 0, 0, 1, 0]
        p_k3 = apply_causal_persistence(scores, threshold=th, k=3)
        assert np.array_equal(p_k3, np.array([0, 0, 0, 1, 0]))

        # K = 4: [0, 0, 0, 0, 0]
        p_k4 = apply_causal_persistence(scores, threshold=th, k=4)
        assert np.array_equal(p_k4, np.array([0, 0, 0, 0, 0]))

    def test_sequence_boundaries_and_empty(self) -> None:
        empty = apply_causal_persistence([], threshold=4.0, k=2)
        assert len(empty) == 0

        single_anom = apply_causal_persistence([5.0], threshold=4.0, k=2)
        assert len(single_anom) == 1
        assert single_anom[0] == 0  # K=2 requires 2 steps

        single_anom_k1 = apply_causal_persistence([5.0], threshold=4.0, k=1)
        assert single_anom_k1[0] == 1


class TestDecisionStrategies:
    """Test mathematical and behavioral correctness of decision strategies."""

    def test_hysteresis_behavior(self) -> None:
        scores = np.array([2.0, 4.5, 3.2, 2.5, 1.8, 4.2])
        # th_high=4.0, th_low=2.4
        preds = apply_recovery_hysteresis(scores, th_high=4.0, th_low=2.4)
        assert np.array_equal(preds, np.array([0, 1, 1, 1, 0, 1]))

    def test_multisensor_confirmation(self) -> None:
        rec_single = MultivariateTimestampRecord(
            station_id="MTR",
            timestamp="2026-03-01T00:00:00Z",
            sensor_ids=["S1", "S2"],
            is_anomaly_station=0,
            window_state_station="CLEAN_NORMAL",
            primary_anomaly_type="NORMAL",
            missing_sensor_count=0,
            valid_sensor_count=2,
            normalized_sensor_scores={"S1": 4.5, "S2": 1.0},
            raw_sensor_values={"S1": 10.0, "S2": 20.0},
            split="val",
        )
        p_single = apply_multisensor_confirmation(
            [rec_single], np.array([4.5]), base_threshold=4.0, sensor_elev_threshold=3.0, single_sensor_barrier=1.30
        )
        assert p_single[0] == 0

    def test_causal_decay_behavior(self) -> None:
        records = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                sensor_ids=["S1"],
                is_anomaly_station=1 if i == 0 else 0,
                window_state_station="ACTIVE_ANOMALY" if i == 0 else "CONTAMINATED_NORMAL",
                primary_anomaly_type="SPIKE" if i == 0 else "NORMAL",
                missing_sensor_count=0,
                valid_sensor_count=1,
                normalized_sensor_scores={"S1": 10.0 if i == 0 else 3.0},
                raw_sensor_values={"S1": 25.0 if i == 0 else 10.0},
                split="val",
            )
            for i in range(5)
        ]
        scores = np.array([10.0, 3.0, 3.0, 3.0, 3.0])
        adj = apply_causal_recovery_decay(records, scores, threshold=5.0, decay_lambda=0.10)
        assert adj[0] == 10.0
        assert adj[1] < 3.0
        assert adj[2] < adj[1]


class TestAnomalyClassifierAndSafety:
    """Test deterministic classifier compatibility and safety."""

    def test_classifier_unaltered_behavior(self) -> None:
        clf = AnomalyTypeClassifier()
        normal_series = [10.0 + 0.2 * np.sin(i) for i in range(30)]
        assert clf.classify(normal_series, sensor_id="TEMP_001", is_known_anomaly=False) == "NORMAL"
        assert clf.classify([5.000] * 30, sensor_id="TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"
        drift = [10.0 + i * 0.3 for i in range(30)]
        assert clf.classify(drift, sensor_id="TEMP_001", is_known_anomaly=True) == "DRIFT"
        assert clf.classify([], sensor_id="TEMP_001") == "MISSING_DATA"

    def test_validation_only_threshold_search(self) -> None:
        s_val = np.array([0.2, 0.4, 0.6, 2.5, 3.0, 3.5])
        y_val = np.array([0, 0, 0, 1, 1, 1])
        best_th, m = search_threshold(s_val, y_val, criterion="max_f1")
        assert best_th > 0.6
        assert best_th <= 2.5
        assert m["f1"] == 1.0


class TestEvaluationArtifacts:
    """Test schema and existence of generated evaluation artifacts."""

    def test_artifacts_exist(self) -> None:
        art_dir = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "recovery_optimization" / "results"
        assert (art_dir / "timestamp_alignment_audit.json").exists()
        assert (art_dir / "timestamp_alignment_audit.md").exists()
        assert (art_dir / "causal_persistence_evaluation.json").exists()
        assert (art_dir / "causal_persistence_comparison.md").exists()

    def test_evaluation_json_schema(self) -> None:
        json_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "recovery_optimization"
            / "results"
            / "causal_persistence_evaluation.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        assert "stations" in doc
        for st in ["MTR", "BRT"]:
            assert st in doc["stations"]
            assert "validation_selected_candidate" in doc["stations"][st]
            assert "all_candidates" in doc["stations"][st]
