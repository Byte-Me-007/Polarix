"""Unit tests for Polarix Maitri Model Comparison Pipeline."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.training.compare_models import (
    calculate_metrics_dict,
    evaluate_zscore_splits,
    run_model_comparison,
)


def test_current_dataset_is_used():
    """Verify evaluation uses the current 10,000-row corrected Maitri dataset."""
    df = pd.read_csv("ml/data/maitri_synthetic_telemetry.csv")
    assert len(df) == 10000
    assert set(df["sensor_id"].unique()) == {
        "TEMP_001",
        "PRESS_001",
        "HUM_001",
        "VIB_001",
        "POWER_001",
    }


def test_metrics_mathematical_correctness():
    """Verify precision, recall, F1, and rate calculations."""
    y_true = np.array([1, 1, 1, 0, 0, 0, 1, 0])
    y_pred = np.array([1, 1, 0, 0, 0, 1, 1, 0])
    # TP = 3, TN = 3, FP = 1, FN = 1
    m = calculate_metrics_dict(y_true, y_pred)
    assert m["TP"] == 3
    assert m["TN"] == 3
    assert m["FP"] == 1
    assert m["FN"] == 1
    assert m["precision"] == 0.75
    assert m["recall"] == 0.75
    assert m["f1_score"] == 0.75
    assert m["accuracy"] == 0.75
    assert m["false_positive_rate"] == 0.25
    assert m["false_negative_rate"] == 0.25


def test_metrics_zero_division_safety():
    """Verify metrics calculation handles edge cases without dividing by zero."""
    y_true = np.array([0, 0, 0])
    y_pred = np.array([0, 0, 0])
    m = calculate_metrics_dict(y_true, y_pred)
    assert m["precision"] == 0.0
    assert m["recall"] == 0.0
    assert m["f1_score"] == 0.0
    assert m["accuracy"] == 1.0


def test_confusion_matrix_counts_sum_correctly():
    """Verify confusion matrix counts sum to partition totals."""
    splits_data, _ = evaluate_zscore_splits()

    for s in ["val", "test"]:
        cm_sum = (
            splits_data[s]["TP"]
            + splits_data[s]["TN"]
            + splits_data[s]["FP"]
            + splits_data[s]["FN"]
        )
        assert cm_sum == splits_data[s]["total"]
        assert cm_sum == 1500


def test_per_anomaly_type_counts_sum_correctly():
    """Verify anomaly type counts in test breakdown equal total test partition rows."""
    splits_data, _ = evaluate_zscore_splits()
    per_type = splits_data["test"]["per_anomaly_type"]

    assert "SPIKE" in per_type
    assert "DRIFT" in per_type
    assert "DROPOUT" in per_type
    assert "STUCK_VALUE" in per_type
    assert "NORMAL" in per_type

    total_instances = sum(item["total_instances"] for item in per_type.values())
    assert total_instances == 1500

    # Non-normal types sum to total anomalies
    anom_total = sum(
        item["total_instances"]
        for k, item in per_type.items()
        if k != "NORMAL"
    )
    assert anom_total == splits_data["test"]["TP"] + splits_data["test"]["FN"]


def test_normal_false_alarm_counts_are_correct():
    """Verify normal false-alarm breakdown is mathematically consistent."""
    splits_data, _ = evaluate_zscore_splits()
    normal_data = splits_data["test"]["per_anomaly_type"]["NORMAL"]

    assert normal_data["total_instances"] == normal_data["correct_normal"] + normal_data["false_alarms"]
    assert normal_data["false_alarms"] == splits_data["test"]["FP"]
    assert normal_data["correct_normal"] == splits_data["test"]["TN"]


def test_no_test_labels_used_for_threshold_selection():
    """Verify that thresholds are fixed or derived solely from validation data."""
    # Z-score uses fixed heuristic baseline threshold 3.0
    splits_data, _ = evaluate_zscore_splits(threshold=3.0)
    assert splits_data["threshold_used"] == 3.0

    # LSTM threshold file must indicate selection on validation
    lstm_thresh_file = Path("ml/results/lstm_threshold.json")
    if lstm_thresh_file.exists():
        with open(lstm_thresh_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "validation_f1" in data
        assert data["threshold"] == pytest.approx(0.017674, rel=1e-3)


def test_comparison_output_is_deterministic():
    """Verify repeated runs produce identical deterministic metrics."""
    res1, _ = evaluate_zscore_splits()
    res2, _ = evaluate_zscore_splits()

    assert res1["val"] == res2["val"]
    assert res1["test"] == res2["test"]


def test_generated_json_csv_schemas_and_artifacts(tmp_path: Path):
    """Verify comparison pipeline generates valid JSON, CSV, and PNG visualizations."""
    summary = run_model_comparison(output_dir=str(tmp_path))

    json_path = tmp_path / "maitri_model_comparison.json"
    csv_path = tmp_path / "maitri_model_comparison.csv"
    f1_png = tmp_path / "maitri_model_f1_comparison.png"
    cm_png = tmp_path / "maitri_model_confusion_matrices.png"
    anom_png = tmp_path / "maitri_anomaly_type_detection.png"

    assert json_path.exists()
    assert csv_path.exists()
    assert f1_png.exists()
    assert cm_png.exists()
    assert anom_png.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Schema validation
    assert "dataset" in data
    assert "evaluation_methodology" in data
    assert "models" in data
    assert "zscore_v1" in data["models"]
    assert "lstm_ae_v1" in data["models"]
    assert "comparative_analysis" in data

    # Check metric fields
    for mkey in ["zscore_v1", "lstm_ae_v1"]:
        m = data["models"][mkey]
        for split in ["validation_metrics", "test_metrics"]:
            assert "precision" in m[split]
            assert "recall" in m[split]
            assert "f1_score" in m[split]
            assert "accuracy" in m[split]
            assert "TP" in m[split]
            assert "TN" in m[split]
            assert "FP" in m[split]
            assert "FN" in m[split]

    df_csv = pd.read_csv(csv_path)
    assert len(df_csv) == 2
    expected_cols = [
        "Model",
        "Threshold",
        "Val Precision",
        "Val Recall",
        "Val F1",
        "Test Precision",
        "Test Recall",
        "Test F1",
        "Test Accuracy",
        "Test Spike Recall",
        "Test Drift Recall",
        "Test Stuck Recall",
        "Test Normal FPR",
    ]
    for col in expected_cols:
        assert col in df_csv.columns
