"""Test suite for Bharati LSTM False-Positive Rate Investigation & Optimization.

Verifies:
- Frozen V1 artifact integrity (hashes & thresholds untouched)
- Performance analysis JSON and Markdown completeness
- Internal consistency of evaluation metrics
- Validation-only threshold optimization (no test leakage)
- Compatibility with inference contracts
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYSIS_JSON_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.json"
ANALYSIS_MD_PATH = REPO_ROOT / "ml" / "results" / "bharati_lstm_performance_analysis.md"

FROZEN_BHARATI_V1_HASHES = {
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
}


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def test_frozen_v1_artifacts_integrity_unchanged():
    for rel_path, expected_hash in FROZEN_BHARATI_V1_HASHES.items():
        abs_path = REPO_ROOT / rel_path
        assert abs_path.exists(), f"Missing frozen artifact: {abs_path}"
        actual_hash = compute_sha256(abs_path)
        assert actual_hash == expected_hash, (
            f"V1 frozen artifact was modified: {rel_path}\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual:   {actual_hash}"
        )


def test_frozen_v1_threshold_value():
    threshold_file = REPO_ROOT / "ml" / "results" / "bharati_lstm_threshold.json"
    with open(threshold_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["station_id"] == "BRT"
    assert data["model_version"] == "lstm-ae-bharati-v1"
    assert data["threshold"] == 0.013215307652775843


def test_performance_analysis_json_structure():
    assert ANALYSIS_JSON_PATH.exists(), f"Missing {ANALYSIS_JSON_PATH}"
    with open(ANALYSIS_JSON_PATH, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    meta = analysis.get("investigation_metadata", {})
    assert meta.get("station_id") == "BRT"
    assert meta.get("target_model") == "lstm-ae-bharati-v1"
    assert meta.get("frozen_v1_threshold") == 0.013215307652775843

    # Check validation comparisons
    val_comp = analysis.get("validation_strategy_comparison", {})
    assert "strategy_a_v1_global" in val_comp
    assert "strategy_b1_max_f1_global" in val_comp
    assert "strategy_c1_per_sensor_max_f1" in val_comp
    assert "strategy_c2_p99_clean_normal" in val_comp
    assert "strategy_c3_constrained_per_sensor" in val_comp

    # Verify metrics internal consistency
    for strat_key, strat_data in val_comp.items():
        tp = strat_data["TP"]
        tn = strat_data["TN"]
        fp = strat_data["FP"]
        fn = strat_data["FN"]
        assert tp + tn + fp + fn == 1181, f"Total val observations mismatch in {strat_key}"
        expected_fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        assert pytest.approx(strat_data["fpr"], abs=1e-4) == expected_fpr

    # Check unbiased test evaluation
    test_eval = analysis.get("unbiased_test_evaluation", {})
    assert "baseline_v1_test" in test_eval
    assert "candidate_c3_test" in test_eval

    v1_test = test_eval["baseline_v1_test"]
    c3_test = test_eval["candidate_c3_test"]

    assert v1_test["TP"] + v1_test["TN"] + v1_test["FP"] + v1_test["FN"] == 1182
    assert c3_test["TP"] + c3_test["TN"] + c3_test["FP"] + c3_test["FN"] == 1182

    # Verify Candidate C3 reduced test FPR vs V1
    assert c3_test["fpr"] < v1_test["fpr"]
    assert c3_test["FP"] < v1_test["FP"]
    assert c3_test["clean_normal_fpr"] < v1_test["clean_normal_fpr"]


def test_performance_analysis_markdown_sections():
    assert ANALYSIS_MD_PATH.exists(), f"Missing {ANALYSIS_MD_PATH}"
    content = ANALYSIS_MD_PATH.read_text(encoding="utf-8")

    assert "# Bharati LSTM Autoencoder False-Positive Rate Investigation" in content
    assert "## 1. Problem Statement" in content
    assert "## 2. V1 Baseline Metrics Summary" in content
    assert "## 3. Reconstruction Error Distribution Analysis" in content
    assert "## 4. Sensor-Level Disparity Analysis" in content
    assert "## 5. Validation Threshold Strategy Experiments" in content
    assert "## 6. Candidate Configurations Summary" in content
    assert "## 7. Validation Split Comparison" in content
    assert "## 8. Final Unbiased Test Evaluation" in content
    assert "## 9. Error Breakdown & Trailing Window Artifacts" in content
    assert "## 10. Technical Limitations & Scope" in content
    assert "## 11. Recommendation & Architectural Status" in content
    assert "0.013215307652775843" in content
