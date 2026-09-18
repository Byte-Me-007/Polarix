"""Test suite for ML Handoff Package (Step 36).

Verifies the integrity, completeness, and correctness of:
- ml/ML_HANDOFF.md
- ml/results/ml_handoff_contract.json
- Frozen artifact SHA-256 integrity against repository files
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFF_MD_PATH = REPO_ROOT / "ml" / "ML_HANDOFF.md"
HANDOFF_JSON_PATH = REPO_ROOT / "ml" / "results" / "ml_handoff_contract.json"

EXPECTED_HASHES = {
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
    "ml/models/lstm-ae-v1.pt": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
    "ml/models/lstm-ae-v1_config.json": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
    "ml/models/lstm-ae-v1_scaler.json": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
    "ml/results/lstm_threshold.json": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
}


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def test_handoff_files_exist():
    assert HANDOFF_MD_PATH.exists(), f"Missing {HANDOFF_MD_PATH}"
    assert HANDOFF_JSON_PATH.exists(), f"Missing {HANDOFF_JSON_PATH}"


def test_contract_json_schema_and_content():
    with open(HANDOFF_JSON_PATH, "r", encoding="utf-8") as f:
        contract = json.load(f)

    # Metadata
    metadata = contract.get("handoff_metadata", {})
    assert metadata.get("version") == "1.0.0"
    assert "synthetic" in metadata.get("synthetic_disclaimer", "").lower()

    # State management / window size
    assert contract.get("state_management", {}).get("window_size") == 30

    # Ownership boundaries
    boundaries = contract.get("ownership_boundaries", {})
    assert "person_c_ml" in boundaries
    assert "person_a_backend" in boundaries
    assert "person_b_frontend" in boundaries

    # Stations
    stations = contract.get("stations", {})
    assert "MTR" in stations
    assert "BRT" in stations

    # Maitri specs
    mtr = stations["MTR"]
    assert mtr["station_name"] == "Maitri"
    assert mtr["model_version"] == "lstm-ae-v1"
    assert mtr["threshold"] == 0.017674
    assert mtr["sequence_length"] == 30
    assert set(mtr["supported_sensors"]) == {
        "TEMP_001",
        "PRESS_001",
        "HUM_001",
        "VIB_001",
        "POWER_001",
    }

    # Bharati specs
    brt = stations["BRT"]
    assert brt["station_name"] == "Bharati"
    assert brt["model_version"] == "lstm-ae-bharati-v1"
    assert brt["threshold"] == 0.013215307652775843
    assert brt["sequence_length"] == 30
    assert set(brt["supported_sensors"]) == {
        "BRT_TEMP_001",
        "BRT_PRESS_001",
        "BRT_HUM_001",
        "BRT_VIB_001",
        "BRT_POWER_001",
    }

    # Statuses
    statuses = set(contract.get("status_semantics", {}).keys())
    assert statuses == {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}

    # Anomaly Types
    anomaly_types = set(contract.get("anomaly_type_semantics", {}).keys())
    assert anomaly_types == {"SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN", "NORMAL"}

    # Input / Output contract fields
    contracts_sec = contract.get("contracts", {})
    input_fields = contracts_sec.get("input_fields", {})
    required_inputs = {k for k, v in input_fields.items() if v.get("required")}
    optional_inputs = {k for k, v in input_fields.items() if not v.get("required")}
    assert required_inputs == {"station_id", "sensor_id", "timestamp", "value"}
    assert optional_inputs == {"unit", "quality", "source"}

    output_fields = contracts_sec.get("output_fields", {})
    assert "anomaly_status" in output_fields
    assert "model_version" in output_fields
    assert output_fields["anomaly_score"]["nullable"] is True
    assert output_fields["anomaly_type"]["nullable"] is True

    # Error Categories
    error_cats = contract.get("error_categories", {})
    assert "DuplicateTelemetryError" in error_cats
    assert "StaleTelemetryError" in error_cats
    assert "UnsupportedStationError" in error_cats
    assert "UnsupportedSensorError" in error_cats

    # Artifact references and hashes
    for stn_key, stn_dict in stations.items():
        artifacts = stn_dict["artifacts"]
        for art_type in ["model", "config", "scaler", "threshold"]:
            path = artifacts[art_type]["path"]
            expected_hash = EXPECTED_HASHES[path]
            assert artifacts[art_type]["sha256"] == expected_hash


def test_frozen_artifacts_sha256_on_disk():
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Frozen artifact missing on disk: {abs_path}"
        actual_hash = compute_sha256(abs_path)
        assert actual_hash == expected_hash, (
            f"Hash mismatch for {rel_path}:\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual:   {actual_hash}"
        )


def test_handoff_markdown_content():
    content = HANDOFF_MD_PATH.read_text(encoding="utf-8")

    # Check 17 section topics
    assert "## 1. Machine Learning Ownership Boundary" in content
    assert "## 2. Supported Stations & Sensor Registry" in content
    assert "## 3. Canonical Input Contract" in content
    assert "## 4. Canonical Output Contract" in content
    assert "## 5. Status Semantics" in content
    assert "## 6. Anomaly Type Semantics" in content
    assert "## 7. Integration Sequence & Dataflow" in content
    assert "## 8. Per-Sensor State Management & Isolation" in content
    assert "## 9. Error & Rejection Diagnostics" in content
    assert "## 10. Example Integration Flows" in content
    assert "## 11. Backend Integration Checklist (Person A)" in content
    assert "## 12. Frontend Integration Checklist (Person B)" in content
    assert "## 13. Frozen Artifact Registry & Cryptographic Hashes" in content
    assert "## 14. Validation Evidence & Test Coverage" in content
    assert "## 15. Known Limitations & Technical Scope Boundaries" in content
    assert "## 16. Reproducibility Instructions" in content
    assert "## 17. Final ML Handoff Status" in content

    # Check stations & sensors
    assert "MTR" in content
    assert "BRT" in content
    assert "TEMP_001" in content
    assert "BRT_TEMP_001" in content

    # Check exact Bharati threshold
    assert "0.013215307652775843" in content

    # Check statuses
    assert "NORMAL" in content
    assert "ANOMALY" in content
    assert "INSUFFICIENT_DATA" in content
    assert "MISSING_DATA" in content

    # Check anomaly types
    assert "SPIKE" in content
    assert "DRIFT" in content
    assert "STUCK_VALUE" in content
    assert "UNKNOWN" in content

    # Check disclaimer / limitations
    assert "Synthetic Telemetry Only" in content
    assert "synthetic" in content.lower()
    assert "prototype" in content.lower()
    assert "false-positive rate" in content.lower()

    # Ensure no false claims of production readiness
    assert "not a production-certified deployment" in content.lower() or "prototype" in content.lower()
