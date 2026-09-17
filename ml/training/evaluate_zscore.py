#!/usr/bin/env python3
"""
Evaluation script for Maitri Z-Score Anomaly Detector (Polarix SIH26060 - Person C).

Executes the RollingZScoreDetector on telemetry data, computes evaluation metrics
against ground truth 'is_anomaly' labels, and outputs:
- ml/results/zscore_predictions.csv
- ml/results/zscore_metrics.json
- ml/results/zscore_confusion_matrix.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is in sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix as sk_confusion_matrix

from ml.training.zscore_detector import (
    DEFAULT_THRESHOLD,
    DEFAULT_WINDOW,
    RollingZScoreDetector,
)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """
    Compute binary classification metrics explicitly and via scikit-learn.
    """
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

    # Scikit-learn confusion matrix validation: [[TN, FP], [FN, TP]]
    cm = sk_confusion_matrix(y_true, y_pred, labels=[0, 1])

    return {
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "total_samples": total,
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "confusion_matrix": {
            "TN": int(cm[0, 0]),
            "FP": int(cm[0, 1]),
            "FN": int(cm[1, 0]),
            "TP": int(cm[1, 1]),
        },
    }


def plot_confusion_matrix(
    cm_dict: Dict[str, int],
    output_path: Path,
    title: str = "Maitri Z-Score Baseline Confusion Matrix",
) -> None:
    """Plot and save confusion matrix visualization."""
    matrix = np.array(
        [
            [cm_dict["TN"], cm_dict["FP"]],
            [cm_dict["FN"], cm_dict["TP"]],
        ]
    )

    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    cax = ax.matshow(matrix, cmap="Blues", alpha=0.85)
    fig.colorbar(cax)

    labels = ["Normal (0)", "Anomaly (1)"]
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticklabels(labels, fontsize=10)

    for i in range(2):
        for j in range(2):
            val = matrix[i, j]
            text_color = "white" if val > matrix.max() / 2 else "black"
            cell_name = ["TN", "FP", "FN", "TP"][i * 2 + j]
            ax.text(
                j,
                i,
                f"{cell_name}\n{val}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=11,
                fontweight="bold",
            )

    plt.title(title, pad=20, fontsize=12, fontweight="bold")
    plt.xlabel("Predicted Label", fontsize=10, labelpad=10)
    plt.ylabel("Actual Ground Truth", fontsize=10, labelpad=10)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close(fig)


def run_evaluation(
    input_csv: str = "ml/data/maitri_synthetic_telemetry.csv",
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
    output_dir: str = "ml/results",
) -> Dict[str, Any]:
    """Execute complete Z-score evaluation pipeline."""
    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found at '{input_path}'.")

    df = pd.read_csv(input_path)

    # Initialize detector and run detection
    detector = RollingZScoreDetector(window=window, threshold=threshold)
    pred_df = detector.detect(df)

    # Map predicted_status to binary label for anomaly evaluation:
    # ANOMALY and MISSING_DATA -> 1 (anomalous condition)
    # NORMAL -> 0
    y_pred = (
        pred_df["predicted_status"].isin(["ANOMALY", "MISSING_DATA"]).astype(int).to_numpy()
    )

    if "is_anomaly" not in pred_df.columns:
        raise ValueError("Ground truth column 'is_anomaly' is missing from dataset.")

    y_true = pred_df["is_anomaly"].astype(int).to_numpy()

    # Compute classification metrics
    metrics = compute_metrics(y_true, y_pred)
    metrics["model"] = "Rolling Z-Score Baseline"
    metrics["model_version"] = detector.config.model_version
    metrics["station_id"] = "MTR"
    metrics["parameters"] = {
        "window": window,
        "min_periods": detector.config.min_periods,
        "threshold": threshold,
    }
    metrics["breakdown_by_status"] = {
        status: int(count)
        for status, count in pred_df["predicted_status"].value_counts().items()
    }
    if "anomaly_type" in pred_df.columns:
        metrics["breakdown_by_actual_anomaly_type"] = {
            atype: int(count)
            for atype, count in pred_df["anomaly_type"].value_counts().items()
        }

    # Save outputs
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pred_csv_path = out_dir / "zscore_predictions.csv"
    metrics_json_path = out_dir / "zscore_metrics.json"
    cm_png_path = out_dir / "zscore_confusion_matrix.png"

    pred_df.to_csv(pred_csv_path, index=False)
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    plot_confusion_matrix(metrics["confusion_matrix"], cm_png_path)

    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Maitri Rolling Z-Score Anomaly Detector."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="ml/data/maitri_synthetic_telemetry.csv",
        help="Input synthetic telemetry CSV (default: ml/data/maitri_synthetic_telemetry.csv).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_WINDOW,
        help=f"Rolling window size in samples (default: {DEFAULT_WINDOW}).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Z-score absolute anomaly threshold (default: {DEFAULT_THRESHOLD}).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ml/results",
        help="Output directory for predictions, metrics, and plots (default: ml/results).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        f"[Polarix ML] Running Z-Score Evaluation (window={args.window}, threshold={args.threshold})..."
    )
    metrics = run_evaluation(
        input_csv=args.input,
        window=args.window,
        threshold=args.threshold,
        output_dir=args.output_dir,
    )

    print("\n================ MAITRI Z-SCORE EVALUATION REPORT ================")
    print(f"Station ID:          {metrics['station_id']}")
    print(f"Model Version:       {metrics['model_version']}")
    print(f"Window:              {metrics['parameters']['window']}")
    print(f"Threshold:           {metrics['parameters']['threshold']}")
    print(f"Total Samples:       {metrics['total_samples']}")
    print("------------------------------------------------------------------")
    print(f"True Positives (TP): {metrics['true_positives']}")
    print(f"True Negatives (TN): {metrics['true_negatives']}")
    print(f"False Positives (FP):{metrics['false_positives']}")
    print(f"False Negatives (FN):{metrics['false_negatives']}")
    print("------------------------------------------------------------------")
    print(f"Accuracy:            {metrics['accuracy'] * 100:.2f}%")
    print(f"Precision:           {metrics['precision']:.4f}")
    print(f"Recall:              {metrics['recall']:.4f}")
    print(f"F1-Score:            {metrics['f1_score']:.4f}")
    print("------------------------------------------------------------------")
    print("Predicted Status Breakdown:")
    for status, count in metrics["breakdown_by_status"].items():
        print(f"  {status}: {count}")
    print("==================================================================")


if __name__ == "__main__":
    main()
