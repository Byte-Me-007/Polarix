"""Unit tests for Polarix Maitri LSTM Autoencoder Inference Layer."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from ml.inference.lstm_inference import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_SCALER_PATH,
    DEFAULT_THRESHOLD_PATH,
    LSTMAutoencoderInference,
)


@pytest.fixture
def inference_engine():
    """Fixture providing initialized inference service."""
    return LSTMAutoencoderInference()


def test_artifacts_load_successfully(inference_engine):
    """Verify pre-trained weights, config, scalers, and threshold load cleanly."""
    assert inference_engine.model is not None
    assert inference_engine.model_version == "lstm-ae-v1"
    assert inference_engine.threshold > 0.0
    assert "TEMP_001" in inference_engine.scalers
    assert "POWER_001" in inference_engine.scalers


def test_insufficient_data_behavior(inference_engine):
    """Verify observations < 30 return INSUFFICIENT_DATA and None score."""
    inference_engine.reset_history("MTR", "TEMP_001")

    for i in range(29):
        res = inference_engine.infer_observation(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=-15.0 + i * 0.01,
            quality="GOOD",
        )
        assert res["anomaly_status"] == "INSUFFICIENT_DATA"
        assert res["anomaly_score"] is None
        assert res["model_version"] == "lstm-ae-v1"


def test_exact_and_extended_window_inference(inference_engine):
    """Verify exactly 30 and >30 observations produce valid numeric scoring."""
    inference_engine.reset_history("MTR", "TEMP_001")

    # Feed 30 observations
    res = None
    for i in range(30):
        res = inference_engine.infer_observation(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=-15.0 + np.sin(i / 10.0) * 2.0,
            quality="GOOD",
        )

    assert res["anomaly_status"] in ["NORMAL", "ANOMALY"]
    assert isinstance(res["anomaly_score"], float)
    assert res["anomaly_score"] >= 0.0

    # 31st observation uses latest 30-step window
    res_31 = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:30:00Z",
        value=-15.2,
        quality="GOOD",
    )
    assert res_31["anomaly_status"] in ["NORMAL", "ANOMALY"]
    assert isinstance(res_31["anomaly_score"], float)


def test_sensor_history_isolation(inference_engine):
    """Verify streams for different sensors never mix."""
    inference_engine.reset_history()

    # Feed 29 points to TEMP_001
    for i in range(29):
        inference_engine.infer_observation(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=-15.0,
        )

    # Feed 1 point to PRESS_001
    res_press = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="PRESS_001",
        timestamp="2026-03-01T00:00:00Z",
        value=990.0,
    )
    # PRESS_001 has only 1 point, so must be INSUFFICIENT_DATA
    assert res_press["anomaly_status"] == "INSUFFICIENT_DATA"

    # TEMP_001 30th point triggers complete sequence for TEMP_001
    res_temp = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:29:00Z",
        value=-15.0,
    )
    assert res_temp["anomaly_status"] in ["NORMAL", "ANOMALY"]


def test_station_history_isolation(inference_engine):
    """Verify streams for unsupported stations are rejected and isolated."""
    from ml.inference.inference_contract import UnsupportedStationError

    inference_engine.reset_history()

    for i in range(29):
        inference_engine.infer_observation(
            station_id="MTR",
            sensor_id="VIB_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=0.85,
        )

    with pytest.raises(UnsupportedStationError):
        inference_engine.infer_observation(
            station_id="OTHER_STATION",
            sensor_id="VIB_001",
            timestamp="2026-03-01T00:00:00Z",
            value=0.85,
        )


def test_missing_data_and_bad_quality(inference_engine):
    """Verify null values and non-GOOD quality return MISSING_DATA and clear buffer."""
    inference_engine.reset_history("MTR", "HUM_001")

    # Feed 20 points
    for i in range(20):
        inference_engine.infer_observation(
            station_id="MTR",
            sensor_id="HUM_001",
            timestamp=f"2026-03-01T00:{i:02d}:00Z",
            value=55.0,
        )

    # Missing observation
    res_missing = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-03-01T00:20:00Z",
        value=None,
    )
    assert res_missing["anomaly_status"] == "MISSING_DATA"
    assert res_missing["anomaly_score"] is None

    # Next valid point starts warmup again (buffer was cleared)
    res_next = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-03-01T00:21:00Z",
        value=55.0,
        quality="GOOD",
    )
    assert res_next["anomaly_status"] == "INSUFFICIENT_DATA"

    # Bad quality flag
    res_bad = inference_engine.infer_observation(
        station_id="MTR",
        sensor_id="HUM_001",
        timestamp="2026-03-01T00:22:00Z",
        value=55.0,
        quality="BAD",
    )
    assert res_bad["anomaly_status"] == "MISSING_DATA"


def test_stateless_window_inference(inference_engine):
    """Verify infer_window handles direct sequence scoring and status thresholds."""
    # Window of normal temperature values
    norm_vals = [-15.0 + np.sin(i / 5.0) * 3.0 for i in range(30)]
    res_norm = inference_engine.infer_window(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:29:00Z",
        window_values=norm_vals,
    )
    assert res_norm["anomaly_status"] in ["NORMAL", "ANOMALY"]
    assert isinstance(res_norm["anomaly_score"], float)

    # Window with corrupted NaN value
    nan_vals = list(norm_vals)
    nan_vals[15] = np.nan
    res_nan = inference_engine.infer_window(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:29:00Z",
        window_values=nan_vals,
    )
    assert res_nan["anomaly_status"] == "MISSING_DATA"
    assert res_nan["anomaly_score"] is None


def test_determinism_and_no_retraining(inference_engine):
    """Verify identical sequences produce identical reconstruction errors."""
    window = [35.0 + np.cos(i / 6.0) * 4.0 for i in range(30)]

    # Take initial model parameters
    initial_weights = [p.clone() for p in inference_engine.model.parameters()]

    res1 = inference_engine.infer_window("MTR", "POWER_001", "2026-03-01T00:30:00Z", window)
    res2 = inference_engine.infer_window("MTR", "POWER_001", "2026-03-01T00:30:00Z", window)

    assert res1["anomaly_score"] == res2["anomaly_score"]
    assert res1["anomaly_status"] == res2["anomaly_status"]

    # Verify model weights remained untouched
    for p_init, p_curr in zip(initial_weights, inference_engine.model.parameters()):
        assert torch.equal(p_init, p_curr)
