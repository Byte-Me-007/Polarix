"""Test suite for ML Documentation Consistency & Accuracy (Step 39).

Verifies:
- Accurate timeline descriptions (Steps 23-36 for Bharati ML + Handoff)
- Proper frozen artifact categorization (2 models, 2 configs, 2 scalers, 2 thresholds)
- Hybrid ML pipeline description (LSTM reconstruction + deterministic classification + missing data)
- Acknowledgement of STUCK_VALUE / LSTM reconstruction limitations
- Candidate calibration wording (empirical candidate evaluation, no mathematical proof claims)
- Frozen Bharati V1 identification and preserved authoritative metrics
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
READINESS_MD_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.md"
READINESS_JSON_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.json"
PERF_ANALYSIS_MD_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.md"
PERF_ANALYSIS_JSON_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.json"
HANDOFF_MD_PATH = REPO_ROOT / "ml" / "ML_HANDOFF.md"

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


def test_frozen_artifacts_sha256_match_expected():
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Missing artifact: {abs_path}"
        actual = compute_sha256(abs_path)
        assert actual == expected_hash, f"Hash mismatch for {rel_path}"


def test_bharati_timeline_wording():
    md_content = READINESS_MD_PATH.read_text(encoding="utf-8")
    assert "Steps 23–36" in md_content or "Steps 23-36" in md_content
    assert "Handoff Complete" in md_content or "Bharati ML + Handoff" in md_content

    with open(READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)
    brt_steps = audit_json.get("station_specifications", {}).get("BRT", {}).get("steps_completed", "")
    assert "36" in brt_steps and "Handoff" in brt_steps


def test_frozen_artifact_inventory_wording():
    md_content = READINESS_MD_PATH.read_text(encoding="utf-8")
    # Must describe 2 models, 2 configs, 2 scalers, 2 decision thresholds (not calling all 8 PyTorch models)
    assert "2 models, 2 configs, 2 scalers, and 2 decision thresholds" in md_content
    assert "8 frozen PyTorch models" not in md_content


def test_hybrid_pipeline_and_limitations_wording():
    md_content = READINESS_MD_PATH.read_text(encoding="utf-8")
    assert "hybrid" in md_content.lower()
    assert "reconstruction" in md_content.lower()
    assert "deterministic" in md_content.lower()

    # Stuck value limitation
    assert "stuck_value" in md_content.lower() or "flatline" in md_content.lower()


def test_candidate_calibration_wording():
    perf_md = PERF_ANALYSIS_MD_PATH.read_text(encoding="utf-8")
    assert "mathematically proven" not in perf_md.lower()
    assert "mathematically justified" not in perf_md.lower()
    assert "empirically validated" in perf_md.lower() or "candidate calibration" in perf_md.lower()

    with open(PERF_ANALYSIS_JSON_PATH, "r", encoding="utf-8") as f:
        perf_json = json.load(f)
    findings = " ".join(perf_json.get("tradeoff_and_recommendation", {}).get("key_findings", []))
    assert "mathematically proven" not in findings.lower()
    assert "mathematically justified" not in findings.lower()


def test_authoritative_metrics_preserved():
    with open(READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        audit_json = json.load(f)
    metrics = audit_json.get("authoritative_bharati_metrics", {})
    assert metrics["zscore_test"]["f1"] == 0.2281
    assert metrics["zscore_test"]["fpr"] == 0.0144
    assert metrics["lstm_test"]["f1"] == 0.3646
    assert metrics["lstm_test"]["fpr"] == 0.5050
    assert metrics["lstm_validation"]["fpr"] == 0.4949

    with open(PERF_ANALYSIS_JSON_PATH, "r", encoding="utf-8") as f:
        perf_json = json.load(f)
    v1_test = perf_json["unbiased_test_evaluation"]["baseline_v1_test"]
    assert v1_test["TP"] == 165
    assert v1_test["TN"] == 442
    assert v1_test["FP"] == 451
    assert v1_test["FN"] == 124

    c3_test = perf_json["unbiased_test_evaluation"]["candidate_c3_test"]
    assert c3_test["TP"] == 144
    assert c3_test["TN"] == 541
    assert c3_test["FP"] == 352
    assert c3_test["FN"] == 145
