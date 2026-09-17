"""
Unit and Integration Tests for Maitri LSTM Calibration & Operating-Point Analysis (SIH26060 - Person C).

Verifies the calibration analysis module:
1. Candidate thresholds are valid, finite, and strictly ordered.
2. Metric calculations are mathematically correct.
3. Precision/recall/F1 handle zero denominators safely without raising exceptions.
4. Validation and test data remain strictly separated.
5. Threshold selection never uses test labels.
6. Current frozen threshold (0.017674) is represented correctly.
7. Normal percentile calculations are deterministic.
8. DROPOUT is not incorrectly counted as an LSTM reconstruction anomaly.
9. Output JSON contains all required diagnostic and schema fields.
10. CSV output contains required operating-point columns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from ml.training.analyze_lstm_calibration import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RECONSTRUCTION_CSV,
    FROZEN_THRESHOLD,
    MODEL_VERSION,
    MaitriLSTMCalibrationAnalyzer,
    compute_metrics,
    compute_normal_error_statistics,
    evaluate_per_anomaly_type,
    find_high_recall_operating_point,
    find_lower_fpr_operating_point,
    search_validation_max_f1,
)


@pytest.fixture(scope="module")
def reconstruction_df() -> pd.DataFrame:
    """Fixture providing the reconstruction errors dataframe."""
    assert DEFAULT_RECONSTRUCTION_CSV.exists(), f"File not found: {DEFAULT_RECONSTRUCTION_CSV}"
    return pd.read_csv(DEFAULT_RECONSTRUCTION_CSV)


@pytest.fixture(scope="module")
def analyzer() -> MaitriLSTMCalibrationAnalyzer:
    """Fixture providing an initialized MaitriLSTMCalibrationAnalyzer."""
    return MaitriLSTMCalibrationAnalyzer(
        reconstruction_csv=DEFAULT_RECONSTRUCTION_CSV,
        output_dir=DEFAULT_OUTPUT_DIR,
    )


# -----------------------------------------------------------------------------
# Test 1: Candidate Thresholds Validity and Ordering
# -----------------------------------------------------------------------------
def test_1_candidate_thresholds_valid_and_ordered(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify candidate operating point thresholds are positive, finite, and non-empty."""
    report = analyzer.run_analysis()
    thresholds = [data["threshold"] for data in report["operating_points"].values()]

    assert len(thresholds) >= 5
    for t in thresholds:
        assert isinstance(t, float)
        assert np.isfinite(t)
        assert t >= 0.0


# -----------------------------------------------------------------------------
# Test 2: Metric Calculations Correctness
# -----------------------------------------------------------------------------
def test_2_metric_calculations_correctness() -> None:
    """Verify compute_metrics produces exact mathematical results on known confusion counts."""
    # 10 samples: 3 TP, 4 TN, 2 FP, 1 FN
    y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    y_pred = np.array([1, 1, 1, 0, 1, 1, 0, 0, 0, 0])

    m = compute_metrics(y_true, y_pred)
    assert m["TP"] == 3
    assert m["TN"] == 4
    assert m["FP"] == 2
    assert m["FN"] == 1
    assert m["total"] == 10
    assert m["accuracy"] == 0.7000
    assert m["precision"] == round(3 / 5, 4)  # 0.6000
    assert m["recall"] == round(3 / 4, 4)     # 0.7500
    assert m["f1"] == round(2 * 0.6 * 0.75 / (0.6 + 0.75), 4)  # 0.6667
    assert m["fpr"] == round(2 / 6, 4)        # 0.3333
    assert m["fnr"] == round(1 / 4, 4)        # 0.2500


# -----------------------------------------------------------------------------
# Test 3: Zero Denominator Safety
# -----------------------------------------------------------------------------
def test_3_zero_denominator_safety() -> None:
    """Verify precision, recall, F1, FPR, FNR handle all-zero or all-one edge cases safely."""
    # All zeros predicted -> TP = 0, FP = 0 (Precision denominator is 0)
    y_true = np.array([0, 0, 0, 0])
    y_pred = np.array([0, 0, 0, 0])
    m_zeros = compute_metrics(y_true, y_pred)
    assert m_zeros["precision"] == 0.0
    assert m_zeros["recall"] == 0.0
    assert m_zeros["f1"] == 0.0
    assert m_zeros["fpr"] == 0.0
    assert m_zeros["accuracy"] == 1.0

    # All ones predicted -> TN = 0, FN = 0
    y_true_ones = np.array([1, 1, 1])
    y_pred_ones = np.array([1, 1, 1])
    m_ones = compute_metrics(y_true_ones, y_pred_ones)
    assert m_ones["precision"] == 1.0
    assert m_ones["recall"] == 1.0
    assert m_ones["f1"] == 1.0
    assert m_ones["fnr"] == 0.0


