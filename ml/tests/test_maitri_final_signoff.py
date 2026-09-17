"""
Polarix Maitri ML Final Engineering Sign-Off Tests (SIH26060 - Person C).

Verifies the final sign-off record and documentation to ensure internal consistency,
artifact integrity, and absence of ungrounded real-world Antarctic claims.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from ml.models.model_registry import validate_model_artifacts

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SIGNOFF_JSON_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_final_signoff.json"
_SIGNOFF_MD_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_final_signoff.md"
_HANDOFF_MANIFEST_PATH = _REPO_ROOT / "ml" / "results" / "maitri_ml_handoff_manifest.json"


@pytest.fixture(scope="module")
def signoff_data():
    assert _SIGNOFF_JSON_PATH.exists(), f"Signoff JSON not found at {_SIGNOFF_JSON_PATH}"
    with open(_SIGNOFF_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_signoff_status_and_invariants(signoff_data):
    """Verify signoff status string and frozen model invariants."""
    assert signoff_data["signoff_status"] == "MAITRI ML ENGINEERING HANDOFF COMPLETE"
    assert signoff_data["station_id"] == "MTR"
    assert signoff_data["station_name"] == "Maitri"
    assert signoff_data["model_version"] == "lstm-ae-v1"
    assert signoff_data["threshold"] == 0.017674


def test_synthetic_data_status_and_limitations(signoff_data):
    """Verify data_status explicitly identifies synthetic telemetry without real Antarctic claims."""
    data_status = signoff_data.get("data_status", "").lower()
    assert "synthetic telemetry" in data_status or "synthetic" in data_status

    limitations = signoff_data.get("known_limitations", {})
    no_field = limitations.get("no_field_claims", "").lower()
    assert "no claim" in no_field or "no real" in no_field


def test_bharati_not_started_status(signoff_data):
    """Verify next_station_status marks Bharati as not started."""
    bharati_status = signoff_data.get("next_station_status", "").lower()
    assert "not been started" in bharati_status or "not started" in bharati_status


def test_artifact_hashes_match_expected(signoff_data):
    """Verify artifact integrity hashes in signoff match current model manifest integrity."""
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    rep_dict = report.to_dict()
    assert rep_dict["overall_status"] == "VALID"

    expected_hashes = {
        "model": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
        "config": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
        "scaler": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
        "threshold": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
    }

    signoff_artifacts = {a["role"]: a["sha256"] for a in signoff_data["artifact_integrity"]["artifacts"]}
    for role, exp_hash in expected_hashes.items():
        assert signoff_artifacts[role] == exp_hash
        assert rep_dict["artifact_results"][role]["actual_sha256"] == exp_hash


def test_documents_and_manifest_exist():
    """Verify final signoff document and handoff manifest exist on disk."""
    assert _SIGNOFF_MD_PATH.exists()
    assert _HANDOFF_MANIFEST_PATH.exists()

    content = _SIGNOFF_MD_PATH.read_text(encoding="utf-8")
    assert "MAITRI ML ENGINEERING HANDOFF COMPLETE" in content
    assert "Not started. Maitri is the completed Person C station scope." in content
