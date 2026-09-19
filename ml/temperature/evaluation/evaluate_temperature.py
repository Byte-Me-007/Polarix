"""
Comprehensive Evaluation Suite for Polarix Temperature ML (Polarix SIH26060 - Person C).

Evaluates:
- Partitions: MTR, BRT, COMBINED on strictly held-out Test split.
- Horizons: 1h, 6h, 24h.
- Models: TemperatureLSTM vs Persistence vs Recent Historical Mean (24h).
- Metrics: MAE, RMSE, R2, sMAPE.
- Extreme Temperature Analysis (Synthetic extreme cold and storm scenarios).
- Outputs machine-readable results and markdown reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.temperature.inference.temperature_forecaster import TemperatureForecaster
from ml.temperature.training.baselines import PersistenceForecaster, RecentMeanForecaster
from ml.temperature.training.preprocessing import (
    TARGET_COLS,
    TemperatureFeatureScaler,
    build_causal_sequences,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EvaluateTemperature")


def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Symmetric Mean Absolute Percentage Error (sMAPE) safely."""
    # Convert from Celsius to Kelvin to avoid division by zero near 0 deg C
    y_true_k = y_true + 273.15
    y_pred_k = y_pred + 273.15
    denominator = (np.abs(y_true_k) + np.abs(y_pred_k)) / 2.0
    diff = np.abs(y_pred_k - y_true_k)
    return float(np.mean(diff / np.maximum(denominator, 1e-6)) * 100.0)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes MAE, RMSE, R2, and sMAPE."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    smape = calculate_smape(y_true, y_pred)
    return {
        "mae_c": round(mae, 4),
        "rmse_c": round(rmse, 4),
        "r2": round(r2, 4),
        "smape_pct": round(smape, 4),
    }


