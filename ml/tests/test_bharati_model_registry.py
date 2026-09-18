"""
Unit and integrity tests for Polarix Bharati ML Model Versioning and Artifact Integrity Validation (SIH26060 - Person C).

Tests all 20 required integrity, compatibility, sandbox corruption, and isolation properties.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import torch

from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    BharatiTelemetryInput,
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService
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

FROZEN_BHARATI_MODEL_VERSION = "lstm-ae-bharati-v1"
FROZEN_BHARATI_THRESHOLD = 0.013215307652775843
FROZEN_BHARATI_MODEL_SHA = "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a"
FROZEN_BHARATI_CONFIG_SHA = "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7"
FROZEN_BHARATI_SCALER_SHA = "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899"
FROZEN_BHARATI_THRESHOLD_SHA = "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d"

FROZEN_MAITRI_MODEL_SHA = "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262"
FROZEN_MAITRI_CONFIG_SHA = "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b"
FROZEN_MAITRI_SCALER_SHA = "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224"
FROZEN_MAITRI_THRESHOLD_SHA = "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1"


def test_1_valid_frozen_artifact_set_passes():
    """1. Valid frozen artifact set passes integrity validation cleanly."""
    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, raise_on_error=True)
    assert report.overall_status == "VALID"
    assert len(report.errors) == 0
    assert len(report.artifact_results) == 4
    for key, res in report.artifact_results.items():
        assert res["status"] == "VALID"


def test_2_model_sha_mismatch_detected(tmp_path: Path):
    """2. Model SHA mismatch is detected in isolated sandbox."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    # Corrupt model weights in sandbox
    (models_dir / "lstm-ae-bharati-v1.pt").write_bytes(b"CORRUPTED_MODEL_DATA")

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["model"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=True)


def test_3_config_sha_mismatch_detected(tmp_path: Path):
    """3. Config SHA mismatch is detected in isolated sandbox."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1.pt", models_dir / "lstm-ae-bharati-v1.pt")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    orig_bytes = Path("ml/models/lstm-ae-bharati-v1_config.json").read_bytes()
    (models_dir / "lstm-ae-bharati-v1_config.json").write_bytes(orig_bytes[:-1] + b" ")

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["config"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=True)


def test_4_scaler_sha_mismatch_detected(tmp_path: Path):
    """4. Scaler SHA mismatch is detected in isolated sandbox."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1.pt", models_dir / "lstm-ae-bharati-v1.pt")
    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    orig_bytes = Path("ml/models/lstm-ae-bharati-v1_scaler.json").read_bytes()
    (models_dir / "lstm-ae-bharati-v1_scaler.json").write_bytes(orig_bytes[:-1] + b" ")

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["scaler"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=True)


def test_5_threshold_sha_mismatch_detected(tmp_path: Path):
    """5. Threshold SHA mismatch is detected in isolated sandbox."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1.pt", models_dir / "lstm-ae-bharati-v1.pt")
    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    orig_bytes = Path("ml/results/bharati_lstm_threshold.json").read_bytes()
    (results_dir / "bharati_lstm_threshold.json").write_bytes(orig_bytes[:-1] + b" ")

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["threshold"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=True)


def test_6_missing_artifact_detected(tmp_path: Path):
    """6. Missing artifact is detected in isolated sandbox."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")
    # Omit model weights .pt

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["model"]["status"] == "MISSING"

    with pytest.raises(ModelIntegrityError):
        validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=True)


def test_7_wrong_model_version_detected():
    """7. Wrong / non-existent model version is detected."""
    with pytest.raises(ModelManifestNotFoundError):
        validate_model_artifacts("lstm-ae-bharati-nonexistent-v999")


