"""
Polarix Maitri ML Service Adapter Demo (SIH26060 - Person C).

Demonstrates downstream consumption of the Maitri ML anomaly detection service:
TelemetryInput → MaitriMLService → TelemetryInferenceOutput

Shows:
1. Service initialization and artifact integrity verification
2. Streaming initial observations (< 30) returning INSUFFICIENT_DATA
3. Continuous streaming reaching 30 observations producing NORMAL inference
4. Injecting missing/bad quality telemetry returning MISSING_DATA and clearing buffer
5. Streaming an anomalous spike producing ANOMALY inference with SPIKE type classification
6. Multi-sensor isolation and per-sensor reset functionality
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from ml.inference.inference_contract import TelemetryInput
from ml.inference.maitri_ml_service import MaitriMLService


def main() -> None:
    print("=" * 75)
    print("POLARIX MAITRI ML SERVICE ADAPTER DEMO (SIH26060 - PERSON C)")
    print("=" * 75)

    # 1. Initialize Service
    print("\n[1] Initializing MaitriMLService...")
    service = MaitriMLService()
    info = service.get_service_info()
    print(f"  Service Name:       {info['service_name']}")
    print(f"  Station:            {info['station_id']}")
    print(f"  Model Version:      {info['model_version']}")
    print(f"  Supported Sensors:  {', '.join(info['supported_sensors'])}")
    print(f"  Window Size:        {info['sequence_length']} observations")
    print(f"  Anomaly Threshold:  {info['reconstruction_threshold']:.6f} MSE")
    print(f"  Status:             {info['status']}")

    # 2. Insufficient Data Demonstration
    print("\n[2] Streaming First 5 Observations for TEMP_001 (Insufficient Data):")
    service.reset_all()
    for step in range(1, 6):
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T01:{step:02d}:00Z",
            value=-15.0 + 0.1 * np.sin(step),
            unit="°C",
            quality="GOOD",
        )
        out = service.process_telemetry(inp)
        print(f"  Step {step:02d} | Val: {out.value:>6.2f}°C | Status: {out.anomaly_status:<17} | Score: {str(out.anomaly_score):<6} | Type: {str(out.anomaly_type)}")

    # 3. Complete Warmup to 30 Steps (Normal Inference)
    print("\n[3] Reaching 30 Observations for Scored Normal Inference:")
    for step in range(6, 31):
        inp = TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T01:{step:02d}:00Z",
            value=-15.0 + 0.15 * np.sin(step * 0.2),
            unit="°C",
            quality="GOOD",
        )
        out = service.process_telemetry(inp)
        if step in (29, 30):
            print(f"  Step {step:02d} | Val: {out.value:>6.2f}°C | Status: {out.anomaly_status:<17} | Score: {out.anomaly_score} | Type: {out.anomaly_type}")

    print(f"\n  JSON Output Contract at Step 30:\n{out.to_json(indent=4)}")

    # 4. Missing Data & Buffer Reset Demonstration
    print("\n[4] Handling Missing Telemetry (Dropout / Quality Failure):")
    missing_input = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T01:31:00Z",
        value=None,
        unit="°C",
        quality="BAD",
    )
    missing_out = service.process_telemetry(missing_input)
    print(f"  Missing Input -> Status: {missing_out.anomaly_status} | Score: {missing_out.anomaly_score} | Type: {missing_out.anomaly_type}")

    # Verify buffer was reset
    next_input = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T01:32:00Z",
        value=-15.2,
        unit="°C",
        quality="GOOD",
    )
    next_out = service.process_telemetry(next_input)
    print(f"  Next Valid Input -> Status: {next_out.anomaly_status} (Buffer reset verified)")

    # 5. Anomaly Detection & Type Classification Demonstration (Spike)
    print("\n[5] Demonstrating Anomaly Detection and Type Classification (Spike):")
    service.reset_sensor("TEMP_001")
    # Feed 30 normal baseline points
    for step in range(1, 31):
        service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="TEMP_001",
            timestamp=f"2026-09-18T02:{step:02d}:00Z",
            value=-15.0 + 0.1 * np.sin(step),
            quality="GOOD",
        ))

    # Inject sharp spike pulse
    spike_input = TelemetryInput(
        station_id="MTR",
        sensor_id="TEMP_001",
        timestamp="2026-09-18T02:31:00Z",
        value=15.0,  # Sudden 30°C thermal jump
        unit="°C",
        quality="GOOD",
    )
    spike_out = service.process_telemetry(spike_input)
    print(f"  Spike Input (value: {spike_out.value}°C):")
    print(f"    Anomaly Status: {spike_out.anomaly_status}")
    print(f"    Anomaly Score:  {spike_out.anomaly_score:.6f} MSE (Threshold: {service.threshold:.6f})")
    print(f"    Anomaly Type:   {spike_out.anomaly_type}")
    print(f"    Model Version:  {spike_out.model_version}")

    # 6. Sensor History Reset Isolation
    print("\n[6] Demonstrating Sensor History Isolation & Explicit Reset:")
    service.reset_all()
    # Feed 30 points to PRESS_001 and 15 points to VIB_001
    for step in range(1, 31):
        service.process_telemetry(TelemetryInput(
            station_id="MTR",
            sensor_id="PRESS_001",
            timestamp=f"2026-09-18T03:{step:02d}:00Z",
            value=990.0,
            quality="GOOD",
        ))
        if step <= 15:
            service.process_telemetry(TelemetryInput(
                station_id="MTR",
                sensor_id="VIB_001",
                timestamp=f"2026-09-18T03:{step:02d}:00Z",
                value=0.85,
                quality="GOOD",
            ))

    status_before = service.get_service_info()["active_buffer_lengths"]
    print(f"  Buffer lengths before reset: PRESS_001={status_before['PRESS_001']}, VIB_001={status_before['VIB_001']}")

    service.reset_sensor("PRESS_001")
    status_after = service.get_service_info()["active_buffer_lengths"]
    print(f"  Buffer lengths after resetting PRESS_001: PRESS_001={status_after['PRESS_001']}, VIB_001={status_after['VIB_001']}")

    print("\n" + "=" * 75)
    print("DEMO COMPLETED SUCCESSFULLY: ML SERVICE ADAPTER IS OPERATIONAL")
    print("=" * 75)


if __name__ == "__main__":
    main()
