"""
Sensor ML V2 Training Pipeline (Polarix SIH26060 - Person C).

Implements improved training setup for V2 candidate models:
- Extended epoch budget (60 epochs)
- ReduceLROnPlateau dynamic learning rate scheduling
- Best-validation checkpoint selection
- Early stopping tracking
- Complete artifact separation in ml/experiments/sensor_v2/
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

from ml.experiments.sensor_v2.config import (
    BHARATI_V2_CONFIG,
    MAITRI_V2_CONFIG,
    SensorV2ExperimentConfig,
)
from ml.models.bharati_lstm_autoencoder import (
    BharatiLSTMAutoencoder,
    BharatiLSTMConfig,
)
from ml.training.lstm_autoencoder import (
    LSTMAutoencoder,
    LSTMAutoencoderConfig,
)
from ml.training.prepare_bharati_sequences import (
    BharatiSequenceDataset,
    prepare_bharati_datasets,
    save_bharati_scalers,
)
from ml.training.prepare_sequences import (
    TelemetrySequenceDataset,
    prepare_maitri_datasets,
    save_scalers,
)


def set_seed(seed: int = 42) -> None:
    """Set random seeds for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.MSELoss,
    device: torch.device,
) -> float:
    """Run a single training epoch."""
    model.train()
    total_loss = 0.0
    total_samples = 0

    for batch in dataloader:
        batch = batch.to(device)
        optimizer.zero_grad()
        reconstruction = model(batch)
        loss = criterion(reconstruction, batch)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * len(batch)
        total_samples += len(batch)

    return total_loss / total_samples if total_samples > 0 else 0.0


def evaluate_loss(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.MSELoss,
    device: torch.device,
) -> float:
    """Compute mean reconstruction loss across a dataset."""
    model.eval()
    total_loss = 0.0
    total_samples = 0

    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            reconstruction = model(batch)
            loss = criterion(reconstruction, batch)
            total_loss += loss.item() * len(batch)
            total_samples += len(batch)

    return total_loss / total_samples if total_samples > 0 else 0.0


def compute_dataset_reconstruction_errors(
    model: nn.Module,
    sequences: np.ndarray,
    metadata: List[Dict[str, Any]],
    model_version: str,
    batch_size: int = 64,
    device: torch.device = torch.device("cpu"),
) -> pd.DataFrame:
    """Compute per-sequence MSE reconstruction error for evaluation sets."""
    if len(sequences) == 0:
        return pd.DataFrame()

    dataset = TelemetrySequenceDataset(sequences)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_errors: List[float] = []
    model.eval()
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            reconstruction = model(batch)
            # Element-wise MSE across (seq_len, 1) -> (batch_size,)
            mse_per_sample = torch.mean((batch - reconstruction) ** 2, dim=(1, 2))
            all_errors.extend(mse_per_sample.cpu().numpy().tolist())

    records = []
    for meta, err in zip(metadata, all_errors):
        rec = dict(meta)
        rec["reconstruction_error"] = float(err)
        rec["model_version"] = model_version
        records.append(rec)

    return pd.DataFrame(records)


