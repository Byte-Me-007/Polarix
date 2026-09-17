#!/usr/bin/env python3
"""
Maitri Anomaly Type Classifier Evaluation Pipeline (Polarix SIH26060 - Person C).

Evaluates the feature-based AnomalyTypeClassifier integrated with the LSTM Autoencoder
across chronological Validation (70-85%) and Test (85-100%) partitions:
- Zero ground truth label leakage during inference.
- Evaluates per-class precision, recall, F1, and UNKNOWN rate.
- Generates JSON summary, metrics CSV, and confusion matrix plot.
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
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml.inference.anomaly_type_classifier import AnomalyTypeClassifier
from ml.inference.lstm_inference import LSTMAutoencoderInference


def evaluate_classifier_on_dataset(
    dataset_csv: str = "ml/data/maitri_synthetic_telemetry.csv",
    output_dir: str = "ml/results",
) -> Dict[str, Any]:
    """Execute evaluation of AnomalyTypeClassifier on validation and test partitions."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[Polarix ML] Loading dataset and initializing inference engine...")
    df = pd.read_csv(dataset_csv)

    # Sort chronologically per sensor
    df["_parsed_ts"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
    df.sort_values(by=["sensor_id", "_parsed_ts"], inplace=True)
    df.drop(columns=["_parsed_ts"], inplace=True)

    # Chronological partition tagging
    df["sensor_step"] = df.groupby("sensor_id").cumcount()
    total_per_sensor = df.groupby("sensor_id")["sensor_step"].transform("count")
    train_thresh = (total_per_sensor * 0.70).astype(int)
    val_thresh = (total_per_sensor * 0.85).astype(int)

    df["split"] = np.where(
        df["sensor_step"] < train_thresh,
        "train",
        np.where(df["sensor_step"] < val_thresh, "val", "test"),
    )

    inference_engine = LSTMAutoencoderInference()
    classifier = AnomalyTypeClassifier()

    eval_results: Dict[str, Any] = {
        "dataset": "ml/data/maitri_synthetic_telemetry.csv",
        "station_id": "MTR",
        "model_version": inference_engine.model_version,
        "lstm_threshold": inference_engine.threshold,
        "splits": {},
        "note": "Descriptive evaluation on synthetic telemetry; no real Antarctic data claimed.",
    }

    all_eval_rows: List[Dict[str, Any]] = []

    for split_name in ["val", "test"]:
        print(f"[Polarix ML] Evaluating anomaly type classification on '{split_name}' split...")
        split_df = df[df["split"] == split_name]

        true_labels: List[str] = []
        pred_types: List[str] = []
        pred_statuses: List[str] = []

        # Iterate per sensor to simulate streaming window
        for sensor_id, grp in split_df.groupby("sensor_id"):
            grp_sorted = grp.sort_values("sensor_step").reset_index(drop=True)
            sensor_vals = grp_sorted["value"].tolist()
            sensor_types = grp_sorted["anomaly_type"].tolist()
            sensor_qualities = grp_sorted["quality"].tolist()

            # Need 30 steps of historical context
            # Look up preceding observations if near split boundary
            full_sensor_df = df[df["sensor_id"] == sensor_id].sort_values("sensor_step").reset_index(drop=True)
            start_step = grp_sorted["sensor_step"].min()

            for i in range(len(grp_sorted)):
                global_idx = start_step + i
                true_type = sensor_types[i]

                # If missing / dropout
                if pd.isna(sensor_vals[i]) or true_type == "DROPOUT":
                    true_labels.append("DROPOUT")
                    pred_types.append("MISSING_DATA")
                    pred_statuses.append("MISSING_DATA")
                    continue

                if global_idx < 29:
                    true_labels.append(true_type)
                    pred_types.append("INSUFFICIENT_DATA")
                    pred_statuses.append("INSUFFICIENT_DATA")
                    continue

                # 30-step window
                window_slice = full_sensor_df.iloc[global_idx - 29 : global_idx + 1]["value"].to_numpy(dtype=np.float32)

                if np.isnan(window_slice).any():
                    true_labels.append(true_type)
                    pred_types.append("MISSING_DATA")
                    pred_statuses.append("MISSING_DATA")
                    continue

                # Run inference on the 30-step window
                out = inference_engine.infer_window(
                    station_id="MTR",
                    sensor_id=sensor_id,
                    timestamp=str(grp_sorted.iloc[i]["timestamp"]),
                    window_values=window_slice.tolist(),
                    quality="GOOD",
                )

                true_labels.append(true_type)
                pred_types.append(out.anomaly_type or "UNKNOWN")
                pred_statuses.append(out.anomaly_status)

        # Compute confusion matrix and metrics for numeric evaluated points
        classes = ["NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE"]
        matrix_classes = classes + ["UNKNOWN"]

        cm: Dict[str, Dict[str, int]] = {t: {p: 0 for p in matrix_classes} for t in classes}
        dropout_count = 0

        for t, p in zip(true_labels, pred_types):
            if t in ["DROPOUT", "MISSING"] or p in ["MISSING_DATA", "INSUFFICIENT_DATA"]:
                dropout_count += 1
                continue
            if t in cm and p in cm[t]:
                cm[t][p] += 1

        # Per-class metrics
        class_metrics: Dict[str, Any] = {}
        for c in classes:
            tp = cm[c].get(c, 0)
            total_true = sum(cm[c].values())
            total_pred = sum(cm[t].get(c, 0) for t in classes)

            prec = tp / total_pred if total_pred > 0 else 0.0
            rec = tp / total_true if total_true > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            class_metrics[c] = {
                "total_instances": total_true,
                "true_positives": tp,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
            }

            all_eval_rows.append(
                {
                    "Split": split_name,
                    "Class": c,
                    "Total": total_true,
                    "TP": tp,
                    "Precision": round(prec, 4),
                    "Recall": round(rec, 4),
                    "F1": round(f1, 4),
                }
            )

        unknown_count = sum(cm[t].get("UNKNOWN", 0) for t in classes)
        total_eval = sum(sum(cm[t].values()) for t in classes)
        unknown_rate = unknown_count / total_eval if total_eval > 0 else 0.0

        eval_results["splits"][split_name] = {
            "total_evaluated": total_eval,
            "dropout_missing_count": dropout_count,
            "unknown_count": unknown_count,
            "unknown_rate": round(unknown_rate, 4),
            "class_metrics": class_metrics,
            "confusion_matrix": cm,
        }

    # Save JSON summary
    json_path = out_dir / "maitri_anomaly_type_validation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    # Save CSV metrics
    csv_path = out_dir / "maitri_anomaly_type_metrics.csv"
    pd.DataFrame(all_eval_rows).to_csv(csv_path, index=False)

    # Plot Confusion Matrix for Test split
    test_cm = eval_results["splits"]["test"]["confusion_matrix"]
    plot_cm_path = out_dir / "maitri_anomaly_type_confusion_matrix.png"
    _plot_confusion_matrix(test_cm, plot_cm_path)

    print(f"[Polarix ML] Successfully exported anomaly classification validation artifacts to {out_dir}")
    return eval_results


def _plot_confusion_matrix(cm_dict: Dict[str, Dict[str, int]], output_path: Path) -> None:
    """Plot heatmap confusion matrix for anomaly type classification on test data."""
    true_labels = ["NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE"]
    pred_labels = ["NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"]

    matrix = np.zeros((len(true_labels), len(pred_labels)), dtype=int)
    for i, t in enumerate(true_labels):
        for j, p in enumerate(pred_labels):
            matrix[i, j] = cm_dict.get(t, {}).get(p, 0)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    cax = ax.matshow(matrix, cmap="Purples", alpha=0.85)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(pred_labels)))
    ax.set_yticks(range(len(true_labels)))
    ax.set_xticklabels(pred_labels, fontsize=9, fontweight="bold")
    ax.set_yticklabels(true_labels, fontsize=9, fontweight="bold")

    for i in range(len(true_labels)):
        for j in range(len(pred_labels)):
            val = matrix[i, j]
            color = "white" if val > matrix.max() / 2 else "black"
            ax.text(j, i, str(val), ha="center", va="center", color=color, fontsize=10, fontweight="bold")

    ax.set_title("Maitri Anomaly Type Classification Matrix (Test Set)", pad=20, fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Anomaly Type", fontsize=10, fontweight="bold")
    ax.set_ylabel("Ground Truth Type", fontsize=10, fontweight="bold")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AnomalyTypeClassifier on synthetic telemetry.")
    parser.add_argument("--dataset", type=str, default="ml/data/maitri_synthetic_telemetry.csv")
    parser.add_argument("--output-dir", type=str, default="ml/results")
    args = parser.parse_args()
    evaluate_classifier_on_dataset(dataset_csv=args.dataset, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
