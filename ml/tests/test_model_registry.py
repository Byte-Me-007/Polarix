"""
Unit tests for Polarix ML Model Registry & Integrity Validation (SIH26060 - Person C).
"""

import json
import shutil
from pathlib import Path

import pytest
import torch

from ml.inference.lstm_inference import LSTMAutoencoderInference
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    ModelRecord,
    ModelValidationReport,
    ModelVersionMismatchError,
    compute_file_sha256,
    get_model_record,
    load_manifest,
    validate_model_artifacts,
)


def test_1_manifest_loads_successfully():
    """Verify lstm-ae-v1 manifest JSON loads cleanly with all expected keys."""
    manifest = load_manifest("lstm-ae-v1")
    assert manifest["model_version"] == "lstm-ae-v1"
    assert manifest["model_type"] == "LSTM_AUTOENCODER"
    assert manifest["station_id"] == "MTR"
    assert "artifacts" in manifest
    assert "training_metadata" in manifest


def test_2_model_version_is_correct():
    """Verify model version in manifest and record matches expected 'lstm-ae-v1'."""
    record = get_model_record("lstm-ae-v1")
    assert record.model_version == "lstm-ae-v1"
    assert record.station_id == "MTR"
    assert record.sequence_length == 30
    assert record.hidden_size == 32
    assert record.latent_size == 16


def test_3_all_expected_artifacts_exist():
    """Verify all 4 referenced artifacts exist on filesystem."""
    manifest = load_manifest("lstm-ae-v1")
    manifest_dir = Path("ml/models")

    for key, spec in manifest["artifacts"].items():
        rel_path = spec["file"]
        artifact_path = (manifest_dir / rel_path).resolve()
        assert artifact_path.exists(), f"Missing artifact '{key}': {artifact_path}"


def test_4_sha256_validation_passes():
    """Verify live SHA-256 checksum of every artifact matches manifest."""
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    assert report.overall_status == "VALID"
    assert len(report.errors) == 0
    for key, res in report.artifact_results.items():
        assert res["status"] == "VALID"
        assert res["actual_sha256"] == res["expected_sha256"]


def test_5_file_size_validation_passes():
    """Verify live byte sizes match manifest specifications."""
    report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
    for key, res in report.artifact_results.items():
        assert res["actual_size"] == res["expected_size"]
        assert res["actual_size"] > 0


def test_6_missing_artifact_is_detected(tmp_path: Path):
    """Verify validator detects missing artifact and reports error without touching live repo."""
    # Create isolated sandbox in tmp_path
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    # Copy files
    shutil.copy("ml/models/lstm-ae-v1.pt", models_dir / "lstm-ae-v1.pt")
    shutil.copy("ml/models/lstm-ae-v1_config.json", models_dir / "lstm-ae-v1_config.json")
    shutil.copy("ml/models/lstm-ae-v1_scaler.json", models_dir / "lstm-ae-v1_scaler.json")
    shutil.copy("ml/models/lstm-ae-v1_manifest.json", models_dir / "lstm-ae-v1_manifest.json")
    # Omit threshold file intentionally

    report = validate_model_artifacts("lstm-ae-v1", base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["threshold"]["status"] == "MISSING"

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts("lstm-ae-v1", base_dir=models_dir, raise_on_error=True)


def test_7_checksum_mismatch_is_detected(tmp_path: Path):
    """Verify validator detects byte-level corruption / checksum alteration in temporary copy."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-v1.pt", models_dir / "lstm-ae-v1.pt")
    shutil.copy("ml/models/lstm-ae-v1_scaler.json", models_dir / "lstm-ae-v1_scaler.json")
    shutil.copy("ml/results/lstm_threshold.json", results_dir / "lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-v1_manifest.json", models_dir / "lstm-ae-v1_manifest.json")

    # Corrupt the config file by padding spaces (same size or different content)
    config_orig = Path("ml/models/lstm-ae-v1_config.json").read_bytes()
    corrupted_config = config_orig[:-1] + b" "
    (models_dir / "lstm-ae-v1_config.json").write_bytes(corrupted_config)

    report = validate_model_artifacts("lstm-ae-v1", base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["config"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts("lstm-ae-v1", base_dir=models_dir, raise_on_error=True)


def test_8_incorrect_model_version_is_rejected():
    """Verify requesting non-existent model version raises ModelManifestNotFoundError."""
    with pytest.raises(ModelManifestNotFoundError):
        validate_model_artifacts("non_existent_version_v999")


def test_9_inference_refuses_corrupted_artifacts(tmp_path: Path):
    """Verify LSTMAutoencoderInference refuses initialization if manifest validation fails."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    # Create dummy corrupted model in sandbox
    shutil.copy("ml/models/lstm-ae-v1_config.json", models_dir / "lstm-ae-v1_config.json")
    shutil.copy("ml/models/lstm-ae-v1_scaler.json", models_dir / "lstm-ae-v1_scaler.json")
    shutil.copy("ml/results/lstm_threshold.json", results_dir / "lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-v1_manifest.json", models_dir / "lstm-ae-v1_manifest.json")
    # Corrupt model weights file in sandbox
    (models_dir / "lstm-ae-v1.pt").write_bytes(b"CORRUPTED_WEIGHTS")

    with pytest.raises(ModelIntegrityError):
        LSTMAutoencoderInference(
            model_path=models_dir / "lstm-ae-v1.pt",
            config_path=models_dir / "lstm-ae-v1_config.json",
            scaler_path=models_dir / "lstm-ae-v1_scaler.json",
            threshold_path=results_dir / "lstm_threshold.json",
            manifest_path=models_dir / "lstm-ae-v1_manifest.json",
            verify_manifest=True,
        )


def test_10_registry_metadata_serialization_deterministic():
    """Verify ModelRecord serialization to dict and JSON is deterministic."""
    rec1 = get_model_record("lstm-ae-v1")
    rec2 = get_model_record("lstm-ae-v1")

    assert rec1 == rec2
    assert rec1.to_dict() == rec2.to_dict()
    assert rec1.to_json() == rec2.to_json()
    assert json.loads(rec1.to_json())["model_version"] == "lstm-ae-v1"
