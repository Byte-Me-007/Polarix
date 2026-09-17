"""Unit tests for Polarix Rolling Z-Score Anomaly Detector & Evaluation."""

import numpy as np
import pandas as pd
import pytest

from ml.training.evaluate_zscore import compute_metrics, run_evaluation
from ml.training.zscore_detector import (
    MODEL_VERSION,
    PREDICTION_COLUMNS,
    RollingZScoreDetector,
)


def test_required_output_columns_and_version():
    """Verify detector adds required columns and version tag."""
    df = pd.DataFrame(
        {
            "station_id": ["MTR"] * 10,
            "sensor_id": ["TEMP_001"] * 10,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(10)],
            "value": [-15.0 + i * 0.1 for i in range(10)],
            "unit": ["°C"] * 10,
            "quality": ["GOOD"] * 10,
            "source": ["SYNTHETIC_ML_DATASET"] * 10,
        }
    )
    detector = RollingZScoreDetector(window=5, min_periods=2)
    res = detector.detect(df)

    for col in PREDICTION_COLUMNS:
        assert col in res.columns, f"Missing expected column '{col}'"

    assert (res["model_version"] == MODEL_VERSION).all()
    assert (res["model_version"] == "zscore-v1").all()


def test_sensor_isolation():
    """Verify statistics are computed strictly per sensor and do not bleed across sensors."""
    df = pd.DataFrame(
        {
            "sensor_id": ["TEMP_001"] * 10 + ["PRESS_001"] * 10,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(10)] * 2,
            # TEMP values ~ -15, PRESS values ~ 990
            "value": [-15.0] * 10 + [990.0] * 10,
        }
    )
    detector = RollingZScoreDetector(window=5, min_periods=2)
    res = detector.detect(df)

    # For constant values, std is 0 and z_score is 0
    temp_rows = res[res["sensor_id"] == "TEMP_001"]
    press_rows = res[res["sensor_id"] == "PRESS_001"]

    assert len(temp_rows) == 10
    assert len(press_rows) == 10
    assert (temp_rows["z_score"] == 0.0).all()
    assert (press_rows["z_score"] == 0.0).all()


def test_chronological_ordering_handling():
    """Verify out-of-order timestamps produce identical results to sorted input."""
    # Chronological series with normal baseline and spike
    vals = [10.0, 10.1, 9.9, 10.0, 10.2, 50.0, 10.0, 10.1]
    timestamps = [f"2026-03-01T00:0{i}:00Z" for i in range(len(vals))]

    df_sorted = pd.DataFrame(
        {
            "sensor_id": ["VIB_001"] * len(vals),
            "timestamp": timestamps,
            "value": vals,
        }
    )

    # Shuffle DataFrame rows
    df_shuffled = df_sorted.sample(frac=1.0, random_state=42).reset_index(drop=True)

    detector = RollingZScoreDetector(window=5, min_periods=3, threshold=2.0)
    res_sorted = detector.detect(df_sorted)
    res_shuffled = detector.detect(df_shuffled)

    # Match by timestamp
    for ts in timestamps:
        row_sorted = res_sorted[res_sorted["timestamp"] == ts].iloc[0]
        row_shuffled = res_shuffled[res_shuffled["timestamp"] == ts].iloc[0]
        assert row_sorted["predicted_status"] == row_shuffled["predicted_status"]
        if np.isnan(row_sorted["z_score"]):
            assert np.isnan(row_shuffled["z_score"])
        else:
            assert np.isclose(row_sorted["z_score"], row_shuffled["z_score"])


def test_spike_detection_behavior():
    """Verify sudden high magnitude spikes trigger ANOMALY status."""
    normal_vals = [10.0 + np.sin(i / 5.0) * 0.5 for i in range(40)]
    # Insert clear spike
    vals = list(normal_vals)
    vals[25] = 50.0  # Massive spike

    df = pd.DataFrame(
        {
            "sensor_id": ["POWER_001"] * len(vals),
            "timestamp": [f"2026-03-01T{i//60:02d}:{i%60:02d}:00Z" for i in range(len(vals))],
            "value": vals,
        }
    )
    detector = RollingZScoreDetector(window=20, threshold=3.0)
    res = detector.detect(df)

    assert res.iloc[25]["predicted_status"] == "ANOMALY"
    assert res.iloc[25]["anomaly_score"] > 3.0
    # Normal points should be NORMAL
    assert res.iloc[10]["predicted_status"] == "NORMAL"


