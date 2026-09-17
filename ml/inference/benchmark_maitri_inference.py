"""
Maitri ML Inference Performance & Latency Benchmark Harness.
Polarix SIH26060 - Person C.

Measures quantitative latency and throughput characteristics of the existing
Maitri ML streaming inference service under controlled, synthetic offline workloads.
This is a measurement harness only; model weights, thresholds, and inference logic
remain completely unchanged.
"""

from __future__ import annotations

import csv
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    TelemetryInput,
)
from ml.inference.maitri_ml_service import MaitriMLService


def calculate_latency_stats(latencies_ms: List[float]) -> Dict[str, float]:
    """
    Calculate statistical summary metrics from a list of measured latency durations in ms.
    """
    if not latencies_ms:
        raise ValueError("Cannot calculate statistics on empty latency list.")

    arr = np.array(latencies_ms, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError("Latency list contains non-finite values.")
    if np.any(arr < 0):
        raise ValueError("Latency list contains negative durations.")

    return {
        "sample_count": len(arr),
        "min_latency_ms": round(float(np.min(arr)), 4),
        "max_latency_ms": round(float(np.max(arr)), 4),
        "mean_latency_ms": round(float(np.mean(arr)), 4),
        "median_latency_ms": round(float(np.median(arr)), 4),
        "p50_latency_ms": round(float(np.percentile(arr, 50)), 4),
        "p90_latency_ms": round(float(np.percentile(arr, 90)), 4),
        "p95_latency_ms": round(float(np.percentile(arr, 95)), 4),
        "p99_latency_ms": round(float(np.percentile(arr, 99)), 4),
        "std_latency_ms": round(float(np.std(arr)), 4),
    }


def format_iso_timestamp(step: int, base_hour: int = 0) -> str:
    """Format step index into a valid, monotonically increasing ISO-8601 timestamp."""
    second = step % 60
    total_minutes = step // 60
    minute = total_minutes % 60
    hour = (base_hour + total_minutes // 60) % 24
    return f"2026-09-18T{hour:02d}:{minute:02d}:{second:02d}Z"


def run_benchmark(
    warmup_iterations: int = 20,
    measured_iterations: int = 200,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Execute controlled benchmark scenarios across the Maitri ML Service.
    """
    print("=" * 70)
    print("POLARIX MAITRI ML INFERENCE LATENCY & PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"Platform: {platform.platform()} | Python: {platform.python_version()}")
    print(f"Warm-up: {warmup_iterations} ops | Measured per scenario: {measured_iterations} ops")
    print("=" * 70)

    # 1. Measure Startup & Model Initialization
    t_start = time.perf_counter()
    service = MaitriMLService()
    t_init = time.perf_counter()
    startup_ms = round((t_init - t_start) * 1000.0, 4)
    print(f"[STARTUP] Model loading and initialization: {startup_ms:.4f} ms")

    rng = np.random.default_rng(random_seed)
    scenarios_results: Dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # Scenario 1: WARM_NORMAL (Steady-state normal scored inference)
    # -------------------------------------------------------------------------
    print("Benchmarking Scenario 1: WARM_NORMAL...")
    service.reset_all()
    # Warmup buffer to 30 steps
    for step in range(1, 31):
        ts = format_iso_timestamp(step, base_hour=0)
        val = -15.0 + float(rng.normal(0, 0.2))
        service.process_telemetry(TelemetryInput("MTR", "TEMP_001", ts, val))

    # Pre-benchmark warmup
    for w in range(warmup_iterations):
        ts = format_iso_timestamp(31 + w, base_hour=0)
        val = -15.0 + float(rng.normal(0, 0.2))
        service.process_telemetry(TelemetryInput("MTR", "TEMP_001", ts, val))

    # Timed runs
    warm_normal_latencies: List[float] = []
    base_step = 31 + warmup_iterations
    for i in range(measured_iterations):
        ts = format_iso_timestamp(base_step + i, base_hour=0)
        val = -15.0 + float(rng.normal(0, 0.2))
        inp = TelemetryInput("MTR", "TEMP_001", ts, val)

        t0 = time.perf_counter()
        out = service.process_telemetry(inp)
        t1 = time.perf_counter()
        warm_normal_latencies.append((t1 - t0) * 1000.0)

    scenarios_results["WARM_NORMAL"] = calculate_latency_stats(warm_normal_latencies)
    print(
        f" -> WARM_NORMAL: P50={scenarios_results['WARM_NORMAL']['p50_latency_ms']:.4f}ms, "
        f"P95={scenarios_results['WARM_NORMAL']['p95_latency_ms']:.4f}ms, "
        f"Mean={scenarios_results['WARM_NORMAL']['mean_latency_ms']:.4f}ms"
    )

    # -------------------------------------------------------------------------
    # Scenario 2: ANOMALY (Scored inference on anomaly sequence)
    # -------------------------------------------------------------------------
    print("Benchmarking Scenario 2: ANOMALY...")
    anomaly_latencies: List[float] = []
    for i in range(measured_iterations):
        ts = format_iso_timestamp(i + 1, base_hour=2)
        val = 25.0 if i % 2 == 0 else (-15.0 + (i % 30) * 0.5)
        inp = TelemetryInput("MTR", "TEMP_001", ts, val)

        t0 = time.perf_counter()
        out = service.process_telemetry(inp)
        t1 = time.perf_counter()
        anomaly_latencies.append((t1 - t0) * 1000.0)

    scenarios_results["ANOMALY"] = calculate_latency_stats(anomaly_latencies)
    print(
        f" -> ANOMALY: P50={scenarios_results['ANOMALY']['p50_latency_ms']:.4f}ms, "
        f"P95={scenarios_results['ANOMALY']['p95_latency_ms']:.4f}ms, "
        f"Mean={scenarios_results['ANOMALY']['mean_latency_ms']:.4f}ms"
    )

    # -------------------------------------------------------------------------
    # Scenario 3: MISSING_DATA (Handling missing / bad-quality records)
    # -------------------------------------------------------------------------
    print("Benchmarking Scenario 3: MISSING_DATA...")
    missing_latencies: List[float] = []
    for i in range(measured_iterations):
        ts = format_iso_timestamp(i + 1, base_hour=4)
        if i % 3 == 0:
            inp = TelemetryInput("MTR", "PRESS_001", ts, None, quality="MISSING")
        elif i % 3 == 1:
            inp = TelemetryInput("MTR", "PRESS_001", ts, float("nan"), quality="GOOD")
        else:
            inp = TelemetryInput("MTR", "PRESS_001", ts, 985.0, quality="BAD")

        t0 = time.perf_counter()
        out = service.process_telemetry(inp)
        t1 = time.perf_counter()
        missing_latencies.append((t1 - t0) * 1000.0)

    scenarios_results["MISSING_DATA"] = calculate_latency_stats(missing_latencies)
    print(
        f" -> MISSING_DATA: P50={scenarios_results['MISSING_DATA']['p50_latency_ms']:.4f}ms, "
        f"P95={scenarios_results['MISSING_DATA']['p95_latency_ms']:.4f}ms, "
        f"Mean={scenarios_results['MISSING_DATA']['mean_latency_ms']:.4f}ms"
    )

    # -------------------------------------------------------------------------
    # Scenario 4: INSUFFICIENT_DATA (Handling history with < 30 observations)
    # -------------------------------------------------------------------------
    print("Benchmarking Scenario 4: INSUFFICIENT_DATA...")
    insufficient_latencies: List[float] = []
    for i in range(measured_iterations):
        if i % 10 == 0:
            service.reset_sensor("HUM_001")
        ts = format_iso_timestamp(i + 1, base_hour=6)
        val = 60.0 + float(rng.normal(0, 0.5))
        inp = TelemetryInput("MTR", "HUM_001", ts, val)

        t0 = time.perf_counter()
        out = service.process_telemetry(inp)
        t1 = time.perf_counter()
        insufficient_latencies.append((t1 - t0) * 1000.0)

    scenarios_results["INSUFFICIENT_DATA"] = calculate_latency_stats(insufficient_latencies)
    print(
        f" -> INSUFFICIENT_DATA: P50={scenarios_results['INSUFFICIENT_DATA']['p50_latency_ms']:.4f}ms, "
        f"P95={scenarios_results['INSUFFICIENT_DATA']['p95_latency_ms']:.4f}ms, "
        f"Mean={scenarios_results['INSUFFICIENT_DATA']['mean_latency_ms']:.4f}ms"
    )

    # -------------------------------------------------------------------------
    # Scenario 5: MULTI_SENSOR (Interleaved stream across all 5 Maitri sensors)
    # -------------------------------------------------------------------------
    print("Benchmarking Scenario 5: MULTI_SENSOR...")
    service.reset_all()
    # Warmup all 5 sensors to 30 steps
    sensors = sorted(list(SUPPORTED_SENSORS))
    for step in range(1, 31):
        ts = format_iso_timestamp(step, base_hour=8)
        for s in sensors:
            service.process_telemetry(TelemetryInput("MTR", s, ts, 10.0))

    multi_sensor_latencies: List[float] = []
    for i in range(measured_iterations):
        sensor_id = sensors[i % len(sensors)]
        ts = format_iso_timestamp(31 + (i // len(sensors)), base_hour=8)
        val = 10.0 + float(rng.normal(0, 0.2))
        inp = TelemetryInput("MTR", sensor_id, ts, val)

        t0 = time.perf_counter()
        out = service.process_telemetry(inp)
        t1 = time.perf_counter()
        multi_sensor_latencies.append((t1 - t0) * 1000.0)

    scenarios_results["MULTI_SENSOR"] = calculate_latency_stats(multi_sensor_latencies)
    print(
        f" -> MULTI_SENSOR: P50={scenarios_results['MULTI_SENSOR']['p50_latency_ms']:.4f}ms, "
        f"P95={scenarios_results['MULTI_SENSOR']['p95_latency_ms']:.4f}ms, "
        f"Mean={scenarios_results['MULTI_SENSOR']['mean_latency_ms']:.4f}ms"
    )

    # -------------------------------------------------------------------------
    # Aggregate Benchmark Output Object
    # -------------------------------------------------------------------------
    benchmark_data: Dict[str, Any] = {
        "benchmark_metadata": {
            "module": "ml.inference.benchmark_maitri_inference",
            "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
            "station_id": "MTR",
            "model_version": DEFAULT_MODEL_VERSION,
            "threshold": service.threshold,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "warmup_count_per_scenario": warmup_iterations,
            "measured_iterations_per_scenario": measured_iterations,
            "random_seed": random_seed,
            "benchmark_type": "synthetic_offline_benchmark_only",
            "disclaimer": (
                "Synthetic offline benchmark measurements only. Results are machine- and environment-dependent "
                "and do not constitute production SLAs, real-time edge hardware certifications, or claims on real "
                "Antarctic station telemetry. Model architecture, scalers, weights, and decision thresholds remain strictly frozen."
            ),
        },
        "startup_initialization": {
            "startup_initialization_ms": startup_ms,
            "description": "Model weight loading, manifest SHA-256 verification, scaler loading, and inference engine initialization.",
        },
        "scenarios": scenarios_results,
    }

    # Save to JSON
    json_path = Path("ml/results/maitri_inference_performance.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"\n[OUTPUT] Benchmark JSON saved to: {json_path}")

    # Save to CSV
    csv_path = Path("ml/results/maitri_inference_performance.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "scenario",
            "sample_count",
            "min_latency_ms",
            "median_p50_ms",
            "mean_latency_ms",
            "p90_ms",
            "p95_ms",
            "p99_ms",
            "max_latency_ms",
            "std_ms",
        ])
        for sc_name, sc_stats in scenarios_results.items():
            writer.writerow([
                sc_name,
                sc_stats["sample_count"],
                sc_stats["min_latency_ms"],
                sc_stats["p50_latency_ms"],
                sc_stats["mean_latency_ms"],
                sc_stats["p90_latency_ms"],
                sc_stats["p95_latency_ms"],
                sc_stats["p99_latency_ms"],
                sc_stats["max_latency_ms"],
                sc_stats["std_latency_ms"],
            ])
    print(f"[OUTPUT] Benchmark CSV saved to: {csv_path}")
    print("=" * 70)

    return benchmark_data


if __name__ == "__main__":
    run_benchmark()