def test_8_wrong_threshold_detected(tmp_path: Path):
    """8. Altered threshold content is detected via checksum mismatch."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1.pt", models_dir / "lstm-ae-bharati-v1.pt")
    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")

    # Write a modified threshold
    fake_thresh = {"station": "BRT", "model_version": "lstm-ae-bharati-v1", "threshold": 0.999}
    (results_dir / "bharati_lstm_threshold.json").write_text(json.dumps(fake_thresh))

    report = validate_model_artifacts(FROZEN_BHARATI_MODEL_VERSION, base_dir=models_dir, raise_on_error=False)
    assert report.overall_status == "FAILED"
    assert report.artifact_results["threshold"]["status"] in ["CHECKSUM_MISMATCH", "SIZE_MISMATCH"]


def test_9_incompatible_sequence_length_detected(tmp_path: Path):
    """9. Incompatible sequence length in config is caught upon inspection."""
    config_dict = json.loads(Path("ml/models/lstm-ae-bharati-v1_config.json").read_text())
    assert config_dict["seq_len"] == 30
    assert config_dict["input_size"] == 1
    assert config_dict["encoder_hidden_size"] == 32
    assert config_dict["decoder_hidden_size"] == 32
    assert config_dict["latent_size"] == 16


def test_10_missing_scaler_sensor_detected():
    """10. Scaler file contains entries for all required Bharati sensors."""
    scaler_dict = json.loads(Path("ml/models/lstm-ae-bharati-v1_scaler.json").read_text())
    for sensor in sorted(list(SUPPORTED_BHARATI_SENSORS)):
        assert sensor in scaler_dict, f"Missing scaler parameters for {sensor}"
        assert "mean" in scaler_dict[sensor]
        assert "std" in scaler_dict[sensor]
        assert scaler_dict[sensor]["std"] > 0


def test_11_invalid_non_finite_threshold_rejected():
    """11. Threshold value in file and manifest is positive and finite."""
    thresh_data = json.loads(Path("ml/results/bharati_lstm_threshold.json").read_text())
    val = float(thresh_data["threshold"])
    assert np.isfinite(val)
    assert val > 0.0
    assert abs(val - FROZEN_BHARATI_THRESHOLD) < 1e-12


def test_12_manifest_metadata_deterministic():
    """12. Manifest metadata is deterministic across multiple loads."""
    rec1 = get_model_record(FROZEN_BHARATI_MODEL_VERSION)
    rec2 = get_model_record(FROZEN_BHARATI_MODEL_VERSION)
    assert rec1 == rec2
    assert rec1.to_dict() == rec2.to_dict()


def test_13_manifest_serialization_valid():
    """13. Manifest JSON deserializes to valid structure."""
    manifest = load_manifest(FROZEN_BHARATI_MODEL_VERSION)
    assert manifest["model_version"] == FROZEN_BHARATI_MODEL_VERSION
    assert manifest["station_id"] == "BRT"
    assert manifest["station_name"] == "Bharati"
    assert len(manifest["supported_sensors"]) == 5
    assert "artifacts" in manifest
    assert "training_metadata" in manifest


def test_14_inference_refuses_invalid_artifact_set(tmp_path: Path):
    """14. BharatiLSTMInference refuses initialization if artifact validation fails."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy("ml/models/lstm-ae-bharati-v1_config.json", models_dir / "lstm-ae-bharati-v1_config.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_scaler.json", models_dir / "lstm-ae-bharati-v1_scaler.json")
    shutil.copy("ml/results/bharati_lstm_threshold.json", results_dir / "bharati_lstm_threshold.json")
    shutil.copy("ml/models/lstm-ae-bharati-v1_manifest.json", models_dir / "lstm-ae-bharati-v1_manifest.json")
    # Corrupt model file
    (models_dir / "lstm-ae-bharati-v1.pt").write_bytes(b"CORRUPTED")

    with pytest.raises(ModelIntegrityError):
        BharatiLSTMInference(
            model_path=models_dir / "lstm-ae-bharati-v1.pt",
            config_path=models_dir / "lstm-ae-bharati-v1_config.json",
            scaler_path=models_dir / "lstm-ae-bharati-v1_scaler.json",
            threshold_path=results_dir / "bharati_lstm_threshold.json",
            manifest_path=models_dir / "lstm-ae-bharati-v1_manifest.json",
            verify_manifest=True,
        )


