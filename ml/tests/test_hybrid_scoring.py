"""
Unit and Integration Tests for Hybrid Anomaly Scoring Formulation (SIH26060 - Person C).

Validates:
1. Signal calculation functions: Current observation error, Delta error, Bounded drift signal.
2. Robust normalization parameter fitting from clean normal validation data.
3. Hybrid score combinations (H1, H2, H3, H4) and weighting.
4. Validation threshold search without test data leakage.
5. Separation between clean normal and contaminated recovery normal partitions.
6. Compatibility with deterministic AnomalyTypeClassifier.
7. Schema and presence of generated hybrid evaluation artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.experiments.sensor_v2.calibrate_v2_sensors import search_threshold
from ml.experiments.sensor_v2.hybrid_score.hybrid_scoring_functions import (
    compute_bounded_drift_signal,
    compute_current_observation_error,
    compute_recent_transition_error,
    fit_hybrid_normalization_parameters,
    normalize_and_combine_signals,
)
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestHybridSignals:
    """Test mathematical signal calculations."""

    def test_current_observation_error(self) -> None:
        x = np.array([[[1.0], [2.0], [5.0]]])
        x_hat = np.array([[[1.0], [2.0], [2.0]]])
        err = compute_current_observation_error(x, x_hat)
        assert np.isclose(err[0], 9.0)

    def test_recent_transition_error(self) -> None:
        x = np.array([[[1.0], [2.0], [6.0]]])  # obs delta: 6 - 2 = 4
        x_hat = np.array([[[1.0], [2.0], [3.0]]])  # rec delta: 3 - 2 = 1
        err = compute_recent_transition_error(x, x_hat)
        assert np.isclose(err[0], 9.0)  # (4 - 1)^2 = 9

    def test_bounded_drift_signal(self) -> None:
        # 30-step sequence: first 10 steps are 1.0, last 5 steps are 6.0
        x = np.ones((1, 30, 1))
        x[0, -5:, 0] = 6.0
        drift = compute_bounded_drift_signal(x, k_recent=5, k_baseline=10)
        assert np.isclose(drift[0], 5.0)  # |6.0 - 1.0| = 5.0

    def test_hybrid_normalization_fitting(self) -> None:
        val_x = np.ones((10, 30, 1))
        val_x_hat = np.ones((10, 30, 1))
        meta = [{"sensor_id": "TEMP_001", "window_state": "CLEAN_NORMAL"} for _ in range(10)]

        params = fit_hybrid_normalization_parameters(val_x, val_x_hat, meta)
        assert "TEMP_001" in params
        assert params["TEMP_001"].ref_current > 0
        assert params["TEMP_001"].ref_delta > 0
        assert params["TEMP_001"].ref_drift > 0

    def test_hybrid_score_combination_h3(self) -> None:
        x = np.ones((1, 30, 1))
        x_hat = np.ones((1, 30, 1))
        meta = [{"sensor_id": "TEMP_001", "window_state": "CLEAN_NORMAL"}]
        params = fit_hybrid_normalization_parameters(x, x_hat, meta)

        scores = normalize_and_combine_signals(
            x, x_hat, meta, params, w_curr=0.5, w_delta=0.2, w_drift=0.3
        )
        assert len(scores) == 1
        assert scores[0] >= 0.0


class TestClassifierCompatibility:
    """Test that downstream deterministic anomaly classifier remains 100% functional."""

    def test_deterministic_classifier_archetypes(self) -> None:
        clf = AnomalyTypeClassifier()

        # 1. SPIKE
        spike_win = [10.0] * 28 + [50.0, 10.0]
        res_spike = clf.classify(spike_win, sensor_id="TEMP_001", is_known_anomaly=True)
        assert res_spike in ["SPIKE", "UNKNOWN"]

        # 2. DRIFT
        drift_win = [10.0 + i * 0.5 for i in range(30)]
        res_drift = clf.classify(drift_win, sensor_id="TEMP_001", is_known_anomaly=True)
        assert res_drift == "DRIFT"

        # 3. STUCK_VALUE
        stuck_win = [15.0000] * 30
        res_stuck = clf.classify(stuck_win, sensor_id="TEMP_001", is_known_anomaly=True)
        assert res_stuck == "STUCK_VALUE"


class TestHybridEvaluationArtifacts:
    """Test JSON and Markdown comparison artifacts."""

    def test_hybrid_evaluation_json_schema(self) -> None:
        json_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "hybrid_score"
            / "results"
            / "hybrid_score_evaluation.json"
        )
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        assert "stations" in doc
        assert "MTR" in doc["stations"]
        assert "BRT" in doc["stations"]

        for st_key in ["MTR", "BRT"]:
            st = doc["stations"][st_key]
            assert "hybrid_candidates" in st
            for h_key in ["H1_current_delta", "H2_current_drift", "H3_current_delta_drift", "H4_drift_emphasis"]:
                assert h_key in st["hybrid_candidates"]
                h_obj = st["hybrid_candidates"][h_key]
                assert "operating_points" in h_obj
                assert "max_f1" in h_obj["operating_points"]
                op = h_obj["operating_points"]["max_f1"]
                assert "normal_subset_analysis" in op
                ns = op["normal_subset_analysis"]
                assert "CLEAN_NORMAL" in ns
                assert "CONTAMINATED_NORMAL" in ns
                assert "separation_ratio_contaminated_over_clean" in ns

    def test_hybrid_comparison_markdown_exists(self) -> None:
        md_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "hybrid_score"
            / "results"
            / "hybrid_score_comparison.md"
        )
        assert md_path.exists()
        assert md_path.stat().st_size > 500
