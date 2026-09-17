"""
Deterministic validation script for Maitri ML Inference Performance Benchmark.
Polarix SIH26060 - Person C.

Validates:
1. Benchmark JSON artifact presence and valid schema
2. Correct model version (lstm-ae-v1) and threshold (0.017674)
3. Finite, non-negative startup initialization latency
4. Presence of all 5 required scenarios: WARM_NORMAL, ANOMALY, MISSING_DATA, INSUFFICIENT_DATA, MULTI_SENSOR
5. Sample count consistency across scenarios
6. All latency metrics finite and non-negative
7. Monotonic percentile ordering: min <= P50 <= P90 <= P95 <= P99 <= max
8. Standard deviation non-negative
9. Presence of explicit synthetic offline disclaimers (no production SLA claims)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

EXPECTED_SCENARIOS = {
    "WARM_NORMAL",
    "ANOMALY",
    "MISSING_DATA",
    "INSUFFICIENT_DATA",
    "MULTI_SENSOR",
}

REQUIRED_METRICS = [
    "sample_count",
    "min_latency_ms",
    "max_latency_ms",
    "mean_latency_ms",
    "median_latency_ms",
    "p50_latency_ms",
    "p90_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "std_latency_ms",
]


def validate_performance_results(
    json_path: Path = Path("ml/results/maitri_inference_performance.json"),
) -> bool:
    print("=" * 70)
    print("POLARIX MAITRI ML INFERENCE PERFORMANCE VALIDATION")
    print("=" * 70)

    if not json_path.exists():
        print(f"[FAIL] Benchmark results file not found at: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    checks_passed = 0
    total_checks = 0

    def check(condition: bool, description: str) -> None:
        nonlocal checks_passed, total_checks
        total_checks += 1
        if condition:
            checks_passed += 1
            print(f"[PASS] {total_checks}. {description}")
        else:
            print(f"[FAIL] {total_checks}. {description}")

    # 1. Metadata Schema
    meta = data.get("benchmark_metadata", {})
    check(
        meta.get("model_version") == "lstm-ae-v1",
        "Metadata contains model_version == 'lstm-ae-v1'",
    )
    check(
        meta.get("threshold") == 0.017674,
        "Metadata contains frozen threshold == 0.017674",
    )
    check(
        meta.get("station_id") == "MTR",
        "Metadata specifies station_id == 'MTR'",
    )
    check(
        meta.get("benchmark_type") == "synthetic_offline_benchmark_only",
        "Metadata explicitly specifies 'synthetic_offline_benchmark_only'",
    )
    check(
        "disclaimer" in meta and len(meta["disclaimer"]) > 20,
        "Metadata contains comprehensive synthetic offline disclaimer",
    )

    # 2. Startup Metric
    startup = data.get("startup_initialization", {})
    startup_val = startup.get("startup_initialization_ms")
    check(
        startup_val is not None and isinstance(startup_val, (int, float)) and math.isfinite(startup_val) and startup_val >= 0.0,
        f"Startup initialization latency is finite and non-negative ({startup_val} ms)",
    )

    # 3. Scenarios Coverage
    scenarios = data.get("scenarios", {})
    check(
        set(scenarios.keys()) == EXPECTED_SCENARIOS,
        f"All 5 expected scenarios present: {sorted(EXPECTED_SCENARIOS)}",
    )

    # 4. Per-Scenario Metrics Validation
    for sc_name in sorted(EXPECTED_SCENARIOS):
        sc_data = scenarios.get(sc_name, {})
        has_all_metrics = all(m in sc_data for m in REQUIRED_METRICS)
        check(
            has_all_metrics,
            f"Scenario '{sc_name}' contains all required statistical metrics",
        )

        n_samples = sc_data.get("sample_count", 0)
        check(
            isinstance(n_samples, int) and n_samples >= 100,
            f"Scenario '{sc_name}' has sample_count >= 100 ({n_samples})",
        )

        # Finite and non-negative
        metrics_finite = all(
            isinstance(sc_data[m], (int, float)) and math.isfinite(sc_data[m]) and sc_data[m] >= 0.0
            for m in REQUIRED_METRICS
        )
        check(
            metrics_finite,
            f"Scenario '{sc_name}' all metric values are finite and non-negative",
        )

        # Monotonic Percentile Ordering
        min_v = sc_data.get("min_latency_ms", 0)
        p50_v = sc_data.get("p50_latency_ms", 0)
        p90_v = sc_data.get("p90_latency_ms", 0)
        p95_v = sc_data.get("p95_latency_ms", 0)
        p99_v = sc_data.get("p99_latency_ms", 0)
        max_v = sc_data.get("max_latency_ms", 0)

        monotonic = min_v <= p50_v <= p90_v <= p95_v <= p99_v <= max_v
        check(
            monotonic,
            f"Scenario '{sc_name}' satisfies monotonic ordering: min({min_v}) <= P50({p50_v}) <= P90({p90_v}) <= P95({p95_v}) <= P99({p99_v}) <= max({max_v})",
        )

    print("=" * 70)
    all_passed = (checks_passed == total_checks)
    if all_passed:
        print(f"ALL PASS ({checks_passed}/{total_checks} performance validation checks verified)")
    else:
        print(f"FAILURES DETECTED ({checks_passed}/{total_checks} passed)")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = validate_performance_results()
    sys.exit(0 if success else 1)
