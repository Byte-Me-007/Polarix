#!/usr/bin/env python3
"""
Training & Evaluation Pipeline for Maitri LSTM Autoencoder (Polarix SIH26060 - Person C).

Features:
- Deterministic training on NORMAL synthetic telemetry sequences.
- Validation-based early stopping & best model preservation.
- Generates reconstruction errors on validation & test sets for downstream thresholding.
- Saves model weights, hyperparameters, scalers, and training history.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is in sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.training.lstm_autoencoder import (
    MODEL_VERSION,
    LSTMAutoencoder,
    LSTMAutoencoderConfig,
)
from ml.training.prepare_sequences import (
    TelemetrySequenceDataset,
    load_scalers,
    prepare_maitri_datasets,
    save_scalers,
)


def set_seed(seed: int = 42) -> None:
    """Set random seeds for complete reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_epoch(
    model: LSTMAutoencoder,
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
    model: LSTMAutoencoder,
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
    model: LSTMAutoencoder,
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

    dataset = TelemetrySequenceDataset(sequences)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_errors = []
    model.eval()
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            # Per-sample MSE: (batch_size,)
            errors = model.compute_reconstruction_error(batch, reduction="none")
            all_errors.extend(errors.cpu().numpy().tolist())

    records = []
    for meta, err in zip(metadata, all_errors):
        rec = dict(meta)
        rec["reconstruction_error"] = float(err)
        rec["model_version"] = MODEL_VERSION
        records.append(rec)

    df_errors = pd.DataFrame(records)
    return df_errors


def run_training_pipeline(
    input_csv: str = "ml/data/maitri_synthetic_telemetry.csv",
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
    """Execute complete training and validation pipeline."""
    set_seed(seed)
    device = torch.device("cpu")  # Lightweight CPU training

    models_path = Path(models_dir)
    results_path = Path(results_dir)
    models_path.mkdir(parents=True, exist_ok=True)
    results_path.mkdir(parents=True, exist_ok=True)

    print(f"[Polarix ML] Preparing Maitri sequences (seq_len={seq_len})...")
    data_dict = prepare_maitri_datasets(
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

    # Save scalers
    scaler_file = models_path / f"{MODEL_VERSION}_scaler.json"
    save_scalers(scalers, scaler_file)
    print(f"  Saved scalers to {scaler_file}")

    # DataLoaders
    train_dataset = TelemetrySequenceDataset(train_seqs)
    val_dataset = TelemetrySequenceDataset(val_seqs)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Initialize Model & Config
    config = LSTMAutoencoderConfig(
        input_size=1,
        seq_len=seq_len,
        encoder_hidden_size=hidden_size,
        latent_size=latent_size,
        decoder_hidden_size=hidden_size,
        num_layers=1,
        dropout=0.0,
        model_version=MODEL_VERSION,
    )
    model = LSTMAutoencoder(config).to(device)

    # Save configuration
    config_file = models_path / f"{MODEL_VERSION}_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    # Training Loop with Early Stopping
    history: List[Dict[str, Any]] = []
    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    best_state_dict = None

    model_file = models_path / f"{MODEL_VERSION}.pt"

    print(f"\n[Polarix ML] Starting LSTM Autoencoder training for {epochs} epochs...")
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
    history_file = results_path / "lstm_training_history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_version": MODEL_VERSION,
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
    errors_file = results_path / "lstm_reconstruction_errors.csv"
    combined_errors_df.to_csv(errors_file, index=False)
    print(f"  Saved {len(combined_errors_df)} evaluation sequence errors to {errors_file}")

    final_train_loss = history[-1]["train_loss"]
    final_val_loss = history[-1]["val_loss"]

    summary = {
        "model_version": MODEL_VERSION,
        "train_sequences": len(train_seqs),
        "val_sequences": len(val_seqs),
        "test_sequences": len(test_seqs),
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val_loss),
        "final_train_loss": float(final_train_loss),
        "final_val_loss": float(final_val_loss),
        "model_file": str(model_file),
        "config_file": str(config_file),
        "scaler_file": str(scaler_file),
        "history_file": str(history_file),
        "errors_file": str(errors_file),
    }

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Maitri LSTM Autoencoder for Polarix Anomaly Detection."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="ml/data/maitri_synthetic_telemetry.csv",
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
    summary = run_training_pipeline(
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

    print("\n================ MAITRI LSTM AUTOENCODER TRAINING SUMMARY ================")
    print(f"Model Version:          {summary['model_version']}")
    print(f"Training Sequences:     {summary['train_sequences']}")
    print(f"Validation Sequences:   {summary['val_sequences']}")
    print(f"Test Sequences:         {summary['test_sequences']}")
    print("--------------------------------------------------------------------------")
    print(f"Epochs Completed:       {summary['epochs_completed']}")
    print(f"Best Epoch:             {summary['best_epoch']}")
    print(f"Best Validation Loss:   {summary['best_val_loss']:.6f}")
    print(f"Final Training Loss:    {summary['final_train_loss']:.6f}")
    print(f"Final Validation Loss:  {summary['final_val_loss']:.6f}")
    print("--------------------------------------------------------------------------")
    print(f"Model Saved:            {summary['model_file']}")
    print(f"Config Saved:           {summary['config_file']}")
    print(f"Scalers Saved:          {summary['scaler_file']}")
    print(f"History Saved:          {summary['history_file']}")
    print(f"Reconstruction Errors:  {summary['errors_file']}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
