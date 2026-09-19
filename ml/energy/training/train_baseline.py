"""
Deterministic Training Pipeline for Energy ML Forecasting Baseline (Polarix SIH26060).

Workflow:
1. Loads Maitri and Bharati 1-year telemetry datasets.
2. Fits standard normal scalers strictly on the training partition.
3. Builds station-isolated sliding window sequences (lookback L=24).
4. Trains multi-target EnergyLSTM on CPU with early stopping on validation loss.
5. Saves model weights, config, and scaler parameters to ml/energy/models/.
6. Evaluates final model on held-out test partitions against classical baselines.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ml.energy.models.energy_lstm import EnergyLSTM, EnergyModelConfig
from ml.energy.training.baselines import (
    MovingAverageForecaster,
    PersistenceForecaster,
    SeasonalLagForecaster,
    compute_regression_metrics,
)
from ml.energy.training.preprocessing import (
    EnergyScalerParams,
    build_station_sequences,
    fit_energy_scaler,
    inverse_transform_targets,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EnergyTrainBaseline")


def set_seed(seed: int = 42) -> None:
    """Ensure strict deterministic reproducibility across CPU threads and numpy/random."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)


def train_energy_model(
    data_dir: Path = Path("ml/energy/data"),
    output_dir: Path = Path("ml/energy/models"),
    results_dir: Path = Path("ml/energy/results"),
    config: Optional[EnergyModelConfig] = None,
) -> Dict[str, Any]:
    """Train baseline EnergyLSTM model and evaluate performance."""
    if config is None:
        config = EnergyModelConfig()

    set_seed(config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    mtr_csv = data_dir / "maitri_energy_telemetry.csv"
    brt_csv = data_dir / "bharati_energy_telemetry.csv"
    assert mtr_csv.exists(), f"Maitri data not found: {mtr_csv}"
    assert brt_csv.exists(), f"Bharati data not found: {brt_csv}"

    mtr_df = pd.read_csv(mtr_csv)
    brt_df = pd.read_csv(brt_csv)

    # Filter splits
    mtr_train = mtr_df[mtr_df["split"] == "train"].copy()
    mtr_val = mtr_df[mtr_df["split"] == "val"].copy()
    mtr_test = mtr_df[mtr_df["split"] == "test"].copy()

    brt_train = brt_df[brt_df["split"] == "train"].copy()
    brt_val = brt_df[brt_df["split"] == "val"].copy()
    brt_test = brt_df[brt_df["split"] == "test"].copy()

    # 2. Fit Scaler strictly on combined training partitions
    train_combined = pd.concat([mtr_train, brt_train], ignore_index=True)
    scaler = fit_energy_scaler(train_combined)
    scaler_path = output_dir / "energy_lstm_baseline_scaler.json"
    scaler.save(scaler_path)
    logger.info(f"Saved scaler parameters to {scaler_path}")

    # 3. Build Sequences per Station
    mtr_X_tr, mtr_y_tr, mtr_yn_tr = build_station_sequences(mtr_train, scaler, lookback=config.lookback)
    mtr_X_val, mtr_y_val, mtr_yn_val = build_station_sequences(mtr_val, scaler, lookback=config.lookback)
    mtr_X_te, mtr_y_te, mtr_yn_te = build_station_sequences(mtr_test, scaler, lookback=config.lookback)

    brt_X_tr, brt_y_tr, brt_yn_tr = build_station_sequences(brt_train, scaler, lookback=config.lookback)
    brt_X_val, brt_y_val, brt_yn_val = build_station_sequences(brt_val, scaler, lookback=config.lookback)
    brt_X_te, brt_y_te, brt_yn_te = build_station_sequences(brt_test, scaler, lookback=config.lookback)

    # Combine for training
    X_train = np.concatenate([mtr_X_tr, brt_X_tr], axis=0)
    y_train_norm = np.concatenate([mtr_yn_tr, brt_yn_tr], axis=0)

    X_val = np.concatenate([mtr_X_val, brt_X_val], axis=0)
    y_val_norm = np.concatenate([mtr_yn_val, brt_yn_val], axis=0)

    logger.info(f"Training sequences: X={X_train.shape}, Val sequences: X={X_val.shape}")

    # PyTorch DataLoaders
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train_norm, dtype=torch.float32))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val_norm, dtype=torch.float32))

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False)

    # 4. Initialize Model
    model = EnergyLSTM(config)
    criterion = nn.SmoothL1Loss()  # Robust to outliers
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.max_epochs, eta_min=1e-5)

    # 5. Training Loop with Early Stopping
    best_val_loss = float("inf")
    best_state_dict = None
    patience_counter = 0

    history = {"train_loss": [], "val_loss": []}

    logger.info(f"Starting EnergyLSTM training for up to {config.max_epochs} epochs...")
    for epoch in range(1, config.max_epochs + 1):
        model.train()
        total_train_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_train_loss += loss.item() * len(batch_x)

        avg_train_loss = total_train_loss / len(train_dataset)

        # Validation
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                preds = model(batch_x)
                loss = criterion(preds, batch_y)
                total_val_loss += loss.item() * len(batch_x)

        avg_val_loss = total_val_loss / len(val_dataset)
        scheduler.step()

        history["train_loss"].append(round(avg_train_loss, 6))
        history["val_loss"].append(round(avg_val_loss, 6))

        if epoch % 5 == 0 or epoch == 1:
            logger.info(f"Epoch {epoch:02d}/{config.max_epochs:02d} - Train Loss: {avg_train_loss:.5f} - Val Loss: {avg_val_loss:.5f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping triggered at epoch {epoch} (Best Val Loss: {best_val_loss:.5f})")
                break

    # Save Best Model Artifacts
    model_path = output_dir / "energy_lstm_baseline.pt"
    config_path = output_dir / "energy_lstm_baseline_config.json"

    assert best_state_dict is not None
    torch.save(best_state_dict, model_path)
    config.save(config_path)
    logger.info(f"Saved best model weights to {model_path} and config to {config_path}")

    # Load best model for evaluation
    model.load_state_dict(best_state_dict)
    model.eval()

    # 6. Evaluation Function for a Dataset Partition
    def evaluate_model_on_sequences(
        X_seq: np.ndarray,
        y_true_raw: np.ndarray,
    ) -> Dict[str, Dict[str, float]]:
        if len(X_seq) == 0:
            return {}
        with torch.no_grad():
            preds_norm = model(torch.tensor(X_seq, dtype=torch.float32)).numpy()
        preds_raw = inverse_transform_targets(preds_norm, scaler)

        metrics = {}
        for target_idx, target_name in enumerate(scaler.target_names):
            t_true = y_true_raw[:, target_idx]
            t_pred = preds_raw[:, target_idx]
            metrics[target_name] = compute_regression_metrics(t_true, t_pred)
        return metrics

    # Evaluate Neural Model on Test Partitions
    mtr_neural_test_metrics = evaluate_model_on_sequences(mtr_X_te, mtr_y_te)
    brt_neural_test_metrics = evaluate_model_on_sequences(brt_X_te, brt_y_te)

    # Combined test evaluation
    comb_X_te = np.concatenate([mtr_X_te, brt_X_te], axis=0)
    comb_y_te = np.concatenate([mtr_y_te, brt_y_te], axis=0)
    comb_neural_test_metrics = evaluate_model_on_sequences(comb_X_te, comb_y_te)

    # 7. Evaluate Classical Baselines on Test Partition
    def evaluate_baseline_on_df(forecaster, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        preds_df = forecaster.predict(df)
        b_metrics = {}
        b_metrics["target_power_demand_1h_kw"] = compute_regression_metrics(
            df["target_power_demand_1h_kw"].to_numpy(), preds_df["pred_power_demand_1h_kw"].to_numpy()
        )
        b_metrics["target_battery_soc_1h_percent"] = compute_regression_metrics(
            df["target_battery_soc_1h_percent"].to_numpy(), preds_df["pred_battery_soc_1h_percent"].to_numpy()
        )
        b_metrics["target_energy_demand_6h_kwh"] = compute_regression_metrics(
            df["target_energy_demand_6h_kwh"].to_numpy(), preds_df["pred_energy_demand_6h_kwh"].to_numpy()
        )
        b_metrics["target_energy_demand_24h_kwh"] = compute_regression_metrics(
            df["target_energy_demand_24h_kwh"].to_numpy(), preds_df["pred_energy_demand_24h_kwh"].to_numpy()
        )
        return b_metrics

    pers_forecaster = PersistenceForecaster()
    lag_forecaster = SeasonalLagForecaster()
    ma_forecaster = MovingAverageForecaster()

    mtr_pers_metrics = evaluate_baseline_on_df(pers_forecaster, mtr_test)
    mtr_lag_metrics = evaluate_baseline_on_df(lag_forecaster, mtr_test)
    mtr_ma_metrics = evaluate_baseline_on_df(ma_forecaster, mtr_test)

    brt_pers_metrics = evaluate_baseline_on_df(pers_forecaster, brt_test)
    brt_lag_metrics = evaluate_baseline_on_df(lag_forecaster, brt_test)
    brt_ma_metrics = evaluate_baseline_on_df(ma_forecaster, brt_test)

    comb_test = pd.concat([mtr_test, brt_test], ignore_index=True)
    comb_pers_metrics = evaluate_baseline_on_df(pers_forecaster, comb_test)
    comb_lag_metrics = evaluate_baseline_on_df(lag_forecaster, comb_test)
    comb_ma_metrics = evaluate_baseline_on_df(ma_forecaster, comb_test)

    full_evaluation_results = {
        "model_version": config.model_name,
        "best_val_loss": round(float(best_val_loss), 6),
        "training_history": history,
        "evaluation_split": "test",
        "station_metrics": {
            "MTR": {
                "neural_lstm": mtr_neural_test_metrics,
                "persistence": mtr_pers_metrics,
                "seasonal_24h_lag": mtr_lag_metrics,
                "moving_average": mtr_ma_metrics,
            },
            "BRT": {
                "neural_lstm": brt_neural_test_metrics,
                "persistence": brt_pers_metrics,
                "seasonal_24h_lag": brt_lag_metrics,
                "moving_average": brt_ma_metrics,
            },
            "COMBINED": {
                "neural_lstm": comb_neural_test_metrics,
                "persistence": comb_pers_metrics,
                "seasonal_24h_lag": comb_lag_metrics,
                "moving_average": comb_ma_metrics,
            },
        },
    }

    metrics_json_path = results_dir / "baseline_metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(full_evaluation_results, f, indent=2)
    logger.info(f"Saved evaluation metrics summary to {metrics_json_path}")

    return full_evaluation_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Energy Forecasting Neural Baseline")
    parser.add_argument("--epochs", type=int, default=40, help="Max training epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    cfg = EnergyModelConfig(
        max_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
    )
    train_energy_model(config=cfg)
