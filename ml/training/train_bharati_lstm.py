#!/usr/bin/env python3
"""
Training & Evaluation Pipeline for Bharati LSTM Autoencoder (Polarix SIH26060 - Person C).

Features:
- Deterministic training on NORMAL synthetic telemetry sequences.
- Validation-based early stopping & best model preservation.
- Generates reconstruction errors on validation & test sets for downstream thresholding.
- Saves model weights, hyperparameters, scalers, and training history for Bharati ('BRT').
- Computes cryptographic SHA-256 checksums of all generated Bharati artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.models.bharati_lstm_autoencoder import (
    MODEL_VERSION,
    STATION_ID,
    BharatiLSTMAutoencoder,
    BharatiLSTMConfig,
)
from ml.training.prepare_bharati_sequences import (
    BharatiSequenceDataset,
    load_bharati_scalers,
    prepare_bharati_datasets,
    save_bharati_scalers,
)


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def set_seed(seed: int = 42) -> None:
    """Set random seeds for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_epoch(
    model: BharatiLSTMAutoencoder,
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
    model: BharatiLSTMAutoencoder,
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
    model: BharatiLSTMAutoencoder,
    sequences: np.ndarray,
    metadata: List[Dict[str, Any]],
    batch_size: int = 64,
    device: torch.device = torch.device("cpu"),
) -> pd.DataFrame:
    """
    Compute per-sequence MSE reconstruction error for evaluation sets.
    """
    if len(sequences) == 0:
        return pd.DataFrame()

    dataset = BharatiSequenceDataset(sequences)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_errors = []
    model.eval()
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            errors = model.compute_reconstruction_error(batch, reduction="none")
            all_errors.extend(errors.cpu().numpy().tolist())

    records = []
    for meta, err in zip(metadata, all_errors):
        rec = dict(meta)
        rec["reconstruction_error"] = float(err)
        rec["model_version"] = MODEL_VERSION
        records.append(rec)

    return pd.DataFrame(records)