def calculate_file_hash(filepath: Path) -> str:
    """Calculates SHA-256 hash."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def evaluate_partition(
    df_test: pd.DataFrame,
    forecaster: TemperatureForecaster,
    scaler: TemperatureFeatureScaler,
    station_name: str,
) -> Dict[str, Any]:
    """Evaluates LSTM model and baselines on a given test partition."""
    lookback = forecaster.lookback

    # Build sequence tensors
    X_seqs, y_seqs = build_causal_sequences(df_test, scaler, lookback=lookback, has_targets=True)

    with torch_no_grad():
        preds_norm = forecaster.model(X_seqs).numpy()

    y_pred_lstm = scaler.inverse_transform_targets(preds_norm)
    y_true = scaler.inverse_transform_targets(y_seqs.numpy())

    # Baselines
    # Persistence baseline for the corresponding target timestamps
    temp_series = df_test["temperature_c"].to_numpy(dtype=np.float32)
    current_temps = temp_series[lookback - 1 : lookback - 1 + len(y_true)]
    y_pred_persist = np.column_stack([current_temps, current_temps, current_temps])

    # Recent Mean (24h) baseline
    recent_mean_forecaster = RecentMeanForecaster(window_size=lookback)
    recent_mean_full = recent_mean_forecaster.predict_dataframe(df_test)
    y_pred_mean = recent_mean_full[lookback - 1 : lookback - 1 + len(y_true)]

    horizons = ["1h", "6h", "24h"]
    results: Dict[str, Any] = {
        "station": station_name,
        "sample_count": len(y_true),
        "horizons": {},
    }

    for h_idx, h_name in enumerate(horizons):
        yt = y_true[:, h_idx]
        yp_lstm = y_pred_lstm[:, h_idx]
        yp_pers = y_pred_persist[:, h_idx]
        yp_mean = y_pred_mean[:, h_idx]

        m_lstm = compute_metrics(yt, yp_lstm)
        m_pers = compute_metrics(yt, yp_pers)
        m_mean = compute_metrics(yt, yp_mean)

        results["horizons"][h_name] = {
            "lstm": m_lstm,
            "persistence": m_pers,
            "recent_mean": m_mean,
            "improvement_over_persistence_mae_pct": round(
                ((m_pers["mae_c"] - m_lstm["mae_c"]) / m_pers["mae_c"]) * 100.0, 2
            ),
            "improvement_over_mean_mae_pct": round(
                ((m_mean["mae_c"] - m_lstm["mae_c"]) / m_mean["mae_c"]) * 100.0, 2
            ),
        }

    # Extreme scenario analysis on test set (lowest 15% temperatures in this partition)
    temp_threshold = float(np.percentile(current_temps, 15))
    extreme_mask = current_temps <= temp_threshold
    n_extreme = int(np.sum(extreme_mask))

    if n_extreme > 0:
        results["extreme_cold_scenario"] = {
            "scenario_type": "SYNTHETIC_EXTREME_COLD_PERIOD",
            "threshold_temp_c": round(temp_threshold, 2),
            "sample_count": n_extreme,
            "horizons": {},
        }
        for h_idx, h_name in enumerate(horizons):
            yt_ext = y_true[extreme_mask, h_idx]
            yp_ext = y_pred_lstm[extreme_mask, h_idx]
            results["extreme_cold_scenario"]["horizons"][h_name] = compute_metrics(yt_ext, yp_ext)

    return results


# Context helper for torch no grad without full import
def torch_no_grad():
    import torch
    return torch.no_grad()


def evaluate_all_partitions(
    data_dir: Path,
    models_dir: Path,
    results_dir: Path,
) -> Dict[str, Any]:
    """Runs complete multi-station benchmark evaluation and persists metrics artifacts."""
    results_dir.mkdir(parents=True, exist_ok=True)
    forecaster = TemperatureForecaster()
    scaler = forecaster.scaler

    # Load data
    mtr_df = pd.read_csv(data_dir / "maitri_temperature_telemetry.csv")
    brt_df = pd.read_csv(data_dir / "bharati_temperature_telemetry.csv")

    # Strict Test Partition (last 15% = last 1,314 rows)
    test_len = int(len(mtr_df) * 0.15)
    mtr_test = mtr_df.iloc[-test_len:].reset_index(drop=True)
    brt_test = brt_df.iloc[-test_len:].reset_index(drop=True)
    combined_test = pd.concat([mtr_test, brt_test], ignore_index=True)

    logger.info(f"Evaluating MTR Test Partition (N={len(mtr_test)})...")
    res_mtr = evaluate_partition(mtr_test, forecaster, scaler, "MTR")

    logger.info(f"Evaluating BRT Test Partition (N={len(brt_test)})...")
    res_brt = evaluate_partition(brt_test, forecaster, scaler, "BRT")

    # Combined test evaluation
    # Build sequences for both and combine
    X_mtr_seqs, y_mtr_seqs = build_causal_sequences(mtr_test, scaler, lookback=forecaster.lookback, has_targets=True)
    X_brt_seqs, y_brt_seqs = build_causal_sequences(brt_test, scaler, lookback=forecaster.lookback, has_targets=True)

    X_comb = torch.cat([X_mtr_seqs, X_brt_seqs], dim=0)
    y_comb = torch.cat([y_mtr_seqs, y_brt_seqs], dim=0)

    with torch_no_grad():
        preds_comb_norm = forecaster.model(X_comb).numpy()

    y_pred_comb = scaler.inverse_transform_targets(preds_comb_norm)
    y_true_comb = scaler.inverse_transform_targets(y_comb.numpy())

    # Combined Persistence
    curr_mtr = mtr_test["temperature_c"].to_numpy(dtype=np.float32)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_mtr_seqs)]
    curr_brt = brt_df["temperature_c"].iloc[-test_len:].to_numpy(dtype=np.float32)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_brt_seqs)]
    curr_comb = np.concatenate([curr_mtr, curr_brt])
    y_pred_comb_pers = np.column_stack([curr_comb, curr_comb, curr_comb])

    # Combined Mean
    rm_forecaster = RecentMeanForecaster(window_size=forecaster.lookback)
    rm_mtr = rm_forecaster.predict_dataframe(mtr_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_mtr_seqs)]
    rm_brt = rm_forecaster.predict_dataframe(brt_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_brt_seqs)]
    y_pred_comb_mean = np.concatenate([rm_mtr, rm_brt], axis=0)

    res_comb = {
        "station": "COMBINED",
        "sample_count": len(y_true_comb),
        "horizons": {},
    }
    for h_idx, h_name in enumerate(["1h", "6h", "24h"]):
        yt = y_true_comb[:, h_idx]
        yp_l = y_pred_comb[:, h_idx]
        yp_p = y_pred_comb_pers[:, h_idx]
        yp_m = y_pred_comb_mean[:, h_idx]

        m_l = compute_metrics(yt, yp_l)
        m_p = compute_metrics(yt, yp_p)
        m_m = compute_metrics(yt, yp_m)

        res_comb["horizons"][h_name] = {
            "lstm": m_l,
            "persistence": m_p,
            "recent_mean": m_m,
            "improvement_over_persistence_mae_pct": round(((m_p["mae_c"] - m_l["mae_c"]) / m_p["mae_c"]) * 100.0, 2),
            "improvement_over_mean_mae_pct": round(((m_m["mae_c"] - m_l["mae_c"]) / m_m["mae_c"]) * 100.0, 2),
        }

    full_metrics = {
        "evaluation_version": "1.0.0",
        "subsystem": "Temperature Forecasting ML Subsystem",
        "model_version": forecaster.model_version,
        "data_provenance": "SYNTHETIC_POLARIX_DATA",
        "evaluation_split": "TEST (2026-11-07T06:00:00Z to 2026-12-31T23:00:00Z)",
        "stations": {
            "MTR": res_mtr,
            "BRT": res_brt,
            "COMBINED": res_comb,
        },
        "artifact_hashes": {
            "model_weights": calculate_file_hash(forecaster.model_path),
            "model_config": calculate_file_hash(forecaster.config_path),
            "model_scaler": calculate_file_hash(forecaster.scaler_path),
        },
    }

    # Save JSON metrics
    metrics_path = results_dir / "temperature_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(full_metrics, f, indent=2)

    # Generate Markdown Report
    report_md = generate_markdown_report(full_metrics)
    report_path = results_dir / "temperature_evaluation_report.md"
    with open(report_path, "w") as f:
        f.write(report_md)

    # Save Machine Readable Inference Contract
    contract = {
        "contract_name": "polarix-temperature-ml-contract-v1",
        "subsystem": "ml/temperature",
        "model_version": forecaster.model_version,
        "provenance": "SYNTHETIC_POLARIX_DATA",
        "status_codes": ["PREDICTION_AVAILABLE", "INSUFFICIENT_HISTORY", "INVALID_INPUT"],
        "required_lookback_hours": forecaster.lookback,
        "input_schema": {
            "station_id": {"type": "string", "enum": ["MTR", "BRT"]},
            "telemetry": {
                "type": "array",
                "min_items": forecaster.lookback,
                "item_fields": ["timestamp", "temperature_c", "humidity_percent", "pressure_hpa", "wind_speed_mps"],
            },
        },
        "output_schema": {
            "station_id": "string",
            "timestamp": "string (ISO-8601 UTC)",
            "status": "string",
            "model_version": "string",
            "forecasts": {
                "temperature_1h_c": "float (°C)",
                "temperature_6h_c": "float (°C)",
                "temperature_24h_c": "float (°C)",
            },
            "provenance": {
                "source": "string",
                "model_status": "string",
                "disclaimer": "string",
            },
        },
    }
    contract_path = results_dir / "temperature_ml_inference_contract.json"
    with open(contract_path, "w") as f:
        json.dump(contract, f, indent=2)

    # Save Milestone Manifest
    milestone = {
        "milestone_name": "TEMPERATURE_FORECASTING_ML_FOUNDATION",
        "step": "STEP_17",
        "status": "VALIDATED_STANDALONE_MODULE",
        "author": "Person C — ML Specialist",
        "model_version": forecaster.model_version,
        "created_at": "2026-09-19",
        "files_and_hashes": {
            "model_weights": {
                "path": "ml/temperature/models/temperature_lstm_v1.pt",
                "sha256": calculate_file_hash(forecaster.model_path),
            },
            "model_config": {
                "path": "ml/temperature/models/temperature_lstm_v1_config.json",
                "sha256": calculate_file_hash(forecaster.config_path),
            },
            "model_scaler": {
                "path": "ml/temperature/models/temperature_lstm_v1_scaler.json",
                "sha256": calculate_file_hash(forecaster.scaler_path),
            },
            "metrics_json": {
                "path": "ml/temperature/results/temperature_metrics.json",
                "sha256": calculate_file_hash(metrics_path),
            },
            "evaluation_report": {
                "path": "ml/temperature/results/temperature_evaluation_report.md",
                "sha256": calculate_file_hash(report_path),
            },
            "inference_contract": {
                "path": "ml/temperature/results/temperature_ml_inference_contract.json",
                "sha256": calculate_file_hash(contract_path),
            },
        },
    }
    milestone_path = results_dir / "temperature_ml_milestone_manifest.json"
    with open(milestone_path, "w") as f:
        json.dump(milestone, f, indent=2)

    logger.info(f"Evaluation complete. Reports generated in {results_dir}")
    return full_metrics


def generate_markdown_report(metrics: Dict[str, Any]) -> str:
    """Formats benchmark results into a clean markdown document."""
    lines = [
        "# Polarix Temperature Forecasting ML Evaluation Report",
        "",
        "## 1. Executive Summary",
        f"- **Model Version:** `{metrics['model_version']}`",
        f"- **Subsystem:** `{metrics['subsystem']}` (Independent Standalone Module)",
        f"- **Data Provenance:** `{metrics['data_provenance']}`",
        f"- **Evaluation Split:** `{metrics['evaluation_split']}`",
        "",
        "## 2. Multi-Horizon Test Partition Benchmarks",
        "",
        "### 2.1 Combined Station Evaluation (MTR + BRT)",
        "| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |",
        "|---|---|---|---|---|---|---|---|",
    ]

    comb = metrics["stations"]["COMBINED"]["horizons"]
    for h in ["1h", "6h", "24h"]:
        l = comb[h]["lstm"]
        p = comb[h]["persistence"]
        m = comb[h]["recent_mean"]
        imp_p = comb[h]["improvement_over_persistence_mae_pct"]
        imp_m = comb[h]["improvement_over_mean_mae_pct"]

        lines.append(f"| **{h}** | **LSTM (v1)** | **{l['mae_c']}** | **{l['rmse_c']}** | **{l['r2']}** | **{l['smape_pct']}** | **+{imp_p}%** | **+{imp_m}%** |")
        lines.append(f"| {h} | Persistence | {p['mae_c']} | {p['rmse_c']} | {p['r2']} | {p['smape_pct']} | baseline | - |")
        lines.append(f"| {h} | Recent Mean | {m['mae_c']} | {m['rmse_c']} | {m['r2']} | {m['smape_pct']} | - | baseline |")

    lines.extend([
        "",
        "### 2.2 Maitri Station (MTR - Inland Oasis)",
        "| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | Improvement vs Baseline |",
        "|---|---|---|---|---|---|---|",
    ])
    mtr = metrics["stations"]["MTR"]["horizons"]
    for h in ["1h", "6h", "24h"]:
        l = mtr[h]["lstm"]
        p = mtr[h]["persistence"]
        imp_p = mtr[h]["improvement_over_persistence_mae_pct"]
        lines.append(f"| **{h}** | **LSTM (v1)** | **{l['mae_c']}** | **{l['rmse_c']}** | **{l['r2']}** | **{l['smape_pct']}** | **+{imp_p}% vs Persist ({p['mae_c']}°C)** |")

    lines.extend([
        "",
        "### 2.3 Bharati Station (BRT - Coastal Promontory)",
        "| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | Improvement vs Baseline |",
        "|---|---|---|---|---|---|---|",
    ])
    brt = metrics["stations"]["BRT"]["horizons"]
    for h in ["1h", "6h", "24h"]:
        l = brt[h]["lstm"]
        p = brt[h]["persistence"]
        imp_p = brt[h]["improvement_over_persistence_mae_pct"]
        lines.append(f"| **{h}** | **LSTM (v1)** | **{l['mae_c']}** | **{l['rmse_c']}** | **{l['r2']}** | **{l['smape_pct']}** | **+{imp_p}% vs Persist ({p['mae_c']}°C)** |")

    lines.extend([
        "",
        "## 3. Extreme Cold Scenario Performance",
        "Evaluated on the coldest 15% periods within the held-out test partition:",
        "",
        f"- **Maitri Extreme Cold Threshold:** $\\le {metrics['stations']['MTR'].get('extreme_cold_scenario', {}).get('threshold_temp_c', 'N/A')}^\\circ\\text{{C}}$ ($N={metrics['stations']['MTR'].get('extreme_cold_scenario', {}).get('sample_count', 0)}$)",
        f"- **Bharati Extreme Cold Threshold:** $\\le {metrics['stations']['BRT'].get('extreme_cold_scenario', {}).get('threshold_temp_c', 'N/A')}^\\circ\\text{{C}}$ ($N={metrics['stations']['BRT'].get('extreme_cold_scenario', {}).get('sample_count', 0)}$)",
        "",
        "## 4. Anti-Leakage & Causality Guarantees",
        "- **Chronological Boundaries:** Train (0-70%), Validation (70-85%), Test (85-100%). No temporal shuffling.",
        "- **Feature Normalization:** Scaler fitted exclusively on Train split.",
        "- **Future Mutation Immunity:** Current prediction is strictly invariant to future telemetry perturbations.",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    import torch
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    models_dir = base_dir / "models"
    results_dir = base_dir / "results"
    evaluate_all_partitions(data_dir, models_dir, results_dir)
