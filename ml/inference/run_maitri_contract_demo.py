#!/usr/bin/env python3
"""
Maitri ML Inference Contract Demonstration (Polarix SIH26060 - Person C).

Demonstrates the typed ML-to-Backend integration contract:
1. Instantiating a valid `TelemetryInput` object.
2. Executing inference through `LSTMAutoencoderInference`.
3. Generating a typed `TelemetryInferenceOutput` contract object.
4. Serializing the output to standard JSON.
5. Saving representative examples across all four operational statuses:
   - INSUFFICIENT_DATA
   - NORMAL
   - ANOMALY
   - MISSING_DATA

NOTE:
- Uses synthetic Maitri telemetry only.
- Does NOT connect to FastAPI, MQTT, or backend databases.
- Does NOT claim to represent live Antarctic data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from ml.inference.inference_contract import (
    TelemetryInferenceOutput,
    TelemetryInput,
)
from ml.inference.lstm_inference import LSTMAutoencoderInference


def run_contract_demo(
    csv_path: str = "ml/data/maitri_synthetic_telemetry.csv",
    output_json: str = "ml/results/maitri_inference_contract_example.json",
) -> Dict[str, Any]:
    """Execute contract demonstration and export representative JSON artifacts."""
    print("[Polarix ML] Initializing LSTMAutoencoderInference for Contract Demo...")
    engine = LSTMAutoencoderInference()
    engine.reset_history()

    df = pd.read_csv(csv_path)
    temp_df = (
        df[df["sensor_id"] == "TEMP_001"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    examples: Dict[str, Any] = {
        "description": "Representative Polarix ML Inference Contract Outputs for Maitri Station",
        "station_id": "MTR",
        "supported_sensors": ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"],
        "model_version": engine.model_version,
        "reconstruction_threshold": engine.threshold,
        "note": "Synthetic telemetry only; no real Antarctic data is claimed or used.",
        "examples": {},
    }

    # 1. INSUFFICIENT_DATA Example (Observation 1 of 30)
    print("\n1. Generating INSUFFICIENT_DATA contract example...")
    input_warmup = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:01:00Z",
        value=-34.50,
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
    )
    output_warmup = engine.infer_telemetry(input_warmup)
    examples["examples"]["INSUFFICIENT_DATA"] = {
        "input": input_warmup.to_dict(),
        "output": output_warmup.to_dict(),
    }
    print(f"   Input:  {input_warmup.to_json()}")
    print(f"   Output: {output_warmup.to_json()}")

    # 2. NORMAL Example (Observation 30 of normal pattern)
    print("\n2. Generating NORMAL contract example...")
    engine.reset_history("MTR", "TEMP_001")
    # Stream first 29 points
    for i in range(29):
        val = float(temp_df.iloc[i]["value"])
        ts = str(temp_df.iloc[i]["timestamp"])
        engine.infer_telemetry(
            TelemetryInput(
                station_id="MTR",
                sensor_id="TEMP_001",
                timestamp=ts,
                value=val,
                unit="C",
                quality="GOOD",
                source="SIMULATOR",
            )
        )

    norm_row = temp_df.iloc[29]
    input_normal = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp=str(norm_row["timestamp"]),
        value=float(norm_row["value"]),
        unit="C",
        quality="GOOD",
        source="SIMULATOR",
    )
    output_normal = engine.infer_telemetry(input_normal)
    examples["examples"]["NORMAL"] = {
        "input": input_normal.to_dict(),
        "output": output_normal.to_dict(),
    }
    print(f"   Input:  {input_normal.to_json()}")
    print(f"   Output: {output_normal.to_json()}")

    # 3. ANOMALY Example (Injected Spike from test set)
    print("\n3. Generating ANOMALY contract example...")
    spike_rows = temp_df[temp_df["anomaly_type"] == "SPIKE"]
    if len(spike_rows) > 0:
        spike_idx = spike_rows.index[0]
        engine.reset_history("MTR", "TEMP_001")
        start_idx = max(0, spike_idx - 29)
        for i in range(start_idx, spike_idx):
            s_row = temp_df.iloc[i]
            engine.infer_telemetry(
                TelemetryInput(
                    station_id="MTR",
                    sensor_id="TEMP_001",
                    timestamp=str(s_row["timestamp"]),
                    value=float(s_row["value"]),
                    unit="C",
                    quality="GOOD",
                    source="SIMULATOR",
                )
            )

        spike_row = temp_df.iloc[spike_idx]
        input_anomaly = TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=str(spike_row["timestamp"]),
            value=float(spike_row["value"]),
            unit="C",
            quality="GOOD",
            source="SIMULATOR",
        )
        output_anomaly = engine.infer_telemetry(input_anomaly)
        examples["examples"]["ANOMALY"] = {
            "input": input_anomaly.to_dict(),
            "output": output_anomaly.to_dict(),
        }
        print(f"   Input:  {input_anomaly.to_json()}")
        print(f"   Output: {output_anomaly.to_json()}")

    # 4. MISSING_DATA Example (null value / bad quality)
    print("\n4. Generating MISSING_DATA contract example...")
    input_missing = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-17T10:35:00Z",
        value=None,
        unit="C",
        quality="BAD",
        source="SIMULATOR",
    )
    output_missing = engine.infer_telemetry(input_missing)
    examples["examples"]["MISSING_DATA"] = {
        "input": input_missing.to_dict(),
        "output": output_missing.to_dict(),
    }
    print(f"   Input:  {input_missing.to_json()}")
    print(f"   Output: {output_missing.to_json()}")

    # Save to ml/results/maitri_inference_contract_example.json
    out_file = Path(output_json)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2)

    print(f"\n[Polarix ML] Successfully exported contract examples to {out_file}")
    return examples


if __name__ == "__main__":
    run_contract_demo()
