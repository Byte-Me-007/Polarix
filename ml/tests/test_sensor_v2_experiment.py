"""
Unit and Integration Tests for Sensor ML V2 Retraining, Diagnostic & Recovery-Aware Framework (SIH26060 - Person C).

Validates:
1. V2 experiment configuration objects and types.
2. Cryptographic immutability of frozen V1 production artifacts.
3. V2 experiment output structure, models, scalers, and results.
4. Validation-only threshold selection integrity (no test leakage).
5. Comparison artifact JSON schema compliance and valid metric intervals.
6. Diagnostic and window contamination artifact schemas and statistical consistency.
7. Sensor-wise robust normalization and operating point calibration algorithms.
8. Recovery-aware sequence classification (CLEAN_NORMAL, CONTAMINATED_NORMAL, ACTIVE_ANOMALY).
9. Chronological non-leakage in recovery-aware dataset preparation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import pytest

from ml.experiments.sensor_v2.calibrate_v2_sensors import (
    fit_sensor_norm_parameters,
    search_threshold,
    transform_scores,
)
from ml.experiments.sensor_v2.config import (
    BHARATI_V2_CONFIG,
    MAITRI_V2_CONFIG,
    SensorV2ExperimentConfig,
)
from ml.experiments.sensor_v2.evaluate_v2_experiments import (
    calculate_binary_metrics,
    compute_roc_pr_metrics,
    select_validation_threshold,
)
from ml.experiments.sensor_v2.prepare_recovery_aware_sequences import (
    SensorScalerSpec,
    extract_recovery_aware_windows,
    prepare_recovery_aware_dataset,
)
from ml.experiments.sensor_v2.train_recovery_aware_models import (
    BHARATI_RECOVERY_CONFIG,
    MAITRI_RECOVERY_CONFIG,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Cryptographic SHA-256 baseline hashes for frozen V1 production artifacts
FROZEN_V1_HASHES: Dict[str, str] = {
    "ml/models/lstm-ae-v1.pt": "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262",
    "ml/models/lstm-ae-v1_config.json": "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b",
    "ml/models/lstm-ae-v1_scaler.json": "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224",
    "ml/results/lstm_threshold.json": "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1",
    "ml/models/lstm-ae-bharati-v1.pt": "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a",
    "ml/models/lstm-ae-bharati-v1_config.json": "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7",
    "ml/models/lstm-ae-bharati-v1_scaler.json": "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899",
    "ml/results/bharati_lstm_threshold.json": "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d",
}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestSensorV2Config:
    """Test suite for V2 experiment configuration objects."""

    def test_maitri_v2_config_integrity(self) -> None:
        assert MAITRI_V2_CONFIG.station_id == "MTR"
        assert MAITRI_V2_CONFIG.station_name == "Maitri"
        assert MAITRI_V2_CONFIG.model_version == "lstm-ae-v2-candidate"
        assert MAITRI_V2_CONFIG.epochs == 60
        assert MAITRI_V2_CONFIG.batch_size == 64
        assert MAITRI_V2_CONFIG.lr_scheduler == "ReduceLROnPlateau"
        assert MAITRI_V2_CONFIG.early_stopping_patience == 12
        assert MAITRI_V2_CONFIG.seed == 42
        assert (REPO_ROOT / MAITRI_V2_CONFIG.dataset_csv).exists()

    def test_bharati_v2_config_integrity(self) -> None:
        assert BHARATI_V2_CONFIG.station_id == "BRT"
        assert BHARATI_V2_CONFIG.station_name == "Bharati"
        assert BHARATI_V2_CONFIG.model_version == "lstm-ae-bharati-v2-candidate"
        assert BHARATI_V2_CONFIG.epochs == 60
        assert BHARATI_V2_CONFIG.batch_size == 64
        assert BHARATI_V2_CONFIG.lr_scheduler == "ReduceLROnPlateau"
        assert BHARATI_V2_CONFIG.early_stopping_patience == 12
        assert BHARATI_V2_CONFIG.seed == 42
        assert (REPO_ROOT / BHARATI_V2_CONFIG.dataset_csv).exists()


class TestFrozenV1Preservation:
    """Verify that all 8 frozen V1 artifacts remain 100% untouched."""

    @pytest.mark.parametrize("rel_path,expected_hash", FROZEN_V1_HASHES.items())
    def test_frozen_v1_artifact_hashes_unchanged(self, rel_path: str, expected_hash: str) -> None:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"Frozen V1 file missing: {rel_path}"
        actual_hash = _sha256(file_path)
        assert actual_hash == expected_hash, (
            f"CRITICAL: Frozen V1 artifact '{rel_path}' was modified! Expected {expected_hash}, got {actual_hash}"
        )


class TestV2ExperimentOutputs:
    """Verify presence and validity of all generated V2 experiment artifacts."""

    def test_v2_model_artifacts_exist(self) -> None:
        models_dir = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "models"
        required_files = [
            "lstm-ae-v2-candidate.pt",
            "lstm-ae-v2-candidate_config.json",
            "lstm-ae-v2-candidate_scaler.json",
            "lstm-ae-bharati-v2-candidate.pt",
            "lstm-ae-bharati-v2-candidate_config.json",
            "lstm-ae-bharati-v2-candidate_scaler.json",
            "lstm-ae-v2-recovery-aware-candidate.pt",
            "lstm-ae-v2-recovery-aware-candidate_config.json",
            "lstm-ae-v2-recovery-aware-candidate_scaler.json",
            "lstm-ae-bharati-v2-recovery-aware-candidate.pt",
            "lstm-ae-bharati-v2-recovery-aware-candidate_config.json",
            "lstm-ae-bharati-v2-recovery-aware-candidate_scaler.json",
        ]
        for f_name in required_files:
            p = models_dir / f_name
            assert p.exists(), f"Missing V2 model artifact: {p}"
            assert p.stat().st_size > 0, f"Artifact is empty: {p}"

    def test_v2_results_artifacts_exist(self) -> None:
        results_dir = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "results"
        required_files = [
            "mtr_v2_training_history.json",
            "brt_v2_training_history.json",
            "mtr_v2_threshold.json",
            "brt_v2_threshold.json",
            "mtr_v2_reconstruction_errors.csv",
            "brt_v2_reconstruction_errors.csv",
            "sensor_v2_comparison.json",
            "sensor_v2_comparison.md",
            "reconstruction_error_diagnostics.json",
            "reconstruction_error_diagnostics.md",
            "window_contamination_analysis.json",
            "sensor_v2_calibration_experiments.json",
            "sensor_v2_calibration_experiments.md",
            "recovery_aware_comparison.json",
            "recovery_aware_comparison.md",
        ]
        for f_name in required_files:
            p = results_dir / f_name
            assert p.exists(), f"Missing V2 result artifact: {p}"
            assert p.stat().st_size > 0, f"Result file is empty: {p}"


class TestV2ThresholdCalibrationLogic:
    """Verify validation-only threshold tuning mathematical properties."""

    def test_select_validation_threshold_no_leakage(self) -> None:
        val_df = pd.DataFrame({
            "reconstruction_error": [0.001, 0.002, 0.005, 0.010, 0.020, 0.050],
            "is_anomaly": [0, 0, 0, 1, 1, 1],
            "split": ["val"] * 6,
        })
        thresh, metrics = select_validation_threshold(val_df, num_candidates=50)
        assert isinstance(thresh, float)
        assert thresh > 0.002
        assert metrics["f1"] == 1.0

    def test_binary_metrics_bounds(self) -> None:
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 1, 0, 0, 1])
        metrics = calculate_binary_metrics(y_true, y_pred)
        for key in ["accuracy", "precision", "recall", "f1", "fpr"]:
            assert 0.0 <= metrics[key] <= 1.0


class TestV2ComparisonArtifactSchema:
    """Verify schema integrity of the machine-readable comparison artifact."""

    def test_comparison_json_schema(self) -> None:
        json_path = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "results" / "sensor_v2_comparison.json"
        assert json_path.exists()

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "stations" in data
        assert "MTR" in data["stations"]
        assert "BRT" in data["stations"]

        for st_key in ["MTR", "BRT"]:
            st_data = data["stations"][st_key]
            assert "v1" in st_data
            assert "v2" in st_data
            assert "delta" in st_data

            for sec in ["v1", "v2", "delta"]:
                sub = st_data[sec]
                for m in ["precision", "recall", "f1", "fpr", "accuracy"]:
                    assert m in sub
                    if sub[m] is not None:
                        assert isinstance(sub[m], (int, float))

            assert "test_confusion_matrix" in st_data
            assert "per_anomaly_type_breakdown" in st_data
            assert "per_sensor_threshold_candidate" in st_data


class TestV2DiagnosticsAndNormalization:
    """Test suite for distribution diagnostics and robust normalization."""

    def test_robust_norm_parameter_fitting(self) -> None:
        val_df = pd.DataFrame({
            "sensor_id": ["S1"] * 10 + ["S2"] * 10,
            "reconstruction_error": [0.01 + i * 0.001 for i in range(10)] + [0.05 + i * 0.005 for i in range(10)],
            "is_anomaly": [0] * 10 + [0] * 10,
            "any_anomaly_in_window": [0] * 10 + [0] * 10,
        })
        params = fit_sensor_norm_parameters(val_df)
        assert "S1" in params
        assert "S2" in params
        assert params["S1"].median_clean_normal < params["S2"].median_clean_normal
        assert params["S1"].robust_scale > 0.0
        assert params["S2"].robust_scale > 0.0

    def test_robust_transform_scores(self) -> None:
        val_df = pd.DataFrame({
            "sensor_id": ["S1", "S1", "S2"],
            "reconstruction_error": [0.01, 0.05, 0.05],
            "is_anomaly": [0, 1, 0],
            "any_anomaly_in_window": [0, 0, 0],
        })
        params = fit_sensor_norm_parameters(val_df)
        scores = transform_scores(val_df, params, method="robust")
        assert len(scores) == 3
        assert scores[1] > scores[0]

    def test_search_threshold_criteria(self) -> None:
        scores = np.array([0.1, 0.2, 0.3, 1.5, 2.0, 3.5])
        y_true = np.array([0, 0, 0, 1, 1, 1])

        th_f1, m_f1 = search_threshold(scores, y_true, criterion="max_f1")
        assert m_f1["f1"] == 1.0

        th_fpr, m_fpr = search_threshold(scores, y_true, criterion="fpr_constrained", max_fpr=0.10)
        assert m_fpr["fpr"] <= 0.10

    def test_window_contamination_schema(self) -> None:
        p = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "results" / "window_contamination_analysis.json"
        assert p.exists()
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
        assert "stations" in doc
        assert "MTR" in doc["stations"]
        assert "BRT" in doc["stations"]
        for st_key in ["MTR", "BRT"]:
            st_data = doc["stations"][st_key]
            assert "val" in st_data["splits"]
            assert "test" in st_data["splits"]
            for split_name in ["val", "test"]:
                split_info = st_data["splits"][split_name]
                assert "clean_normal" in split_info["global_distributions"]
                assert "contaminated_normal" in split_info["global_distributions"]
                assert "active_anomaly" in split_info["global_distributions"]
                cn_mean = split_info["global_distributions"]["clean_normal"]["mean"]
                con_mean = split_info["global_distributions"]["contaminated_normal"]["mean"]
                assert con_mean > cn_mean


class TestRecoveryAwareSequences:
    """Test suite for recovery-aware window extraction and classification."""

    def test_window_state_classification(self) -> None:
        # Create a synthetic series of length 35 with an anomaly at index 20
        df = pd.DataFrame({
            "timestamp": [f"2026-03-01T00:{i:02d}:00+00:00" for i in range(35)],
            "value": [10.0 + i * 0.1 for i in range(35)],
            "is_anomaly": [0] * 20 + [1] + [0] * 14,
            "anomaly_type": ["NORMAL"] * 20 + ["SPIKE"] + ["NORMAL"] * 14,
            "station_id": ["MTR"] * 35,
        })
        scaler = SensorScalerSpec(sensor_id="TEMP_001", station_id="MTR", mean=10.0, std=1.0, unit="C")

        seqs, meta = extract_recovery_aware_windows(
            df, scaler, seq_len=30, clean_normal_only=False, split_name="val"
        )
        assert len(seqs) == 6  # 35 - 30 + 1 = 6 windows
        # Window 0: indices 0..29 -> contains anomaly at 20, target is 29 (is_anom=0) -> CONTAMINATED_NORMAL
        assert meta[0]["window_state"] == "CONTAMINATED_NORMAL"
        assert meta[0]["window_contains_anomaly"] == 1
        assert meta[0]["is_anomaly"] == 0

    def test_clean_normal_only_training_policy(self) -> None:
        df = pd.DataFrame({
            "timestamp": [f"2026-03-01T00:{i:02d}:00+00:00" for i in range(35)],
            "value": [10.0 + i * 0.1 for i in range(35)],
            "is_anomaly": [0] * 20 + [1] + [0] * 14,
            "anomaly_type": ["NORMAL"] * 20 + ["SPIKE"] + ["NORMAL"] * 14,
            "station_id": ["MTR"] * 35,
        })
        scaler = SensorScalerSpec(sensor_id="TEMP_001", station_id="MTR", mean=10.0, std=1.0, unit="C")

        # When clean_normal_only=True, all windows containing index 20 must be excluded
        seqs, meta = extract_recovery_aware_windows(
            df, scaler, seq_len=30, clean_normal_only=True, split_name="train"
        )
        assert len(seqs) == 0  # all 6 windows contain index 20, so 0 are clean normal

    def test_recovery_aware_dataset_non_leakage(self) -> None:
        data = prepare_recovery_aware_dataset(
            station_id="MTR",
            csv_path="ml/data/maitri_synthetic_telemetry.csv",
            seq_len=30,
        )
        assert len(data["train_sequences"]) > 0
        assert len(data["val_sequences"]) > 0
        assert len(data["test_sequences"]) > 0

        # Verify no anomalous points in training metadata
        for m in data["train_metadata"]:
            assert m["window_state"] == "CLEAN_NORMAL"
            assert m["is_anomaly"] == 0
            assert m["window_contains_anomaly"] == 0

    def test_recovery_aware_comparison_schema(self) -> None:
        p = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "results" / "recovery_aware_comparison.json"
        assert p.exists()
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
        assert "stations" in doc
        assert "MTR" in doc["stations"]
        assert "BRT" in doc["stations"]
        for st_key in ["MTR", "BRT"]:
            st = doc["stations"][st_key]
            assert "clean_normal_subset_metrics" in st
            assert "recovery_normal_subset_metrics" in st
            assert "test_metrics" in st
            assert "v1_frozen" in st
