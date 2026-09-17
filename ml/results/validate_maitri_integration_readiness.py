#!/usr/bin/env python3
"""
Polarix Maitri ML Integration Readiness Validation Runner (SIH26060 - Person C).

Executes deterministic validation checks verifying that the ML contract, backend adapters,
service boundary, ownership specifications, and documentation are ready for team integration.
Emits a structured JSON validation record and prints a concise PASS/FAIL summary.
"""

from __future__ import annotations

import datetime
import importlib
import json
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
)
from ml.models.model_registry import validate_model_artifacts


def run_integration_readiness_validation() -> Dict[str, Any]:
    """Execute deterministic validation checks for the Maitri ML integration readiness."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks: List[Dict[str, Any]] = []

    def record_check(name: str, passed: bool, details: str):
        checks.append({
            "check_name": name,
            "passed": passed,
            "details": details,
        })

    # Check 1: Readiness JSON existence & parsing
    json_path = _REPO_ROOT / "ml" / "results" / "maitri_ml_integration_readiness.json"
    if not json_path.exists():
        record_check("readiness_json_exists", False, f"Missing: {json_path}")
        data = {}
    else:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            record_check("readiness_json_exists", True, "Integration readiness JSON parsed successfully.")
        except Exception as e:
            record_check("readiness_json_exists", False, f"Failed to parse JSON: {e}")
            data = {}

    # Check 2: Readiness status & model invariants
    status_ok = data.get("readiness_status") == "ML interface and handoff are internally validated and ready for team integration."
    station_ok = data.get("station_id") == "MTR" and "MTR" in SUPPORTED_STATIONS
    version_ok = data.get("model_version") == "lstm-ae-v1" and DEFAULT_MODEL_VERSION == "lstm-ae-v1"
    thresh_ok = data.get("threshold") == 0.017674
    record_check(
        "readiness_status_and_model_invariants",
        status_ok and station_ok and version_ok and thresh_ok,
        f"Station={data.get('station_id')}, Version={data.get('model_version')}, Threshold={data.get('threshold')}."
    )

    # Check 3: Supported sensors and contract vocabulary
    expected_sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
    sensors_ok = sorted(data.get("supported_sensors", [])) == sorted(expected_sensors)
    expected_statuses = {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}
    expected_types = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
    statuses_ok = set(data.get("supported_statuses", [])) == expected_statuses
    types_ok = set(data.get("supported_anomaly_types", [])) == expected_types
    record_check(
        "supported_sensors_and_vocabulary",
        sensors_ok and statuses_ok and types_ok,
        f"Sensors={sensors_ok}, Statuses={statuses_ok}, Types={types_ok}."
    )

    # Check 4: Module and function importability
    try:
        service_mod = importlib.import_module(data.get("inference_entry_point", {}).get("module", "ml.inference.maitri_ml_service"))
        has_service = hasattr(service_mod, data.get("inference_entry_point", {}).get("class", "MaitriMLService"))

        adapter_mod = importlib.import_module(data.get("backend_adapter", {}).get("module", "ml.inference.maitri_backend_contract"))
        has_adapter_funcs = (
            hasattr(adapter_mod, "process_backend_payload")
            and hasattr(adapter_mod, "adapt_backend_input")
            and hasattr(adapter_mod, "adapt_backend_output")
        )
        record_check(
            "module_and_function_importability",
            has_service and has_adapter_funcs,
            "MaitriMLService and backend adapter functions exist and import cleanly."
        )
    except Exception as e:
        record_check("module_and_function_importability", False, f"Import error: {e}")

    # Check 5: Cryptographic model registry integrity
    try:
        report_obj = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
        rep_dict = report_obj.to_dict()
        valid_count = sum(1 for item in rep_dict["artifact_results"].values() if item.get("status") == "VALID")
        integrity_ok = rep_dict["overall_status"] == "VALID" and valid_count == 4
        record_check("model_artifact_integrity", integrity_ok, f"Artifacts verified: {valid_count}/4 matching SHA-256 manifest.")
        registry_report = rep_dict
    except Exception as e:
        record_check("model_artifact_integrity", False, f"Integrity error: {e}")
        registry_report = {"overall_status": "FAILED", "errors": [str(e)]}

    # Check 6: Integration checklist document existence
    doc_path = _REPO_ROOT / "ml" / "results" / "maitri_ml_integration_checklist.md"
    if doc_path.exists() and len(doc_path.read_text(encoding="utf-8")) > 1000:
        record_check("integration_checklist_document_exists", True, f"Checklist markdown exists ({doc_path.stat().st_size} bytes).")
    else:
        record_check("integration_checklist_document_exists", False, "Checklist document missing or too short.")

    # Check 7: Synthetic data disclosure and limitations
    data_basis = data.get("data_basis", "").lower()
    limitations = data.get("known_limitations", {})
    synth_text = limitations.get("synthetic_data_only", "").lower()
    field_text = limitations.get("no_field_claims", "").lower()
    disclosure_ok = "synthetic" in data_basis and "synthetic" in synth_text and ("no claim" in field_text or "no real" in field_text)
    record_check(
        "synthetic_data_disclosure",
        disclosure_ok,
        "Confirmed synthetic data basis explicitly disclosed without real Antarctic claims."
    )

    # Check 8: Ownership boundaries and Bharati status
    has_a = len(data.get("person_a_responsibility", [])) > 0
    has_b = len(data.get("person_b_responsibility", [])) > 0
    has_c = len(data.get("person_c_responsibility", [])) > 0
    bharati_ok = "not started" in data.get("bharati_status", "").lower()
    record_check(
        "ownership_boundaries_and_bharati_status",
        has_a and has_b and has_c and bharati_ok,
        f"Person A/B/C responsibilities documented; Bharati status: '{data.get('bharati_status')}'."
    )

    checks_total = len(checks)
    checks_passed = sum(1 for c in checks if c["passed"])
    checks_failed = checks_total - checks_passed
    overall_status = "PASSED" if checks_failed == 0 else "FAILED"

    valid_artifacts_count = sum(1 for item in registry_report.get("artifact_results", {}).values() if item.get("status") == "VALID") if "artifact_results" in registry_report else 0

    validation_result: Dict[str, Any] = {
        "timestamp": timestamp,
        "project": "Polarix",
        "station_id": "MTR",
        "model_version": "lstm-ae-v1",
        "threshold": 0.017674,
        "readiness_status": data.get("readiness_status"),
        "overall_status": overall_status,
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "artifact_integrity": {
            "status": registry_report.get("overall_status"),
            "valid_artifacts_count": valid_artifacts_count,
            "errors": registry_report.get("errors", []),
        },
        "checks": checks,
    }

    # Save to JSON
    out_path = _REPO_ROOT / "ml" / "results" / "maitri_ml_integration_readiness_validation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(validation_result, f, indent=2)

    return validation_result


def main() -> int:
    result = run_integration_readiness_validation()
    print("=" * 70)
    print(" POLARIX MAITRI ML INTEGRATION READINESS VALIDATION (Person C)")
    print("=" * 70)
    print(f" Timestamp:      {result['timestamp']}")
    print(f" Station:        {result['station_id']}")
    print(f" Model Version:  {result['model_version']}")
    print(f" Threshold:      {result['threshold']}")
    print(f" Readiness:      {result['readiness_status']}")
    print(f" Overall Status: {result['overall_status']} ({result['checks_passed']}/{result['checks_total']} checks passed)")
    print("-" * 70)
    for c in result["checks"]:
        mark = "✓ PASS" if c["passed"] else "✗ FAIL"
        print(f" [{mark}] {c['check_name']}: {c['details']}")
    print("=" * 70)
    return 0 if result["overall_status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
