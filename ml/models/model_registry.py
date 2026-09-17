"""
Polarix ML Model Registry & Integrity Validation Layer (SIH26060 - Person C).

Features:
- Framework-independent model metadata and registry management.
- Cryptographic SHA-256 and byte-size artifact integrity verification.
- Enforces strict manifest validation before model weights or scalers are loaded into inference.
- Provides structured validation reports and clean exception handling.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_DIR = REPO_ROOT / "ml" / "models"


class ModelRegistryError(Exception):
    """Base exception for model registry and integrity errors."""
    pass


class ModelManifestNotFoundError(ModelRegistryError, FileNotFoundError):
    """Raised when a model manifest file cannot be located."""
    pass


class ModelIntegrityError(ModelRegistryError, ValueError):
    """Raised when an artifact is missing, corrupted, or has a checksum mismatch."""
    pass


class ModelVersionMismatchError(ModelRegistryError, ValueError):
    """Raised when the loaded manifest does not match the requested model version."""
    pass


@dataclass(frozen=True)
class ArtifactEntry:
    """Metadata specification for an individual model artifact."""

    file: str
    role: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelRecord:
    """Consolidated metadata record representing a registered model version."""

    model_version: str
    model_type: str
    station_id: str
    supported_sensors: List[str]
    sequence_length: int
    hidden_size: int
    latent_size: int
    loss_function: str
    training_dataset: str
    training_dataset_version: str
    training_seed: int
    training_split: str
    threshold_file: str
    scaler_file: str
    model_file: str
    created_at: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass(frozen=True)
class ArtifactValidationItem:
    """Result of integrity validation for a single artifact."""

    role: str
    file: str
    expected_sha256: str
    actual_sha256: Optional[str]
    expected_size: int
    actual_size: Optional[int]
    status: str  # "VALID", "MISSING", "CHECKSUM_MISMATCH", "SIZE_MISMATCH"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelValidationReport:
    """Comprehensive artifact validation report for a registered model."""

    model_version: str
    manifest_file: str
    overall_status: str  # "VALID", "FAILED"
    validated_at: str
    artifact_results: Dict[str, Dict[str, Any]]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_manifest_path(
    model_version: str = "lstm-ae-v1",
    manifest_path: Optional[Union[str, Path]] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Locate the manifest JSON file for a given model version."""
    if manifest_path is not None:
        p = Path(manifest_path)
        if not p.exists():
            raise ModelManifestNotFoundError(f"Manifest not found at explicit path: {p}")
        return p

    search_dir = Path(base_dir) if base_dir is not None else DEFAULT_MODELS_DIR
    candidate = search_dir / f"{model_version}_manifest.json"
    if not candidate.exists():
        raise ModelManifestNotFoundError(
            f"Manifest file '{candidate.name}' not found in '{search_dir}'."
        )
    return candidate


