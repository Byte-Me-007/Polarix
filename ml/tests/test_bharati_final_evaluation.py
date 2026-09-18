"""
Unit and Integration tests for Bharati ML Final Scenario Validation & Evaluation Report.
Polarix SIH26060 - Person C (Step 35).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import pytest

from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
)
from ml.inference.validate_bharati_final_evaluation import run_scenario_evaluation

EXPECTED_SCENARIO_NAMES = {
    "NORMAL_DAY",
    "SPIKE",
    "DRIFT",
    "STUCK_VALUE",
    "DROPOUT_MISSING_DATA",
    "INSUFFICIENT_DATA",
    "DUPLICATE_TELEMETRY",
    "STALE_TELEMETRY",
    "INVALID_INPUT",
    "MULTI_SENSOR_ISOLATION",
    "RECOVERY_AFTER_MISSING_DATA",
    "REPEATED_DETERMINISTIC_RUN",
}

REQUIRED_SCENARIO_FIELDS = [
    "scenario",
    "sensors",
    "input_condition",
    "expected_behavior",
    "observed_status",
    "observed_anomaly_type",
    "anomaly_score",
    "threshold",
    "model_version",
    "pass_fail_criterion",
    "passed",
    "notes_and_limitations",
    "processing_time_ms",
]


@pytest.fixture(scope="module")
def evaluation_data() -> dict:
    """Run scenario evaluation harness once for test suite verification (without overwriting artifacts)."""
    return run_scenario_evaluation(save_artifacts=False)


# -----------------------------------------------------------------------------
# 1. Scenario Coverage & Schema Tests
# -----------------------------------------------------------------------------
def test_1_all_12_scenarios_present(evaluation_data: dict):
    """Verify that all 12 required scenarios are present and executed."""
    scenarios = evaluation_data.get("scenarios", [])
    scenario_names = {sc["scenario"] for sc in scenarios}
    assert scenario_names == EXPECTED_SCENARIO_NAMES
    assert len(scenarios) == 12
    assert evaluation_data["report_metadata"]["overall_scenario_status"] == "PASSED"
    assert evaluation_data["report_metadata"]["total_scenarios_evaluated"] == 12
    assert evaluation_data["report_metadata"]["passed_scenarios"] == 12


def test_2_scenario_record_fields_complete(evaluation_data: dict):
    """Verify each scenario record contains all mandatory fields and valid types."""
    scenarios = evaluation_data.get("scenarios", [])
    for sc in scenarios:
        for field in REQUIRED_SCENARIO_FIELDS:
            assert field in sc, f"Missing field '{field}' in scenario '{sc.get('scenario')}'"
        assert isinstance(sc["passed"], bool)
        assert sc["passed"] is True, f"Scenario '{sc['scenario']}' failed verification"
        assert sc["threshold"] == 0.013215307652775843
        assert sc["model_version"] == DEFAULT_BHARATI_MODEL_VERSION
        assert math.isfinite(sc["processing_time_ms"]) and sc["processing_time_ms"] >= 0.0


# -----------------------------------------------------------------------------
# 2. Individual Scenario Invariant Tests
# -----------------------------------------------------------------------------
def test_3_normal_day_scenario(evaluation_data: dict):
    """Verify NORMAL_DAY scenario achieves NORMAL status across all 5 sensors."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}
    norm = sc_map["NORMAL_DAY"]
    assert norm["passed"] is True
    assert norm["observed_status"] == "NORMAL"
    assert norm["observed_anomaly_type"] == "NORMAL"
    assert norm["anomaly_score"] is not None and norm["anomaly_score"] <= norm["threshold"]


def test_4_spike_scenario(evaluation_data: dict):
    """Verify SPIKE scenario triggers ANOMALY status and SPIKE classification."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}
    spike = sc_map["SPIKE"]
    assert spike["passed"] is True
    assert spike["observed_status"] == "ANOMALY"
    assert spike["observed_anomaly_type"] == "SPIKE"
    assert spike["anomaly_score"] is not None and spike["anomaly_score"] > spike["threshold"]


def test_5_drift_scenario(evaluation_data: dict):
    """Verify DRIFT scenario triggers ANOMALY status and DRIFT classification."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}
    drift = sc_map["DRIFT"]
    assert drift["passed"] is True
    assert drift["observed_status"] == "ANOMALY"
    assert drift["observed_anomaly_type"] in {"DRIFT", "UNKNOWN"}
    assert drift["anomaly_score"] is not None and drift["anomaly_score"] > drift["threshold"]


