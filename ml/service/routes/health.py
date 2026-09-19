"""
Health and Version Routes for Polarix ML Service (SIH26060 - Person C).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

from ml.service.schemas import HealthResponse, VersionResponse

router = APIRouter(prefix="/api/v1/ml", tags=["Health & Metadata"])

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Check whether the Polarix ML service is active and healthy."""
    return HealthResponse(status="ok", service="polarix-ml")


@router.get("/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    """Get metadata regarding deployed model releases, thresholds, and contracts."""
    energy_manifest_path = REPO_ROOT / "ml/energy/results/energy_ml_milestone_manifest.json"
    if energy_manifest_path.exists():
        try:
            energy_manifest = json.loads(energy_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            energy_manifest = {}
    else:
        energy_manifest = {}

    sensor_models = {
        "maitri": {
            "model_version": "lstm-ae-v1",
            "station_id": "MTR",
            "model_type": "LSTM Autoencoder",
            "frozen_threshold": 0.017674,
            "sequence_length": 30,
            "status": "PRODUCTION",
        },
        "bharati": {
            "model_version": "lstm-ae-bharati-v1",
            "station_id": "BRT",
            "model_type": "LSTM Autoencoder",
            "frozen_threshold": 0.013215307652775843,
            "sequence_length": 30,
            "status": "PRODUCTION",
        },
    }

    energy_models = {
        "unified_model_version": energy_manifest.get("model_versions", {}).get("unified_service", "energy-ml-v1-candidate"),
        "model_status": energy_manifest.get("model_status", "CANDIDATE"),
        "forecast_model_version": energy_manifest.get("model_versions", {}).get("forecast_model", "lstm-energy-baseline-v1"),
        "risk_model_version": energy_manifest.get("model_versions", {}).get("risk_model", "energy-deficit-risk-v1"),
        "deficit_risk_threshold": 0.35,
        "required_history_hours": 24,
        "supported_stations": ["MTR", "BRT"],
    }

    provenance = {
        "source": "SYNTHETIC_POLARIX_OPERATIONAL_DATA",
        "calibration_references": [
            "National Centre for Polar and Ocean Research (NCPOR) Meteorological Archives",
            "Australian Antarctic Data Centre (AADC CC BY 4.0) Electrical Load Archives",
        ],
        "disclaimer": "Validated on synthetic Polarix operational microgrid telemetry. Not validated on real classified station SCADA telemetry.",
    }

    return VersionResponse(
        service_name="polarix-ml-service",
        service_version="1.0.0",
        contract_version="energy-ml-contract-v1",
        sensor_models=sensor_models,
        energy_models=energy_models,
        provenance=provenance,
    )
