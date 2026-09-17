#!/usr/bin/env python3
"""
Threshold Selection & Test Evaluation Pipeline for Maitri LSTM Autoencoder (SIH26060).

Methodology:
1. Select optimal anomaly threshold exclusively on VALIDATION reconstruction errors.
2. Criterion: Maximize validation F1-score (tie-breaking: higher recall, higher precision, lower threshold).
3. Freeze the selected threshold and evaluate on untouched TEST split.
4. Compute comprehensive test metrics and per-anomaly-type performance breakdown.
5. Export search history, threshold JSON, test metrics JSON, prediction CSV, and evaluation plot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MODEL_VERSION = "lstm-ae-v1"


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Calculate binary classification metrics."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "total": total,
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def generate_candidate_thresholds(
    errors: np.ndarray, num_quantiles: int = 200, num_linear: int = 200
) -> np.ndarray:
    """
    Generate candidate threshold grid from error distribution.
    Combines quantile-based steps with linearly spaced values.
    """
    clean_errors = errors[~np.isnan(errors) & ~np.isinf(errors)]
    if len(clean_errors) == 0:
        return np.array([1.0], dtype=float)

    q_grid = np.linspace(0.001, 0.999, num=num_quantiles)
    quantiles = np.quantile(clean_errors, q_grid)

    min_val, max_val = float(np.min(clean_errors)), float(np.max(clean_errors))
    linear_grid = np.linspace(min_val, max_val, num=num_linear)

    candidates = np.unique(np.concatenate([quantiles, linear_grid]))
    candidates.sort()
    return candidates


def search_optimal_threshold(
    val_df: pd.DataFrame, num_candidates: int = 300
) -> Tuple[float, Dict[str, Any], pd.DataFrame]:
    """
    Search for the optimal reconstruction error threshold on validation data.

    Returns:
    --------
    best_threshold : float
    best_metrics : Dict[str, Any]
    search_df : pd.DataFrame
    """
    errors = val_df["reconstruction_error"].to_numpy(dtype=float)
    y_true = val_df["is_anomaly"].to_numpy(dtype=int)

    candidates = generate_candidate_thresholds(
        errors, num_quantiles=num_candidates // 2, num_linear=num_candidates // 2
    )

    records = []
    best_key = (-1.0, -1.0, -1.0, float("inf"))
    best_threshold = float(candidates[0])
    best_metrics: Dict[str, Any] = {}

    for thresh in candidates:
        y_pred = (errors > thresh).astype(int)
        m = calculate_metrics(y_true, y_pred)
        m["threshold"] = float(thresh)
        records.append(m)

        # Tie-breaking key: (F1, Recall, Precision, -Threshold)
        current_key = (m["f1"], m["recall"], m["precision"], -thresh)
        if current_key > best_key:
            best_key = current_key
            best_threshold = float(thresh)
            best_metrics = m

    search_df = pd.DataFrame(records)
    return best_threshold, best_metrics, search_df


def evaluate_test_set(
    test_df: pd.DataFrame, threshold: float
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Evaluate frozen threshold on untouched test set.
    """
    errors = test_df["reconstruction_error"].to_numpy(dtype=float)
    y_true = test_df["is_anomaly"].to_numpy(dtype=int)
    y_pred = (errors > threshold).astype(int)

    metrics = calculate_metrics(y_true, y_pred)
    metrics["threshold_used"] = threshold
    metrics["model_version"] = MODEL_VERSION
    metrics["test_sample_count"] = len(test_df)

    # Prediction dataframe
    pred_df = test_df.copy()
    pred_df["predicted_status"] = np.where(y_pred == 1, "ANOMALY", "NORMAL")

    # If any rows had null target_value or missing data tag, preserve MISSING_DATA
    if "quality" in pred_df.columns:
        pred_df.loc[pred_df["quality"] == "MISSING", "predicted_status"] = "MISSING_DATA"

    # Per-anomaly-type metrics breakdown
    per_type = {}
    for atype, group in pred_df.groupby("anomaly_type"):
        g_true = group["is_anomaly"].to_numpy(dtype=int)
        g_pred = (group["reconstruction_error"].to_numpy(dtype=float) > threshold).astype(int)
        type_total = len(group)
        type_detected = int(np.sum(g_pred == 1))

        if (g_true == 1).all():
            recall_type = type_detected / type_total if type_total > 0 else 0.0
            per_type[atype] = {
                "total_instances": type_total,
                "detected_anomalies": type_detected,
                "detection_rate": round(float(recall_type), 4),
            }
        elif (g_true == 0).all():
            fp_type = type_detected
            fp_rate = fp_type / type_total if type_total > 0 else 0.0
            per_type[atype] = {
                "total_instances": type_total,
                "false_alarms": fp_type,
                "false_positive_rate": round(float(fp_rate), 4),
            }
        else:
            m_type = calculate_metrics(g_true, g_pred)
            per_type[atype] = {
                "total_instances": type_total,
                "precision": round(m_type["precision"], 4),
                "recall": round(m_type["recall"], 4),
                "f1": round(m_type["f1"], 4),
            }

    metrics["per_anomaly_type"] = per_type
    return metrics, pred_df


