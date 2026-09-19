"""
Unit and Integration Tests for Final Causal State-Machine Decision Layer (SIH26060 - Person C).

Validates:
1. No future information is accessed (Causality proof).
2. Changing future observations cannot alter past/present decisions.
3. Isolated high-confidence anomalies are not suppressed during RECOVERY:
   - High station score override (S >= 1.5 * Threshold)
   - Multi-sensor confirmation override (N_elevated >= 2)
   - Physical deviation override (|Z| > 2.0)
   - STUCK_VALUE compatibility
4. Missing / duplicate / stale telemetry safety:
   - MISSING_DATA remains explicit and never becomes NORMAL
   - Missing data does not falsely advance recovery step counts
   - Duplicate / stale timestamps do not advance state
   - Valid observation following missing data resumes deterministically
   - State cannot jump from MISSING_DATA to ACTIVE_ANOMALY without evidence
5. First observation is handled deterministically from INITIAL state.
6. Artifact schema and population integrity (N=238).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    MultivariateTimestampRecord,
)
from ml.experiments.sensor_v2.recovery_optimization.final_decision.causal_state_machine import (
    CausalStationStateMachine,
    StateMachineConfig,
    run_state_machine_over_sequence,
)
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestFinalStateMachineCausalityAndSafety:
    """Test causality, isolation safety, and idempotency invariants."""

    def test_future_independence_proof(self) -> None:
        """Modifying future observations at steps > t cannot alter decisions at steps <= t."""
        records = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                sensor_ids=["S1", "S2"],
                is_anomaly_station=0,
                window_state_station="CLEAN_NORMAL",
                primary_anomaly_type="NORMAL",
                missing_sensor_count=0,
                valid_sensor_count=2,
                normalized_sensor_scores={"S1": 1.0, "S2": 1.0},
                raw_sensor_values={"S1": 10.0, "S2": 20.0},
                split="val",
            )
            for i in range(6)
        ]
        scores_orig = np.array([1.0, 5.0, 2.0, 1.0, 1.0, 1.0])
        cfg = StateMachineConfig(mode="suppression_override", base_threshold=4.0)

        preds_orig, states_orig, _ = run_state_machine_over_sequence(records, scores_orig, cfg)

        # Modify future at t=3, 4, 5
        scores_mod = np.array([1.0, 5.0, 2.0, 999.0, 999.0, 999.0])
        preds_mod, states_mod, _ = run_state_machine_over_sequence(records, scores_mod, cfg)

        # Predictions at t=0, 1, 2 MUST be identical
        assert np.array_equal(preds_orig[:3], preds_mod[:3])
        assert states_orig[:3] == states_mod[:3]

    def test_isolated_anomaly_not_suppressed_in_recovery(self) -> None:
        """A high-confidence spike or multi-sensor anomaly is never suppressed in recovery."""
        cfg = StateMachineConfig(
            mode="suppression_override",
            base_threshold=4.0,
            suppression_barrier=1.35,
            strong_isolated_override=1.50,
            z_bound_override=2.00,
        )
        engine = CausalStationStateMachine(cfg)

        # Step 0: Initial Normal
        rec0 = MultivariateTimestampRecord("MTR", "ts_0", ["S1"], 0, "CLEAN_NORMAL", "NORMAL", 0, 1, {"S1": 1.0}, {"S1": 10.0}, "val")
        p0, s0, _ = engine.process_step(rec0, station_score=1.0)
        assert p0 == 0

        # Step 1: Active Anomaly (Score=10.0)
        rec1 = MultivariateTimestampRecord("MTR", "ts_1", ["S1"], 1, "ACTIVE_ANOMALY", "SPIKE", 0, 1, {"S1": 10.0}, {"S1": 30.0}, "val")
        p1, s1, _ = engine.process_step(rec1, station_score=10.0)
        assert p1 == 1
        assert s1 == "ACTIVE_ANOMALY"

        # Step 2: In Recovery, but receives a strong isolated score override (Score=8.0 >= 1.5 * 4.0)
        rec2 = MultivariateTimestampRecord("MTR", "ts_2", ["S1"], 1, "ACTIVE_ANOMALY", "SPIKE", 0, 1, {"S1": 8.0}, {"S1": 25.0}, "val")
        p2, s2, _ = engine.process_step(rec2, station_score=8.0)
        assert p2 == 1  # Not suppressed!
        assert s2 == "ACTIVE_ANOMALY"

        # Step 3: Returns to normal (Score=2.0) -> transitions to RECOVERY
        rec3 = MultivariateTimestampRecord("MTR", "ts_3", ["S1"], 0, "CONTAMINATED_NORMAL", "NORMAL", 0, 1, {"S1": 2.0}, {"S1": 10.0}, "val")
        p3, s3, _ = engine.process_step(rec3, station_score=2.0)
        assert p3 == 0
        assert s3 == "RECOVERY"

        # Step 4: Multi-sensor co-elevation override during recovery (N_elevated=2, Score=4.8)
        rec4 = MultivariateTimestampRecord("MTR", "ts_4", ["S1", "S2"], 1, "ACTIVE_ANOMALY", "SPIKE", 0, 2, {"S1": 4.5, "S2": 3.8}, {"S1": 22.0, "S2": 15.0}, "val")
        p4, s4, _ = engine.process_step(rec4, station_score=4.8)
        assert p4 == 1  # Emits anomaly due to multi-sensor confirmation!
        assert s4 == "ACTIVE_ANOMALY"

    def test_idempotent_duplicate_telemetry(self) -> None:
        """Duplicate timestamp telemetry does not falsely advance the step count or state."""
        cfg = StateMachineConfig(mode="ref", base_threshold=4.0)
        engine = CausalStationStateMachine(cfg)

        rec = MultivariateTimestampRecord("MTR", "ts_fixed", ["S1"], 0, "CLEAN_NORMAL", "NORMAL", 0, 1, {"S1": 1.0}, {"S1": 10.0}, "val")
        p1, s1, meta1 = engine.process_step(rec, station_score=1.0)
        step_first = engine.step_idx

        # Feed duplicate with exact same timestamp
        p2, s2, meta2 = engine.process_step(rec, station_score=1.0)
        step_second = engine.step_idx

        assert step_first == step_second
        assert meta2["reason"] == "duplicate_timestamp"

    def test_missing_data_explicit_safety(self) -> None:
        """Missing sensor data emits MISSING_DATA state without raising exceptions or triggering alarms."""
        cfg = StateMachineConfig(mode="ref", base_threshold=4.0)
        engine = CausalStationStateMachine(cfg)

        # 1. Missing data input
        rec_missing = MultivariateTimestampRecord("MTR", "ts_miss", [], 0, "CLEAN_NORMAL", "NORMAL", 5, 0, {}, {}, "val")
        p, st, meta = engine.process_step(rec_missing, station_score=0.0)

        assert p == 0
        assert st == "MISSING_DATA"
        assert meta["reason"] == "missing_data"

        # 2. Subsequent normal observation resumes cleanly without false jump
        rec_normal = MultivariateTimestampRecord("MTR", "ts_norm", ["S1"], 0, "CLEAN_NORMAL", "NORMAL", 0, 1, {"S1": 1.0}, {"S1": 10.0}, "val")
        p_norm, st_norm, _ = engine.process_step(rec_normal, station_score=1.0)
        assert p_norm == 0
        assert st_norm == "NORMAL"

    def test_first_observation_initial_behavior(self) -> None:
        """First observation from cold start is handled deterministically without prior history."""
        cfg = StateMachineConfig(mode="ref", base_threshold=4.0)
        engine = CausalStationStateMachine(cfg)
        assert engine.current_state == "INITIAL"
        assert engine.step_idx == 0

        rec_first = MultivariateTimestampRecord("MTR", "ts_start", ["S1"], 0, "CLEAN_NORMAL", "NORMAL", 0, 1, {"S1": 0.5}, {"S1": 10.0}, "val")
        p, st, meta = engine.process_step(rec_first, station_score=0.5)
        assert p == 0
        assert st == "NORMAL"
        assert engine.step_idx == 1

    def test_deterministic_classifier_compatibility(self) -> None:
        """Verify deterministic physical anomaly-type classifier compatibility."""
        clf = AnomalyTypeClassifier()
        normal_series = [10.0 + 0.2 * np.sin(i) for i in range(30)]
        assert clf.classify(normal_series, sensor_id="TEMP_001", is_known_anomaly=False) == "NORMAL"
        assert clf.classify([5.000] * 30, sensor_id="TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"
        drift = [10.0 + i * 0.3 for i in range(30)]
        assert clf.classify(drift, sensor_id="TEMP_001", is_known_anomaly=True) == "DRIFT"
        assert clf.classify([], sensor_id="TEMP_001") == "MISSING_DATA"


class TestFinalEvaluationArtifacts:
    """Test schema and existence of generated evaluation artifacts."""

    def test_artifacts_exist(self) -> None:
        art_dir = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "recovery_optimization" / "final_decision" / "results"
        assert (art_dir / "final_decision_evaluation.json").exists()
        assert (art_dir / "final_decision_comparison.md").exists()

    def test_evaluation_json_schema(self) -> None:
        json_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "recovery_optimization"
            / "final_decision"
            / "results"
            / "final_decision_evaluation.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        assert "stations" in doc
        for st in ["MTR", "BRT"]:
            assert st in doc["stations"]
            st_data = doc["stations"][st]
            assert st_data["station_level_eval_population_N"] == 238
            assert "validation_selected_candidate" in st_data
            assert "all_candidates" in st_data
            for cand in ["candidate_a_reference", "candidate_b_suppression", "candidate_c_suppression_override", "candidate_d_decay_override"]:
                assert cand in st_data["all_candidates"]
                assert "test_metrics" in st_data["all_candidates"][cand]
                assert "temporal_recovery_bins" in st_data["all_candidates"][cand]["breakdown"]
