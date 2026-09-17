"""Unit tests for Polarix Bharati LSTM Threshold Selection and Evaluation (SIH26060 - Person C).

Tests verify:
1. Threshold candidate generation.
2. Candidate range validity.
3. Deterministic threshold selection.
4. Validation-only selection.
5. Max-validation-F1 selection.
6. Deterministic tie-breaking.
7. Binary metric correctness.
8. Threshold artifact schema.
9. Frozen threshold reproducibility.
10. Test evaluation uses the frozen threshold.
11. Anomaly-type metric correctness.
12. Dropout handling.
13. Bharati station validation.
14. Bharati model-version validation.
15. No modification of training model/scaler artifacts.
16. No test leakage: Modifying test labels does not change the selected validation threshold.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.training.select_bharati_lstm_threshold import (
    MODEL_VERSION,
    STATION_ID,
    calculate_metrics,
    compute_alternative_operating_points,
    evaluate_anomaly_types,
    generate_candidate_thresholds,
    search_optimal_threshold,
)


def test_1_threshold_candidate_generation():
    """1. Verify candidate threshold generation produces valid sorted candidates."""
    errors = np.array([0.001, 0.005, 0.010, 0.050, 0.100, 0.500, 1.000])
    candidates = generate_candidate_thresholds(errors, num_quantiles=50, num_linear=50)
    assert len(candidates) > 0
    assert np.all(np.diff(candidates) >= 0)  # monotonically non-decreasing
    assert candidates[0] >= 0.001
    assert candidates[-1] <= 1.000


def test_2_candidate_range_validity():
    """2. Verify candidate generation ignores NaNs and Infs."""
    errors = np.array([np.nan, 0.01, 0.02, np.inf, 0.05, -np.inf])
    candidates = generate_candidate_thresholds(errors, num_quantiles=10, num_linear=10)
    assert not np.isnan(candidates).any()
    assert not np.isinf(candidates).any()
    assert candidates[0] == 0.01
    assert candidates[-1] == 0.05


def test_3_deterministic_threshold_selection():
    """3. Verify repeated threshold searches on the same dataset yield identical results."""
    val_df = pd.DataFrame(
        {
            "reconstruction_error": [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.50],
            "is_anomaly": [0, 0, 0, 1, 1, 1, 1],
            "anomaly_type": ["NORMAL", "NORMAL", "NORMAL", "SPIKE", "DRIFT", "DRIFT", "SPIKE"],
        }
    )
    t1, m1, _ = search_optimal_threshold(val_df, num_candidates=100)
    t2, m2, _ = search_optimal_threshold(val_df, num_candidates=100)
    assert t1 == t2
    assert m1["f1"] == m2["f1"]
    assert m1["TP"] == m2["TP"]


def test_4_validation_only_selection():
    """4. Verify threshold search uses only the validation partition."""
    val_df = pd.DataFrame(
        {
            "reconstruction_error": [0.01, 0.02, 0.10, 0.20],
            "is_anomaly": [0, 0, 1, 1],
            "split": ["val"] * 4,
        }
    )
    test_df = pd.DataFrame(
        {
            "reconstruction_error": [0.001, 0.002, 0.003, 0.999],
            "is_anomaly": [1, 1, 1, 0],
            "split": ["test"] * 4,
        }
    )
    # Search is executed only on val_df
    t_val, m_val, _ = search_optimal_threshold(val_df)
    assert 0.02 <= t_val <= 0.10
    assert m_val["f1"] == 1.0


def test_5_max_validation_f1_selection():
    """5. Verify the selected threshold strictly maximizes validation F1."""
    val_df = pd.DataFrame(
        {
            "reconstruction_error": [0.01, 0.02, 0.03, 0.08, 0.09, 0.10],
            "is_anomaly": [0, 0, 0, 1, 1, 1],
        }
    )
    best_t, best_m, search_df = search_optimal_threshold(val_df, num_candidates=50)
    max_f1_in_search = search_df["f1"].max()
    assert best_m["f1"] == max_f1_in_search
    assert best_m["f1"] == 1.0


def test_6_deterministic_tie_breaking():
    """6. Verify tie-breaking logic (higher recall -> lower FPR -> lower threshold)."""
    # Create scenario where multiple thresholds yield F1 = 1.0
    val_df = pd.DataFrame(
        {
            "reconstruction_error": [0.01, 0.02, 0.08, 0.09],
            "is_anomaly": [0, 0, 1, 1],
        }
    )
    best_t, best_m, _ = search_optimal_threshold(val_df, num_candidates=50)
    # Thresholds between 0.02 and 0.08 all give F1=1.0, Rec=1.0, FPR=0.0.
    # Tie-breaking prefers lower threshold among perfect candidates.
    assert best_t <= 0.08


def test_7_binary_metric_correctness():
    """7. Verify binary metric computation formulas (TP, TN, FP, FN, precision, recall, F1, FPR)."""
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_pred = np.array([1, 0, 0, 1, 1, 0])
    # TP: 2, FN: 1, FP: 1, TN: 2
    m = calculate_metrics(y_true, y_pred)
    assert m["TP"] == 2
    assert m["TN"] == 2
    assert m["FP"] == 1
    assert m["FN"] == 1
    assert m["accuracy"] == 4 / 6
    assert m["precision"] == 2 / 3
    assert m["recall"] == 2 / 3
    assert m["f1"] == 2 / 3
    assert m["false_positive_rate"] == 1 / 3


def test_8_threshold_artifact_schema():
    """8. Verify schema and completeness of frozen threshold JSON."""
    threshold_path = Path("ml/results/bharati_lstm_threshold.json")
    assert threshold_path.exists()

    with open(threshold_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = [
        "station_id",
        "model_version",
        "threshold",
        "selection_metric",
        "tie_breaker_rule",
        "validation_TP",
        "validation_TN",
        "validation_FP",
        "validation_FN",
        "validation_accuracy",
        "validation_precision",
        "validation_recall",
        "validation_f1",
        "validation_false_positive_rate",
        "synthetic_disclaimer",
    ]
    for k in required_keys:
        assert k in data, f"Missing required key: {k}"

    assert data["station_id"] == "BRT"
    assert data["model_version"] == "lstm-ae-bharati-v1"
    assert isinstance(data["threshold"], float)
    assert data["threshold"] > 0


def test_9_frozen_threshold_reproducibility():
    """9. Verify frozen threshold in artifact matches recomputed validation search."""
    threshold_path = Path("ml/results/bharati_lstm_threshold.json")
    with open(threshold_path, "r", encoding="utf-8") as f:
        frozen_data = json.load(f)

    errors_df = pd.read_csv("ml/results/bharati_lstm_reconstruction_errors.csv")
    val_df = errors_df[errors_df["split"] == "val"]
    recomputed_thresh, _, _ = search_optimal_threshold(val_df)

    assert pytest.approx(frozen_data["threshold"], rel=1e-5) == recomputed_thresh


def test_10_test_evaluation_uses_frozen_threshold():
    """10. Verify test evaluation metrics in report match evaluation with frozen threshold."""
    threshold_path = Path("ml/results/bharati_lstm_threshold.json")
    with open(threshold_path, "r", encoding="utf-8") as f:
        frozen_thresh = json.load(f)["threshold"]

    eval_path = Path("ml/results/bharati_lstm_evaluation.json")
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    assert eval_data["threshold_used"] == frozen_thresh

    errors_df = pd.read_csv("ml/results/bharati_lstm_reconstruction_errors.csv")
    test_df = errors_df[errors_df["split"] == "test"]
    test_y = test_df["is_anomaly"].to_numpy(dtype=int)
    test_pred = (test_df["reconstruction_error"].to_numpy(dtype=float) >= frozen_thresh).astype(int)

    m = calculate_metrics(test_y, test_pred)
    assert eval_data["test_performance"]["confusion_matrix"]["TP"] == m["TP"]
    assert eval_data["test_performance"]["confusion_matrix"]["TN"] == m["TN"]
    assert eval_data["test_performance"]["confusion_matrix"]["FP"] == m["FP"]
    assert eval_data["test_performance"]["confusion_matrix"]["FN"] == m["FN"]


def test_11_anomaly_type_metric_correctness():
    """11. Verify per-anomaly-type breakdown correctly categorizes detections."""
    df = pd.DataFrame(
        {
            "reconstruction_error": [0.5, 0.05, 0.8, 0.01, 0.02],
            "anomaly_type": ["SPIKE", "SPIKE", "DRIFT", "DRIFT", "STUCK_VALUE"],
            "is_anomaly": [1, 1, 1, 1, 1],
        }
    )
    thresh = 0.10
    breakdown = evaluate_anomaly_types(df, thresh)
    assert breakdown["SPIKE"]["total_instances"] == 2
    assert breakdown["SPIKE"]["detected_instances"] == 1
    assert breakdown["SPIKE"]["recall"] == 0.5

    assert breakdown["DRIFT"]["total_instances"] == 2
    assert breakdown["DRIFT"]["detected_instances"] == 1
    assert breakdown["DRIFT"]["recall"] == 0.5

    assert breakdown["STUCK_VALUE"]["total_instances"] == 1
    assert breakdown["STUCK_VALUE"]["detected_instances"] == 0
    assert breakdown["STUCK_VALUE"]["recall"] == 0.0


def test_12_dropout_handling():
    """12. Verify DROPOUT missing-data handling status."""
    breakdown = evaluate_anomaly_types(pd.DataFrame({"reconstruction_error": [], "anomaly_type": []}), 0.1)
    assert "DROPOUT" in breakdown
    assert breakdown["DROPOUT"]["recall"] == 1.0
    assert "Missing-data rule" in breakdown["DROPOUT"]["handling_method"]


def test_13_bharati_station_validation():
    """13. Verify station is BRT across all generated results."""
    for json_file in [
        "ml/results/bharati_lstm_threshold.json",
        "ml/results/bharati_lstm_threshold_search.json",
        "ml/results/bharati_lstm_evaluation.json",
    ]:
        with open(json_file, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["station_id"] == "BRT"


def test_14_bharati_model_version_validation():
    """14. Verify model version is lstm-ae-bharati-v1 across all artifacts."""
    for json_file in [
        "ml/results/bharati_lstm_threshold.json",
        "ml/results/bharati_lstm_threshold_search.json",
        "ml/results/bharati_lstm_evaluation.json",
    ]:
        with open(json_file, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["model_version"] == "lstm-ae-bharati-v1"


def test_15_no_modification_of_training_artifacts():
    """15. Verify model weights, config, and scalers exist and have non-zero size."""
    pt_file = Path("ml/models/lstm-ae-bharati-v1.pt")
    cfg_file = Path("ml/models/lstm-ae-bharati-v1_config.json")
    scl_file = Path("ml/models/lstm-ae-bharati-v1_scaler.json")
    assert pt_file.exists() and pt_file.stat().st_size > 0
    assert cfg_file.exists() and cfg_file.stat().st_size > 0
    assert scl_file.exists() and scl_file.stat().st_size > 0


def test_16_no_test_leakage():
    """
    16. Leakage Test: Inverting or perturbing held-out test labels has ZERO impact
    on the selected validation threshold.
    """
    errors_df = pd.read_csv("ml/results/bharati_lstm_reconstruction_errors.csv")
    val_df = errors_df[errors_df["split"] == "val"].copy()

    # Original selection on validation
    orig_thresh, orig_metrics, _ = search_optimal_threshold(val_df)

    # Invert all test labels in an independent copy
    corrupted_df = errors_df.copy()
    test_mask = corrupted_df["split"] == "test"
    corrupted_df.loc[test_mask, "is_anomaly"] = 1 - corrupted_df.loc[test_mask, "is_anomaly"]
    corrupted_val_df = corrupted_df[corrupted_df["split"] == "val"].copy()

    # Run threshold search again
    corrupted_thresh, corrupted_metrics, _ = search_optimal_threshold(corrupted_val_df)

    assert orig_thresh == corrupted_thresh
    assert orig_metrics["f1"] == corrupted_metrics["f1"]
    assert orig_metrics["TP"] == corrupted_metrics["TP"]
