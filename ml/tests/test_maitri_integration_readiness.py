"""
Polarix Maitri ML Integration Readiness Tests (SIH26060 - Person C).

Verifies the integration readiness document and JSON record, ensuring contract stability,
module references, ownership boundaries, and absence of ungrounded real-world claims.
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
from ml.models.model_registry import validate_model_artifacts

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_READINESS_JSON_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_integration_readiness.json"
_CHECKLIST_MD_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_integration_checklist.md"


@pytest.fixture(scope="module")
def readiness_data():
    assert _READINESS_JSON_PATH.exists(), f"Readiness JSON not found at {_READINESS_JSON_PATH}"
    with open(_READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_readiness_status_and_invariants(readiness_data):
    """Verify readiness status string and frozen model invariants."""
    assert readiness_data["readiness_status"] == "ML interface and handoff are internally validated and ready for team integration."
    assert readiness_data["station_id"] == "MTR"
    assert readiness_data["station_name"] == "Maitri"
    assert readiness_data["model_version"] == "lstm-ae-v1"
    assert readiness_data["threshold"] == 0.017674


def test_supported_sensors_and_contract_vocabulary(readiness_data):
    """Verify supported sensors, statuses, and anomaly types match contract."""
    expected_sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
    assert sorted(readiness_data["supported_sensors"]) == sorted(expected_sensors)
    assert sorted(SUPPORTED_SENSORS) == sorted(expected_sensors)

    expected_statuses = {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}
    assert set(readiness_data["supported_statuses"]) == expected_statuses
    assert set(VALID_STATUSES) == expected_statuses

    expected_types = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
    assert set(readiness_data["supported_anomaly_types"]) == expected_types
    assert set(VALID_ANOMALY_TYPES) == expected_types


def test_referenced_modules_and_functions_exist(readiness_data):
    """Verify referenced entry points and adapters exist in python namespace."""
    import importlib

    # Check inference entry point
    inf_mod_name = readiness_data["inference_entry_point"]["module"]
    inf_cls_name = readiness_data["inference_entry_point"]["class"]
    inf_mod = importlib.import_module(inf_mod_name)
    assert hasattr(inf_mod, inf_cls_name)

    # Check backend adapter module
    adapter_mod_name = readiness_data["backend_adapter"]["module"]
    adapter_mod = importlib.import_module(adapter_mod_name)
    assert hasattr(adapter_mod, "process_backend_payload")
    assert hasattr(adapter_mod, "adapt_backend_input")
    assert hasattr(adapter_mod, "adapt_backend_output")


def test_artifact_integrity_verification():
    """Verify 4/4 artifact checksums match registered manifest."""
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    rep_dict = report.to_dict()
    assert rep_dict["overall_status"] == "VALID"
    valid_count = sum(1 for item in rep_dict["artifact_results"].values() if item.get("status") == "VALID")
    assert valid_count == 4
    assert len(rep_dict["errors"]) == 0


def test_synthetic_data_limitations_and_ownership(readiness_data):
    """Verify synthetic data limitations and Person A/B/C ownership boundaries."""
    data_basis = readiness_data.get("data_basis", "").lower()
    assert "synthetic telemetry" in data_basis or "synthetic" in data_basis

    limitations = readiness_data.get("known_limitations", {})
    no_field = limitations.get("no_field_claims", "").lower()
    assert "no claim" in no_field or "no real" in no_field

    # Check ownership boundaries
    assert len(readiness_data.get("person_a_responsibility", [])) > 0
    assert len(readiness_data.get("person_b_responsibility", [])) > 0
    assert len(readiness_data.get("person_c_responsibility", [])) > 0


def test_bharati_status_and_checklist_doc(readiness_data):
    """Verify Bharati is marked not started and integration checklist document exists."""
    bharati_status = readiness_data.get("bharati_status", "").lower()
    assert "not started" in bharati_status

    assert _CHECKLIST_MD_PATH.exists()
    content = _CHECKLIST_MD_PATH.read_text(encoding="utf-8")
    assert "### 1. Backend → ML Input" in content
    assert "### 2. ML Processing" in content
    assert "### 3. ML → Backend Output" in content
    assert "### 5. Ownership Boundary" in content
    assert "### 7. Integration Sequence" in content
