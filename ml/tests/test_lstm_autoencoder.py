"""Unit tests for Polarix Maitri LSTM Autoencoder & Sequence Preparation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from ml.training.lstm_autoencoder import (
    MODEL_VERSION,
    Decoder,
    Encoder,
    LSTMAutoencoder,
    LSTMAutoencoderConfig,
)
from ml.training.prepare_sequences import (
    SensorScaler,
    extract_sliding_windows,
    fit_sensor_scalers,
    load_scalers,
    prepare_maitri_datasets,
    save_scalers,
)


def test_model_instantiation_and_forward_shape():
    """Verify LSTM Autoencoder forward pass shape matches input shape."""
    config = LSTMAutoencoderConfig(
        input_size=1,
        seq_len=20,
        encoder_hidden_size=16,
        latent_size=8,
        decoder_hidden_size=16,
    )
    model = LSTMAutoencoder(config)

    batch_size = 4
    x = torch.randn(batch_size, config.seq_len, config.input_size)
    out = model(x)

    assert out.shape == (batch_size, config.seq_len, config.input_size)


def test_reconstruction_error_computation():
    """Verify compute_reconstruction_error calculates expected per-sample and mean MSE."""
    config = LSTMAutoencoderConfig(input_size=1, seq_len=10, encoder_hidden_size=8, latent_size=4)
    model = LSTMAutoencoder(config)

    x = torch.randn(3, 10, 1)
    err_none = model.compute_reconstruction_error(x, reduction="none")
    err_mean = model.compute_reconstruction_error(x, reduction="mean")

    assert err_none.shape == (3,)
    assert (err_none >= 0).all()
    assert torch.isclose(torch.mean(err_none), err_mean)


def test_fit_scalers_on_normal_only():
    """Verify scalers are computed strictly from normal training rows, ignoring anomalies and test data."""
    df_train = pd.DataFrame(
        {
            "sensor_id": ["TEMP_001"] * 6,
            "value": [10.0, 10.0, 10.0, 100.0, np.nan, 10.0],
            "is_anomaly": [0, 0, 0, 1, 1, 0],
            "unit": ["°C"] * 6,
        }
    )

    scalers = fit_sensor_scalers(df_train)
    assert "TEMP_001" in scalers
    # The normal values are 10.0, 10.0, 10.0, 10.0 -> mean = 10.0, std = 0.0 (clipped to min_std)
    assert scalers["TEMP_001"].mean == 10.0
    assert scalers["TEMP_001"].std >= 1e-6


def test_sliding_window_dropout_handling():
    """Verify windows containing NaN/dropout values are excluded from sequences."""
    scaler = SensorScaler(sensor_id="TEMP_001", mean=10.0, std=1.0, unit="°C")
    df = pd.DataFrame(
        {
            "station_id": ["MTR"] * 10,
            "sensor_id": ["TEMP_001"] * 10,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(10)],
            "value": [10.0, 10.0, np.nan, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
            "is_anomaly": [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            "anomaly_type": ["NORMAL", "NORMAL", "DROPOUT"] + ["NORMAL"] * 7,
        }
    )

    # Window of length 4. Any window spanning index 2 (the NaN) must be omitted.
    seqs, meta = extract_sliding_windows(df, scaler, seq_len=4, normal_only=False)
    # Total possible windows = 10 - 4 + 1 = 7.
    # Windows spanning index 2: [0..3], [1..4], [2..5] -> 3 invalid windows.
    # Remaining valid windows: [3..6], [4..7], [5..8], [6..9] -> 4 valid windows.
    assert len(seqs) == 4
    assert len(meta) == 4
    for seq in seqs:
        assert not np.isnan(seq).any()


def test_normal_only_training_sequence_extraction():
    """Verify normal_only flag excludes windows that contain any anomaly point."""
    scaler = SensorScaler(sensor_id="POWER_001", mean=35.0, std=5.0, unit="kW")
    df = pd.DataFrame(
        {
            "station_id": ["MTR"] * 10,
            "sensor_id": ["POWER_001"] * 10,
            "timestamp": [f"2026-03-01T00:0{i}:00Z" for i in range(10)],
            "value": [35.0] * 10,
            "is_anomaly": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # Spike at index 4
            "anomaly_type": ["NORMAL"] * 4 + ["SPIKE"] + ["NORMAL"] * 5,
        }
    )

    seqs_norm, meta_norm = extract_sliding_windows(df, scaler, seq_len=3, normal_only=True)
    # Windows spanning index 4: [2..4], [3..5], [4..6] are excluded.
    # Valid normal windows: [0..2], [1..3], [5..7], [6..8], [7..9] -> 5 windows
    assert len(seqs_norm) == 5
    for m in meta_norm:
        assert m["any_anomaly_in_window"] == 0


def test_prepare_maitri_datasets_pipeline(tmp_path: Path):
    """Verify prepare_maitri_datasets end-to-end on synthetic CSV."""
    df = pd.DataFrame(
        {
            "station_id": ["MTR"] * 200,
            "sensor_id": ["TEMP_001"] * 100 + ["PRESS_001"] * 100,
            "timestamp": [f"2026-03-01T{i//60:02d}:{i%60:02d}:00Z" for i in range(100)] * 2,
            "value": np.random.randn(200) * 2 + 10,
            "unit": ["°C"] * 100 + ["hPa"] * 100,
            "quality": ["GOOD"] * 200,
            "source": ["SYNTHETIC_ML_DATASET"] * 200,
            "anomaly_type": ["NORMAL"] * 200,
            "is_anomaly": [0] * 200,
        }
    )
    csv_file = tmp_path / "dummy_telemetry.csv"
    df.to_csv(csv_file, index=False)

    data = prepare_maitri_datasets(str(csv_file), seq_len=10)
    assert len(data["train_sequences"]) > 0
    assert len(data["val_sequences"]) > 0
    assert len(data["test_sequences"]) > 0
    assert "TEMP_001" in data["scalers"]
    assert "PRESS_001" in data["scalers"]


def test_model_save_and_load(tmp_path: Path):
    """Verify model weights and config can be saved and reloaded accurately."""
    config = LSTMAutoencoderConfig(
        input_size=1,
        seq_len=15,
        encoder_hidden_size=16,
        latent_size=8,
        decoder_hidden_size=16,
    )
    model = LSTMAutoencoder(config)
    save_path = tmp_path / "test_model.pt"
    torch.save(model.state_dict(), save_path)

    loaded_model = LSTMAutoencoder(config)
    loaded_model.load_state_dict(torch.load(save_path, weights_only=True))
    loaded_model.eval()

    x = torch.randn(2, 15, 1)
    with torch.no_grad():
        out_orig = model(x)
        out_loaded = loaded_model(x)

    assert torch.allclose(out_orig, out_loaded)
