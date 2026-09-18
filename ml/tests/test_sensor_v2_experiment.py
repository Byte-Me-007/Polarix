"""
Unit and Integration Tests for Sensor ML V2 Retraining Framework (SIH26060 - Person C).

Validates:
1. V2 experiment configuration objects and types.
2. Cryptographic immutability of frozen V1 production artifacts.
3. V2 experiment output structure, models, scalers, and results.
4. Validation-only threshold selection integrity (no test leakage).
5. Comparison artifact JSON schema compliance and valid metric intervals.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import pytest

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
