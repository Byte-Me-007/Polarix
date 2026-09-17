"""
Polarix Maitri ML Handoff Validation Tests (SIH26060 - Person C).

Verifies the consistency, completeness, and integrity of the final Maitri ML
handoff package, ensuring stable contracts and truthful metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_ANOMALY_TYPES,
    VALID_STATUSES,
)
from ml.inference.maitri_backend_contract import (
    adapt_backend_input,
    adapt_backend_output,
    process_backend_payload,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.models.model_registry import validate_model_artifacts

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MANIFEST_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_handoff_manifest.json"
_HANDOFF_DOC_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_handoff.md"
_MODEL_MANIFEST_PATH = _REPO_ROOT / "ml" / "models" / "lstm-ae-v1_manifest.json"
_THRESHOLD_PATH = _REPO_ROOT / "ml" / "results" / "lstm_threshold.json"


@pytest.fixture(scope="module")
def handoff_manifest():
    assert _MANIFEST_PATH.exists(), f"Handoff manifest not found at {_MANIFEST_PATH}"
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_station_and_model_version_invariants(handoff_manifest):
    """Verify that station is strictly MTR and model version is lstm-ae-v1."""
    assert handoff_manifest["station_id"] == "MTR"
    assert "MTR" in SUPPORTED_STATIONS
    assert len(SUPPORTED_STATIONS) == 1
    assert handoff_manifest["model_version"] == "lstm-ae-v1"
    assert DEFAULT_MODEL_VERSION == "lstm-ae-v1"


def test_threshold_and_sensors_invariants(handoff_manifest):
    """Verify threshold value and supported sensor list."""
    assert handoff_manifest["threshold"] == 0.017674
    expected_sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
    assert sorted(handoff_manifest["supported_sensors"]) == sorted(expected_sensors)
    assert sorted(SUPPORTED_SENSORS) == sorted(expected_sensors)


def test_supported_statuses_and_anomaly_types(handoff_manifest):
    """Verify inference statuses and anomaly types match contract vocabulary."""
    expected_statuses = {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}
    assert set(handoff_manifest["supported_statuses"]) == expected_statuses
    assert set(VALID_STATUSES) == expected_statuses

    expected_types = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
    assert set(handoff_manifest["supported_anomaly_types"]) == expected_types
    assert set(VALID_ANOMALY_TYPES) == expected_types


def test_handoff_document_exists_and_contains_key_sections():
    """Verify human-readable handoff documentation exists and contains essential sections."""
    assert _HANDOFF_DOC_PATH.exists()
    content = _HANDOFF_DOC_PATH.read_text(encoding="utf-8")
    assert "## A. Purpose" in content
    assert "## B. What Person C Owns" in content
    assert "## C. Frozen ML Artifacts" in content
    assert "## D. Input Telemetry Contract" in content
    assert "## E. Output Telemetry Contract" in content
    assert "## F. ML Service Entry Point" in content
    assert "## G. Backend Adapter Entry Point" in content
    assert "## O. Known Limitations and What MUST NOT Be Claimed" in content
    assert "## P. How Person A Should Consume the ML Service" in content


def test_manifest_agrees_with_model_manifest_and_threshold(handoff_manifest):
    """Verify agreement between handoff manifest, model registry manifest, and threshold file."""
    with open(_MODEL_MANIFEST_PATH, "r", encoding="utf-8") as f:
        model_manifest = json.load(f)
    with open(_THRESHOLD_PATH, "r", encoding="utf-8") as f:
        threshold_data = json.load(f)

    assert handoff_manifest["model_version"] == model_manifest["model_version"]
    assert handoff_manifest["station_id"] == model_manifest["station_id"]
    assert handoff_manifest["threshold"] == threshold_data["threshold"]
    assert handoff_manifest["sequence_length"] == model_manifest["training_metadata"]["sequence_length"]


def test_referenced_artifacts_exist(handoff_manifest):
    """Verify that all files referenced in the handoff manifest exist on disk."""
    dataset_path = _REPO_ROOT / handoff_manifest["synthetic_dataset"]["path"]
    scenario_eval_path = _REPO_ROOT / handoff_manifest["scenario_evaluation_reference"]
    eval_report_path = _REPO_ROOT / handoff_manifest["evaluation_report_reference"]

    assert dataset_path.exists(), f"Dataset not found: {dataset_path}"
    assert scenario_eval_path.exists(), f"Scenario evaluation not found: {scenario_eval_path}"
    assert eval_report_path.exists(), f"Evaluation report not found: {eval_report_path}"


def test_model_artifact_integrity_verification():
    """Verify that cryptographic model registry integrity check passes with zero errors."""
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    rep_dict = report.to_dict()
    assert rep_dict["overall_status"] == "VALID"
    valid_count = sum(1 for item in rep_dict["artifact_results"].values() if item.get("status") == "VALID")
    assert valid_count == 4
    assert len(rep_dict["errors"]) == 0


def test_no_real_antarctic_claims_in_manifest(handoff_manifest):
    """Verify that no false claims of real Antarctic telemetry or field readiness exist."""
    limitations = handoff_manifest.get("known_limitations", {})
    synth_text = limitations.get("synthetic_data_only", "").lower()
    field_text = limitations.get("no_field_claims", "").lower()

    assert "synthetic telemetry" in synth_text or "synthetic" in synth_text
    assert "no claim of real-world antarctic telemetry" in field_text or "no real" in field_text


def test_backend_adapter_smoke_execution():
    """Verify that backend adapter functions run correctly with a valid sample."""
    service = MaitriMLService()
    sample_payload = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": "2026-09-17T10:30:00Z",
        "value": -34.5,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    result = process_backend_payload(service, sample_payload)
    assert result["station_id"] == "MTR"
    assert result["sensor_id"] == "TEMP_001"
    assert result["anomaly_status"] == "INSUFFICIENT_DATA"
    assert result["anomaly_score"] is None
    assert result["model_version"] == "lstm-ae-v1"