def test_dropout_missing_handling():
    """Verify missing / NaN values result in MISSING_DATA and NaN scores."""
    vals = [10.0, 10.2, np.nan, np.nan, 10.1]
    df = pd.DataFrame(
        {
            "sensor_id": ["HUM_001"] * 5,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(5)],
            "value": vals,
        }
    )
    detector = RollingZScoreDetector(window=5, min_periods=2)
    res = detector.detect(df)

    assert res.iloc[2]["predicted_status"] == "MISSING_DATA"
    assert np.isnan(res.iloc[2]["z_score"])
    assert np.isnan(res.iloc[2]["anomaly_score"])

    assert res.iloc[3]["predicted_status"] == "MISSING_DATA"
    assert np.isnan(res.iloc[3]["z_score"])

    assert res.iloc[0]["predicted_status"] == "NORMAL"
    assert res.iloc[4]["predicted_status"] == "NORMAL"


def test_zero_rolling_std_handling():
    """Verify zero variance does not produce divide-by-zero or crash."""
    vals = [5.0] * 20
    df = pd.DataFrame(
        {
            "sensor_id": ["PRESS_001"] * 20,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(20)],
            "value": vals,
        }
    )
    detector = RollingZScoreDetector(window=10, min_periods=2)
    res = detector.detect(df)

    assert not np.isinf(res["z_score"]).any()
    assert (res["z_score"] == 0.0).all()
    assert (res["anomaly_score"] == 0.0).all()
    assert (res["predicted_status"] == "NORMAL").all()


def test_determinism():
    """Verify detector produces strictly deterministic output on multiple runs."""
    vals = [1.0, 2.0, 1.5, 8.0, 1.2, 1.4]
    df = pd.DataFrame(
        {
            "sensor_id": ["VIB_001"] * len(vals),
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(len(vals))],
            "value": vals,
        }
    )
    detector1 = RollingZScoreDetector(window=4, threshold=2.5)
    detector2 = RollingZScoreDetector(window=4, threshold=2.5)

    res1 = detector1.detect(df)
    res2 = detector2.detect(df)

    pd.testing.assert_frame_equal(res1, res2)


def test_compute_metrics_correctness():
    """Verify explicit metric calculations on known test array."""
    y_true = np.array([1, 1, 0, 0, 1, 0, 1, 0])
    y_pred = np.array([1, 0, 0, 0, 1, 1, 1, 0])

    # TP = 3 (indices 0, 4, 6)
    # TN = 3 (indices 2, 3, 7)
    # FP = 1 (index 5)
    # FN = 1 (index 1)
    # total = 8
    # precision = 3 / (3 + 1) = 0.75
    # recall = 3 / (3 + 1) = 0.75
    # f1 = 0.75
    # accuracy = 6 / 8 = 0.75
    metrics = compute_metrics(y_true, y_pred)

    assert metrics["true_positives"] == 3
    assert metrics["true_negatives"] == 3
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["accuracy"] == 0.75
    assert metrics["precision"] == 0.75
    assert metrics["recall"] == 0.75
    assert metrics["f1_score"] == 0.75


def test_end_to_end_evaluation_pipeline(tmp_path):
    """Verify complete evaluation pipeline outputs valid files."""
    df = pd.DataFrame(
        {
            "station_id": ["MTR"] * 20,
            "sensor_id": ["TEMP_001"] * 20,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(20)],
            "value": [10.0] * 18 + [50.0, np.nan],
            "unit": ["°C"] * 20,
            "quality": ["GOOD"] * 18 + ["BAD", "MISSING"],
            "source": ["SYNTHETIC_ML_DATASET"] * 20,
            "anomaly_type": ["NORMAL"] * 18 + ["SPIKE", "DROPOUT"],
            "is_anomaly": [0] * 18 + [1, 1],
        }
    )
    in_csv = tmp_path / "test_input.csv"
    out_dir = tmp_path / "results"
    df.to_csv(in_csv, index=False)

    metrics = run_evaluation(
        input_csv=str(in_csv),
        window=10,
        threshold=3.0,
        output_dir=str(out_dir),
    )

    assert (out_dir / "zscore_predictions.csv").exists()
    assert (out_dir / "zscore_metrics.json").exists()
    assert (out_dir / "zscore_confusion_matrix.png").exists()
    assert metrics["true_positives"] >= 1