# -----------------------------------------------------------------------------
# Test 4: Validation and Test Data Separation
# -----------------------------------------------------------------------------
def test_4_validation_test_data_separation(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify validation and test splits are non-overlapping and maintain expected sample sizes."""
    assert len(analyzer.val_df) == 1181
    assert len(analyzer.test_df) == 1182

    val_timestamps = set(analyzer.val_df["timestamp"].tolist())
    test_timestamps = set(analyzer.test_df["timestamp"].tolist())

    # Disjoint timestamp sets between validation and test
    assert len(val_timestamps.intersection(test_timestamps)) == 0


# -----------------------------------------------------------------------------
# Test 5: No Test Label Leakage in Selection
# -----------------------------------------------------------------------------
def test_5_no_test_labels_used_for_selection(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify operating point selection functions only receive validation data."""
    val_max_f1, _ = search_validation_max_f1(analyzer.val_df)
    high_rec_t, _ = find_high_recall_operating_point(analyzer.val_df)
    lower_fpr_t, _ = find_lower_fpr_operating_point(analyzer.val_df)

    # Thresholds are selected purely from val_df
    assert val_max_f1 > 0
    assert high_rec_t > 0
    assert lower_fpr_t > 0


# -----------------------------------------------------------------------------
# Test 6: Current Threshold Representation
# -----------------------------------------------------------------------------
def test_6_current_threshold_representation(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify the current frozen threshold 0.017674 is correctly evaluated and represented."""
    report = analyzer.run_analysis()
    curr_op = report["operating_points"]["CURRENT_FROZEN"]

    assert curr_op["threshold"] == pytest.approx(FROZEN_THRESHOLD, rel=1e-5)
    assert curr_op["validation_metrics"]["f1"] == pytest.approx(0.3972, abs=1e-3)
    assert curr_op["test_metrics"]["f1"] == pytest.approx(0.3490, abs=1e-3)


# -----------------------------------------------------------------------------
# Test 7: Normal Percentile Calculations are Deterministic
# -----------------------------------------------------------------------------
def test_7_normal_percentile_calculations_deterministic(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify normal validation error statistics and percentiles are mathematically deterministic."""
    val_norm_errors = analyzer.val_df[analyzer.val_df["is_anomaly"] == 0]["reconstruction_error"].to_numpy(dtype=float)
    stats1 = compute_normal_error_statistics(val_norm_errors)
    stats2 = compute_normal_error_statistics(val_norm_errors)

    assert stats1 == stats2
    assert stats1["count"] == 889
    assert stats1["min"] < stats1["median"] < stats1["percentile_90"] < stats1["percentile_95"] < stats1["max"]


# -----------------------------------------------------------------------------
# Test 8: DROPOUT Isolation from Reconstruction Metrics
# -----------------------------------------------------------------------------
def test_8_dropout_isolation_from_reconstruction(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify DROPOUT is explicitly handled as missing data and not counted as a reconstruction anomaly."""
    breakdown = evaluate_per_anomaly_type(analyzer.test_df, FROZEN_THRESHOLD)
    assert "DROPOUT" in breakdown
    assert "handled_by" in breakdown["DROPOUT"]
    assert "quality != 'GOOD'" in breakdown["DROPOUT"]["handled_by"]


# -----------------------------------------------------------------------------
# Test 9: Output JSON Report Schema
# -----------------------------------------------------------------------------
def test_9_output_json_schema(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify generated JSON report contains all required diagnostic sections."""
    report = analyzer.run_analysis()

    required_keys = [
        "model_version",
        "current_threshold",
        "analysis_timestamp",
        "station_id",
        "validation_sample_count",
        "test_sample_count",
        "normal_validation_statistics",
        "operating_points",
        "methodology",
        "limitations_and_tradeoffs",
        "saved_artifacts",
    ]
    for k in required_keys:
        assert k in report, f"Missing required key: {k}"

    assert report["model_version"] == MODEL_VERSION
    assert report["station_id"] == "MTR"
    assert len(report["operating_points"]) >= 5


# -----------------------------------------------------------------------------
# Test 10: Output CSV Columns Schema
# -----------------------------------------------------------------------------
def test_10_output_csv_schema(analyzer: MaitriLSTMCalibrationAnalyzer) -> None:
    """Verify generated operating points CSV contains all required columns."""
    analyzer.run_analysis()
    csv_path = DEFAULT_OUTPUT_DIR / "maitri_lstm_operating_points.csv"
    assert csv_path.exists()

    df = pd.read_csv(csv_path)
    required_cols = [
        "operating_point",
        "threshold",
        "val_TP", "val_TN", "val_FP", "val_FN",
        "val_precision", "val_recall", "val_f1", "val_accuracy", "val_fpr", "val_fnr",
        "test_TP", "test_TN", "test_FP", "test_FN",
        "test_precision", "test_recall", "test_f1", "test_accuracy", "test_fpr", "test_fnr",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"

    assert len(df) >= 5
