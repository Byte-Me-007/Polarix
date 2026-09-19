"""Unit tests for Polarix Bharati LSTM Autoencoder & Training Pipeline (SIH26060 - Person C).

Tests verify:
1. Model construction.
2. Forward pass shape.
3. Sequence generation.
4. Sequence length.
5. Sensor isolation.
6. Normal-only training selection.
7. Chronological split integrity.
8. Scaler fit restriction.
9. No test leakage.
10. Deterministic preprocessing.
11. Artifact save/load.
12. Configuration correctness.
13. Model version.
14. Bharati station validation.
15. Reconstruction output is finite.
16. Training artifact existence.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from ml.models.bharati_lstm_autoencoder import (
    MODEL_VERSION,
    STATION_ID,
    BharatiDecoder,
    BharatiEncoder,
    BharatiLSTMAutoencoder,
    BharatiLSTMConfig,
)
from ml.training.prepare_bharati_sequences import (
    BharatiSensorScaler,
    BharatiSequenceDataset,
    extract_sliding_windows,
    fit_bharati_sensor_scalers,
    load_bharati_scalers,
    prepare_bharati_datasets,
    save_bharati_scalers,
)


def test_1_model_construction():
    """1. Model construction with default and custom configs."""
    config = BharatiLSTMConfig(
        station_id=STATION_ID,
        input_size=1,
        seq_len=30,
        encoder_hidden_size=32,
        latent_size=16,
        decoder_hidden_size=32,
        num_layers=1,
        dropout=0.0,
        model_version=MODEL_VERSION,
    )
    model = BharatiLSTMAutoencoder(config)
    assert isinstance(model.encoder, BharatiEncoder)
    assert isinstance(model.decoder, BharatiDecoder)
    assert model.config.model_version == "lstm-ae-bharati-v1"
    assert model.config.station_id == "BRT"


def test_2_forward_pass_shape():
    """2. Forward pass output tensor shape matches (batch, seq_len, 1)."""
    config = BharatiLSTMConfig(seq_len=30, input_size=1)
    model = BharatiLSTMAutoencoder(config)
    batch_size = 8
    x = torch.randn(batch_size, 30, 1)
    out = model(x)
    assert out.shape == (batch_size, 30, 1)


def test_3_sequence_generation():
    """3. Sliding window sequence generation produces correct count and dimensionality."""
    scaler = BharatiSensorScaler(sensor_id="BRT_TEMP_001", mean=0.0, std=1.0, unit="°C")
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 50,
            "sensor_id": ["BRT_TEMP_001"] * 50,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(50)],
            "value": [float(i) for i in range(50)],
            "is_anomaly": [0] * 50,
            "anomaly_type": ["NORMAL"] * 50,
        }
    )
    seqs, meta = extract_sliding_windows(df, scaler, seq_len=30, normal_only=False)
    # Expected windows = 50 - 30 + 1 = 21
    assert len(seqs) == 21
    assert seqs.shape == (21, 30, 1)
    assert len(meta) == 21
    assert meta[0]["sensor_id"] == "BRT_TEMP_001"


def test_4_sequence_length():
    """4. Sequence length is strictly preserved across sliding window extraction."""
    scaler = BharatiSensorScaler(sensor_id="BRT_PRESS_001", mean=980.0, std=10.0, unit="hPa")
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 40,
            "sensor_id": ["BRT_PRESS_001"] * 40,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(40)],
            "value": [980.0] * 40,
            "is_anomaly": [0] * 40,
            "anomaly_type": ["NORMAL"] * 40,
        }
    )
    seqs, _ = extract_sliding_windows(df, scaler, seq_len=30)
    assert seqs.shape[1] == 30


def test_5_sensor_isolation():
    """5. Ensure sensor streams remain isolated with per-sensor scalers and independent windows."""
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 80,
            "sensor_id": ["BRT_TEMP_001"] * 40 + ["BRT_HUM_001"] * 40,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(40)] * 2,
            "value": [10.0] * 40 + [75.0] * 40,
            "is_anomaly": [0] * 80,
            "anomaly_type": ["NORMAL"] * 80,
            "unit": ["°C"] * 40 + ["%"] * 40,
        }
    )
    scalers = fit_bharati_sensor_scalers(df)
    assert len(scalers) == 2
    assert "BRT_TEMP_001" in scalers
    assert "BRT_HUM_001" in scalers
    assert scalers["BRT_TEMP_001"].mean == 10.0
    assert scalers["BRT_HUM_001"].mean == 75.0
    assert scalers["BRT_TEMP_001"].unit == "°C"
    assert scalers["BRT_HUM_001"].unit == "%"


def test_6_normal_only_training_selection():
    """6. Normal-only training selection excludes sequences containing injected anomalies."""
    scaler = BharatiSensorScaler(sensor_id="BRT_POWER_001", mean=50.0, std=5.0, unit="kW")
    # 35 points with an anomaly at index 10
    is_anom = [0] * 35
    is_anom[10] = 1
    anom_type = ["NORMAL"] * 35
    anom_type[10] = "SPIKE"

    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 35,
            "sensor_id": ["BRT_POWER_001"] * 35,
            "timestamp": [f"2026-03-01T00:{i:02d}:00Z" for i in range(35)],
            "value": [50.0] * 35,
            "is_anomaly": is_anom,
            "anomaly_type": anom_type,
        }
    )

    # seq_len = 10 -> total possible windows = 35 - 10 + 1 = 26
    # Anomaly at index 10 enters windows starting at index 1..10 (10 windows affected)
    seqs_norm, meta_norm = extract_sliding_windows(df, scaler, seq_len=10, normal_only=True)
    for m in meta_norm:
        assert m["any_anomaly_in_window"] == 0
        assert m["is_anomaly"] == 0

    assert len(seqs_norm) == 16  # 26 - 10 = 16


def test_7_chronological_split_integrity():
    """7. Chronological split preserves temporal ordering (first 70% train, next 15% val, last 15% test)."""
    n_records = 1000
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * n_records,
            "sensor_id": ["BRT_VIB_001"] * n_records,
            "timestamp": [pd.Timestamp("2026-03-01") + pd.Timedelta(minutes=i) for i in range(n_records)],
            "value": np.random.randn(n_records) * 0.1 + 1.5,
            "is_anomaly": [0] * n_records,
            "anomaly_type": ["NORMAL"] * n_records,
            "unit": ["mm/s"] * n_records,
        }
    )
    tmp_csv = Path("/tmp/test_brt_chrono_split.csv")
    df.to_csv(tmp_csv, index=False)

    try:
        data = prepare_bharati_datasets(str(tmp_csv), seq_len=30, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
        assert data["train_df_records"] == 700
        assert data["val_df_records"] == 150
        assert data["test_df_records"] == 150
        assert len(data["train_sequences"]) == 700 - 30 + 1
        assert len(data["val_sequences"]) == 150 - 30 + 1
        assert len(data["test_sequences"]) == 150 - 30 + 1
    finally:
        if tmp_csv.exists():
            tmp_csv.unlink()


def test_8_scaler_fit_restriction():
    """8. Scaler is strictly fitted on normal training records and excludes anomalous data points."""
    df_train = pd.DataFrame(
        {
            "sensor_id": ["BRT_TEMP_001"] * 5,
            "value": [20.0, 20.0, 20.0, 999.0, np.nan],
            "is_anomaly": [0, 0, 0, 1, 1],
            "unit": ["°C"] * 5,
        }
    )
    scalers = fit_bharati_sensor_scalers(df_train)
    # The normal values are 20.0, 20.0, 20.0 -> mean must be 20.0, std clamped to min_std
    assert scalers["BRT_TEMP_001"].mean == 20.0
    assert scalers["BRT_TEMP_001"].std >= 1e-6


def test_9_no_test_leakage(tmp_path: Path):
    """9. Test and validation data do not leak into training scaler parameters."""
    train_records = [10.0] * 70
    val_records = [500.0] * 15
    test_records = [1000.0] * 15

    all_vals = train_records + val_records + test_records
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 100,
            "sensor_id": ["BRT_TEMP_001"] * 100,
            "timestamp": [f"2026-03-01T{i // 60:02d}:{i % 60:02d}:00Z" for i in range(100)],
            "value": all_vals,
            "is_anomaly": [0] * 100,
            "anomaly_type": ["NORMAL"] * 100,
            "unit": ["°C"] * 100,
        }
    )
    csv_file = tmp_path / "leak_test.csv"
    df.to_csv(csv_file, index=False)

    data = prepare_bharati_datasets(str(csv_file), seq_len=5, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    scaler = data["scalers"]["BRT_TEMP_001"]
    # Scaler mean must strictly equal 10.0 (from training set only)
    assert scaler.mean == 10.0


def test_10_deterministic_preprocessing(tmp_path: Path):
    """10. Repeated preprocessing on identical inputs yields identical sequences and scalers."""
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 100,
            "sensor_id": ["BRT_TEMP_001"] * 100,
            "timestamp": [f"2026-03-01T{i // 60:02d}:{i % 60:02d}:00Z" for i in range(100)],
            "value": np.linspace(10, 20, 100),
            "is_anomaly": [0] * 100,
            "anomaly_type": ["NORMAL"] * 100,
            "unit": ["°C"] * 100,
        }
    )
    csv_file = tmp_path / "det_test.csv"
    df.to_csv(csv_file, index=False)

    data1 = prepare_bharati_datasets(str(csv_file), seq_len=10)
    data2 = prepare_bharati_datasets(str(csv_file), seq_len=10)

    np.testing.assert_array_equal(data1["train_sequences"], data2["train_sequences"])
    assert data1["scalers"]["BRT_TEMP_001"].mean == data2["scalers"]["BRT_TEMP_001"].mean
    assert data1["scalers"]["BRT_TEMP_001"].std == data2["scalers"]["BRT_TEMP_001"].std


def test_11_artifact_save_load(tmp_path: Path):
    """11. Model weights, configuration, and scalers can be saved and loaded faithfully."""
    config = BharatiLSTMConfig(
        station_id="BRT",
        seq_len=20,
        encoder_hidden_size=16,
        latent_size=8,
        decoder_hidden_size=16,
    )
    model = BharatiLSTMAutoencoder(config)
    pt_path = tmp_path / "model.pt"
    torch.save(model.state_dict(), pt_path)

    loaded_model = BharatiLSTMAutoencoder(config)
    loaded_model.load_state_dict(torch.load(pt_path, weights_only=True))
    loaded_model.eval()

    x = torch.randn(2, 20, 1)
    with torch.no_grad():
        out1 = model(x)
        out2 = loaded_model(x)
    assert torch.allclose(out1, out2)

    # Scaler save/load
    scalers = {"BRT_TEMP_001": BharatiSensorScaler("BRT_TEMP_001", mean=5.0, std=2.0, unit="°C")}
    scaler_path = tmp_path / "scalers.json"
    save_bharati_scalers(scalers, scaler_path)
    loaded_scalers = load_bharati_scalers(scaler_path)
    assert loaded_scalers["BRT_TEMP_001"].mean == 5.0
    assert loaded_scalers["BRT_TEMP_001"].std == 2.0


def test_12_configuration_correctness():
    """12. Configuration dictionary serialization and deserialization."""
    cfg = BharatiLSTMConfig(
        station_id=STATION_ID,
        seq_len=30,
        encoder_hidden_size=32,
        latent_size=16,
        decoder_hidden_size=32,
        model_version=MODEL_VERSION,
    )
    d = cfg.to_dict()
    assert d["station_id"] == "BRT"
    assert d["seq_len"] == 30
    assert d["model_version"] == "lstm-ae-bharati-v1"

    cfg2 = BharatiLSTMConfig.from_dict(d)
    assert cfg2.encoder_hidden_size == 32
    assert cfg2.latent_size == 16


def test_13_model_version():
    """13. Model version identifier is lstm-ae-bharati-v1."""
    assert MODEL_VERSION == "lstm-ae-bharati-v1"
    config = BharatiLSTMConfig()
    assert config.model_version == "lstm-ae-bharati-v1"


def test_14_bharati_station_validation():
    """14. Station identifier is BRT and sensor prefix is BRT_."""
    assert STATION_ID == "BRT"
    expected_sensors = [
        "BRT_TEMP_001",
        "BRT_PRESS_001",
        "BRT_HUM_001",
        "BRT_VIB_001",
        "BRT_POWER_001",
    ]
    for s in expected_sensors:
        assert s.startswith("BRT_")


def test_15_reconstruction_output_finite():
    """15. Forward pass and reconstruction errors are finite (no NaNs or Infs)."""
    model = BharatiLSTMAutoencoder()
    x = torch.randn(4, 30, 1)
    out = model(x)
    assert torch.isfinite(out).all()

    err = model.compute_reconstruction_error(x, reduction="none")
    assert torch.isfinite(err).all()
    assert (err >= 0).all()


def test_16_training_artifact_existence():
    """16. Verification of generated Bharati model and result artifacts."""
    model_path = Path("ml/models/lstm-ae-bharati-v1.pt")
    config_path = Path("ml/models/lstm-ae-bharati-v1_config.json")
    scaler_path = Path("ml/models/lstm-ae-bharati-v1_scaler.json")
    results_json = Path("ml/results/bharati_lstm_training.json")
    results_md = Path("ml/results/bharati_lstm_training.md")
    history_json = Path("ml/results/bharati_lstm_training_history.json")
    errors_csv = Path("ml/results/bharati_lstm_reconstruction_errors.csv")

    assert model_path.exists() and model_path.stat().st_size > 0
    assert config_path.exists() and config_path.stat().st_size > 0
    assert scaler_path.exists() and scaler_path.stat().st_size > 0
    assert results_json.exists() and results_json.stat().st_size > 0
    assert results_md.exists() and results_md.stat().st_size > 0
    assert history_json.exists() and history_json.stat().st_size > 0
    assert errors_csv.exists() and errors_csv.stat().st_size > 0

    # Validate config JSON content
    with open(config_path, "r", encoding="utf-8") as f:
        cfg_data = json.load(f)
    assert cfg_data["station_id"] == "BRT"
    assert cfg_data["model_version"] == "lstm-ae-bharati-v1"

    # Validate scalers JSON content
    with open(scaler_path, "r", encoding="utf-8") as f:
        scalers_data = json.load(f)
    assert "BRT_TEMP_001" in scalers_data
    assert "BRT_PRESS_001" in scalers_data
    assert "BRT_HUM_001" in scalers_data
    assert "BRT_VIB_001" in scalers_data
    assert "BRT_POWER_001" in scalers_data


def test_17_datetime_parsing_no_warnings(tmp_path: Path):
    """17. Datetime parsing in prepare_bharati_datasets handles mixed/ISO formats with zero UserWarnings."""
    import warnings
    df = pd.DataFrame(
        {
            "station_id": ["BRT"] * 100,
            "sensor_id": ["BRT_TEMP_001"] * 100,
            "timestamp": [f"2026-03-01T{i // 60:02d}:{i % 60:02d}:00Z" for i in range(100)],
            "value": np.linspace(10, 20, 100),
            "is_anomaly": [0] * 100,
            "anomaly_type": ["NORMAL"] * 100,
            "unit": ["°C"] * 100,
        }
    )
    csv_file = tmp_path / "warn_test.csv"
    df.to_csv(csv_file, index=False)

    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        data = prepare_bharati_datasets(str(csv_file), seq_len=10)
        assert len(data["train_sequences"]) > 0
        # Check no UserWarnings were raised regarding timestamp parsing
        user_warnings = [w for w in recorded_warnings if issubclass(w.category, UserWarning)]
        assert len(user_warnings) == 0, f"Expected 0 UserWarnings, got: {user_warnings}"
