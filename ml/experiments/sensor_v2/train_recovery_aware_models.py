"""
Sensor ML V2 Recovery-Aware Model Training Pipeline (Polarix SIH26060 - Person C).

Trains recovery-aware candidate models:
- lstm-ae-v2-recovery-aware-candidate (Maitri)
- lstm-ae-bharati-v2-recovery-aware-candidate (Bharati)

Features:
- Exclusively CLEAN_NORMAL training sequences (no contaminated or active anomaly sequences).
- Dynamic ReduceLROnPlateau scheduler.
- Best validation loss checkpointing.
- Exact filesystem path, byte size, and SHA-256 hash logging for all .pt models.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

from ml.experiments.sensor_v2.config import SensorV2ExperimentConfig
from ml.experiments.sensor_v2.prepare_recovery_aware_sequences import (
    RecoveryAwareDataset,
    prepare_recovery_aware_dataset,
)
from ml.models.bharati_lstm_autoencoder import (
    BharatiLSTMAutoencoder,
    BharatiLSTMConfig,
)
from ml.training.lstm_autoencoder import (
    LSTMAutoencoder,
    LSTMAutoencoderConfig,
)

MAITRI_RECOVERY_CONFIG = SensorV2ExperimentConfig(
    station_id="MTR",
    station_name="Maitri",
    model_version="lstm-ae-v2-recovery-aware-candidate",
    dataset_csv="ml/data/maitri_synthetic_telemetry.csv",
    seq_len=30,
    hidden_size=32,
    latent_size=16,
    epochs=60,
    batch_size=64,
    initial_lr=0.001,
    lr_scheduler="ReduceLROnPlateau",
    lr_scheduler_factor=0.5,
    lr_scheduler_patience=4,
    min_lr=1e-5,
    early_stopping_patience=12,
    seed=42,
)

BHARATI_RECOVERY_CONFIG = SensorV2ExperimentConfig(
    station_id="BRT",
    station_name="Bharati",
    model_version="lstm-ae-bharati-v2-recovery-aware-candidate",
    dataset_csv="ml/data/bharati_synthetic_telemetry.csv",
    seq_len=30,
    hidden_size=32,
    latent_size=16,
    epochs=60,
    batch_size=64,
    initial_lr=0.001,
    lr_scheduler="ReduceLROnPlateau",
    lr_scheduler_factor=0.5,
    lr_scheduler_patience=4,
    min_lr=1e-5,
    early_stopping_patience=12,
    seed=42,
)


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_reconstruction_errors_df(
    model: nn.Module,
    sequences: np.ndarray,
    metadata: List[Dict[str, Any]],
    model_version: str,
    batch_size: int = 64,
    device: torch.device = torch.device("cpu"),
) -> pd.DataFrame:
    if len(sequences) == 0:
        return pd.DataFrame()

    dataset = RecoveryAwareDataset(sequences)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_errors: List[float] = []
    model.eval()
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            reconstruction = model(batch)
            mse_per_sample = torch.mean((batch - reconstruction) ** 2, dim=(1, 2))
            all_errors.extend(mse_per_sample.cpu().numpy().tolist())

    records = []
    for meta, err in zip(metadata, all_errors):
        rec = dict(meta)
        rec["reconstruction_error"] = float(err)
        rec["model_version"] = model_version
        records.append(rec)

    return pd.DataFrame(records)


def train_recovery_candidate(cfg: SensorV2ExperimentConfig) -> Dict[str, Any]:
    set_seed(cfg.seed)
    device = torch.device("cpu")

    models_dir = REPO_ROOT / cfg.models_dir
    results_dir = REPO_ROOT / cfg.results_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n================================================================================")
    print(f"TRAINING RECOVERY-AWARE SENSOR V2: {cfg.station_name} ({cfg.model_version})")
    print(f"================================================================================")

    # 1. Prepare Recovery-Aware Dataset
    data_dict = prepare_recovery_aware_dataset(
        station_id=cfg.station_id,
        csv_path=cfg.dataset_csv,
        seq_len=cfg.seq_len,
        train_ratio=cfg.train_ratio,
        val_ratio=cfg.val_ratio,
        test_ratio=cfg.test_ratio,
    )

    train_seqs = data_dict["train_sequences"]
    val_seqs = data_dict["val_sequences"]
    test_seqs = data_dict["test_sequences"]
    val_meta = data_dict["val_metadata"]
    test_meta = data_dict["test_metadata"]
    stats = data_dict["stats"]

    print(f"  Training Windows (CLEAN NORMAL ONLY): {len(train_seqs)}")
    print(f"  Validation Windows Total:             {len(val_seqs)} (Clean: {stats['val_window_counts']['CLEAN_NORMAL']}, Contaminated: {stats['val_window_counts']['CONTAMINATED_NORMAL']}, Active Anomaly: {stats['val_window_counts']['ACTIVE_ANOMALY']})")
    print(f"  Test Windows Total:                   {len(test_seqs)} (Clean: {stats['test_window_counts']['CLEAN_NORMAL']}, Contaminated: {stats['test_window_counts']['CONTAMINATED_NORMAL']}, Active Anomaly: {stats['test_window_counts']['ACTIVE_ANOMALY']})")

    # Save Scaler
    scaler_file = models_dir / f"{cfg.model_version}_scaler.json"
    with open(scaler_file, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in data_dict["scalers"].items()}, f, indent=2)

    # Save Config
    config_file = models_dir / f"{cfg.model_version}_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, indent=2)

    # Model architecture
    if cfg.station_id == "MTR":
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
    else:
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

    train_loader = DataLoader(RecoveryAwareDataset(train_seqs), batch_size=cfg.batch_size, shuffle=True)
    val_loader = DataLoader(RecoveryAwareDataset(val_seqs), batch_size=cfg.batch_size, shuffle=False)

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

    print(f"\n[Training] Max {cfg.epochs} epochs with ReduceLROnPlateau...")
    for epoch in range(1, cfg.epochs + 1):
        # Train epoch
        model.train()
        t_loss, t_count = 0.0, 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            rec = model(batch)
            loss = criterion(rec, batch)
            loss.backward()
            optimizer.step()
            t_loss += loss.item() * len(batch)
            t_count += len(batch)
        avg_train_loss = t_loss / t_count if t_count > 0 else 0.0

        # Val epoch
        model.eval()
        v_loss, v_count = 0.0, 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                rec = model(batch)
                loss = criterion(rec, batch)
                v_loss += loss.item() * len(batch)
                v_count += len(batch)
        avg_val_loss = v_loss / v_count if v_count > 0 else 0.0

        current_lr = optimizer.param_groups[0]["lr"]
        scheduler.step(avg_val_loss)

        history.append({
            "epoch": epoch,
            "train_loss": float(avg_train_loss),
            "val_loss": float(avg_val_loss),
            "learning_rate": float(current_lr),
        })

        improved = False
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            best_state_dict = model.state_dict()
            torch.save(best_state_dict, model_file)
            improved = True
        else:
            patience_counter += 1

        print(
            f"Epoch {epoch:02d}/{cfg.epochs:02d} | LR: {current_lr:.6f} | Train: {avg_train_loss:.6f} | Val: {avg_val_loss:.6f}"
            + (" [Checkpoint Saved]" if improved else "")
        )

        if patience_counter >= cfg.early_stopping_patience:
            print(f"[*] Early stopping triggered at epoch {epoch} (Best: {best_epoch}, Val Loss: {best_val_loss:.6f})")
            break

    # Save History
    history_file = results_dir / f"{cfg.station_id.lower()}_v2_recovery_training_history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump({
            "station_id": cfg.station_id,
            "model_version": cfg.model_version,
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "epochs_run": len(history),
            "window_counts": stats,
            "history": history,
        }, f, indent=2)

    # Reload best weights
    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    # Compute reconstruction errors
    val_errors_df = compute_reconstruction_errors_df(
        model, val_seqs, val_meta, cfg.model_version, batch_size=cfg.batch_size, device=device
    )
    test_errors_df = compute_reconstruction_errors_df(
        model, test_seqs, test_meta, cfg.model_version, batch_size=cfg.batch_size, device=device
    )

    combined_errors_df = pd.concat([val_errors_df, test_errors_df], ignore_index=True)
    errors_csv = results_dir / f"{cfg.station_id.lower()}_v2_recovery_reconstruction_errors.csv"
    combined_errors_df.to_csv(errors_csv, index=False)

    file_size = model_file.stat().st_size
    file_sha256 = compute_file_sha256(model_file)

    print(f"\n[Artifact Verification]")
    print(f"  Exact Model Path: {model_file.resolve()}")
    print(f"  File Size:        {file_size} bytes")
    print(f"  SHA-256:          {file_sha256}")

    return {
        "station_id": cfg.station_id,
        "model_version": cfg.model_version,
        "model_path": str(model_file),
        "file_size_bytes": file_size,
        "sha256": file_sha256,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "epochs_run": len(history),
        "errors_csv": str(errors_csv),
    }


def main() -> None:
    train_recovery_candidate(MAITRI_RECOVERY_CONFIG)
    train_recovery_candidate(BHARATI_RECOVERY_CONFIG)


if __name__ == "__main__":
    main()
