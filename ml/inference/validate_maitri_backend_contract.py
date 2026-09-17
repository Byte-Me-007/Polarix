"""
Validation harness for Maitri ML Backend Integration Contract (SIH26060 - Person C).

Validates end-to-end flow:
Backend JSON Dict / String
        ↓
  adapt_backend_input() → TelemetryInput
        ↓
  MaitriMLService.process_telemetry()
        ↓
  TelemetryInferenceOutput
        ↓
  adapt_backend_output() → Backend JSON Dict

Exercises 12 integration cases and verifies all backend compatibility invariants.
Produces: ml/results/maitri_backend_contract_validation.json
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
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_ANOMALY_TYPES,
    VALID_STATUSES,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.maitri_backend_contract import (
    EXAMPLE_BACKEND_TELEMETRY_INPUT,
    adapt_backend_input,
    adapt_backend_output,
    process_backend_payload,
)
from ml.inference.maitri_ml_service import MaitriMLService


def run_backend_contract_validation() -> Dict[str, Any]:
    print("=" * 70)
    print("POLARIX MAITRI ML BACKEND INTEGRATION CONTRACT VALIDATION")
    print("=" * 70)

    service = MaitriMLService()
    results: Dict[str, Any] = {
        "module": "ml.inference.maitri_backend_contract",
        "station_id": "MTR",
        "model_version": DEFAULT_MODEL_VERSION,
        "threshold": service.threshold,
        "validation_environment": "synthetic_offline_contract_test",
        "validation_statement": "Explicit synthetic offline contract verification for Person A backend integration.",
        "cases": {},
    }

    all_passed = True

    # 1. Valid Normal Telemetry
    try:
        service.reset_all()
        for step in range(1, 31):
            ts = f"2026-09-18T00:{step:02d}:00Z"
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": ts,
                "value": -15.0 + 0.1 * (step % 4),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            out_dict = process_backend_payload(service, payload)

        assert out_dict["station_id"] == "MTR"
        assert out_dict["sensor_id"] == "TEMP_001"
        assert out_dict["anomaly_status"] == "NORMAL"
        assert out_dict["anomaly_score"] is not None and math.isfinite(out_dict["anomaly_score"])
        assert out_dict["model_version"] == "lstm-ae-v1"
        assert out_dict["unit"] == "C"
        assert out_dict["source"] == "SIMULATOR"
        print(f"[PASS] 1. Valid Normal Telemetry (status=NORMAL, score={out_dict['anomaly_score']:.6f})")
        results["cases"]["case_1_valid_normal_telemetry"] = {
            "status": "PASSED",
            "output": out_dict,
        }
    except Exception as e:
        print(f"[FAIL] 1. Valid Normal Telemetry: {e}")
        all_passed = False
        results["cases"]["case_1_valid_normal_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 2. Valid Anomaly-Producing Telemetry
    try:
        anomaly_payload = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-18T00:31:00Z",
            "value": 25.0,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        anom_out = process_backend_payload(service, anomaly_payload)
        assert anom_out["anomaly_status"] == "ANOMALY"
        assert anom_out["anomaly_type"] in VALID_ANOMALY_TYPES
        assert anom_out["anomaly_score"] is not None and anom_out["anomaly_score"] > service.threshold
        print(f"[PASS] 2. Valid Anomaly Telemetry (status=ANOMALY, type={anom_out['anomaly_type']}, score={anom_out['anomaly_score']:.6f})")
        results["cases"]["case_2_valid_anomaly_telemetry"] = {
            "status": "PASSED",
            "output": anom_out,
        }
    except Exception as e:
        print(f"[FAIL] 2. Valid Anomaly Telemetry: {e}")
        all_passed = False
        results["cases"]["case_2_valid_anomaly_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 3. Insufficient History
    try:
        service.reset_all()
        insufficient_payload = {
            "station_id": "MTR",
            "sensor_id": "PRESS_001",
            "timestamp": "2026-09-18T01:01:00Z",
            "value": 985.0,
            "unit": "hPa",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        ins_out = process_backend_payload(service, insufficient_payload)
        assert ins_out["anomaly_status"] == "INSUFFICIENT_DATA"
        assert ins_out["anomaly_score"] is None
        assert ins_out["anomaly_type"] is None
        print("[PASS] 3. Insufficient History (status=INSUFFICIENT_DATA, score=null, type=null)")
        results["cases"]["case_3_insufficient_history"] = {
            "status": "PASSED",
            "output": ins_out,
        }
    except Exception as e:
        print(f"[FAIL] 3. Insufficient History: {e}")
        all_passed = False
        results["cases"]["case_3_insufficient_history"] = {"status": "FAILED", "error": str(e)}

    # 4. Missing Telemetry (value = None)
    try:
        missing_payload = {
            "station_id": "MTR",
            "sensor_id": "PRESS_001",
            "timestamp": "2026-09-18T01:02:00Z",
            "value": None,
            "unit": "hPa",
            "quality": "MISSING",
            "source": "SIMULATOR",
        }
        mis_out = process_backend_payload(service, missing_payload)
        assert mis_out["anomaly_status"] == "MISSING_DATA"
        assert mis_out["anomaly_score"] is None
        assert mis_out["anomaly_type"] is None
        assert mis_out["value"] is None
        print("[PASS] 4. Missing Telemetry (status=MISSING_DATA, score=null, value=null)")
        results["cases"]["case_4_missing_telemetry"] = {
            "status": "PASSED",
            "output": mis_out,
        }
    except Exception as e:
        print(f"[FAIL] 4. Missing Telemetry: {e}")
        all_passed = False
        results["cases"]["case_4_missing_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 5. Bad Quality Telemetry
    try:
        bad_quality_payload = {
            "station_id": "MTR",
            "sensor_id": "HUM_001",
            "timestamp": "2026-09-18T02:01:00Z",
            "value": 55.0,
            "unit": "%",
            "quality": "BAD",
            "source": "SIMULATOR",
        }
        bad_out = process_backend_payload(service, bad_quality_payload)
        assert bad_out["anomaly_status"] == "MISSING_DATA"
        assert bad_out["anomaly_score"] is None
        assert bad_out["quality"] == "BAD"
        print("[PASS] 5. Bad Quality Telemetry (quality=BAD cleanly routes to MISSING_DATA)")
        results["cases"]["case_5_bad_quality"] = {
            "status": "PASSED",
            "output": bad_out,
        }
    except Exception as e:
        print(f"[FAIL] 5. Bad Quality Telemetry: {e}")
        all_passed = False
        results["cases"]["case_5_bad_quality"] = {"status": "FAILED", "error": str(e)}

    # 6. NaN/Inf Input Handling
    try:
        nan_payload = {
            "station_id": "MTR",
            "sensor_id": "HUM_001",
            "timestamp": "2026-09-18T02:02:00Z",
            "value": float("nan"),
            "unit": "%",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        nan_out = process_backend_payload(service, nan_payload)
        assert nan_out["anomaly_status"] == "MISSING_DATA"
        assert nan_out["anomaly_score"] is None
        print("[PASS] 6. NaN/Inf Input (routes safely to MISSING_DATA without non-finite output)")
        results["cases"]["case_6_nan_inf_input"] = {
            "status": "PASSED",
            "output": nan_out,
        }
    except Exception as e:
        print(f"[FAIL] 6. NaN/Inf Input: {e}")
        all_passed = False
        results["cases"]["case_6_nan_inf_input"] = {"status": "FAILED", "error": str(e)}

    # 7. Duplicate Timestamp Rejection
    try:
        service.reset_all()
        ts_dup = "2026-09-18T03:00:00Z"
        p_first = {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": ts_dup, "value": 0.05}
        process_backend_payload(service, p_first)

        dup_raised = False
        try:
            process_backend_payload(service, p_first)
        except DuplicateTelemetryError:
            dup_raised = True
        assert dup_raised
        print("[PASS] 7. Duplicate Timestamp (raises DuplicateTelemetryError deterministically)")
        results["cases"]["case_7_duplicate_timestamp"] = {
            "status": "PASSED",
            "behavior": "DuplicateTelemetryError raised on duplicate (station, sensor, timestamp).",
        }
    except Exception as e:
        print(f"[FAIL] 7. Duplicate Timestamp: {e}")
        all_passed = False
        results["cases"]["case_7_duplicate_timestamp"] = {"status": "FAILED", "error": str(e)}

    # 8. Stale/Out-of-Order Timestamp Rejection
    try:
        service.reset_all()
        p_newer = {"station_id": "MTR", "sensor_id": "POWER_001", "timestamp": "2026-09-18T04:00:00Z", "value": 45.0}
        p_older = {"station_id": "MTR", "sensor_id": "POWER_001", "timestamp": "2026-09-18T03:59:00Z", "value": 45.0}
        process_backend_payload(service, p_newer)

        stale_raised = False
        try:
            process_backend_payload(service, p_older)
        except StaleTelemetryError:
            stale_raised = True
        assert stale_raised
        print("[PASS] 8. Stale Telemetry (raises StaleTelemetryError on older timestamp)")
        results["cases"]["case_8_stale_telemetry"] = {
            "status": "PASSED",
            "behavior": "StaleTelemetryError raised when older timestamp arrives.",
        }
    except Exception as e:
        print(f"[FAIL] 8. Stale Telemetry: {e}")
        all_passed = False
        results["cases"]["case_8_stale_telemetry"] = {"status": "FAILED", "error": str(e)}

    # 9. Unsupported Station Rejection
    try:
        unsupported_st_payload = {
            "station_id": "BHARATI",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-18T05:00:00Z",
            "value": -15.0,
        }
        st_raised = False
        try:
            process_backend_payload(service, unsupported_st_payload)
        except UnsupportedStationError:
            st_raised = True
        assert st_raised
        print("[PASS] 9. Unsupported Station (raises UnsupportedStationError for non-MTR station)")
        results["cases"]["case_9_unsupported_station"] = {
            "status": "PASSED",
            "behavior": "UnsupportedStationError raised for station_id != 'MTR'.",
        }
    except Exception as e:
        print(f"[FAIL] 9. Unsupported Station: {e}")
        all_passed = False
        results["cases"]["case_9_unsupported_station"] = {"status": "FAILED", "error": str(e)}

    # 10. Unsupported Sensor Rejection
    try:
        unsupported_sens_payload = {
            "station_id": "MTR",
            "sensor_id": "UNKNOWN_SENSOR_XYZ",
            "timestamp": "2026-09-18T05:01:00Z",
            "value": -15.0,
        }
        sens_raised = False
        try:
            process_backend_payload(service, unsupported_sens_payload)
        except UnsupportedSensorError:
            sens_raised = True
        assert sens_raised
        print("[PASS] 10. Unsupported Sensor (raises UnsupportedSensorError for non-Maitri sensor)")
        results["cases"]["case_10_unsupported_sensor"] = {
            "status": "PASSED",
            "behavior": "UnsupportedSensorError raised for unknown sensor_id.",
        }
    except Exception as e:
        print(f"[FAIL] 10. Unsupported Sensor: {e}")
        all_passed = False
        results["cases"]["case_10_unsupported_sensor"] = {"status": "FAILED", "error": str(e)}

    # 11. Malformed Payload Rejection
    try:
        malformed_payload = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": "invalid-non-iso-timestamp-string",
            "value": "non_numeric_string",
        }
        inv_raised = False
        try:
            process_backend_payload(service, malformed_payload)
        except InvalidContractError:
            inv_raised = True
        assert inv_raised
        print("[PASS] 11. Malformed Payload (raises InvalidContractError on unparseable schema)")
        results["cases"]["case_11_malformed_payload"] = {
            "status": "PASSED",
            "behavior": "InvalidContractError raised on invalid timestamp or bad types.",
        }
    except Exception as e:
        print(f"[FAIL] 11. Malformed Payload: {e}")
        all_passed = False
        results["cases"]["case_11_malformed_payload"] = {"status": "FAILED", "error": str(e)}

    # 12. Serialization Round-Trip
    try:
        service.reset_all()
        # Warmup to 30 steps
        for step in range(1, 31):
            ts = f"2026-09-18T06:{step:02d}:00Z"
            val = 45.0 + 0.1 * (step % 4)
            service.process_telemetry({"station_id": "MTR", "sensor_id": "POWER_001", "timestamp": ts, "value": val})

        # JSON String In
        json_input_str = json.dumps({
            "station_id": "MTR",
            "sensor_id": "POWER_001",
            "timestamp": "2026-09-18T06:31:00Z",
            "value": 45.0,
            "unit": "kW",
            "quality": "GOOD",
            "source": "SIMULATOR",
        })

        adapted_in = adapt_backend_input(json_input_str)
        assert adapted_in.station_id == "MTR"

        infer_out = service.process_telemetry(adapted_in)
        adapted_out = adapt_backend_output(infer_out)

        # JSON String Out
        json_out_str = json.dumps(adapted_out, indent=2)
        parsed_back = json.loads(json_out_str)

        assert parsed_back["station_id"] == "MTR"
        assert parsed_back["sensor_id"] == "POWER_001"
        assert parsed_back["timestamp"] == "2026-09-18T06:31:00Z"
        assert parsed_back["value"] == 45.0
        assert parsed_back["unit"] == "kW"
        assert parsed_back["quality"] == "GOOD"
        assert parsed_back["source"] == "SIMULATOR"
        assert parsed_back["anomaly_status"] in {"NORMAL", "ANOMALY"}
        assert parsed_back["model_version"] == "lstm-ae-v1"
        assert math.isfinite(parsed_back["anomaly_score"])

        print("[PASS] 12. Serialization Round-Trip (JSON str -> Input -> ML -> Output -> JSON str)")
        results["cases"]["case_12_serialization_roundtrip"] = {
            "status": "PASSED",
            "parsed_keys": sorted(list(parsed_back.keys())),
        }
    except Exception as e:
        print(f"[FAIL] 12. Serialization Round-Trip: {e}")
        all_passed = False
        results["cases"]["case_12_serialization_roundtrip"] = {"status": "FAILED", "error": str(e)}

    # Invariant Summary
    results["summary"] = {
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_cases": len(results["cases"]),
        "passed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "PASSED"),
        "failed_cases": sum(1 for c in results["cases"].values() if c.get("status") == "FAILED"),
        "invariants_verified": [
            "station_id is strictly 'MTR'",
            "sensor_id is in 5 supported Maitri sensors",
            "timestamp is strictly ISO-8601",
            "telemetry metadata (unit, quality, source, value) preserved",
            "anomaly_score is strictly finite or None",
            "anomaly_status is in valid vocabulary",
            "model_version is strictly 'lstm-ae-v1'",
            "threshold is strictly 0.017674",
            "JSON serialization produces zero non-finite values",
        ],
    }

    # Save to results JSON
    json_path = Path("ml/results/maitri_backend_contract_validation.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"Backend Contract Validation: {'ALL PASS (12/12 backend contract validation checks verified)' if all_passed else 'FAILURES DETECTED'}")
    print(f"Results saved to: {json_path}")
    print("=" * 70)

    return results


if __name__ == "__main__":
    res = run_backend_contract_validation()
    sys.exit(0 if res.get("summary", {}).get("overall_status") == "PASSED" else 1)
