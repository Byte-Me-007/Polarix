"""
Unit and Integration tests for Maitri ML Inference Performance Benchmark.
Polarix SIH26060 - Person C.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import pytest

from ml.inference.benchmark_maitri_inference import (
    calculate_latency_stats,
    format_iso_timestamp,
)
from ml.inference.inference_contract import parse_iso_timestamp


# -----------------------------------------------------------------------------
# 1. Statistical Helper Tests
# -----------------------------------------------------------------------------
def test_1_calculate_latency_stats_valid():
    """Verify calculate_latency_stats computes exact and ordered statistical metrics."""
    latencies = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    stats = calculate_latency_stats(latencies)

    assert stats["sample_count"] == 10
    assert stats["min_latency_ms"] == 1.0
    assert stats["max_latency_ms"] == 10.0
    assert stats["mean_latency_ms"] == 5.5
    assert stats["median_latency_ms"] == 5.5
    assert stats["p50_latency_ms"] == 5.5
    assert stats["p90_latency_ms"] == 9.1
    assert stats["p95_latency_ms"] == 9.55
    assert stats["p99_latency_ms"] == 9.91
    assert stats["std_latency_ms"] >= 0.0

    # Monotonic order check
    assert (
        stats["min_latency_ms"]
        <= stats["p50_latency_ms"]
        <= stats["p90_latency_ms"]
        <= stats["p95_latency_ms"]
        <= stats["p99_latency_ms"]
        <= stats["max_latency_ms"]
    )


def test_2_calculate_latency_stats_empty():
    """Verify calculate_latency_stats raises ValueError on empty list."""
    with pytest.raises(ValueError, match="empty latency list"):
        calculate_latency_stats([])


def test_3_calculate_latency_stats_non_finite():
    """Verify calculate_latency_stats raises ValueError on NaN or Inf."""
    with pytest.raises(ValueError, match="non-finite values"):
        calculate_latency_stats([1.0, float("nan"), 3.0])

    with pytest.raises(ValueError, match="non-finite values"):
        calculate_latency_stats([1.0, float("inf"), 3.0])


def test_4_calculate_latency_stats_negative():
    """Verify calculate_latency_stats raises ValueError on negative latency."""
    with pytest.raises(ValueError, match="negative durations"):
        calculate_latency_stats([1.0, -0.5, 3.0])


# -----------------------------------------------------------------------------
# 2. Timestamp Formatting Helper Tests
# -----------------------------------------------------------------------------
def test_5_format_iso_timestamp_valid():
    """Verify format_iso_timestamp generates strictly parseable ISO-8601 strings."""
    ts1 = format_iso_timestamp(0, base_hour=0)
    assert ts1 == "2026-09-18T00:00:00Z"
    dt1 = parse_iso_timestamp(ts1)
    assert dt1.hour == 0 and dt1.minute == 0 and dt1.second == 0

    ts2 = format_iso_timestamp(3665, base_hour=1)
    # 3665 seconds = 1 hr, 1 min, 5 sec -> hour = 1 + 1 = 2
    assert ts2 == "2026-09-18T02:01:05Z"
    dt2 = parse_iso_timestamp(ts2)
    assert dt2.hour == 2 and dt2.minute == 1 and dt2.second == 5


# -----------------------------------------------------------------------------
# 3. Benchmark Artifact Schema & Consistency Tests
# -----------------------------------------------------------------------------
def test_6_benchmark_json_artifact_schema():
    """Verify the saved benchmark JSON conforms to schema requirements."""
    json_path = Path("ml/results/maitri_inference_performance.json")
    assert json_path.exists(), "Performance results JSON must exist."

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Metadata
    meta = data["benchmark_metadata"]
    assert meta["model_version"] == "lstm-ae-v1"
    assert meta["threshold"] == 0.017674
    assert meta["station_id"] == "MTR"
    assert meta["benchmark_type"] == "synthetic_offline_benchmark_only"
    assert "disclaimer" in meta

    # Startup
    startup = data["startup_initialization"]
    assert "startup_initialization_ms" in startup
    assert math.isfinite(startup["startup_initialization_ms"])
    assert startup["startup_initialization_ms"] >= 0.0

    # Scenarios
    expected_scenarios = {"WARM_NORMAL", "ANOMALY", "MISSING_DATA", "INSUFFICIENT_DATA", "MULTI_SENSOR"}
    assert set(data["scenarios"].keys()) == expected_scenarios

    for sc_name, sc_stats in data["scenarios"].items():
        assert sc_stats["sample_count"] >= 100
        assert math.isfinite(sc_stats["mean_latency_ms"])
        assert math.isfinite(sc_stats["p50_latency_ms"])
        assert math.isfinite(sc_stats["p95_latency_ms"])
        assert math.isfinite(sc_stats["p99_latency_ms"])
        assert (
            sc_stats["min_latency_ms"]
            <= sc_stats["p50_latency_ms"]
            <= sc_stats["p90_latency_ms"]
            <= sc_stats["p95_latency_ms"]
            <= sc_stats["p99_latency_ms"]
            <= sc_stats["max_latency_ms"]
        )
        assert sc_stats["std_latency_ms"] >= 0.0


def test_7_benchmark_csv_artifact_schema():
    """Verify the saved benchmark CSV matches scenarios and metrics."""
    csv_path = Path("ml/results/maitri_inference_performance.csv")
    assert csv_path.exists(), "Performance results CSV must exist."

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 5
    scenarios_found = {r["scenario"] for r in rows}
    assert scenarios_found == {"WARM_NORMAL", "ANOMALY", "MISSING_DATA", "INSUFFICIENT_DATA", "MULTI_SENSOR"}

    for r in rows:
        assert int(r["sample_count"]) >= 100
        p50 = float(r["median_p50_ms"])
        p95 = float(r["p95_ms"])
        p99 = float(r["p99_ms"])
        assert 0.0 <= p50 <= p95 <= p99