def run_bharati_training_pipeline(
    input_csv: str = "ml/data/bharati_synthetic_telemetry.csv",
    seq_len: int = 30,
    epochs: int = 30,
    batch_size: int = 64,
    lr: float = 0.001,
    hidden_size: int = 32,
    latent_size: int = 16,
    patience: int = 7,
    seed: int = 42,
    models_dir: str = "ml/models",
    results_dir: str = "ml/results",
) -> Dict[str, Any]:
    """Execute complete Bharati LSTM Autoencoder training and evaluation pipeline."""
    set_seed(seed)
    device = torch.device("cpu")

    models_path = Path(models_dir)
    results_path = Path(results_dir)
    models_path.mkdir(parents=True, exist_ok=True)
    results_path.mkdir(parents=True, exist_ok=True)

    print(f"[Polarix ML] Preparing Bharati sequences (seq_len={seq_len})...")
    data_dict = prepare_bharati_datasets(
        csv_path=input_csv,
        seq_len=seq_len,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
    )

    train_seqs = data_dict["train_sequences"]
    val_seqs = data_dict["val_sequences"]
    test_seqs = data_dict["test_sequences"]
    scalers = data_dict["scalers"]

    print(f"  Train sequences (NORMAL only): {len(train_seqs)}")
    print(f"  Validation sequences:          {len(val_seqs)}")
    print(f"  Test sequences:                {len(test_seqs)}")

    # Save Bharati scalers
    scaler_file = models_path / f"{MODEL_VERSION}_scaler.json"
    save_bharati_scalers(scalers, scaler_file)
    print(f"  Saved scalers to {scaler_file}")

    # DataLoaders
    train_dataset = BharatiSequenceDataset(train_seqs)
    val_dataset = BharatiSequenceDataset(val_seqs)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Initialize Model & Config
    config = BharatiLSTMConfig(
        station_id=STATION_ID,
        input_size=1,
        seq_len=seq_len,
        encoder_hidden_size=hidden_size,
        latent_size=latent_size,
        decoder_hidden_size=hidden_size,
        num_layers=1,
        dropout=0.0,
        model_version=MODEL_VERSION,
    )
    model = BharatiLSTMAutoencoder(config).to(device)

    # Save configuration
    config_file = models_path / f"{MODEL_VERSION}_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    # Model parameter count
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    # Training Loop with Early Stopping
    history: List[Dict[str, Any]] = []
    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    best_state_dict = None

    model_file = models_path / f"{MODEL_VERSION}.pt"

    print(f"\n[Polarix ML] Starting Bharati LSTM Autoencoder training for {epochs} epochs...")
    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss = evaluate_loss(model, val_loader, criterion, device)

        history.append(
            {
                "epoch": epoch,
                "train_loss": float(train_loss),
                "val_loss": float(val_loss),
            }
        )

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
            f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}"
            + (" [Saved Best]" if improved else "")
        )

        if patience_counter >= patience:
            print(f"[Polarix ML] Early stopping triggered at epoch {epoch} (best epoch: {best_epoch}).")
            break

    # Load best weights
    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    # Save history
    history_file = results_path / "bharati_lstm_training_history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_version": MODEL_VERSION,
                "station_id": STATION_ID,
                "epochs_completed": len(history),
                "best_epoch": best_epoch,
                "best_val_loss": float(best_val_loss),
                "history": history,
            },
            f,
            indent=2,
        )

    # Compute reconstruction errors for Validation and Test sets
    print("\n[Polarix ML] Computing reconstruction errors on evaluation sets...")
    val_errors_df = compute_dataset_reconstruction_errors(
        model, val_seqs, data_dict["val_metadata"], batch_size=batch_size, device=device
    )
    test_errors_df = compute_dataset_reconstruction_errors(
        model, test_seqs, data_dict["test_metadata"], batch_size=batch_size, device=device
    )

    combined_errors_df = pd.concat([val_errors_df, test_errors_df], ignore_index=True)
    errors_file = results_path / "bharati_lstm_reconstruction_errors.csv"
    combined_errors_df.to_csv(errors_file, index=False)
    print(f"  Saved {len(combined_errors_df)} evaluation sequence errors to {errors_file}")

    final_train_loss = history[-1]["train_loss"]
    final_val_loss = history[-1]["val_loss"]

    # Compute artifact hashes and sizes
    model_sha = compute_file_sha256(model_file)
    config_sha = compute_file_sha256(config_file)
    scaler_sha = compute_file_sha256(scaler_file)

    summary: Dict[str, Any] = {
        "project": "Polarix",
        "station_id": STATION_ID,
        "station_name": "Bharati",
        "model_version": MODEL_VERSION,
        "model_type": "LSTM_AUTOENCODER",
        "training_data": {
            "source_dataset": input_csv,
            "synthetic_disclaimer": "All training performed strictly on synthetic telemetry. No real Antarctic telemetry used.",
            "total_dataset_rows": 10000,
            "sensor_count": 5,
            "normal_training_records": data_dict["train_df_records"],
            "train_sequences_count": len(train_seqs),
            "val_sequences_count": len(val_seqs),
            "test_sequences_count": len(test_seqs),
            "normal_only_training": True,
        },
        "hyperparameters": {
            "seq_len": seq_len,
            "input_size": 1,
            "encoder_hidden_size": hidden_size,
            "latent_size": latent_size,
            "decoder_hidden_size": hidden_size,
            "num_layers": 1,
            "dropout": 0.0,
            "batch_size": batch_size,
            "learning_rate": lr,
            "optimizer": "Adam",
            "loss_function": "MSELoss",
            "seed": seed,
            "max_epochs": epochs,
            "early_stopping_patience": patience,
        },
        "training_results": {
            "epochs_completed": len(history),
            "best_epoch": best_epoch,
            "best_val_loss": float(best_val_loss),
            "final_train_loss": float(final_train_loss),
            "final_val_loss": float(final_val_loss),
            "train_val_loss_observation": "Validation loss reflects mixed normal and injected anomaly sequences in the validation split.",
            "total_trainable_parameters": total_params,
            "threshold_status": "THRESHOLD_NOT_SELECTED_YET",
        },
        "artifacts": {
            "model": {
                "file": str(model_file),
                "sha256": model_sha,
                "size_bytes": model_file.stat().st_size,
            },
            "config": {
                "file": str(config_file),
                "sha256": config_sha,
                "size_bytes": config_file.stat().st_size,
            },
            "scaler": {
                "file": str(scaler_file),
                "sha256": scaler_sha,
                "size_bytes": scaler_file.stat().st_size,
            },
        },
        "file_references": {
            "history_file": str(history_file),
            "errors_file": str(errors_file),
        },
    }

    # Save machine-readable training summary
    training_json_path = results_path / "bharati_lstm_training.json"
    with open(training_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Generate Markdown training report
    training_md_path = results_path / "bharati_lstm_training.md"
    generate_training_markdown_report(summary, training_md_path)

    return summary


def generate_training_markdown_report(summary: Dict[str, Any], output_path: Path) -> None:
    """Generate human-readable training report for Bharati LSTM Autoencoder."""
    hp = summary["hyperparameters"]
    tr = summary["training_results"]
    td = summary["training_data"]
    arts = summary["artifacts"]

    md_content = f"""# Polarix Bharati LSTM Autoencoder Training Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Model Version:** `{summary['model_version']}`  
**Architecture:** Sequence-to-Sequence LSTM Autoencoder  
**Training Status:** Model Trained & Saved (Validation-Selected Best Epoch)  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> This model was trained and evaluated strictly on synthetic telemetry generated for Bharati station.
> No real Antarctic sensor telemetry was used or claimed.
> **Notice on Anomaly Threshold**: The anomaly detection threshold has **NOT** been selected in this step. A dedicated threshold selection and calibration step will be performed next.

---

## 1. Model Architecture & Hyperparameters

- **Input Dimension**: `{hp['input_size']}` (univariate sliding sequence per sensor)
- **Sequence Length**: `{hp['seq_len']}` time steps
- **Encoder LSTM**: `{hp['encoder_hidden_size']}` hidden units (`num_layers = {hp['num_layers']}`)
- **Latent Bottleneck**: `{hp['latent_size']}` linear units
- **Decoder LSTM**: `{hp['decoder_hidden_size']}` hidden units with Linear output projection
- **Trainable Parameters**: `{tr['total_trainable_parameters']:,}`
- **Loss Function**: `{hp['loss_function']}` (Mean Squared Error)
- **Optimizer**: `{hp['optimizer']}(lr={hp['learning_rate']})`, Batch Size: `{hp['batch_size']}`
- **Random Seed**: `{hp['seed']}`

---

## 2. Training Data & Leakage Prevention Strategy

- **Source Dataset**: `{td['source_dataset']}` (10,000 synthetic records)
- **Chronological Split**: 70% Train (7,000 records), 15% Validation (1,500 records), 15% Test (1,500 records).
- **Normal-Only Training**: Scalers and training sequences are constructed **exclusively from NORMAL training records** (`is_anomaly == 0`). Zero labeled anomalies were included during training.
- **Sequence Counts**:
  - **Training Sequences (Normal Only)**: `{td['train_sequences_count']:,}`
  - **Validation Sequences**: `{td['val_sequences_count']:,}`
  - **Test Sequences**: `{td['test_sequences_count']:,}` (held-out untouched)

---

## 3. Training Dynamics & Convergence

- **Epochs Completed**: `{tr['epochs_completed']}` (Max: `{hp['max_epochs']}`, Early Stopping Patience: `{hp['early_stopping_patience']}`)
- **Best Epoch**: `{tr['best_epoch']}`
- **Best Validation Loss (MSE)**: `{tr['best_val_loss']:.6f}`
- **Final Training Loss (MSE)**: `{tr['final_train_loss']:.6f}`
- **Final Validation Loss (MSE)**: `{tr['final_val_loss']:.6f}`
- **Loss Observation**: `{tr['train_val_loss_observation']}`

---

## 4. Generated Bharati Artifacts & Checksums

| Artifact Role | File Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Model Weights** | `{arts['model']['file']}` | `{arts['model']['size_bytes']:,}` | `{arts['model']['sha256']}` |
| **Architecture Config** | `{arts['config']['file']}` | `{arts['config']['size_bytes']:,}` | `{arts['config']['sha256']}` |
| **Sensor Scalers** | `{arts['scaler']['file']}` | `{arts['scaler']['size_bytes']:,}` | `{arts['scaler']['sha256']}` |

---

## 5. Next Step

The model weights and evaluation reconstruction errors (`ml/results/bharati_lstm_reconstruction_errors.csv`) are prepared for subsequent validation threshold optimization and quantitative baseline comparison against `zscore-bharati-v1`.
"""
    output_path.write_text(md_content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Bharati LSTM Autoencoder for Polarix Anomaly Detection."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="ml/data/bharati_synthetic_telemetry.csv",
        help="Path to input synthetic telemetry CSV.",
    )
    parser.add_argument(
        "--seq-len",
        type=int,
        default=30,
        help="Sequence length (default: 30).",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=30,
        help="Maximum training epochs (default: 30).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size (default: 64).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Learning rate (default: 0.001).",
    )
    parser.add_argument(
        "--hidden-size",
        type=int,
        default=32,
        help="LSTM hidden units (default: 32).",
    )
    parser.add_argument(
        "--latent-size",
        type=int,
        default=16,
        help="Bottleneck latent dimension (default: 16).",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=7,
        help="Early stopping patience epochs (default: 7).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Directory to save model artifacts.",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="ml/results",
        help="Directory to save results.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_bharati_training_pipeline(
        input_csv=args.input,
        seq_len=args.seq_len,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden_size=args.hidden_size,
        latent_size=args.latent_size,
        patience=args.patience,
        seed=args.seed,
        models_dir=args.models_dir,
        results_dir=args.results_dir,
    )

    print("\n================ BHARATI LSTM AUTOENCODER TRAINING SUMMARY ================")
    print(f"Station:                {summary['station_id']} ({summary['station_name']})")
    print(f"Model Version:          {summary['model_version']}")
    print(f"Training Sequences:     {summary['training_data']['train_sequences_count']}")
    print(f"Validation Sequences:   {summary['training_data']['val_sequences_count']}")
    print(f"Test Sequences:         {summary['training_data']['test_sequences_count']}")
    print("--------------------------------------------------------------------------")
    print(f"Epochs Completed:       {summary['training_results']['epochs_completed']}")
    print(f"Best Epoch:             {summary['training_results']['best_epoch']}")
    print(f"Best Validation Loss:   {summary['training_results']['best_val_loss']:.6f}")
    print(f"Final Training Loss:    {summary['training_results']['final_train_loss']:.6f}")
    print(f"Final Validation Loss:  {summary['training_results']['final_val_loss']:.6f}")
    print("--------------------------------------------------------------------------")
    print(f"Model Weights:          {summary['artifacts']['model']['file']}")
    print(f"  SHA-256:              {summary['artifacts']['model']['sha256']}")
    print(f"Config File:            {summary['artifacts']['config']['file']}")
    print(f"Scaler File:            {summary['artifacts']['scaler']['file']}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
