"""Unit tests for Polarix Maitri LSTM Threshold Selection & Evaluation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.training.select_lstm_threshold import (
    MODEL_VERSION,
    calculate_metrics,
    evaluate_test_set,
    generate_candidate_thresholds,
    run_threshold_selection_pipeline,
    search_optimal_threshold,
)


def test_calculate_metrics_edge_cases():
    """Verify metrics calculation under edge cases (all zeros, all ones, empty)."""
    # All correct normals
    m_norm = calculate_metrics(np.array([0, 0, 0]), np.array([0, 0, 0]))
    assert m_norm["TN"] == 3
    assert m_norm["accuracy"] == 1.0
    assert m_norm["precision"] == 0.0
    assert m_norm["recall"] == 0.0
    assert m_norm["f1"] == 0.0

    # All correct anomalies
    m_anom = calculate_metrics(np.array([1, 1, 1]), np.array([1, 1, 1]))
    assert m_anom["TP"] == 3
    assert m_anom["accuracy"] == 1.0
    assert m_anom["precision"] == 1.0
    assert m_anom["recall"] == 1.0
    assert m_anom["f1"] == 1.0


def test_candidate_threshold_generation():
    """Verify candidate thresholds are bounded by min and max errors and sorted."""
    errors = np.array([0.1, 0.5, 1.2, 3.4, 10.0])
    candidates = generate_candidate_thresholds(errors, num_quantiles=20, num_linear=20)

    assert len(candidates) > 0
    assert candidates[0] == pytest.approx(0.1, rel=1e-3)
    assert candidates[-1] == pytest.approx(10.0, rel=1e-3)
    assert (np.diff(candidates) >= 0).all()  # Strictly monotonic non-decreasing


def test_f1_threshold_selection_and_tie_breaking():
    """Verify threshold search selects the highest F1 threshold with tie-breaking."""
    # Synthetic validation set:
    # 5 normals with errors [0.1, 0.2, 0.3, 0.4, 0.5]
    # 5 anomalies with errors [1.0, 1.2, 1.5, 2.0, 3.0]
    val_df = pd.DataFrame(
        {
            "reconstruction_error": [0.1, 0.2, 0.3, 0.4, 0.5, 1.0, 1.2, 1.5, 2.0, 3.0],
            "is_anomaly": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
        }
    )

    best_thresh, best_metrics, search_df = search_optimal_threshold(val_df)
    # Any threshold between 0.5 and 1.0 yields perfect separation (F1 = 1.0)
    assert best_metrics["f1"] == 1.0
    assert best_metrics["precision"] == 1.0
    assert best_metrics["recall"] == 1.0
    assert 0.5 <= best_thresh <= 1.0


def test_validation_only_selection_applied_to_test(tmp_path: Path):
    """Verify threshold is chosen strictly on validation and applied unchanged to test."""
    # Validation: perfectly separated around error = 2.0
    val_records = [
        {"reconstruction_error": 1.0, "is_anomaly": 0, "anomaly_type": "NORMAL", "split": "val"},
        {"reconstruction_error": 3.0, "is_anomaly": 1, "anomaly_type": "SPIKE", "split": "val"},
    ]
    # Test: has an anomaly with error = 0.5 (which will be missed if threshold is ~2.0)
    test_records = [
        {"reconstruction_error": 1.0, "is_anomaly": 0, "anomaly_type": "NORMAL", "split": "test"},
        {"reconstruction_error": 0.5, "is_anomaly": 1, "anomaly_type": "DRIFT", "split": "test"},
        {"reconstruction_error": 4.0, "is_anomaly": 1, "anomaly_type": "SPIKE", "split": "test"},
    ]

    all_records = []
    for r in val_records + test_records:
        rec = dict(r)
        rec.update(
            {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": "2026-03-01T00:00:00Z",
                "target_value": 10.0,
                "any_anomaly_in_window": r["is_anomaly"],
                "model_version": MODEL_VERSION,
            }
        )
        all_records.append(rec)

    csv_path = tmp_path / "test_errors.csv"
    pd.DataFrame(all_records).to_csv(csv_path, index=False)

    results = run_threshold_selection_pipeline(
        input_csv=str(csv_path), output_dir=str(tmp_path / "out")
    )

    selected_thresh = results["selected_threshold"]
    # Selected threshold from validation must be between 1.0 and 3.0
    assert 1.0 <= selected_thresh <= 3.0
    # Test metrics must reflect applying this exact threshold
    test_m = results["test_metrics"]
    assert test_m["threshold_used"] == selected_thresh
    assert test_m["TP"] == 1  # only error=4.0 detected
    assert test_m["FN"] == 1  # error=0.5 missed
    assert test_m["TN"] == 1  # error=1.0 correct normal


def test_missing_data_quality_tag_preservation():
    """Verify records tagged with quality='MISSING' retain MISSING_DATA predicted_status."""
    test_df = pd.DataFrame(
        {
            "reconstruction_error": [0.2, 5.0, 0.1],
            "is_anomaly": [0, 1, 1],
            "anomaly_type": ["NORMAL", "SPIKE", "DROPOUT"],
            "quality": ["GOOD", "BAD", "MISSING"],
        }
    )
    metrics, pred_df = evaluate_test_set(test_df, threshold=1.0)
    assert pred_df.iloc[0]["predicted_status"] == "NORMAL"
    assert pred_df.iloc[1]["predicted_status"] == "ANOMALY"
    assert pred_df.iloc[2]["predicted_status"] == "MISSING_DATA"