def train_v2_candidate(cfg: SensorV2ExperimentConfig) -> Dict[str, Any]:
    """Execute complete V2 training pipeline for a given station configuration."""
    set_seed(cfg.seed)
    device = torch.device("cpu")

    models_dir = REPO_ROOT / cfg.models_dir
    results_dir = REPO_ROOT / cfg.results_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n================================================================================")
    print(f"TRAINING SENSOR V2 CANDIDATE: {cfg.station_name} ({cfg.model_version})")
    print(f"================================================================================")

    # 1. Prepare Datasets
    if cfg.station_id == "MTR":
        data_dict = prepare_maitri_datasets(
            csv_path=str(REPO_ROOT / cfg.dataset_csv),
            seq_len=cfg.seq_len,
            train_ratio=cfg.train_ratio,
            val_ratio=cfg.val_ratio,
            test_ratio=cfg.test_ratio,
        )
        # Scalers
        scaler_file = models_dir / f"{cfg.model_version}_scaler.json"
        save_scalers(data_dict["scalers"], scaler_file)

        # Model
        arch_config = LSTMAutoencoderConfig(
            input_size=cfg.input_size,
            seq_len=cfg.seq_len,
            encoder_hidden_size=cfg.hidden_size,
            latent_size=cfg.latent_size,
            decoder_hidden_size=cfg.hidden_size,
            num_layers=cfg.num_layers,
            dropout=cfg.dropout,
            model_version=cfg.model_version,
        )
        model = LSTMAutoencoder(arch_config).to(device)

    elif cfg.station_id == "BRT":
        data_dict = prepare_bharati_datasets(
            csv_path=str(REPO_ROOT / cfg.dataset_csv),
            seq_len=cfg.seq_len,
            train_ratio=cfg.train_ratio,
            val_ratio=cfg.val_ratio,
            test_ratio=cfg.test_ratio,
        )
        # Scalers
        scaler_file = models_dir / f"{cfg.model_version}_scaler.json"
        save_bharati_scalers(data_dict["scalers"], scaler_file)

        # Model
        arch_config = BharatiLSTMConfig(
            station_id=cfg.station_id,
            input_size=cfg.input_size,
            seq_len=cfg.seq_len,
            encoder_hidden_size=cfg.hidden_size,
            latent_size=cfg.latent_size,
            decoder_hidden_size=cfg.hidden_size,
            num_layers=cfg.num_layers,
            dropout=cfg.dropout,
            model_version=cfg.model_version,
        )
        model = BharatiLSTMAutoencoder(arch_config).to(device)
    else:
        raise ValueError(f"Unsupported station: {cfg.station_id}")

    train_seqs = data_dict["train_sequences"]
    val_seqs = data_dict["val_sequences"]
    test_seqs = data_dict["test_sequences"]
    val_meta = data_dict["val_metadata"]
    test_meta = data_dict["test_metadata"]

    print(f"  Train sequences (NORMAL only): {len(train_seqs)}")
    print(f"  Validation sequences:          {len(val_seqs)}")
    print(f"  Test sequences:                {len(test_seqs)}")

    # Save V2 Config
    config_file = models_dir / f"{cfg.model_version}_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, indent=2)

    # DataLoaders
    train_loader = DataLoader(TelemetrySequenceDataset(train_seqs), batch_size=cfg.batch_size, shuffle=True)
    val_loader = DataLoader(TelemetrySequenceDataset(val_seqs), batch_size=cfg.batch_size, shuffle=False)

    # Optimizer, Criterion, Scheduler
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.initial_lr)
    criterion = nn.MSELoss()
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=cfg.lr_scheduler_factor,
        patience=cfg.lr_scheduler_patience,
        min_lr=cfg.min_lr,
    )

    history: List[Dict[str, Any]] = []
    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    best_state_dict = None

    model_file = models_dir / f"{cfg.model_version}.pt"

    print(f"\n[Training] Running for max {cfg.epochs} epochs with ReduceLROnPlateau and early stopping (patience={cfg.early_stopping_patience})...")
    for epoch in range(1, cfg.epochs + 1):
        current_lr = optimizer.param_groups[0]["lr"]
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss = evaluate_loss(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        history.append({
            "epoch": epoch,
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "learning_rate": float(current_lr),
        })

        improved = False
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_state_dict = model.state_dict()
            torch.save(best_state_dict, model_file)
            improved = True
        else:
            patience_counter += 1

        print(
            f"Epoch {epoch:02d}/{cfg.epochs:02d} | LR: {current_lr:.6f} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}"
            + (" [Saved Best Checkpoint]" if improved else "")
        )

        if patience_counter >= cfg.early_stopping_patience:
            print(f"[*] Early stopping triggered at epoch {epoch} (Best epoch: {best_epoch}, Val Loss: {best_val_loss:.6f})")
            break

    # Save History
    history_file = results_dir / f"{cfg.station_id.lower()}_v2_training_history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump({
            "station_id": cfg.station_id,
            "model_version": cfg.model_version,
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "epochs_run": len(history),
            "history": history,
        }, f, indent=2)

    # Reload best model weights for reconstruction error generation
    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    # Compute reconstruction errors on validation & test sets
    val_errors_df = compute_dataset_reconstruction_errors(
        model, val_seqs, val_meta, cfg.model_version, batch_size=cfg.batch_size, device=device
    )
    test_errors_df = compute_dataset_reconstruction_errors(
        model, test_seqs, test_meta, cfg.model_version, batch_size=cfg.batch_size, device=device
    )

    combined_errors_df = pd.concat([val_errors_df, test_errors_df], ignore_index=True)
    errors_csv_file = results_dir / f"{cfg.station_id.lower()}_v2_reconstruction_errors.csv"
    combined_errors_df.to_csv(errors_csv_file, index=False)
    print(f"[Output] Saved reconstruction errors to {errors_csv_file.relative_to(REPO_ROOT)}")

    return {
        "station_id": cfg.station_id,
        "model_version": cfg.model_version,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "epochs_run": len(history),
        "val_errors_df": val_errors_df,
        "test_errors_df": test_errors_df,
    }


def main() -> None:
    train_v2_candidate(MAITRI_V2_CONFIG)
    train_v2_candidate(BHARATI_V2_CONFIG)


if __name__ == "__main__":
    main()
