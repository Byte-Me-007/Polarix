"""
Unit tests for Polarix Bharati Rolling Z-Score Anomaly Detector (SIH26060 - Person C).
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.inference.bharati_zscore_detector import (
    DEFAULT_THRESHOLD,
    DEFAULT_WINDOW,
    MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_STATION,
    BharatiRollingZScoreDetector,
)
from ml.training.evaluate_bharati_zscore import (
    compute_anomaly_type_recall,
    compute_metrics,
    partition_bharati_dataframe,
    run_bharati_zscore_evaluation,
)


def test_detector_construction_and_defaults():
    """Verify detector initialization with defaults and custom parameters."""
    det = BharatiRollingZScoreDetector()
    assert det.config.window == DEFAULT_WINDOW
    assert det.config.threshold == DEFAULT_THRESHOLD
    assert det.config.model_version == "zscore-bharati-v1"

    custom_det = BharatiRollingZScoreDetector(window=15, threshold=2.5, model_version="custom-v1")
    assert custom_det.config.window == 15
    assert custom_det.config.threshold == 2.5
    assert custom_det.config.model_version == "custom-v1"


def test_detector_validation_errors():
    """Verify invalid parameters raise appropriate ValueErrors."""
    with pytest.raises(ValueError, match="window must be >= 2"):
        BharatiRollingZScoreDetector(window=1)

    with pytest.raises(ValueError, match="Threshold must be positive"):
        BharatiRollingZScoreDetector(threshold=0.0)

    with pytest.raises(ValueError, match="min_periods must be >= 1"):
        BharatiRollingZScoreDetector(min_periods=0)


def test_missing_required_columns_error():
    """Verify error raised when required input columns are absent."""
    det = BharatiRollingZScoreDetector()
    invalid_df = pd.DataFrame({"sensor_id": ["BRT_TEMP_001"], "value": [10.0]})
    with pytest.raises(ValueError, match="Missing required input column"):
        det.detect(invalid_df)


def test_insufficient_history_behavior():
    """Verify records during warmup period are scored safely without crashing."""
    det = BharatiRollingZScoreDetector(window=30, min_periods=5)
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001"] * 4,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(4)],
            "value": [10.0, 10.1, 9.9, 10.0],
        }
    )
    res = det.detect(df)
    assert len(res) == 4
    # With min_periods=5, first 4 observations have z_score=0.0 and NORMAL status
    assert (res["predicted_status"] == "NORMAL").all()
    assert (res["z_score"] == 0.0).all()


def test_normal_synthetic_sequence():
    """Verify stable normal time-series produces NORMAL status."""
    det = BharatiRollingZScoreDetector(window=20, threshold=3.0)
    np.random.seed(42)
    normal_vals = 25.0 + np.random.normal(0, 0.2, size=50)
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001"] * 50,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(50)],
            "value": normal_vals,
        }
    )
    res = det.detect(df)
    assert (res["predicted_status"] == "NORMAL").all()
    assert (res["model_version"] == "zscore-bharati-v1").all()


def test_clear_synthetic_spike():
    """Verify a high-magnitude spike triggers ANOMALY status."""
    det = BharatiRollingZScoreDetector(window=20, threshold=3.0)
    vals = [10.0] * 30 + [50.0] + [10.0] * 5
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001"] * len(vals),
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(len(vals))],
            "value": vals,
        }
    )
    res = det.detect(df)
    # The spike at index 30 should exceed threshold 3.0
    assert res.iloc[30]["predicted_status"] == "ANOMALY"
    assert res.iloc[30]["anomaly_score"] > 3.0


def test_missing_and_dropout_telemetry_handling():
    """Verify None and NaN values produce MISSING_DATA status."""
    det = BharatiRollingZScoreDetector(window=10)
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_HUM_001"] * 5,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(5)],
            "value": [50.0, None, np.nan, 52.0, 51.0],
        }
    )
    res = det.detect(df)
    assert res.iloc[1]["predicted_status"] == "MISSING_DATA"
    assert np.isnan(res.iloc[1]["z_score"])
    assert res.iloc[2]["predicted_status"] == "MISSING_DATA"
    assert np.isnan(res.iloc[2]["z_score"])


def test_nan_and_inf_safety():
    """Verify non-finite float inputs (+inf, -inf) are safely intercepted."""
    det = BharatiRollingZScoreDetector(window=10)
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_PRESS_001"] * 4,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(4)],
            "value": [980.0, float("inf"), float("-inf"), 985.0],
        }
    )
    res = det.detect(df)
    assert res.iloc[1]["predicted_status"] == "MISSING_DATA"
    assert res.iloc[2]["predicted_status"] == "MISSING_DATA"


def test_sensor_stream_isolation():
    """Verify separate sensors do not cross-contaminate rolling windows."""
    det = BharatiRollingZScoreDetector(window=10, threshold=3.0)
    # Interleaved multi-sensor observations
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001", "BRT_PRESS_001"] * 20,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(40)],
            "value": [10.0, 1000.0] * 20,
        }
    )
    res = det.detect(df)
    # Both streams have zero variance within their own series
    temp_rows = res[res["sensor_id"] == "BRT_TEMP_001"]
    press_rows = res[res["sensor_id"] == "BRT_PRESS_001"]
    assert (temp_rows["predicted_status"] == "NORMAL").all()
    assert (press_rows["predicted_status"] == "NORMAL").all()


def test_chronological_processing_out_of_order():
    """Verify out-of-order input is internally processed chronologically without distorting results."""
    det = BharatiRollingZScoreDetector(window=10, threshold=3.0)
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001"] * 4,
            "timestamp": [
                "2026-03-01T00:03:00Z",
                "2026-03-01T00:01:00Z",
                "2026-03-01T00:02:00Z",
                "2026-03-01T00:00:00Z",
            ],
            "value": [10.0, 10.0, 10.0, 10.0],
        }
    )
    res = det.detect(df)
    # Output maintains original order
    assert res["timestamp"].tolist() == [
        "2026-03-01T00:03:00Z",
        "2026-03-01T00:01:00Z",
        "2026-03-01T00:02:00Z",
        "2026-03-01T00:00:00Z",
    ]


def test_deterministic_output():
    """Verify identical input data produces identical results."""
    det = BharatiRollingZScoreDetector()
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_VIB_001"] * 25,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(25)],
            "value": np.sin(np.linspace(0, 5, 25)),
        }
    )
    res1 = det.detect(df)
    res2 = det.detect(df)
    pd.testing.assert_frame_equal(res1, res2)


def test_evaluation_metric_correctness():
    """Verify binary metric calculation matches manual calculations."""
    y_true = np.array([1, 1, 0, 0, 0])
    y_pred = np.array([1, 0, 1, 0, 0])

    # TP:1, TN:2, FP:1, FN:1
    metrics = compute_metrics(y_true, y_pred)
    assert metrics["true_positives"] == 1
    assert metrics["true_negatives"] == 2
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["accuracy"] == 0.6
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1_score"] == 0.5


def test_partition_dataframe_splits():
    """Verify chronological dataset partitioning into 70% Train, 15% Val, 15% Test."""
    start_dt = pd.to_datetime("2026-03-01T00:00:00Z", utc=True)
    timestamps = [(start_dt + pd.Timedelta(minutes=i)).isoformat() for i in range(100)]
    df = pd.DataFrame(
        {
            "sensor_id": ["BRT_POWER_001"] * 100,
            "timestamp": timestamps,
            "value": [40.0] * 100,
        }
    )
    train_df, val_df, test_df = partition_bharati_dataframe(df)
    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15


def test_bharati_station_and_sensors_constants():
    """Verify supported station and sensor constants."""
    assert SUPPORTED_STATION == "BRT"
    assert len(SUPPORTED_BHARATI_SENSORS) == 5
    assert "BRT_TEMP_001" in SUPPORTED_BHARATI_SENSORS
    assert "BRT_POWER_001" in SUPPORTED_BHARATI_SENSORS