def plot_threshold_evaluation(
    val_df: pd.DataFrame,
    threshold: float,
    output_path: Path,
) -> None:
    """Plot reconstruction error distribution and selected threshold."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    val_norm = val_df[val_df["is_anomaly"] == 0]["reconstruction_error"].to_numpy()
    val_anom = val_df[val_df["is_anomaly"] == 1]["reconstruction_error"].to_numpy()

    # Plot histograms
    bins = np.linspace(
        0,
        max(float(np.max(val_norm)), float(np.max(val_anom)) if len(val_anom) > 0 else 1.0) * 1.05,
        50,
    )
    ax.hist(
        val_norm,
        bins=bins,
        alpha=0.6,
        color="steelblue",
        label=f"Normal Validation (n={len(val_norm)})",
        density=True,
    )
    if len(val_anom) > 0:
        ax.hist(
            val_anom,
            bins=bins,
            alpha=0.6,
            color="crimson",
            label=f"Anomalous Validation (n={len(val_anom)})",
            density=True,
        )

    # Threshold line
    ax.axvline(
        threshold,
        color="darkorange",
        linestyle="--",
        linewidth=2.2,
        label=f"Selected Threshold: {threshold:.4f}",
    )

    ax.set_title(
        "Maitri LSTM Autoencoder Validation Error Distribution & Threshold",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Reconstruction Error (MSE)", fontsize=10)
    ax.set_ylabel("Density", fontsize=10)
    ax.legend(loc="upper right", frameon=True)
    ax.grid(True, alpha=0.3, linestyle=":")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close(fig)


def run_threshold_selection_pipeline(
    input_csv: str = "ml/results/lstm_reconstruction_errors.csv",
    output_dir: str = "ml/results",
) -> Dict[str, Any]:
    """Execute complete threshold search and test evaluation pipeline."""
    in_path = Path(input_csv)
    if not in_path.exists():
        raise FileNotFoundError(f"Input file '{in_path}' does not exist.")

    df = pd.read_csv(in_path)

    # Validate split names
    val_mask = df["split"].str.lower().isin(["val", "validation"])
    test_mask = df["split"].str.lower().isin(["test", "testing"])

    val_df = df[val_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)

    if len(val_df) == 0:
        raise ValueError("No validation data found in input CSV.")
    if len(test_df) == 0:
        raise ValueError("No test data found in input CSV.")

    print(f"[Polarix ML] Running threshold search on {len(val_df)} validation sequences...")
    best_threshold, val_metrics, search_df = search_optimal_threshold(val_df)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save threshold search results
    search_csv_path = out_dir / "lstm_threshold_search.csv"
    search_df.to_csv(search_csv_path, index=False)

    # Save validation threshold JSON
    threshold_json_path = out_dir / "lstm_threshold.json"
    threshold_data = {
        "model_version": MODEL_VERSION,
        "threshold": round(best_threshold, 6),
        "selection_metric": "F1-score",
        "selection_method": "Grid search over quantiles & linear space on validation split",
        "candidate_count": len(search_df),
        "selected_at_step": "Step 4 - Validation Threshold Selection",
        "validation_TP": val_metrics["TP"],
        "validation_TN": val_metrics["TN"],
        "validation_FP": val_metrics["FP"],
        "validation_FN": val_metrics["FN"],
        "validation_precision": round(val_metrics["precision"], 4),
        "validation_recall": round(val_metrics["recall"], 4),
        "validation_f1": round(val_metrics["f1"], 4),
        "validation_accuracy": round(val_metrics["accuracy"], 4),
    }
    with open(threshold_json_path, "w", encoding="utf-8") as f:
        json.dump(threshold_data, f, indent=2)

    # Evaluate frozen threshold on test set
    print(f"[Polarix ML] Evaluating frozen threshold ({best_threshold:.6f}) on {len(test_df)} test sequences...")
    test_metrics, test_pred_df = evaluate_test_set(test_df, best_threshold)

    # Format test prediction columns
    pred_cols = [
        "station_id",
        "sensor_id",
        "timestamp",
        "target_value",
        "anomaly_type",
        "is_anomaly",
        "reconstruction_error",
        "predicted_status",
        "model_version",
    ]
    # Rename target_value to value if needed or keep both
    if "target_value" in test_pred_df.columns:
        test_pred_df["value"] = test_pred_df["target_value"]
    export_cols = [c for c in pred_cols if c in test_pred_df.columns]
    if "value" in test_pred_df.columns and "value" not in export_cols:
        export_cols.insert(3, "value")

    test_pred_csv_path = out_dir / "lstm_test_predictions.csv"
    test_pred_df[export_cols].to_csv(test_pred_csv_path, index=False)

    test_metrics_json_path = out_dir / "lstm_test_metrics.json"
    with open(test_metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)

    # Generate evaluation plot
    plot_png_path = out_dir / "lstm_threshold_evaluation.png"
    plot_threshold_evaluation(val_df, best_threshold, plot_png_path)

    return {
        "selected_threshold": best_threshold,
        "validation_metrics": threshold_data,
        "test_metrics": test_metrics,
        "search_csv": str(search_csv_path),
        "threshold_json": str(threshold_json_path),
        "test_metrics_json": str(test_metrics_json_path),
        "test_predictions_csv": str(test_pred_csv_path),
        "plot_png": str(plot_png_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select optimal threshold for Maitri LSTM Autoencoder and evaluate on test set."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="ml/results/lstm_reconstruction_errors.csv",
        help="Path to reconstruction errors CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ml/results",
        help="Directory to save evaluation artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_threshold_selection_pipeline(
        input_csv=args.input, output_dir=args.output_dir
    )

    vm = results["validation_metrics"]
    tm = results["test_metrics"]

    print("\n================ MAITRI LSTM THRESHOLD SELECTION REPORT ================")
    print(f"Model Version:         {vm['model_version']}")
    print(f"Selected Threshold:    {vm['threshold']:.6f}")
    print("------------------------------------------------------------------------")
    print("VALIDATION PERFORMANCE (Used strictly for threshold tuning):")
    print(f"  TP: {vm['validation_TP']} | TN: {vm['validation_TN']} | FP: {vm['validation_FP']} | FN: {vm['validation_FN']}")
    print(f"  Precision: {vm['validation_precision']:.4f}")
    print(f"  Recall:    {vm['validation_recall']:.4f}")
    print(f"  F1-Score:  {vm['validation_f1']:.4f}")
    print(f"  Accuracy:  {vm['validation_accuracy'] * 100:.2f}%")
    print("------------------------------------------------------------------------")
    print("TEST PERFORMANCE (Untouched evaluation split with frozen threshold):")
    print(f"  TP: {tm['TP']} | TN: {tm['TN']} | FP: {tm['FP']} | FN: {tm['FN']}")
    print(f"  Precision: {tm['precision']:.4f}")
    print(f"  Recall:    {tm['recall']:.4f}")
    print(f"  F1-Score:  {tm['f1']:.4f}")
    print(f"  Accuracy:  {tm['accuracy'] * 100:.2f}%")
    print("------------------------------------------------------------------------")
    print("PER-ANOMALY-TYPE TEST BREAKDOWN:")
    for atype, stats in tm["per_anomaly_type"].items():
        print(f"  [{atype}]: {stats}")
    print("========================================================================")


if __name__ == "__main__":
    main()
