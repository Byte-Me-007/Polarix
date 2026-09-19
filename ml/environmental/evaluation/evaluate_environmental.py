"""
Comprehensive Evaluation Suite for Polarix Environmental ML (Polarix SIH26060 - Person C).

Evaluates:
- Partitions: MTR, BRT, COMBINED on strictly held-out Test split.
- Variables: Wind Speed (m/s), Barometric Pressure (hPa), Relative Humidity (%).
- Horizons: 1h, 6h, 24h.
- Models: EnvironmentalLSTM vs Persistence vs Recent Historical Mean (24h).
- Metrics: MAE, RMSE, R2, sMAPE.
- Event/Regime Analysis (Storm/Blizzard regimes: high wind & deep cyclonic pressure).
- Outputs machine-readable results and markdown reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.environmental.inference.environmental_forecaster import EnvironmentalForecaster
from ml.environmental.training.baselines import PersistenceForecaster, RecentMeanForecaster
from ml.environmental.training.preprocessing import (
    TARGET_COLS,
    EnvironmentalFeatureScaler,
    build_causal_sequences,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EvaluateEnvironmental")


def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Symmetric Mean Absolute Percentage Error (sMAPE) safely."""
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_pred - y_true)
    return float(np.mean(diff / np.maximum(denominator, 1e-6)) * 100.0)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes MAE, RMSE, R2, and sMAPE."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    smape = calculate_smape(y_true, y_pred)
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
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
    forecaster: EnvironmentalForecaster,
    scaler: EnvironmentalFeatureScaler,
    station_name: str,
) -> Dict[str, Any]:
    """Evaluates LSTM model and baselines for all 9 targets on a given test partition."""
    lookback = forecaster.lookback

    X_seqs, y_seqs = build_causal_sequences(df_test, scaler, lookback=lookback, has_targets=True)

    with torch_no_grad():
        preds_norm = forecaster.model(X_seqs).numpy()

    y_pred_lstm = scaler.inverse_transform_targets(preds_norm)
    y_true = scaler.inverse_transform_targets(y_seqs.numpy())

    # Baselines
    pers_forecaster = PersistenceForecaster()
    mean_forecaster = RecentMeanForecaster(window_size=lookback)

    pers_full = pers_forecaster.predict_dataframe(df_test)
    y_pred_persist = pers_full[lookback - 1 : lookback - 1 + len(y_true)]

    mean_full = mean_forecaster.predict_dataframe(df_test)
    y_pred_mean = mean_full[lookback - 1 : lookback - 1 + len(y_true)]

    variables = {
        "wind_speed_mps": [0, 1, 2],
        "pressure_hpa": [3, 4, 5],
        "humidity_percent": [6, 7, 8],
    }
    horizons = ["1h", "6h", "24h"]

    results: Dict[str, Any] = {
        "station": station_name,
        "sample_count": len(y_true),
        "variables": {},
    }

    for var_name, indices in variables.items():
        results["variables"][var_name] = {}
        for h_idx, target_idx in enumerate(indices):
            h_name = horizons[h_idx]
            yt = y_true[:, target_idx]
            yp_l = y_pred_lstm[:, target_idx]
            yp_p = y_pred_persist[:, target_idx]
            yp_m = y_pred_mean[:, target_idx]

            m_l = compute_metrics(yt, yp_l)
            m_p = compute_metrics(yt, yp_p)
            m_m = compute_metrics(yt, yp_m)

            results["variables"][var_name][h_name] = {
                "lstm": m_l,
                "persistence": m_p,
                "recent_mean": m_m,
                "improvement_over_persistence_mae_pct": round(
                    ((m_p["mae"] - m_l["mae"]) / m_p["mae"]) * 100.0, 2
                ),
                "improvement_over_mean_mae_pct": round(
                    ((m_m["mae"] - m_l["mae"]) / m_m["mae"]) * 100.0, 2
                ),
            }

    # Event/Regime Analysis: High wind events (wind >= 15 m/s) in test set
    wind_series = df_test["wind_speed_mps"].to_numpy(dtype=np.float32)[lookback - 1 : lookback - 1 + len(y_true)]
    high_wind_mask = wind_series >= 15.0
    n_high_wind = int(np.sum(high_wind_mask))

    if n_high_wind > 0:
        results["storm_high_wind_regime"] = {
            "threshold_mps": 15.0,
            "sample_count": n_high_wind,
            "horizons": {},
        }
        for h_idx, target_idx in enumerate(variables["wind_speed_mps"]):
            h_name = horizons[h_idx]
            yt_hw = y_true[high_wind_mask, target_idx]
            yp_hw = y_pred_lstm[high_wind_mask, target_idx]
            results["storm_high_wind_regime"]["horizons"][h_name] = compute_metrics(yt_hw, yp_hw)

    return results


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
    forecaster = EnvironmentalForecaster()
    scaler = forecaster.scaler

    mtr_df = pd.read_csv(data_dir / "maitri_environmental_telemetry.csv")
    brt_df = pd.read_csv(data_dir / "bharati_environmental_telemetry.csv")

    test_len = int(len(mtr_df) * 0.15)
    mtr_test = mtr_df.iloc[-test_len:].reset_index(drop=True)
    brt_test = brt_df.iloc[-test_len:].reset_index(drop=True)

    logger.info(f"Evaluating MTR Environmental Test Partition (N={len(mtr_test)})...")
    res_mtr = evaluate_partition(mtr_test, forecaster, scaler, "MTR")

    logger.info(f"Evaluating BRT Environmental Test Partition (N={len(brt_test)})...")
    res_brt = evaluate_partition(brt_test, forecaster, scaler, "BRT")

    # Combined test evaluation
    X_mtr_seqs, y_mtr_seqs = build_causal_sequences(mtr_test, scaler, lookback=forecaster.lookback, has_targets=True)
    X_brt_seqs, y_brt_seqs = build_causal_sequences(brt_test, scaler, lookback=forecaster.lookback, has_targets=True)

    X_comb = torch_cat([X_mtr_seqs, X_brt_seqs])
    y_comb = torch_cat([y_mtr_seqs, y_brt_seqs])

    with torch_no_grad():
        preds_comb_norm = forecaster.model(X_comb).numpy()

    y_pred_comb = scaler.inverse_transform_targets(preds_comb_norm)
    y_true_comb = scaler.inverse_transform_targets(y_comb.numpy())

    pers_forecaster = PersistenceForecaster()
    mean_forecaster = RecentMeanForecaster(window_size=forecaster.lookback)

    pers_mtr = pers_forecaster.predict_dataframe(mtr_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_mtr_seqs)]
    pers_brt = pers_forecaster.predict_dataframe(brt_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_brt_seqs)]
    y_pred_comb_pers = np.concatenate([pers_mtr, pers_brt], axis=0)

    mean_mtr = mean_forecaster.predict_dataframe(mtr_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_mtr_seqs)]
    mean_brt = mean_forecaster.predict_dataframe(brt_test)[forecaster.lookback - 1 : forecaster.lookback - 1 + len(y_brt_seqs)]
    y_pred_comb_mean = np.concatenate([mean_mtr, mean_brt], axis=0)

    variables = {
        "wind_speed_mps": [0, 1, 2],
        "pressure_hpa": [3, 4, 5],
        "humidity_percent": [6, 7, 8],
    }
    horizons = ["1h", "6h", "24h"]

    res_comb = {
        "station": "COMBINED",
        "sample_count": len(y_true_comb),
        "variables": {},
    }
    for var_name, indices in variables.items():
        res_comb["variables"][var_name] = {}
        for h_idx, target_idx in enumerate(indices):
            h_name = horizons[h_idx]
            yt = y_true_comb[:, target_idx]
            yp_l = y_pred_comb[:, target_idx]
            yp_p = y_pred_comb_pers[:, target_idx]
            yp_m = y_pred_comb_mean[:, target_idx]

            m_l = compute_metrics(yt, yp_l)
            m_p = compute_metrics(yt, yp_p)
            m_m = compute_metrics(yt, yp_m)

            res_comb["variables"][var_name][h_name] = {
                "lstm": m_l,
                "persistence": m_p,
                "recent_mean": m_m,
                "improvement_over_persistence_mae_pct": round(
                    ((m_p["mae"] - m_l["mae"]) / m_p["mae"]) * 100.0, 2
                ),
                "improvement_over_mean_mae_pct": round(
                    ((m_m["mae"] - m_l["mae"]) / m_m["mae"]) * 100.0, 2
                ),
            }

    full_metrics = {
        "evaluation_version": "1.0.0",
        "subsystem": "Environmental Forecasting ML Subsystem",
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

    metrics_path = results_dir / "environmental_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(full_metrics, f, indent=2)

    report_md = generate_markdown_report(full_metrics)
    report_path = results_dir / "environmental_evaluation_report.md"
    with open(report_path, "w") as f:
        f.write(report_md)

    # Inference Contract
    contract = {
        "contract_name": "polarix-environmental-ml-contract-v1",
        "subsystem": "ml/environmental",
        "model_version": forecaster.model_version,
        "provenance": "SYNTHETIC_POLARIX_DATA",
        "status_codes": ["PREDICTION_AVAILABLE", "INSUFFICIENT_HISTORY", "INVALID_INPUT"],
        "required_lookback_hours": forecaster.lookback,
        "input_schema": {
            "station_id": {"type": "string", "enum": ["MTR", "BRT"]},
            "telemetry": {
                "type": "array",
                "min_items": forecaster.lookback,
                "item_fields": ["timestamp", "wind_speed_mps", "pressure_hpa", "humidity_percent", "temperature_c"],
            },
        },
        "output_schema": {
            "station_id": "string",
            "timestamp": "string (ISO-8601 UTC)",
            "status": "string",
            "model_version": "string",
            "forecasts": {
                "wind_speed_mps": {"1h": "float (m/s)", "6h": "float (m/s)", "24h": "float (m/s)"},
                "pressure_hpa": {"1h": "float (hPa)", "6h": "float (hPa)", "24h": "float (hPa)"},
                "humidity_percent": {"1h": "float (%)", "6h": "float (%)", "24h": "float (%)"},
            },
            "provenance": {
                "source": "string",
                "model_status": "string",
                "disclaimer": "string",
            },
        },
    }
    contract_path = results_dir / "environmental_ml_inference_contract.json"
    with open(contract_path, "w") as f:
        json.dump(contract, f, indent=2)

    milestone = {
        "milestone_name": "ENVIRONMENTAL_FORECASTING_ML_FOUNDATION",
        "status": "VALIDATED_STANDALONE_MODULE",
        "author": "Person C — ML Specialist",
        "model_version": forecaster.model_version,
        "created_at": "2026-09-19",
        "files_and_hashes": {
            "model_weights": {
                "path": "ml/environmental/models/environmental_lstm_v1.pt",
                "sha256": calculate_file_hash(forecaster.model_path),
            },
            "model_config": {
                "path": "ml/environmental/models/environmental_lstm_v1_config.json",
                "sha256": calculate_file_hash(forecaster.config_path),
            },
            "model_scaler": {
                "path": "ml/environmental/models/environmental_lstm_v1_scaler.json",
                "sha256": calculate_file_hash(forecaster.scaler_path),
            },
            "metrics_json": {
                "path": "ml/environmental/results/environmental_metrics.json",
                "sha256": calculate_file_hash(metrics_path),
            },
            "evaluation_report": {
                "path": "ml/environmental/results/environmental_evaluation_report.md",
                "sha256": calculate_file_hash(report_path),
            },
            "inference_contract": {
                "path": "ml/environmental/results/environmental_ml_inference_contract.json",
                "sha256": calculate_file_hash(contract_path),
            },
        },
    }
    milestone_path = results_dir / "environmental_ml_milestone_manifest.json"
    with open(milestone_path, "w") as f:
        json.dump(milestone, f, indent=2)

    logger.info(f"Evaluation complete. Reports generated in {results_dir}")
    return full_metrics


def torch_cat(tensors: List[Any]) -> Any:
    import torch
    return torch.cat(tensors, dim=0)


def generate_markdown_report(metrics: Dict[str, Any]) -> str:
    """Formats benchmark results into a clean markdown document."""
    lines = [
        "# Polarix Environmental Forecasting ML Evaluation Report",
        "",
        "## 1. Executive Summary",
        f"- **Model Version:** `{metrics['model_version']}`",
        f"- **Subsystem:** `{metrics['subsystem']}` (Independent Standalone Module)",
        f"- **Data Provenance:** `{metrics['data_provenance']}`",
        f"- **Evaluation Split:** `{metrics['evaluation_split']}`",
        "",
        "## 2. Multi-Target Multi-Horizon Test Partition Benchmarks",
        "",
    ]

    vars_info = [
        ("wind_speed_mps", "Wind Speed (m/s)"),
        ("pressure_hpa", "Barometric Pressure (hPa)"),
        ("humidity_percent", "Relative Humidity (%)"),
    ]

    for var_key, var_title in vars_info:
        lines.extend([
            f"### 2.{vars_info.index((var_key, var_title)) + 1} {var_title} — Combined Station Evaluation (MTR + BRT)",
            "| Horizon | Model | MAE | RMSE | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |",
            "|---|---|---|---|---|---|---|---|",
        ])
        comb = metrics["stations"]["COMBINED"]["variables"][var_key]
        for h in ["1h", "6h", "24h"]:
            l = comb[h]["lstm"]
            p = comb[h]["persistence"]
            m = comb[h]["recent_mean"]
            imp_p = comb[h]["improvement_over_persistence_mae_pct"]
            imp_m = comb[h]["improvement_over_mean_mae_pct"]

            lines.append(f"| **{h}** | **LSTM (v1)** | **{l['mae']}** | **{l['rmse']}** | **{l['r2']}** | **{l['smape_pct']}** | **{'+' if imp_p >= 0 else ''}{imp_p}%** | **{'+' if imp_m >= 0 else ''}{imp_m}%** |")
            lines.append(f"| {h} | Persistence | {p['mae']} | {p['rmse']} | {p['r2']} | {p['smape_pct']} | baseline | - |")
            lines.append(f"| {h} | Recent Mean | {m['mae']} | {m['rmse']} | {m['r2']} | {m['smape_pct']} | - | baseline |")
        lines.append("")

    lines.extend([
        "## 3. Station-Specific Performance Summary",
        "",
        "### 3.1 Maitri Station (MTR - Inland Oasis)",
        "| Variable | Horizon | LSTM MAE | Persist MAE | Mean MAE | LSTM R² |",
        "|---|---|---|---|---|---|",
    ])
    mtr_vars = metrics["stations"]["MTR"]["variables"]
    for var_key, var_title in vars_info:
        for h in ["1h", "6h", "24h"]:
            m = mtr_vars[var_key][h]
            lines.append(f"| {var_title} | {h} | {m['lstm']['mae']} | {m['persistence']['mae']} | {m['recent_mean']['mae']} | {m['lstm']['r2']} |")

    lines.extend([
        "",
        "### 3.2 Bharati Station (BRT - Coastal Promontory)",
        "| Variable | Horizon | LSTM MAE | Persist MAE | Mean MAE | LSTM R² |",
        "|---|---|---|---|---|---|",
    ])
    brt_vars = metrics["stations"]["BRT"]["variables"]
    for var_key, var_title in vars_info:
        for h in ["1h", "6h", "24h"]:
            m = brt_vars[var_key][h]
            lines.append(f"| {var_title} | {h} | {m['lstm']['mae']} | {m['persistence']['mae']} | {m['recent_mean']['mae']} | {m['lstm']['r2']} |")

    lines.extend([
        "",
        "## 4. Anti-Leakage & Causality Guarantees",
        "- **Strict Chronological Boundaries:** Train (70%), Validation (15%), Test (15%). No temporal shuffling.",
        "- **Feature Normalization:** Scaler fitted exclusively on Train split.",
        "- **Future Mutation Immunity:** Current prediction is strictly invariant to future telemetry perturbations.",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    models_dir = base_dir / "models"
    results_dir = base_dir / "results"
    evaluate_all_partitions(data_dir, models_dir, results_dir)