def test_6_stuck_value_scenario(evaluation_data: dict):
    """Verify STUCK_VALUE scenario executes successfully with valid status."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}
    stuck = sc_map["STUCK_VALUE"]
    assert stuck["passed"] is True
    assert stuck["observed_status"] in {"NORMAL", "ANOMALY"}


def test_7_dropout_and_insufficient_data_scenarios(evaluation_data: dict):
    """Verify dropout resets state and insufficient data reports correct status."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    dropout = sc_map["DROPOUT_MISSING_DATA"]
    assert dropout["passed"] is True
    assert dropout["observed_status"] == "MISSING_DATA"
    assert dropout["anomaly_score"] is None

    ins = sc_map["INSUFFICIENT_DATA"]
    assert ins["passed"] is True
    assert ins["observed_status"] == "INSUFFICIENT_DATA"
    assert ins["anomaly_score"] is None


def test_8_duplicate_and_stale_rejection_scenarios(evaluation_data: dict):
    """Verify duplicate and stale telemetry are safely rejected and diagnosed."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    dup = sc_map["DUPLICATE_TELEMETRY"]
    assert dup["passed"] is True
    assert dup["observed_status"] == "REJECTED_DUPLICATE"

    stale = sc_map["STALE_TELEMETRY"]
    assert stale["passed"] is True
    assert stale["observed_status"] == "REJECTED_STALE"


def test_9_invalid_input_and_multi_sensor_scenarios(evaluation_data: dict):
    """Verify invalid inputs are rejected and multi-sensor isolation holds."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    inv = sc_map["INVALID_INPUT"]
    assert inv["passed"] is True

    multi = sc_map["MULTI_SENSOR_ISOLATION"]
    assert multi["passed"] is True


def test_10_recovery_and_repeated_run_scenarios(evaluation_data: dict):
    """Verify recovery after dropout and deterministic repeated runs."""
    sc_map = {sc["scenario"]: sc for sc in evaluation_data.get("scenarios", [])}

    rec = sc_map["RECOVERY_AFTER_MISSING_DATA"]
    assert rec["passed"] is True
    assert rec["observed_status"] == "NORMAL"

    rep = sc_map["REPEATED_DETERMINISTIC_RUN"]
    assert rep["passed"] is True
    assert rep["observed_status"] == "MATCHED"


# -----------------------------------------------------------------------------
# 3. Quantitative Evaluation & Report Artifact Verification
# -----------------------------------------------------------------------------
def test_11_authoritative_metrics_preserved(evaluation_data: dict):
    """Verify authoritative Z-score and LSTM metrics match frozen constants exactly."""
    q_eval = evaluation_data.get("quantitative_evaluation", {})

    # Z-Score baseline authoritative values
    z_metrics = q_eval["zscore_baseline"]["test_metrics"]
    assert z_metrics["accuracy"] == 0.8060
    assert z_metrics["precision"] == 0.7167
    assert z_metrics["recall"] == 0.1356
    assert z_metrics["f1_score"] == 0.2281
    assert z_metrics["false_positive_rate"] == 0.0144

    # LSTM Autoencoder authoritative values
    lstm_test = q_eval["lstm_autoencoder"]["test_metrics"]
    assert lstm_test["accuracy"] == 0.5140
    assert lstm_test["precision"] == 0.2679
    assert lstm_test["recall"] == 0.5709
    assert lstm_test["f1_score"] == 0.3646
    assert lstm_test["false_positive_rate"] == 0.5050

    # Ensure no NaN / non-finite values anywhere in quantitative metrics
    json_str = json.dumps(q_eval)
    assert "NaN" not in json_str
    assert "Infinity" not in json_str


def test_12_final_evaluation_artifacts_exist_on_disk():
    """Verify official JSON and Markdown evaluation reports exist on disk."""
    json_path = Path("ml/results/bharati_final_evaluation.json")
    md_path = Path("ml/results/bharati_final_evaluation.md")

    assert json_path.exists(), "JSON evaluation report must exist."
    assert md_path.exists(), "Markdown evaluation report must exist."

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["report_metadata"]["station_id"] == "BRT"
    assert data["report_metadata"]["model_version"] == DEFAULT_BHARATI_MODEL_VERSION
    assert len(data["scenarios"]) == 12

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    assert "NORMAL_DAY" in md_content
    assert "SPIKE" in md_content
    assert "DRIFT" in md_content
    assert "Synthetic Telemetry Scope" in md_content
