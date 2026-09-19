"""
Unit and Integration Tests for Multivariate Sensor-Context Fusion (SIH26060 - Person C).

Validates:
1. Timestamp alignment and cross-sensor synchronization.
2. Missing sensor handling and zero-context safety.
3. Mathematical correctness of multivariate aggregation strategies (Max, Mean, Robust, Agreement, Hybrid).
4. Validation-only threshold selection without test data leakage.
5. Clean-normal zero false alarm preservation on synchronized timelines.
6. Deterministic classifier compatibility with multivariate signals.
7. Schema and presence of generated multivariate evaluation artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.experiments.sensor_v2.calibrate_v2_sensors import search_threshold
from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    MultivariateTimestampRecord,
    align_station_multivariate_windows,
    compute_multivariate_fusion_scores,
)
from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestMultivariateAlignmentAndFusion:
    """Test multivariate timestamp alignment and fusion strategies."""

    def test_timestamp_alignment(self) -> None:
        meta_s1 = [{"timestamp": "2026-03-01T00:00:00+00:00", "target_value": 10.0, "is_anomaly": 0, "window_state": "CLEAN_NORMAL"}]
        meta_s2 = [{"timestamp": "2026-03-01T00:00:00+00:00", "target_value": 20.0, "is_anomaly": 1, "window_state": "ACTIVE_ANOMALY", "anomaly_type": "SPIKE"}]

        meta_dict = {"S1": meta_s1, "S2": meta_s2}
        scores_dict = {"S1": np.array([0.5]), "S2": np.array([3.0])}

        records = align_station_multivariate_windows("MTR", meta_dict, scores_dict, expected_sensors=["S1", "S2", "S3"])

        assert len(records) == 1
        rec = records[0]
        assert rec.timestamp == "2026-03-01T00:00:00+00:00"
        assert rec.is_anomaly_station == 1  # S2 is anomalous
        assert rec.window_state_station == "ACTIVE_ANOMALY"
        assert rec.primary_anomaly_type == "SPIKE"
        assert rec.valid_sensor_count == 2
        assert rec.missing_sensor_count == 1  # S3 is missing

    def test_fusion_strategies(self) -> None:
        records = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp="2026-03-01T00:00:00+00:00",
                sensor_ids=["S1", "S2", "S3"],
                is_anomaly_station=0,
                window_state_station="CLEAN_NORMAL",
                primary_anomaly_type="NORMAL",
                missing_sensor_count=0,
                valid_sensor_count=3,
                normalized_sensor_scores={"S1": 1.0, "S2": 2.0, "S3": 6.0},
                raw_sensor_values={"S1": 10.0, "S2": 20.0, "S3": 30.0},
                split="val",
            )
        ]

        # Max: max(1, 2, 6) = 6.0
        s_max, y, _ = compute_multivariate_fusion_scores(records, strategy="max")
        assert np.isclose(s_max[0], 6.0)

        # Mean: (1 + 2 + 6) / 3 = 3.0
        s_mean, _, _ = compute_multivariate_fusion_scores(records, strategy="mean")
        assert np.isclose(s_mean[0], 3.0)

        # Robust: median=2.0, p25=1.5, p75=4.0 -> iqr=2.5 -> 2.0 + 0.5 * 2.5 = 3.25
        s_robust, _, _ = compute_multivariate_fusion_scores(records, strategy="robust")
        assert np.isclose(s_robust[0], 3.25)

        # Hybrid: 0.7 * 6.0 + 0.3 * mean(1, 2) = 4.2 + 0.45 = 4.65
        s_hyb, _, _ = compute_multivariate_fusion_scores(records, strategy="hybrid")
        assert np.isclose(s_hyb[0], 4.65)

    def test_agreement_and_scaling(self) -> None:
        # All 3 sensors elevated (>1.5): max * (1 + 0.5 * 1.0) = 4.0 * 1.5 = 6.0
        rec_all_high = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp="2026-03-01T00:00:00+00:00",
                sensor_ids=["S1", "S2", "S3"],
                is_anomaly_station=1,
                window_state_station="ACTIVE_ANOMALY",
                primary_anomaly_type="SPIKE",
                missing_sensor_count=0,
                valid_sensor_count=3,
                normalized_sensor_scores={"S1": 2.0, "S2": 3.0, "S3": 4.0},
                raw_sensor_values={"S1": 10.0, "S2": 20.0, "S3": 30.0},
                split="val",
            )
        ]
        s_agree, _, _ = compute_multivariate_fusion_scores(rec_all_high, strategy="agreement", elevation_threshold=1.5)
        assert np.isclose(s_agree[0], 6.0)

        # Only 1 sensor elevated (>1.5): max * (1 + 0.5 * 1/3) = 4.0 * (1 + 0.1666667) = 4.666667
        rec_one_high = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp="2026-03-01T00:00:00+00:00",
                sensor_ids=["S1", "S2", "S3"],
                is_anomaly_station=1,
                window_state_station="ACTIVE_ANOMALY",
                primary_anomaly_type="SPIKE",
                missing_sensor_count=0,
                valid_sensor_count=3,
                normalized_sensor_scores={"S1": 0.5, "S2": 0.8, "S3": 4.0},
                raw_sensor_values={"S1": 10.0, "S2": 20.0, "S3": 30.0},
                split="val",
            )
        ]
        s_agree_one, _, _ = compute_multivariate_fusion_scores(rec_one_high, strategy="agreement", elevation_threshold=1.5)
        assert np.isclose(s_agree_one[0], 4.0 * (1.0 + 0.5 * (1.0 / 3.0)))

    def test_insufficient_context_safety(self) -> None:
        records = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp="2026-03-01T00:00:00+00:00",
                sensor_ids=[],
                is_anomaly_station=0,
                window_state_station="CLEAN_NORMAL",
                primary_anomaly_type="NORMAL",
                missing_sensor_count=5,
                valid_sensor_count=0,
                normalized_sensor_scores={},
                raw_sensor_values={},
                split="val",
            )
        ]
        s_max, _, _ = compute_multivariate_fusion_scores(records, strategy="max")
        assert s_max[0] == 0.0

    def test_reproducibility(self) -> None:
        rec = [
            MultivariateTimestampRecord(
                station_id="MTR",
                timestamp="2026-03-01T00:00:00+00:00",
                sensor_ids=["S1", "S2"],
                is_anomaly_station=0,
                window_state_station="CLEAN_NORMAL",
                primary_anomaly_type="NORMAL",
                missing_sensor_count=0,
                valid_sensor_count=2,
                normalized_sensor_scores={"S1": 1.25, "S2": 2.50},
                raw_sensor_values={"S1": 1.0, "S2": 2.0},
                split="val",
            )
        ]
        s1, _, _ = compute_multivariate_fusion_scores(rec, strategy="hybrid")
        s2, _, _ = compute_multivariate_fusion_scores(rec, strategy="hybrid")
        assert np.array_equal(s1, s2)


class TestMultivariateCalibrationAndSafety:
    """Test validation-only calibration and leakage protection."""

    def test_threshold_calibration_validation_only(self) -> None:
        # Synthetic val scores: 5 normal (<1.0) and 5 anomaly (>2.0)
        y_val = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        s_val = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 2.1, 2.5, 3.0, 3.5, 4.0])

        best_th, best_metrics = search_threshold(s_val, y_val, criterion="max_f1", num_candidates=50)
        assert best_th > 0.5
        assert best_th <= 2.1
        assert best_metrics["f1"] == 1.0


class TestMultivariateClassifierCompatibility:
    """Test compatibility with downstream deterministic classifier."""

    def test_classifier_unaltered_behavior(self) -> None:
        clf = AnomalyTypeClassifier()
        # Normal with natural noise/variation
        normal_series = [10.0 + 0.2 * np.sin(i) for i in range(30)]
        assert clf.classify(normal_series, sensor_id="TEMP_001", is_known_anomaly=False) == "NORMAL"
        # Stuck flatline
        assert clf.classify([5.000] * 30, sensor_id="TEMP_001", is_known_anomaly=True) == "STUCK_VALUE"
        # Drift
        drift = [10.0 + i * 0.3 for i in range(30)]
        assert clf.classify(drift, sensor_id="TEMP_001", is_known_anomaly=True) == "DRIFT"


class TestMultivariateEvaluationArtifacts:
    """Test schema and integrity of generated multivariate evaluation artifacts."""

    def test_multivariate_json_schema(self) -> None:
        json_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "multivariate_context"
            / "results"
            / "multivariate_context_evaluation.json"
        )
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        assert "stations" in doc
        assert "MTR" in doc["stations"]
        assert "BRT" in doc["stations"]

        for st_key in ["MTR", "BRT"]:
            st = doc["stations"][st_key]
            assert "multivariate_strategies" in st
            for strat_key in [
                "MV1_max_sensor_context",
                "MV2_mean_sensor_context",
                "MV3_robust_aggregate",
                "MV4_agreement_aware",
                "MV5_hybrid_context",
            ]:
                assert strat_key in st["multivariate_strategies"]
                strat_obj = st["multivariate_strategies"][strat_key]
                assert "operating_points" in strat_obj
                op = strat_obj["operating_points"]["max_f1"]
                assert "test_metrics" in op
                assert "normal_subset_analysis" in op
                ns = op["normal_subset_analysis"]
                assert "CLEAN_NORMAL" in ns
                assert "CONTAMINATED_NORMAL" in ns
                # Clean normal FPR should be zero or near zero on synchronized timeline
                assert ns["CLEAN_NORMAL"]["fpr"] <= 0.05

    def test_multivariate_markdown_exists(self) -> None:
        md_path = (
            REPO_ROOT
            / "ml"
            / "experiments"
            / "sensor_v2"
            / "multivariate_context"
            / "results"
            / "multivariate_context_comparison.md"
        )
        assert md_path.exists()
        assert md_path.stat().st_size > 500
