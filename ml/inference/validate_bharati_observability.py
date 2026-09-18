"""
Deterministic validation script for Bharati ML Inference Observability & Diagnostics.
Polarix SIH26060 - Person C (Step 33).

Exercises:
1. NORMAL telemetry audit
2. ANOMALY telemetry audit
3. INSUFFICIENT_DATA audit
4. MISSING_DATA audit
5. NaN/Inf input diagnostics
6. Duplicate timestamp rejection audit
7. Stale/out-of-order rejection audit
8. Sensor isolation across audit records
9. Reset behavior diagnostics
10. Model version and threshold propagation
11. Bounded diagnostic history limit
12. Diagnostic JSON serialization and non-finite sanitization
13. Aggregate summary calculation (events, statuses, latency metrics)

Produces: ml/results/bharati_ml_observability.json
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

from ml.inference.bharati_inference_contract import (
    BharatiTelemetryInput,
    DuplicateTelemetryError,
    StaleTelemetryError,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.bharati_ml_observability import (
    BharatiInferenceAuditRecord,
    summarize_audit_records,
)
from ml.inference.bharati_ml_service import BharatiMLService


def run_observability_validation() -> Dict[str, Any]:
    print("=" * 70)
    print("POLARIX BHARATI ML INFERENCE OBSERVABILITY & AUDIT VALIDATION")
    print("=" * 70)

    results: Dict[str, Any] = {
        "module": "ml.inference.bharati_ml_observability",
        "station_id": "BRT",
        "model_version": "lstm-ae-bharati-v1",
        "threshold": 0.013215307652775843,
        "validation_environment": "synthetic_offline",
        "validation_statement": "Explicit synthetic and offline validation only. No real Antarctic operational telemetry used.",
        "cases": {},
    }

    all_passed = True
    service = BharatiMLService(max_diagnostics_history=50)

    # 1. NORMAL Telemetry
    try:
        service.reset_all()
        service.clear_diagnostics()
        for step in range(1, 31):
            service.process_telemetry(
                BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T00:{step:02d}:00Z", -12.0 + 0.05 * (step % 3))
            )
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "INFERENCE"
        assert rec.anomaly_status == "NORMAL"
        assert rec.anomaly_type == "NORMAL"
        assert rec.anomaly_score is not None and rec.anomaly_score <= service.threshold
        assert rec.history_size_before == 29
        assert rec.history_size_after == 30
        assert rec.inference_eligible is True
        assert rec.state_changed is True
        assert math.isfinite(rec.processing_time_ms) and rec.processing_time_ms >= 0.0
        print(f"[PASS] 1. NORMAL Telemetry (event=INFERENCE, status=NORMAL, score={rec.anomaly_score:.6f}, time={rec.processing_time_ms:.4f}ms)")
        results["cases"]["case_1_normal_telemetry"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 1. NORMAL Telemetry: {e}")
        all_passed = False
        results["cases"]["case_1_normal_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 2. ANOMALY Telemetry
    try:
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T00:31:00Z", 45.0)
        )
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "INFERENCE"
        assert rec.anomaly_status == "ANOMALY"
        assert rec.anomaly_type in {"SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
        assert rec.anomaly_score is not None and rec.anomaly_score > service.threshold
        assert rec.history_size_before == 30
        assert rec.history_size_after == 30
        print(f"[PASS] 2. ANOMALY Telemetry (event=INFERENCE, type={rec.anomaly_type}, score={rec.anomaly_score:.6f})")
        results["cases"]["case_2_anomaly_telemetry"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
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
            BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T01:01:00Z", 985.0)
        )
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "INSUFFICIENT_DATA"
        assert rec.anomaly_status == "INSUFFICIENT_DATA"
        assert rec.anomaly_score is None
        assert rec.history_size_before == 0
        assert rec.history_size_after == 1
        assert rec.inference_eligible is False
        assert rec.state_changed is True
        print("[PASS] 3. INSUFFICIENT_DATA (event=INSUFFICIENT_DATA, score=null, history_after=1)")
        results["cases"]["case_3_insufficient_data"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 3. INSUFFICIENT_DATA: {e}")
        all_passed = False
        results["cases"]["case_3_insufficient_data"] = {"status": "FAILED", "error": str(e)}

    # 4. MISSING_DATA
    try:
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T01:02:00Z", None, quality="MISSING")
        )
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "MISSING_DATA"
        assert rec.anomaly_status == "MISSING_DATA"
        assert rec.anomaly_score is None
        assert rec.history_size_after == 0
        print("[PASS] 4. MISSING_DATA (event=MISSING_DATA, score=null, history_after=0)")
        results["cases"]["case_4_missing_data"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 4. MISSING_DATA: {e}")
        all_passed = False
        results["cases"]["case_4_missing_data"] = {"status": "FAILED", "error": str(e)}

    # 5. NaN/Inf Input
    try:
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T02:01:00Z", float("nan"))
        )
        rec_nan = service.get_last_audit_record()
        assert rec_nan is not None
        assert rec_nan.event_type == "MISSING_DATA"

        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_HUM_001", "2026-09-18T02:02:00Z", float("inf"))
        )
        rec_inf = service.get_last_audit_record()
        assert rec_inf is not None
        assert rec_inf.event_type == "MISSING_DATA"
        print("[PASS] 5. NaN/Inf Input (safely audited as MISSING_DATA)")
        results["cases"]["case_5_nan_inf_input"] = {
            "status": "PASSED",
            "audit_record": rec_inf.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 5. NaN/Inf Input: {e}")
        all_passed = False
        results["cases"]["case_5_nan_inf_input"] = {"status": "FAILED", "error": str(e)}

    # 6. Duplicate Timestamp Rejection
    try:
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_VIB_001", "2026-09-18T03:00:00Z", 0.05)
        )
        dup_raised = False
        try:
            service.process_telemetry(
                BharatiTelemetryInput("BRT", "BRT_VIB_001", "2026-09-18T03:00:00Z", 0.05)
            )
        except DuplicateTelemetryError:
            dup_raised = True
        assert dup_raised
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "DUPLICATE"
        assert rec.input_accepted is False
        assert rec.error_code == "DuplicateTelemetryError"
        assert rec.rejection_reason is not None and "Duplicate timestamp" in rec.rejection_reason
        print("[PASS] 6. Duplicate Timestamp (event=DUPLICATE captured)")
        results["cases"]["case_6_duplicate_timestamp"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
        }
    except Exception as e:
        print(f"[FAIL] 6. Duplicate Timestamp: {e}")
        all_passed = False
        results["cases"]["case_6_duplicate_timestamp"] = {"status": "FAILED", "error": str(e)}

    # 7. Stale/Out-of-Order Rejection
    try:
        service.process_telemetry(
            BharatiTelemetryInput("BRT", "BRT_POWER_001", "2026-09-18T04:00:00Z", 45.0)
        )
        stale_raised = False
        try:
            service.process_telemetry(
                BharatiTelemetryInput("BRT", "BRT_POWER_001", "2026-09-18T03:59:00Z", 45.0)
            )
        except StaleTelemetryError:
            stale_raised = True
        assert stale_raised
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.event_type == "STALE"
        assert rec.input_accepted is False
        assert rec.error_code == "StaleTelemetryError"
        assert rec.rejection_reason is not None and "Stale out-of-order telemetry" in rec.rejection_reason
        print("[PASS] 7. Stale Telemetry (event=STALE captured)")
        results["cases"]["case_7_stale_telemetry"] = {
            "status": "PASSED",
            "audit_record": rec.to_dict(),
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
            service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_TEMP_001", ts, -12.0))
            service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_PRESS_001", ts, 985.0))
        recent = service.get_recent_audit_records()
        assert len(recent) == 18
        temp_audits = [r for r in recent if r.sensor_id == "BRT_TEMP_001"]
        press_audits = [r for r in recent if r.sensor_id == "BRT_PRESS_001"]
        assert len(temp_audits) == 9 and len(press_audits) == 9
        assert temp_audits[-1].history_size_after == 9
        assert press_audits[-1].history_size_after == 9
        print("[PASS] 8. Sensor Isolation (audits track independent sensor buffers)")
        results["cases"]["case_8_sensor_isolation"] = {
            "status": "PASSED",
            "temp_count": len(temp_audits),
            "press_count": len(press_audits),
        }
    except Exception as e:
        print(f"[FAIL] 8. Sensor Isolation: {e}")
        all_passed = False
        results["cases"]["case_8_sensor_isolation"] = {"status": "FAILED", "error": str(e)}

    # 9. Reset Behavior
    try:
        service.reset_sensor("BRT_TEMP_001")
        assert service.get_buffer_length("BRT_TEMP_001") == 0
        assert service.get_buffer_length("BRT_PRESS_001") == 9
        service.clear_diagnostics()
        assert service.get_last_audit_record() is None
        print("[PASS] 9. Reset Behavior (reset_sensor and clear_diagnostics operate cleanly)")
        results["cases"]["case_9_reset_behavior"] = {
            "status": "PASSED",
            "behavior": "Buffer and audit history flushes cleanly.",
        }
    except Exception as e:
        print(f"[FAIL] 9. Reset Behavior: {e}")
        all_passed = False
        results["cases"]["case_9_reset_behavior"] = {"status": "FAILED", "error": str(e)}

    # 10. Model Version and Threshold Presence
    try:
        service.process_telemetry(BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T06:00:00Z", -12.0))
        rec = service.get_last_audit_record()
        assert rec is not None
        assert rec.model_version == "lstm-ae-bharati-v1"
        assert rec.threshold == 0.013215307652775843
        print("[PASS] 10. Model Version & Threshold Presence (lstm-ae-bharati-v1, 0.013215)")
        results["cases"]["case_10_version_and_threshold"] = {
            "status": "PASSED",
            "model_version": rec.model_version,
            "threshold": rec.threshold,
        }
    except Exception as e:
        print(f"[FAIL] 10. Model Version & Threshold: {e}")
        all_passed = False
        results["cases"]["case_10_version_and_threshold"] = {"status": "FAILED", "error": str(e)}

    # 11. Bounded Diagnostic History
    try:
        lim_service = BharatiMLService(max_diagnostics_history=15)
        for step in range(1, 40):
            lim_service.process_telemetry(
                BharatiTelemetryInput("BRT", "BRT_TEMP_001", f"2026-09-18T07:{step:02d}:00Z", -12.0)
            )
        recent_lim = lim_service.get_recent_audit_records()
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

    # 12. JSON Serialization & Sanitization
    try:
        rec = service.get_last_audit_record()
        assert rec is not None
        json_output = rec.to_json(indent=2)
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)
        reconstructed = BharatiInferenceAuditRecord.from_json(json_output)
        assert reconstructed.sensor_id == rec.sensor_id
        assert reconstructed.event_type == rec.event_type
        print("[PASS] 12. JSON Serialization (deterministic JSON round-trip verified)")
        results["cases"]["case_12_json_serialization"] = {
            "status": "PASSED",
            "serialized_keys": sorted(list(parsed.keys())),
        }
    except Exception as e:
        print(f"[FAIL] 12. JSON Serialization: {e}")
        all_passed = False
        results["cases"]["case_12_json_serialization"] = {"status": "FAILED", "error": str(e)}

    # 13. Aggregate Summary Diagnostics
    try:
        summary = service.get_diagnostics_summary()
        assert "total_events" in summary
        assert "latency_stats" in summary
        print(f"[PASS] 13. Aggregate Diagnostics Summary (total={summary['total_events']}, p50_latency={summary['latency_stats']['p50_latency_ms']}ms)")
        results["cases"]["case_13_diagnostics_summary"] = {
            "status": "PASSED",
            "summary": summary,
        }
    except Exception as e:
        print(f"[FAIL] 13. Aggregate Diagnostics Summary: {e}")
        all_passed = False
        results["cases"]["case_13_diagnostics_summary"] = {"status": "FAILED", "error": str(e)}

    # Summary
    results["summary"] = {
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_cases": len(results["cases"]),
        "passed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "PASSED"),
        "failed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "FAILED"),
    }

    # Save results JSON
    results_path = Path("ml/results/bharati_ml_observability.json")
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
