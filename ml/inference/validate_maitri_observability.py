"""
Deterministic validation script for Maitri ML Inference Observability & Diagnostics.
Polarix SIH26060 - Person C.

Exercises:
1. NORMAL telemetry diagnostics
2. ANOMALY telemetry diagnostics
3. INSUFFICIENT_DATA diagnostics
4. MISSING_DATA diagnostics
5. NaN/Inf input diagnostics
6. Duplicate timestamp rejection diagnostics
7. Stale/out-of-order rejection diagnostics
8. Sensor isolation across diagnostic records
9. Reset behavior diagnostics
10. Model version and threshold propagation
11. Bounded diagnostic history limit
12. Diagnostic JSON serialization

Produces: ml/results/maitri_observability_validation.json
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
from ml.inference.inference_diagnostics import InferenceDiagnosticRecord
from ml.inference.maitri_ml_service import MaitriMLService


def run_observability_validation() -> Dict[str, Any]:
    print("=" * 70)
    print("POLARIX MAITRI ML INFERENCE OBSERVABILITY & AUDIT VALIDATION")
    print("=" * 70)

    results: Dict[str, Any] = {
        "module": "ml.inference.inference_diagnostics",
        "station_id": "MTR",
        "model_version": "lstm-ae-v1",
        "threshold": 0.017674,
        "validation_environment": "synthetic_offline",
        "validation_statement": "Explicit synthetic and offline validation only. No real Antarctic operational telemetry used.",
        "cases": {},
    }

    all_passed = True
    service = MaitriMLService(max_diagnostics_history=50)

    # 1. NORMAL Telemetry
    try:
        service.reset_all()
        service.clear_diagnostics()
        for step in range(1, 31):
            service.process_telemetry(
                TelemetryInput("MTR", "TEMP_001", f"2026-09-18T00:{step:02d}:00Z", -15.0 + 0.1 * (step % 4))
            )
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "SUCCESS"
        assert diag.anomaly_status == "NORMAL"
        assert diag.anomaly_score is not None and diag.anomaly_score <= service.threshold
        assert diag.buffer_length == 30
        assert math.isfinite(diag.processing_time_ms) and diag.processing_time_ms >= 0.0
        print(f"[PASS] 1. NORMAL Telemetry (status=SUCCESS, score={diag.anomaly_score:.6f}, time={diag.processing_time_ms:.4f}ms)")
        results["cases"]["case_1_normal_telemetry"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 1. NORMAL Telemetry: {e}")
        all_passed = False
        results["cases"]["case_1_normal_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 2. ANOMALY Telemetry
    try:
        service.process_telemetry(
            TelemetryInput("MTR", "TEMP_001", "2026-09-18T00:31:00Z", 25.0)
        )
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "SUCCESS"
        assert diag.anomaly_status == "ANOMALY"
        assert diag.anomaly_type == "SPIKE"
        assert diag.anomaly_score is not None and diag.anomaly_score > service.threshold
        assert diag.buffer_length == 30
        print(f"[PASS] 2. ANOMALY Telemetry (status=SUCCESS, type=SPIKE, score={diag.anomaly_score:.6f})")
        results["cases"]["case_2_anomaly_telemetry"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 2. ANOMALY Telemetry: {e}")
        all_passed = False
        results["cases"]["case_2_anomaly_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 3. INSUFFICIENT_DATA
    try:
        service.reset_all()
        service.clear_diagnostics()
        service.process_telemetry(
            TelemetryInput("MTR", "PRESS_001", "2026-09-18T01:01:00Z", 985.0)
        )
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "INSUFFICIENT_DATA"
        assert diag.anomaly_status == "INSUFFICIENT_DATA"
        assert diag.anomaly_score is None
        assert diag.buffer_length == 1
        print("[PASS] 3. INSUFFICIENT_DATA (status=INSUFFICIENT_DATA, score=null, buf=1)")
        results["cases"]["case_3_insufficient_data"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 3. INSUFFICIENT_DATA: {e}")
        all_passed = False
        results["cases"]["case_3_insufficient_data"] = {"status": "FAILED", "error": str(e)}

    # 4. MISSING_DATA
    try:
        service.process_telemetry(
            TelemetryInput("MTR", "PRESS_001", "2026-09-18T01:02:00Z", None, quality="MISSING")
        )
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "MISSING_DATA"
        assert diag.anomaly_status == "MISSING_DATA"
        assert diag.anomaly_score is None
        assert diag.buffer_length == 0
        print("[PASS] 4. MISSING_DATA (status=MISSING_DATA, score=null, buf=0)")
        results["cases"]["case_4_missing_data"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 4. MISSING_DATA: {e}")
        all_passed = False
        results["cases"]["case_4_missing_data"] = {"status": "FAILED", "error": str(e)}

    # 5. NaN/Inf Input
    try:
        service.process_telemetry(
            TelemetryInput("MTR", "HUM_001", "2026-09-18T02:01:00Z", float("nan"))
        )
        diag_nan = service.get_last_diagnostic()
        assert diag_nan is not None
        assert diag_nan.inference_status == "MISSING_DATA"

        service.process_telemetry(
            TelemetryInput("MTR", "HUM_001", "2026-09-18T02:02:00Z", float("inf"))
        )
        diag_inf = service.get_last_diagnostic()
        assert diag_inf is not None
        assert diag_inf.inference_status == "MISSING_DATA"
        print("[PASS] 5. NaN/Inf Input (safely recorded as MISSING_DATA)")
        results["cases"]["case_5_nan_inf_input"] = {
            "status": "PASSED",
            "diagnostic": diag_inf.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 5. NaN/Inf Input: {e}")
        all_passed = False
        results["cases"]["case_5_nan_inf_input"] = {"status": "FAILED", "error": str(e)}

    # 6. Duplicate Timestamp Rejection
    try:
        service.process_telemetry(
            TelemetryInput("MTR", "VIB_001", "2026-09-18T03:00:00Z", 0.05)
        )
        dup_raised = False
        try:
            service.process_telemetry(
                TelemetryInput("MTR", "VIB_001", "2026-09-18T03:00:00Z", 0.05)
            )
        except DuplicateTelemetryError:
            dup_raised = True
        assert dup_raised
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "REJECTED_DUPLICATE"
        assert diag.error_message is not None
        print("[PASS] 6. Duplicate Timestamp (status=REJECTED_DUPLICATE captured)")
        results["cases"]["case_6_duplicate_timestamp"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 6. Duplicate Timestamp: {e}")
        all_passed = False
        results["cases"]["case_6_duplicate_timestamp"] = {"status": "FAILED", "error": str(e)}

    # 7. Stale/Out-of-Order Rejection
    try:
        service.process_telemetry(
            TelemetryInput("MTR", "POWER_001", "2026-09-18T04:00:00Z", 45.0)
        )
        stale_raised = False
        try:
            service.process_telemetry(
                TelemetryInput("MTR", "POWER_001", "2026-09-18T03:59:00Z", 45.0)
            )
        except StaleTelemetryError:
            stale_raised = True
        assert stale_raised
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.inference_status == "REJECTED_STALE"
        assert diag.error_message is not None
        print("[PASS] 7. Stale Telemetry (status=REJECTED_STALE captured)")
        results["cases"]["case_7_stale_telemetry"] = {
            "status": "PASSED",
            "diagnostic": diag.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 7. Stale Telemetry: {e}")
        all_passed = False
        results["cases"]["case_7_stale_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 8. Sensor Isolation
    try:
        service.reset_all()
        service.clear_diagnostics()
        for step in range(1, 10):
            ts = f"2026-09-18T05:{step:02d}:00Z"
            service.process_telemetry(TelemetryInput("MTR", "TEMP_001", ts, -15.0))
            service.process_telemetry(TelemetryInput("MTR", "PRESS_001", ts, 985.0))
        recent = service.get_recent_diagnostics()
        assert len(recent) == 18
        temp_diags = [r for r in recent if r.sensor_id == "TEMP_001"]
        press_diags = [r for r in recent if r.sensor_id == "PRESS_001"]
        assert len(temp_diags) == 9 and len(press_diags) == 9
        assert temp_diags[-1].buffer_length == 9
        assert press_diags[-1].buffer_length == 9
        print("[PASS] 8. Sensor Isolation (diagnostics track isolated sensor buffers)")
        results["cases"]["case_8_sensor_isolation"] = {
            "status": "PASSED",
            "temp_count": len(temp_diags),
            "press_count": len(press_diags),
        }
    except Exception as e:
        print(f"[FAIL] 8. Sensor Isolation: {e}")
        all_passed = False
        results["cases"]["case_8_sensor_isolation"] = {"status": "FAILED", "error": str(e)}

    # 9. Reset Behavior
    try:
        service.reset_sensor("TEMP_001")
        assert service.get_buffer_length("TEMP_001") == 0
        assert service.get_buffer_length("PRESS_001") == 9
        service.clear_diagnostics()
        assert service.get_last_diagnostic() is None
        print("[PASS] 9. Reset Behavior (reset_sensor and clear_diagnostics operate cleanly)")
        results["cases"]["case_9_reset_behavior"] = {
            "status": "PASSED",
            "behavior": "Buffer and diagnostic history flushes properly.",
        }
    except Exception as e:
        print(f"[FAIL] 9. Reset Behavior: {e}")
        all_passed = False
        results["cases"]["case_9_reset_behavior"] = {"status": "FAILED", "error": str(e)}

    # 10. Model Version and Threshold Presence
    try:
        service.process_telemetry(TelemetryInput("MTR", "TEMP_001", "2026-09-18T06:00:00Z", -15.0))
        diag = service.get_last_diagnostic()
        assert diag is not None
        assert diag.model_version == "lstm-ae-v1"
        assert diag.threshold == 0.017674
        print("[PASS] 10. Model Version & Threshold Presence (lstm-ae-v1, 0.017674)")
        results["cases"]["case_10_version_and_threshold"] = {
            "status": "PASSED",
            "model_version": diag.model_version,
            "threshold": diag.threshold,
        }
    except Exception as e:
        print(f"[FAIL] 10. Model Version & Threshold: {e}")
        all_passed = False
        results["cases"]["case_10_version_and_threshold"] = {"status": "FAILED", "error": str(e)}

    # 11. Bounded Diagnostic History
    try:
        lim_service = MaitriMLService(max_diagnostics_history=15)
        for step in range(1, 40):
            lim_service.process_telemetry(
                TelemetryInput("MTR", "TEMP_001", f"2026-09-18T07:{step:02d}:00Z", -15.0)
            )
        recent_lim = lim_service.get_recent_diagnostics()
        assert len(recent_lim) == 15
        print("[PASS] 11. Bounded Diagnostic History (strictly capped at max_history=15)")
        results["cases"]["case_11_bounded_history"] = {
            "status": "PASSED",
            "retained_count": len(recent_lim),
            "max_limit": 15,
        }
    except Exception as e:
        print(f"[FAIL] 11. Bounded Diagnostic History: {e}")
        all_passed = False
        results["cases"]["case_11_bounded_history"] = {"status": "FAILED", "error": str(e)}

    # 12. JSON Serialization
    try:
        diag = service.get_last_diagnostic()
        assert diag is not None
        json_output = diag.to_json(indent=2)
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)
        reconstructed = InferenceDiagnosticRecord.from_json(json_output)
        assert reconstructed == diag
        print("[PASS] 12. JSON Serialization (deterministic JSON round-trip verified)")
        results["cases"]["case_12_json_serialization"] = {
            "status": "PASSED",
            "serialized_keys": sorted(list(parsed.keys())),
        }
    except Exception as e:
        print(f"[FAIL] 12. JSON Serialization: {e}")
        all_passed = False
        results["cases"]["case_12_json_serialization"] = {"status": "FAILED", "error": str(e)}

    # Summary
    results["summary"] = {
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_cases": len(results["cases"]),
        "passed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "PASSED"),
        "failed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "FAILED"),
    }

    # Save results JSON
    results_path = Path("ml/results/maitri_observability_validation.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"Observability Validation Result: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")
    print(f"Results saved to: {results_path}")
    print("=" * 70)

    return results


if __name__ == "__main__":
    run_observability_validation()
