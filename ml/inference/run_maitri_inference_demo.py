#!/usr/bin/env python3
"""
Maitri LSTM Autoencoder Inference Demonstration Script (Polarix SIH26060 - Person C).

Demonstrates streaming telemetry inference against the frozen `lstm-ae-v1` model:
- Insufficient data handling (< 30 steps)
- Valid normal telemetry scoring
- Detected anomaly scoring
- Missing / bad quality data handling

NOTE: Uses purely synthetic Maitri telemetry for demonstration; does NOT represent live Antarctic data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from ml.inference.lstm_inference import LSTMAutoencoderInference


def run_inference_demo(
    csv_path: str = "ml/data/maitri_synthetic_telemetry.csv",
    output_json: str = "ml/results/maitri_inference_demo.json",
) -> List[Dict[str, Any]]:
    """Execute streaming inference demonstration on synthetic telemetry."""
    print("[Polarix ML] Initializing LSTMAutoencoderInference engine...")
    inference_service = LSTMAutoencoderInference()
    print(f"  Model Version: {inference_service.model_version}")
    print(f"  Threshold:     {inference_service.threshold:.6f}")
    print(f"  Window Size:   {inference_service.config.seq_len} steps")

    df = pd.read_csv(csv_path)

    # Filter a sequence for TEMP_001
    temp_df = (
        df[df["sensor_id"] == "TEMP_001"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    demo_records: List[Dict[str, Any]] = []

    print("\n--- Streaming Demonstration: Normal & Warmup Sequence ---")
    # Stream first 32 normal points
    for idx in range(32):
        row = temp_df.iloc[idx]
        res = inference_service.infer_observation(
            station_id=row["station_id"],
            sensor_id=row["sensor_id"],
            timestamp=row["timestamp"],
            value=row["value"],
            quality="GOOD",
        )
        demo_records.append(
            {
                "step": idx + 1,
                "input_value": float(row["value"]),
                "quality": "GOOD",
                "ground_truth_anomaly": int(row["is_anomaly"]),
                "result": res,
            }
        )
        if (idx + 1) in [1, 15, 29, 30, 31, 32]:
            score_str = f"{res['anomaly_score']:.6f}" if res["anomaly_score"] is not None else "None"
            print(f"  Step {idx+1:02d} | Val: {row['value']:6.2f}°C | Status: {res['anomaly_status']:17s} | Score: {score_str}")

    # Stream a missing data record
    print("\n--- Streaming Demonstration: Missing / Corrupted Telemetry ---")
    res_missing = inference_service.infer_observation(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-03-01T00:33:00Z",
        value=None,
        quality="MISSING",
    )
    demo_records.append(
        {
            "step": 33,
            "input_value": None,
            "quality": "MISSING",
            "ground_truth_anomaly": 1,
            "result": res_missing,
        }
    )
    print(f"  Step 33 | Val:    None | Status: {res_missing['anomaly_status']:17s} | Score: {res_missing['anomaly_score']}")

    # Stream an anomaly window (e.g. Injected Spike from test set)
    print("\n--- Streaming Demonstration: Injected Spike Anomaly ---")
    spike_rows = temp_df[temp_df["anomaly_type"] == "SPIKE"]
    if len(spike_rows) > 0:
        spike_idx = spike_rows.index[0]
        # Reset and stream 30 points ending at spike
        inference_service.reset_history(station_id="MTR", sensor_id="TEMP_001")
        start_idx = max(0, spike_idx - 29)
        for i in range(start_idx, spike_idx + 1):
            s_row = temp_df.iloc[i]
            res_spike = inference_service.infer_observation(
                station_id=s_row["station_id"],
                sensor_id=s_row["sensor_id"],
                timestamp=s_row["timestamp"],
                value=s_row["value"],
                quality="GOOD",
            )

        demo_records.append(
            {
                "step": 34,
                "input_value": float(spike_rows.iloc[0]["value"]),
                "quality": "GOOD",
                "ground_truth_anomaly": 1,
                "ground_truth_type": "SPIKE",
                "result": res_spike,
            }
        )
        score_val = f"{res_spike['anomaly_score']:.6f}" if res_spike['anomaly_score'] is not None else "None"
        print(f"  Step 34 | Val: {spike_rows.iloc[0]['value']:6.2f}°C | Status: {res_spike['anomaly_status']:17s} | Score: {score_val} (Threshold: {inference_service.threshold:.6f})")

    # Export demo output JSON
    out_path = Path(output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "demonstration": "Maitri LSTM Autoencoder Streaming Inference Demo",
                "model_version": inference_service.model_version,
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "threshold": inference_service.threshold,
                "note": "Synthetic demonstration telemetry only; does NOT represent live Antarctic data.",
                "demo_events": demo_records,
            },
            f,
            indent=2,
        )

    print(f"\n[Polarix ML] Saved demonstration results to {out_path}")
    return demo_records


if __name__ == "__main__":
    run_inference_demo()
