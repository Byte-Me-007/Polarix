"""Final test suite for Polarix ML Readiness & Sign-Off Audit (Step 37).

Verifies the completeness, reproducibility, and cryptographic integrity of the
final ML subsystem sign-off audit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_SCRIPT_PATH = REPO_ROOT / "ml" / "inference" / "validate_ml_readiness.py"
AUDIT_JSON_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.json"
AUDIT_MD_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.md"

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


def test_audit_script_execution():
    assert AUDIT_SCRIPT_PATH.exists(), f"Missing audit script: {AUDIT_SCRIPT_PATH}"
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Audit script failed:\n{result.stderr}\n{result.stdout}"
    assert AUDIT_JSON_PATH.exists()
    assert AUDIT_MD_PATH.exists()


def test_audit_json_contents():
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    meta = audit.get("audit_metadata", {})
    assert meta.get("overall_status") == "ML SUBSYSTEM — READY FOR INTEGRATION"
    assert meta.get("integration_ready") is True
    assert meta.get("branch_observed") == "Rex"

    # Stations
    specs = audit.get("station_specifications", {})
    assert "MTR" in specs and "BRT" in specs
    assert specs["MTR"]["model_version"] == "lstm-ae-v1"
    assert specs["MTR"]["threshold"] == 0.017674
    assert len(specs["MTR"]["sensors"]) == 5

    assert specs["BRT"]["model_version"] == "lstm-ae-bharati-v1"
    assert specs["BRT"]["threshold"] == 0.013215307652775843
    assert len(specs["BRT"]["sensors"]) == 5

    # Frozen artifacts
    art_res = audit.get("frozen_artifact_integrity", {})
    assert art_res.get("all_passed") is True

    # Authoritative Bharati metrics check
    metrics = audit.get("authoritative_bharati_metrics", {})
    assert metrics["zscore_test"]["f1"] == 0.2281
    assert metrics["zscore_test"]["fpr"] == 0.0144
    assert metrics["lstm_test"]["f1"] == 0.3646
    assert metrics["lstm_test"]["fpr"] == 0.5050
    assert metrics["lstm_validation"]["fpr"] == 0.4949

    # Result files audit
    res_files = audit.get("result_files_audit", {})
    assert res_files.get("all_passed") is True

    # Limitations
    limitations = audit.get("known_limitations_and_scope", [])
    assert len(limitations) >= 5
    assert any("synthetic" in l.lower() for l in limitations)
    assert any("prototype" in l.lower() for l in limitations)


def test_frozen_artifact_hashes_integrity():
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Missing frozen artifact: {abs_path}"
        actual = compute_sha256(abs_path)
        assert actual == expected_hash, f"Hash mismatch for {rel_path}"


def test_audit_markdown_structure():
    content = AUDIT_MD_PATH.read_text(encoding="utf-8")
    assert "# Polarix ML Final Readiness Audit" in content
    assert "## 1. Audit Scope" in content
    assert "## 2. Repository Integrity" in content
    assert "## 3. Maitri Readiness" in content
    assert "## 4. Bharati Readiness" in content
    assert "## 5. Frozen Artifact Integrity" in content
    assert "## 6. Model/Version Contract" in content
    assert "## 7. Input/Output Contract" in content
    assert "## 8. Scenario Coverage" in content
    assert "## 9. Authoritative Model Evaluation Metrics" in content
    assert "## 10. Documentation & Handoff Evidence" in content
    assert "## 11. Known Limitations & Scope Boundaries" in content
    assert "## 12. Integration Readiness" in content
    assert "## 13. Final Sign-Off" in content
    assert "ML SUBSYSTEM — READY FOR INTEGRATION" in content
