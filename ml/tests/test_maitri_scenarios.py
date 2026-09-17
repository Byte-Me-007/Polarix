"""
Unit and Integration tests for Maitri ML Scenario Evaluation & Reporting.
Polarix SIH26060 - Person C.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import pytest

from ml.inference.evaluate_maitri_scenarios import run_scenario_evaluation
from ml.inference.inference_contract import DEFAULT_MODEL_VERSION

EXPECTED_SCENARIO_NAMES = {
    "NORMAL",
    "SPIKE",
    "DRIFT",
    "STUCK_VALUE",
    "DROPOUT",
    "INSUFFICIENT_DATA",
    "BAD_QUALITY",
    "NAN_INF",
    "DUPLICATE_TIMESTAMP",
    "STALE_TIMESTAMP",
    "MULTI_SENSOR_ISOLATION",
}

REQUIRED_SCENARIO_FIELDS = [
    "scenario",
    "description",
    "expected_behavior",
    "observed_behavior",
    "contract_status",
    "inference_status",
    "anomaly_status",
    "anomaly_type",
    "anomaly_score",
    "threshold",
    "model_version",
    "buffer_length_before",
    "buffer_length_after",
    "diagnostic_status",
    "processing_time_ms",
    "passed",
]


@pytest.fixture(scope="module")
def evaluation_data() -> dict:
    """Run scenario evaluation harness once for test suite verification."""
    return run_scenario_evaluation()


# -----------------------------------------------------------------------------
# 1. Scenario Coverage and Schema Tests
# -----------------------------------------------------------------------------
def test_1_all_11_scenarios_present(evaluation_data: dict):
    """Verify that all 11 required scenarios are executed and evaluated."""
    scenarios = evaluation_data.get("scenarios", [])
    scenario_names = {sc["scenario"] for sc in scenarios}
    assert scenario_names == EXPECTED_SCENARIO_NAMES
    assert len(scenarios) == 11


def test_2_scenario_record_fields_complete(evaluation_data: dict):
    """Verify each scenario record has all mandatory fields and valid types."""
    scenarios = evaluation_data.get("scenarios", [])
    for sc in scenarios:
        for field in REQUIRED_SCENARIO_FIELDS:
            assert field in sc, f"Missing field '{field}' in scenario '{sc.get('scenario')}'"
        assert isinstance(sc["passed"], bool)
        assert sc["passed"] is True, f"Scenario '{sc['scenario']}' failed verification"
        assert sc["threshold"] == 0.017674
        assert sc["model_version"] == DEFAULT_MODEL_VERSION
        assert math.isfinite(sc["processing_time_ms"]) and sc["processing_time_ms"] >= 0.0


# -----------------------------------------------------------------------------
# 2. Specific Scenario Behavioral Invariants
# -----------------------------------------------------------------------------
def test_3_normal_and_anomaly_scoring_invariants(evaluation_data: dict):
    """Verify NORMAL, SPIKE, and DRIFT scenarios produce valid scored outputs."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    # NORMAL
    norm = sc_map["NORMAL"]
    assert norm["contract_status"] == "VALID"
    assert norm["anomaly_status"] == "NORMAL"
    assert norm["anomaly_score"] is not None and norm["anomaly_score"] <= norm["threshold"]

    # SPIKE
    spike = sc_map["SPIKE"]
    assert spike["contract_status"] == "VALID"
    assert spike["anomaly_status"] == "ANOMALY"
    assert spike["anomaly_type"] == "SPIKE"
    assert spike["anomaly_score"] is not None and spike["anomaly_score"] > spike["threshold"]

    # DRIFT
    drift = sc_map["DRIFT"]
    assert drift["contract_status"] == "VALID"
    assert drift["anomaly_status"] == "ANOMALY"
    assert drift["anomaly_score"] is not None and drift["anomaly_score"] > drift["threshold"]


def test_4_missing_insufficient_and_bad_quality_invariants(evaluation_data: dict):
    """Verify missing, insufficient, bad quality, and NaN inputs produce null scores."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    for name in ["DROPOUT", "INSUFFICIENT_DATA", "BAD_QUALITY", "NAN_INF"]:
        sc = sc_map[name]
        assert sc["anomaly_score"] is None, f"Scenario '{name}' must have null score"
        assert sc["anomaly_type"] is None, f"Scenario '{name}' must have null anomaly_type"

    assert sc_map["DROPOUT"]["anomaly_status"] == "MISSING_DATA"
    assert sc_map["DROPOUT"]["buffer_length_after"] == 0

    assert sc_map["INSUFFICIENT_DATA"]["anomaly_status"] == "INSUFFICIENT_DATA"
    assert sc_map["INSUFFICIENT_DATA"]["buffer_length_after"] == 1

    assert sc_map["BAD_QUALITY"]["anomaly_status"] == "MISSING_DATA"
    assert sc_map["BAD_QUALITY"]["buffer_length_after"] == 0

    assert sc_map["NAN_INF"]["anomaly_status"] == "MISSING_DATA"
    assert sc_map["NAN_INF"]["buffer_length_after"] == 0


def test_5_duplicate_and_stale_rejection_invariants(evaluation_data: dict):
    """Verify duplicate and stale timestamps are rejected and preserve buffer history."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    # Duplicate
    dup = sc_map["DUPLICATE_TIMESTAMP"]
    assert dup["contract_status"] == "REJECTED_DUPLICATE"
    assert dup["diagnostic_status"] == "REJECTED_DUPLICATE"
    assert dup["buffer_length_after"] == 1

    # Stale
    stale = sc_map["STALE_TIMESTAMP"]
    assert stale["contract_status"] == "REJECTED_STALE"
    assert stale["diagnostic_status"] == "REJECTED_STALE"
    assert stale["buffer_length_after"] == 1


def test_6_multi_sensor_isolation_invariant(evaluation_data: dict):
    """Verify multi-sensor isolation maintains independent sequence histories."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}
    multi = sc_map["MULTI_SENSOR_ISOLATION"]
    assert multi["passed"] is True
    assert multi["buffer_length_after"] == 30


# -----------------------------------------------------------------------------
# 3. Quantitative & Artifact Integrity Tests
# -----------------------------------------------------------------------------
def test_7_quantitative_metrics_and_limitations(evaluation_data: dict):
    """Verify quantitative comparisons and limitations sections exist and are factual."""
    q_eval = evaluation_data.get("quantitative_evaluation", {})
    assert "zscore_v1_baseline" in q_eval
    assert "lstm_ae_v1_detector" in q_eval
    assert "comparative_observations" in q_eval

    # Verify no subjective ranking
    obs_text = " ".join(q_eval["comparative_observations"]).lower()
    assert "winner" not in obs_text
    assert "superior to all" not in obs_text

    # Limitations
    limits = evaluation_data.get("limitations", {})
    assert "synthetic_data_only" in limits
    assert "no_field_operational_claims" in limits


def test_8_report_artifacts_exist_and_match():
    """Verify JSON and Markdown report files exist on disk."""
    json_path = Path("ml/results/maitri_ml_evaluation_report.json")
    md_path = Path("ml/results/maitri_ml_evaluation_report.md")

    assert json_path.exists(), "JSON evaluation report must exist."
    assert md_path.exists(), "Markdown evaluation report must exist."

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["report_metadata"]["model_version"] == DEFAULT_MODEL_VERSION
    assert len(data["scenarios"]) == 11

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    assert "NORMAL" in md_content
    assert "SPIKE" in md_content
    assert "Synthetic Telemetry Notice" in md_content
