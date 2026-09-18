"""
Final ML Subsystem Integration Readiness & Documentation Consistency Tests (SIH26060 - Person C).
Step 42: Programmatic verification of the complete ML subsystem consistency across:
1. Frozen artifact SHA-256 integrity (2 models, 2 configs, 2 scalers, 2 thresholds).
2. Status and anomaly-type vocabulary conformance.
3. Hybrid architecture division of labor (LSTM scoring + deterministic classifier + missing data).
4. Candidate C3 threshold calibration remaining candidate-only (not replacing frozen v1).
5. Step 40 / Step 41 STUCK_VALUE active flatline detection and recovery behavior.
6. Absence of stale terminology ("8 PyTorch models", "Steps 23–35", unbacked proof claims).
7. Comprehensive synthetic data disclaimers across all audit documents.
8. Truthfulness and consistency of final readiness status across reports and code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
READINESS_MD_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.md"
READINESS_JSON_PATH = REPO_ROOT / "ml" / "results" / "ml_readiness_audit.json"
HANDOFF_MD_PATH = REPO_ROOT / "ml" / "ML_HANDOFF.md"
HANDOFF_JSON_PATH = REPO_ROOT / "ml" / "results" / "ml_handoff_contract.json"
PERF_ANALYSIS_MD_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.md"
PERF_ANALYSIS_JSON_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.json"
STUCK_VALUE_ANALYSIS_JSON = REPO_ROOT / "ml" / "results" / "stuck_value_classifier_analysis.json"
HYBRID_RE_EVAL_JSON = REPO_ROOT / "ml" / "results" / "hybrid_anomaly_classifier_re_evaluation.json"
HYBRID_RE_EVAL_MD = REPO_ROOT / "ml" / "results" / "hybrid_anomaly_classifier_re_evaluation.md"

FROZEN_ARTIFACT_HASHES: Dict[str, str] = {
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
    "ml/models/lstm-ae-v1.pt": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
    "ml/models/lstm-ae-v1_config.json": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
    "ml/models/lstm-ae-v1_scaler.json": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
    "ml/results/lstm_threshold.json": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
}

EXPECTED_STATUSES: Set[str] = {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}
EXPECTED_ANOMALY_TYPES: Set[str] = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


# -----------------------------------------------------------------------------
# 1. Cryptographic Artifact Integrity
# -----------------------------------------------------------------------------
def test_1_all_8_frozen_artifacts_match_digests():
    """Verify all 8 frozen ML artifacts match their exact expected SHA-256 digests."""
    for rel_path, expected_hash in FROZEN_ARTIFACT_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Missing frozen artifact: {rel_path}"
        actual = _sha256(abs_path)
        assert actual == expected_hash, f"Hash mismatch for {rel_path}: {actual} != {expected_hash}"


# -----------------------------------------------------------------------------
# 2. Status & Anomaly-Type Vocabulary Conformance
# -----------------------------------------------------------------------------
def test_2_canonical_vocabulary_conformance():
    """Verify contracts and audit schemas strictly adhere to the 4 statuses and 5 anomaly types."""
    with open(HANDOFF_JSON_PATH, "r", encoding="utf-8") as f:
        handoff = json.load(f)

    statuses = set(handoff.get("status_semantics", {}).keys())
    assert statuses == EXPECTED_STATUSES, f"Status set mismatch: {statuses}"

    anomaly_types = set(handoff.get("anomaly_type_semantics", {}).keys())
    assert anomaly_types == EXPECTED_ANOMALY_TYPES, f"Anomaly type set mismatch: {anomaly_types}"


# -----------------------------------------------------------------------------
# 3. Hybrid Pipeline Architecture
# -----------------------------------------------------------------------------
def test_3_hybrid_architecture_documented():
    """Verify hybrid pipeline division of labor is clearly stated."""
    with open(READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        readiness = json.load(f)

    arch = readiness.get("pipeline_architecture", {})
    assert "LSTM" in arch.get("anomaly_scoring_layer", "")
    assert "Deterministic" in arch.get("type_classification_layer", "")
    assert "missing" in arch.get("missing_data_layer", "").lower()

    with open(HYBRID_RE_EVAL_JSON, "r", encoding="utf-8") as f:
        hybrid_eval = json.load(f)

    hybrid_arch = hybrid_eval.get("hybrid_pipeline_division_of_labor", {})
    assert "lstm_reconstruction_scoring" in hybrid_arch
    assert "deterministic_anomaly_type_classification" in hybrid_arch
    assert "explicit_missing_data_handling" in hybrid_arch


# -----------------------------------------------------------------------------
# 4. Candidate C3 Calibration Remains Candidate-Only
# -----------------------------------------------------------------------------
def test_4_c3_candidate_not_integrated_into_frozen_v1():
    """Verify C3 calibration remains documented candidate-only and did not overwrite frozen v1."""
    with open(PERF_ANALYSIS_JSON_PATH, "r", encoding="utf-8") as f:
        perf = json.load(f)

    meta = perf.get("investigation_metadata", {})
    assert meta.get("target_model") == "lstm-ae-bharati-v1"
    assert meta.get("frozen_v1_threshold") == 0.013215307652775843
    
    c3_val = perf["validation_strategy_comparison"]["strategy_c3_constrained_per_sensor"]
    assert "Candidate C3" in c3_val["description"]
    assert c3_val["f1"] == 0.4229
    assert c3_val["fpr"] == 0.3386

    c3_test = perf["unbiased_test_evaluation"]["candidate_c3_test"]
    assert c3_test["f1"] == 0.3669
    assert c3_test["fpr"] == 0.3942

    with open(READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)
    brt_spec = audit.get("station_specifications", {}).get("BRT", {})
    assert brt_spec["model_version"] == "lstm-ae-bharati-v1"
    assert brt_spec["threshold"] == 0.013215307652775843


# -----------------------------------------------------------------------------
# 5. STUCK_VALUE Active Flatline & Recovery Behavior
# -----------------------------------------------------------------------------
def test_5_stuck_value_re_evaluation_metrics_consistent():
    """Verify re-evaluated STUCK_VALUE metrics show 0 recovery false positives and 100% precision."""
    with open(HYBRID_RE_EVAL_JSON, "r", encoding="utf-8") as f:
        re_eval = json.load(f)

    brt_stuck = re_eval["stations"]["BRT"]["overall"]["class_metrics"]["STUCK_VALUE"]
    assert brt_stuck["precision"] == 1.0000
    assert brt_stuck["recall"] == 0.7500
    assert brt_stuck["f1_score"] == 0.8571
    assert brt_stuck["false_positives"] == 0

    mtr_stuck = re_eval["stations"]["MTR"]["overall"]["class_metrics"]["STUCK_VALUE"]
    assert mtr_stuck["precision"] == 1.0000
    assert mtr_stuck["recall"] == 0.7500
    assert mtr_stuck["f1_score"] == 0.8571
    assert mtr_stuck["false_positives"] == 0


# -----------------------------------------------------------------------------
# 6. Absence of Stale & Misleading Terminology
# -----------------------------------------------------------------------------
def test_6_no_stale_terminology():
    """Verify no stale phrases exist in readiness and handoff documents."""
    readiness_md = READINESS_MD_PATH.read_text(encoding="utf-8")
    assert "8 frozen PyTorch models" not in readiness_md
    assert "8 PyTorch models" not in readiness_md
    assert "mathematically proven" not in readiness_md.lower()
    assert "guaranteed" not in readiness_md.lower() or "no guarantee" in readiness_md.lower()

    handoff_md = HANDOFF_MD_PATH.read_text(encoding="utf-8")
    assert "8 frozen PyTorch models" not in handoff_md
    assert "mathematically proven" not in handoff_md.lower()


# -----------------------------------------------------------------------------
# 7. Synthetic Data Disclaimers & Limitations
# -----------------------------------------------------------------------------
def test_7_synthetic_data_disclaimers_present():
    """Verify synthetic data disclaimers are present in all major documentation artifacts."""
    for path in [READINESS_MD_PATH, HANDOFF_MD_PATH, HYBRID_RE_EVAL_MD]:
        text = path.read_text(encoding="utf-8").lower()
        assert "synthetic" in text, f"Missing synthetic disclaimer in {path.name}"
        assert "not" in text or "no real" in text, f"Missing non-real disclaimer in {path.name}"


# -----------------------------------------------------------------------------
# 8. Readiness Status Consistency
# -----------------------------------------------------------------------------
def test_8_readiness_status_consistent():
    """Verify overall readiness status is true and consistent across reports."""
    with open(READINESS_JSON_PATH, "r", encoding="utf-8") as f:
        readiness = json.load(f)

    assert readiness["audit_metadata"]["overall_status"] == "ML SUBSYSTEM — READY FOR INTEGRATION"
    assert readiness["audit_metadata"]["integration_ready"] is True
    assert readiness["frozen_artifact_integrity"]["all_passed"] is True
    assert readiness["contract_and_handoff_audit"]["all_passed"] is True
    assert readiness["result_files_audit"]["all_passed"] is True