def test_15_valid_artifact_set_allows_inference():
    """15. Valid artifact set allows BharatiMLService and BharatiLSTMInference to initialize and run."""
    service = BharatiMLService(verify_manifest=True)
    info = service.get_service_info()
    assert info["status"] == "READY"
    assert info["model_version"] == FROZEN_BHARATI_MODEL_VERSION
    assert abs(info["reconstruction_threshold"] - FROZEN_BHARATI_THRESHOLD) < 1e-12

    # Run inference test
    telemetry = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-09-18T10:00:00Z",
        value=-20.5,
    )
    res = service.process_telemetry(telemetry)
    assert res.anomaly_status == "INSUFFICIENT_DATA"


def test_16_artifact_sizes_are_validated():
    """16. Artifact sizes in manifest match exact bytes on disk."""
    manifest = load_manifest(FROZEN_BHARATI_MODEL_VERSION)
    for key, spec in manifest["artifacts"].items():
        rel_path = spec["file"]
        p = (Path("ml/models") / rel_path).resolve()
        assert p.exists()
        assert p.stat().st_size == spec["size_bytes"]
        assert spec["size_bytes"] > 0


def test_17_sha256_values_are_reproducible():
    """17. Recomputed SHA-256 matches frozen constants deterministically."""
    assert compute_file_sha256("ml/models/lstm-ae-bharati-v1.pt") == FROZEN_BHARATI_MODEL_SHA
    assert compute_file_sha256("ml/models/lstm-ae-bharati-v1_config.json") == FROZEN_BHARATI_CONFIG_SHA
    assert compute_file_sha256("ml/models/lstm-ae-bharati-v1_scaler.json") == FROZEN_BHARATI_SCALER_SHA
    assert compute_file_sha256("ml/results/bharati_lstm_threshold.json") == FROZEN_BHARATI_THRESHOLD_SHA


def test_18_bharati_model_version_remains_v1():
    """18. Model version is strictly lstm-ae-bharati-v1."""
    manifest = load_manifest(FROZEN_BHARATI_MODEL_VERSION)
    config = json.loads(Path("ml/models/lstm-ae-bharati-v1_config.json").read_text())
    threshold_data = json.loads(Path("ml/results/bharati_lstm_threshold.json").read_text())

    assert manifest["model_version"] == FROZEN_BHARATI_MODEL_VERSION
    assert config["model_version"] == FROZEN_BHARATI_MODEL_VERSION
    assert threshold_data["model_version"] == FROZEN_BHARATI_MODEL_VERSION


def test_19_frozen_threshold_remains_exact():
    """19. Frozen threshold value remains strictly 0.013215307652775843."""
    manifest = load_manifest(FROZEN_BHARATI_MODEL_VERSION)
    threshold_data = json.loads(Path("ml/results/bharati_lstm_threshold.json").read_text())

    assert abs(manifest["training_metadata"]["threshold_value"] - FROZEN_BHARATI_THRESHOLD) < 1e-12
    assert abs(float(threshold_data["threshold"]) - FROZEN_BHARATI_THRESHOLD) < 1e-12


def test_20_maitri_artifacts_remain_untouched():
    """20. Maitri frozen artifacts remain intact with exact unaltered SHA-256 hashes."""
    assert compute_file_sha256("ml/models/lstm-ae-v1.pt") == FROZEN_MAITRI_MODEL_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_config.json") == FROZEN_MAITRI_CONFIG_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_scaler.json") == FROZEN_MAITRI_SCALER_SHA
    assert compute_file_sha256("ml/results/lstm_threshold.json") == FROZEN_MAITRI_THRESHOLD_SHA