def load_manifest(
    model_version: str = "lstm-ae-v1",
    manifest_path: Optional[Union[str, Path]] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Load and parse the manifest dictionary for a registered model."""
    path = find_manifest_path(
        model_version=model_version,
        manifest_path=manifest_path,
        base_dir=base_dir,
    )
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ModelRegistryError(f"Corrupted JSON in manifest '{path}': {exc}") from exc

    manifest_version = data.get("model_version")
    if manifest_version != model_version:
        raise ModelVersionMismatchError(
            f"Manifest model_version '{manifest_version}' does not match requested '{model_version}'."
        )
    return data


def get_model_record(
    model_version: str = "lstm-ae-v1",
    manifest_path: Optional[Union[str, Path]] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> ModelRecord:
    """Extract a typed ModelRecord from the manifest metadata."""
    manifest = load_manifest(
        model_version=model_version,
        manifest_path=manifest_path,
        base_dir=base_dir,
    )

    t_meta = manifest.get("training_metadata", {})
    artifacts = manifest.get("artifacts", {})

    return ModelRecord(
        model_version=manifest.get("model_version", model_version),
        model_type=manifest.get("model_type", "LSTM_AUTOENCODER"),
        station_id=manifest.get("station_id", "MTR"),
        supported_sensors=manifest.get("supported_sensors", []),
        sequence_length=int(t_meta.get("sequence_length", 30)),
        hidden_size=int(t_meta.get("hidden_size", 32)),
        latent_size=int(t_meta.get("latent_size", 16)),
        loss_function=str(t_meta.get("loss_function", "MSELoss")),
        training_dataset=str(t_meta.get("training_dataset", "unknown")),
        training_dataset_version=str(t_meta.get("training_dataset_version", "unknown")),
        training_seed=int(t_meta.get("training_seed", 42)),
        training_split=str(t_meta.get("training_split", "70% Normal")),
        threshold_file=str(artifacts.get("threshold", {}).get("file", "")),
        scaler_file=str(artifacts.get("scaler", {}).get("file", "")),
        model_file=str(artifacts.get("model", {}).get("file", "")),
        created_at=str(t_meta.get("created_at", "not_recorded")),
        status=str(t_meta.get("status", "VALIDATED")),
    )


def validate_model_artifacts(
    model_version: str = "lstm-ae-v1",
    manifest_path: Optional[Union[str, Path]] = None,
    base_dir: Optional[Union[str, Path]] = None,
    raise_on_error: bool = False,
) -> ModelValidationReport:
    """
    Verify the cryptographic SHA-256 checksums and file sizes of all registered artifacts.

    Parameters:
    -----------
    model_version : str
        The version string of the model to validate (e.g. 'lstm-ae-v1').
    manifest_path : Optional[Union[str, Path]]
        Explicit path to the manifest JSON file.
    base_dir : Optional[Union[str, Path]]
        Directory containing model artifacts (defaults to repo ml/models/).
    raise_on_error : bool
        If True, raises ModelIntegrityError on any verification failure.

    Returns:
    --------
    ModelValidationReport: Detailed status report for each artifact.
    """
    m_path = find_manifest_path(
        model_version=model_version,
        manifest_path=manifest_path,
        base_dir=base_dir,
    )
    manifest = load_manifest(
        model_version=model_version,
        manifest_path=m_path,
    )

    manifest_dir = m_path.parent
    artifacts_dict = manifest.get("artifacts", {})

    results: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    for key, spec in artifacts_dict.items():
        rel_file = spec.get("file", "")
        expected_sha = spec.get("sha256", "").lower().strip()
        expected_size = spec.get("size_bytes", 0)
        role = spec.get("role", key)

        target_file = (manifest_dir / rel_file).resolve()

        if not target_file.exists():
            err = f"Artifact '{key}' ({role}) missing at path: {target_file}"
            errors.append(err)
            results[key] = ArtifactValidationItem(
                role=role,
                file=rel_file,
                expected_sha256=expected_sha,
                actual_sha256=None,
                expected_size=expected_size,
                actual_size=None,
                status="MISSING",
                error_message=err,
            ).to_dict()
            continue

        actual_size = target_file.stat().st_size
        actual_sha = compute_file_sha256(target_file).lower()

        if actual_size != expected_size:
            err = f"Artifact '{key}' size mismatch: expected {expected_size} bytes, got {actual_size} bytes."
            errors.append(err)
            results[key] = ArtifactValidationItem(
                role=role,
                file=rel_file,
                expected_sha256=expected_sha,
                actual_sha256=actual_sha,
                expected_size=expected_size,
                actual_size=actual_size,
                status="SIZE_MISMATCH",
                error_message=err,
            ).to_dict()
            continue

        if actual_sha != expected_sha:
            err = f"Artifact '{key}' checksum mismatch: expected {expected_sha[:10]}..., got {actual_sha[:10]}..."
            errors.append(err)
            results[key] = ArtifactValidationItem(
                role=role,
                file=rel_file,
                expected_sha256=expected_sha,
                actual_sha256=actual_sha,
                expected_size=expected_size,
                actual_size=actual_size,
                status="CHECKSUM_MISMATCH",
                error_message=err,
            ).to_dict()
            continue

        # Valid artifact
        results[key] = ArtifactValidationItem(
            role=role,
            file=rel_file,
            expected_sha256=expected_sha,
            actual_sha256=actual_sha,
            expected_size=expected_size,
            actual_size=actual_size,
            status="VALID",
            error_message=None,
        ).to_dict()

    overall_status = "VALID" if len(errors) == 0 else "FAILED"
    report = ModelValidationReport(
        model_version=model_version,
        manifest_file=str(m_path),
        overall_status=overall_status,
        validated_at=datetime.now(timezone.utc).isoformat(),
        artifact_results=results,
        errors=errors,
    )

    if raise_on_error and overall_status == "FAILED":
        raise ModelIntegrityError(f"Model integrity validation failed for '{model_version}':\n" + "\n".join(errors))

    return report
