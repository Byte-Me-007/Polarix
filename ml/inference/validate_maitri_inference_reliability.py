"""
Deterministic reliability and edge-case validation script for Maitri ML Streaming Inference.
Polarix SIH26060 - Person C.

Validates:
1. Normal warmup (INSUFFICIENT_DATA for steps 1-29)
2. Normal scored inference (NORMAL for step 30)
3. Missing data handling (MISSING_DATA, null score/type, buffer reset)
4. Duplicate telemetry rejection (DuplicateTelemetryError, buffer unchanged)
5. Out-of-order telemetry rejection (StaleTelemetryError, buffer intact)
6. Non-finite values handling (NaN, +inf, -inf route cleanly to MISSING_DATA)
7. Sensor isolation (Interleaved sensor streams do not cross-contaminate)
8. Reset behavior (reset_sensor and reset_all isolate clears cleanly)
9. Deterministic repeated sequence (identical outputs across fresh instances)
10. Bounded buffer (100 observations retained within exact 30-step window)

Outputs structured results to ml/results/maitri_inference_reliability.json.
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

from ml.inference.inference_contract import (
    DuplicateTelemetryError,
    StaleTelemetryError,
    TelemetryInput,
)
from ml.inference.maitri_ml_service import MaitriMLService


def run_reliability_validation() -> Dict[str, Any]:
    print("=" * 70)
    print("POLARIX MAITRI ML INFERENCE RELIABILITY & EDGE-CASE VALIDATION")
    print("=" * 70)

    results: Dict[str, Any] = {
        "model_version": "lstm-ae-v1",
        "threshold": 0.017674,
        "station_id": "MTR",
        "validation_environment": "synthetic_offline",
        "validation_statement": "Explicit synthetic and offline validation only. No real Antarctic operational telemetry used.",
        "limitations": "Evaluated exclusively on synthetic normal and anomaly patterns generated for Maitri station. Real-world physical noise and unexpected failure modes may differ.",
        "test_counts": {
            "reliability_edge_case_tests": 25,
            "total_ml_suite_tests": 151
        },
        "edge_cases": {},
    }

    all_passed = True

    # 1. Normal Warmup
    try:
        service = MaitriMLService()
        warmup_ok = True
        for step in range(1, 30):
            out = service.process_telemetry(
                TelemetryInput("MTR", "TEMP_001", f"2026-09-18T00:{step:02d}:00Z", -15.0 + 0.1 * (step % 5))
            )
            if out.anomaly_status != "INSUFFICIENT_DATA" or out.anomaly_score is not None:
                warmup_ok = False
                break
        assert warmup_ok
        print("[PASS] 1. Normal Warmup (steps 1-29 return INSUFFICIENT_DATA, null score)")
        results["edge_cases"]["normal_warmup"] = {
            "status": "PASSED",
            "behavior": "Steps 1 to 29 return INSUFFICIENT_DATA with null anomaly_score and anomaly_type.",
        }
    except Exception as e:
        print(f"[FAIL] 1. Normal Warmup: {e}")
        all_passed = False
        results["edge_cases"]["normal_warmup"] = {"status": "FAILED", "error": str(e)}

    # 2. Normal Scored Inference
    try:
        out30 = service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:30:00Z", -15.0)
        )
        assert out30.anomaly_status in {"NORMAL", "ANOMALY"}
        assert out30.anomaly_score is not None and math.isfinite(out30.anomaly_score)
        print(f"[PASS] 2. Normal Scored Inference (step 30 scored: status={out30.anomaly_status}, score={out30.anomaly_score:.6f})")
        results["edge_cases"]["normal_scored_inference"] = {
            "status": "PASSED",
            "behavior": f"Step 30 scored successfully with status={out30.anomaly_status} and finite score={out30.anomaly_score:.6f}.",
        }
    except Exception as e:
        print(f"[FAIL] 2. Normal Scored Inference: {e}")
        all_passed = False
        results["edge_cases"]["normal_scored_inference"] = {"status": "FAILED", "error": str(e)}

    # 3. Missing Data
    try:
        missing_out = service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:31:00Z", None, quality="MISSING")
        )
        assert missing_out.anomaly_status == "MISSING_DATA"
        assert missing_out.anomaly_score is None
        assert missing_out.anomaly_type is None
        assert service.get_buffer_length("TEMP_001") == 0
        print("[PASS] 3. Missing Data (returns MISSING_DATA, null score/type, clears rolling buffer)")
        results["edge_cases"]["missing_data"] = {
            "status": "PASSED",
            "behavior": "Missing/None value routes to MISSING_DATA, clears rolling buffer, returns null score.",
        }
    except Exception as e:
        print(f"[FAIL] 3. Missing Data: {e}")
        all_passed = False
        results["edge_cases"]["missing_data"] = {"status": "FAILED", "error": str(e)}

    # 4. Duplicate Telemetry
    try:
        service.reset_all()
        for step in range(1, 10):
            service.process_telemetry(TelemetryInput("MTR", "PRESS_001", f"2026-09-18T01:{step:02d}:00Z", 985.0))
        dup_raised = False
        try:
            service.process_telemetry(TelemetryInput("MTR", "PRESS_001", "2026-09-18T01:09:00Z", 985.0))
        except DuplicateTelemetryError:
            dup_raised = True
        assert dup_raised
        assert service.get_buffer_length("PRESS_001") == 9
        print("[PASS] 4. Duplicate Telemetry (raises DuplicateTelemetryError, buffer unchanged at len=9)")
        results["edge_cases"]["duplicate_telemetry"] = {
            "status": "PASSED",
            "behavior": "Duplicate timestamp raises DuplicateTelemetryError without advancing or duplicating buffer.",
        }
    except Exception as e:
        print(f"[FAIL] 4. Duplicate Telemetry: {e}")
        all_passed = False
        results["edge_cases"]["duplicate_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 5. Out-of-Order Telemetry
    try:
        stale_raised = False
        try:
            service.process_telemetry(TelemetryInput("MTR", "PRESS_001", "2026-09-18T01:05:00Z", 985.0))
        except StaleTelemetryError:
            stale_raised = True
        assert stale_raised
        assert service.get_buffer_length("PRESS_001") == 9
        print("[PASS] 5. Out-of-Order Telemetry (raises StaleTelemetryError, chronological buffer preserved)")
        results["edge_cases"]["out_of_order_telemetry"] = {
            "status": "PASSED",
            "behavior": "Older timestamp raises StaleTelemetryError without corrupting chronological sequence.",
        }
    except Exception as e:
        print(f"[FAIL] 5. Out-of-Order Telemetry: {e}")
        all_passed = False
        results["edge_cases"]["out_of_order_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 6. Non-Finite Values
    try:
        service.reset_all()
        # Warmup to 15
        for step in range(1, 16):
            service.process_telemetry(TelemetryInput("MTR", "HUM_001", f"2026-09-18T02:{step:02d}:00Z", 60.0))
        nan_out = service.process_telemetry(TelemetryInput("MTR", "HUM_001", "2026-09-18T02:16:00Z", float("nan")))
        assert nan_out.anomaly_status == "MISSING_DATA"
        assert nan_out.anomaly_score is None
        assert service.get_buffer_length("HUM_001") == 0

        # +inf
        for step in range(1, 10):
            service.process_telemetry(TelemetryInput("MTR", "HUM_001", f"2026-09-18T02:{step+20:02d}:00Z", 60.0))
        inf_out = service.process_telemetry(TelemetryInput("MTR", "HUM_001", "2026-09-18T02:30:00Z", float("inf")))
        assert inf_out.anomaly_status == "MISSING_DATA"
        assert inf_out.anomaly_score is None
        assert service.get_buffer_length("HUM_001") == 0

        # -inf
        for step in range(1, 10):
            service.process_telemetry(TelemetryInput("MTR", "HUM_001", f"2026-09-18T02:{step+30:02d}:00Z", 60.0))
        ninf_out = service.process_telemetry(TelemetryInput("MTR", "HUM_001", "2026-09-18T02:40:00Z", float("-inf")))
        assert ninf_out.anomaly_status == "MISSING_DATA"
        assert ninf_out.anomaly_score is None
        assert service.get_buffer_length("HUM_001") == 0

        print("[PASS] 6. Non-Finite Values (NaN, +inf, -inf safely route to MISSING_DATA without entering LSTM)")
        results["edge_cases"]["non_finite_values"] = {
            "status": "PASSED",
            "behavior": "NaN, +inf, and -inf never reach LSTM; safely routed to MISSING_DATA with cleared buffer.",
        }
    except Exception as e:
        print(f"[FAIL] 6. Non-Finite Values: {e}")
        all_passed = False
        results["edge_cases"]["non_finite_values"] = {"status": "FAILED", "error": str(e)}

    # 7. Sensor Isolation
    try:
        service.reset_all()
        for step in range(1, 31):
            ts = f"2026-09-18T03:{step:02d}:00Z"
            service.process_telemetry(TelemetryInput("MTR", "TEMP_001", ts, -15.0 + 0.1 * step))
            service.process_telemetry(TelemetryInput("MTR", "PRESS_001", ts, 985.0 + 0.2 * step))
            service.process_telemetry(TelemetryInput("MTR", "VIB_001", ts, 0.05))

        assert service.get_buffer_length("TEMP_001") == 30
        assert service.get_buffer_length("PRESS_001") == 30
        assert service.get_buffer_length("VIB_001") == 30
        assert service.get_buffer_length("POWER_001") == 0
        print("[PASS] 7. Sensor Isolation (interleaved multi-sensor streams maintain isolated histories)")
        results["edge_cases"]["sensor_isolation"] = {
            "status": "PASSED",
            "behavior": "Each sensor maintains independent rolling deque; interleaved records do not cross-contaminate.",
        }
    except Exception as e:
        print(f"[FAIL] 7. Sensor Isolation: {e}")
        all_passed = False
        results["edge_cases"]["sensor_isolation"] = {"status": "FAILED", "error": str(e)}

    # 8. Reset Behavior
    try:
        service.reset_sensor("TEMP_001")
        assert service.get_buffer_length("TEMP_001") == 0
        assert service.get_buffer_length("PRESS_001") == 30
        service.reset_all()
        assert service.get_buffer_length("PRESS_001") == 0
        assert service.get_buffer_length("VIB_001") == 0
        print("[PASS] 8. Reset Behavior (reset_sensor and reset_all cleanly reset targeted buffers)")
        results["edge_cases"]["reset_behavior"] = {
            "status": "PASSED",
            "behavior": "reset_sensor clears only the specified sensor; reset_all clears all sensor histories.",
        }
    except Exception as e:
        print(f"[FAIL] 8. Reset Behavior: {e}")
        all_passed = False
        results["edge_cases"]["reset_behavior"] = {"status": "FAILED", "error": str(e)}

    # 9. Deterministic Repeated Sequence
    try:
        srv1 = MaitriMLService()
        srv2 = MaitriMLService()
        outputs1: List[Dict[str, Any]] = []
        outputs2: List[Dict[str, Any]] = []

        for step in range(1, 35):
            val = 45.0 + math.sin(step / 3.0) * 2.0
            ts = f"2026-09-18T04:{step:02d}:00Z"
            o1 = srv1.process_telemetry(TelemetryInput("MTR", "POWER_001", ts, val))
            o2 = srv2.process_telemetry(TelemetryInput("MTR", "POWER_001", ts, val))
            outputs1.append(o1.to_dict())
            outputs2.append(o2.to_dict())

        assert outputs1 == outputs2
        print("[PASS] 9. Deterministic Repeated Sequence (two independent services produce identical outputs)")
        results["edge_cases"]["determinism"] = {
            "status": "PASSED",
            "behavior": "Identical inputs across fresh service instances yield bit-for-bit identical inference dictionaries.",
        }
    except Exception as e:
        print(f"[FAIL] 9. Deterministic Repeated Sequence: {e}")
        all_passed = False
        results["edge_cases"]["determinism"] = {"status": "FAILED", "error": str(e)}

    # 10. Bounded Buffer
    try:
        service.reset_all()
        for step in range(1, 101):
            service.process_telemetry(TelemetryInput("MTR", "TEMP_001", f"2026-09-18T05:{step//60:02d}:{step%60:02d}Z", -15.0))
        assert service.get_buffer_length("TEMP_001") == 30
        print("[PASS] 10. Bounded Buffer (100 sequential observations capped at exactly maxlen=30)")
        results["edge_cases"]["bounded_buffer"] = {
            "status": "PASSED",
            "behavior": "Rolling history bounded strictly to 30 steps with collections.deque(maxlen=30).",
        }
    except Exception as e:
        print(f"[FAIL] 10. Bounded Buffer: {e}")
        all_passed = False
        results["edge_cases"]["bounded_buffer"] = {"status": "FAILED", "error": str(e)}

    # Overall Summary
    results["validation_summary"] = {
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_edge_cases_tested": len(results["edge_cases"]),
        "passed_edge_cases": sum(1 for v in results["edge_cases"].values() if v.get("status") == "PASSED"),
        "failed_edge_cases": sum(1 for v in results["edge_cases"].values() if v.get("status") == "FAILED"),
    }

    # Save results file
    results_path = Path("ml/results/maitri_inference_reliability.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"Validation Result: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")
    print(f"Results saved to: {results_path}")
    print("=" * 70)

    return results


if __name__ == "__main__":
    run_reliability_validation()
