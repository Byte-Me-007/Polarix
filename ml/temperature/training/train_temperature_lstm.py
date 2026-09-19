"""
Deterministic Training Pipeline for Polarix Temperature LSTM (Polarix SIH26060 - Person C).

Features:
- Enforces strict chronological splits (70/15/15) with zero future leakage.
- Fits feature normalizer solely on the training partition.
- Trains a multi-horizon PyTorch LSTM with early stopping.
- Saves model weights, training configuration, and scaler artifacts.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ml.temperature.models.temperature_lstm import TemperatureLSTM
from ml.temperature.training.preprocessing import (
    FEATURE_COLS,
    TARGET_COLS,
    TemperatureFeatureScaler,
    build_causal_sequences,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TrainTemperatureLSTM")


def set_seed(seed: int = 42) -> None:
    """Sets deterministic seeds across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_and_split_data(
    data_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads station CSVs and applies strict chronological splits without shuffling."""
    mtr_path = data_dir / "maitri_temperature_telemetry.csv"
    brt_path = data_dir / "bharati_temperature_telemetry.csv"

    df_mtr = pd.read_csv(mtr_path)
    df_brt = pd.read_csv(brt_path)

    # Sort chronologically
    df_mtr = df_mtr.sort_values("timestamp").reset_index(drop=True)
    df_brt = df_brt.sort_values("timestamp").reset_index(drop=True)

    n_mtr = len(df_mtr)
    train_idx_mtr = int(n_mtr * train_ratio)
    val_idx_mtr = int(n_mtr * (train_ratio + val_ratio))

    mtr_train = df_mtr.iloc[:train_idx_mtr].reset_index(drop=True)
    mtr_val = df_mtr.iloc[train_idx_mtr:val_idx_mtr].reset_index(drop=True)
    mtr_test = df_mtr.iloc[val_idx_mtr:].reset_index(drop=True)

    n_brt = len(df_brt)
    train_idx_brt = int(n_brt * train_ratio)
    val_idx_brt = int(n_brt * (train_ratio + val_ratio))

    brt_train = df_brt.iloc[:train_idx_brt].reset_index(drop=True)
    brt_val = df_brt.iloc[train_idx_brt:val_idx_brt].reset_index(drop=True)
    brt_test = df_brt.iloc[val_idx_brt:].reset_index(drop=True)

    return mtr_train, mtr_val, mtr_test, brt_train, brt_val, brt_test


def train_model(
    data_dir: Path,
    models_dir: Path,
    seed: int = 42,
    lookback: int = 24,
    hidden_dim: int = 64,
    num_layers: int = 2,
    dropout: float = 0.1,
    learning_rate: float = 1e-3,
    batch_size: int = 64,
    max_epochs: int = 60,
    patience: int = 10,
) -> Dict[str, Any]:
    """Executes deterministic training workflow."""
    set_seed(seed)
    models_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    mtr_train, mtr_val, mtr_test, brt_train, brt_val, brt_test = load_and_split_data(data_dir)

    # 2. Fit scaler strictly on combined train partition
    combined_train = pd.concat([mtr_train, brt_train], ignore_index=True)
    scaler = TemperatureFeatureScaler()
    scaler.fit(combined_train)

    scaler_path = models_dir / "temperature_lstm_v1_scaler.json"
    scaler.save_json(scaler_path)
    logger.info(f"Fitted scaler saved to {scaler_path}")

    # 3. Build sequence tensors
    X_mtr_train, y_mtr_train = build_causal_sequences(mtr_train, scaler, lookback=lookback)
    X_brt_train, y_brt_train = build_causal_sequences(brt_train, scaler, lookback=lookback)

    X_train = torch.cat([X_mtr_train, X_brt_train], dim=0)
    y_train = torch.cat([y_mtr_train, y_brt_train], dim=0)

    X_mtr_val, y_mtr_val = build_causal_sequences(mtr_val, scaler, lookback=lookback)
    X_brt_val, y_brt_val = build_causal_sequences(brt_val, scaler, lookback=lookback)

    X_val = torch.cat([X_mtr_val, X_brt_val], dim=0)
    y_val = torch.cat([y_mtr_val, y_brt_val], dim=0)

    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 4. Instantiate model
    model = TemperatureLSTM(
        input_dim=len(FEATURE_COLS),
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        output_dim=len(TARGET_COLS),
        dropout=dropout,
    )
    param_counts = model.get_parameter_count()
    logger.info(f"Instantiated TemperatureLSTM with {param_counts['total_parameters']} parameters")

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    history = []

    model_path = models_dir / "temperature_lstm_v1.pt"

    # 5. Training loop
    for epoch in range(1, max_epochs + 1):
        model.train()
        total_train_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item() * len(batch_x)

        train_loss = total_train_loss / len(train_dataset)

        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                preds = model(batch_x)
                loss = criterion(preds, batch_y)
                total_val_loss += loss.item() * len(batch_x)

        val_loss = total_val_loss / len(val_dataset)

        history.append({
            "epoch": epoch,
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
        })

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1

        if epoch % 5 == 0 or patience_counter == 0:
            logger.info(f"Epoch {epoch:02d}/{max_epochs} - Train Loss: {train_loss:.6f} - Val Loss: {val_loss:.6f} (Best: {best_val_loss:.6f} @ Ep {best_epoch})")

        if patience_counter >= patience:
            logger.info(f"Early stopping triggered at epoch {epoch} (no improvement for {patience} epochs)")
            break

    # Save training configuration
    config = {
        "model_name": "temperature-lstm-v1",
        "model_type": "TemperatureLSTM",
        "provenance": "SYNTHETIC_POLARIX_DATA",
        "random_seed": seed,
        "input_dim": len(FEATURE_COLS),
        "feature_cols": FEATURE_COLS,
        "target_cols": TARGET_COLS,
        "lookback_hours": lookback,
        "hidden_dim": hidden_dim,
        "num_layers": num_layers,
        "dropout": dropout,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "best_epoch": best_epoch,
        "best_val_loss_normalized": float(best_val_loss),
        "parameter_counts": param_counts,
        "training_samples": len(train_dataset),
        "validation_samples": len(val_dataset),
    }

    config_path = models_dir / "temperature_lstm_v1_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    logger.info(f"Model saved to {model_path}")
    logger.info(f"Config saved to {config_path}")

    return {
        "best_val_loss": best_val_loss,
        "best_epoch": best_epoch,
        "model_path": str(model_path),
        "config_path": str(config_path),
        "scaler_path": str(scaler_path),
    }


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    models_dir = base_dir / "models"
    train_model(data_dir=data_dir, models_dir=models_dir)
