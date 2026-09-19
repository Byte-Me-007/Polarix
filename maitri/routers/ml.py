"""ML Integration Router.

Provides endpoints for inspecting ML integration status and contracts.
"""

from typing import Any
from fastapi import APIRouter, status

from maitri.schemas.ml import (
    MLAdapterResult,
    MLInferenceRequestPlaceholder,
    MLInferenceResponsePlaceholder,
    MLStatusResponse,
)
from maitri.services.ml_adapter import ml_adapter

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status", response_model=MLStatusResponse)
def get_ml_status():
    """Returns the current connection status of Person C's ML API.

    Returns 'ML INTEGRATION: NOT CONNECTED' when unconfigured or unreachable.
    """
    return ml_adapter.get_status()


@router.get("/contract")
def get_placeholder_contract() -> dict[str, Any]:
    """Returns the placeholder request and response contracts for Person C's ML API."""
    return {
        "status": ml_adapter.get_status().status,
        "request_schema": MLInferenceRequestPlaceholder.model_json_schema(),
        "response_schema": MLInferenceResponsePlaceholder.model_json_schema(),
        "example_request": {
            "station_id": 1,
            "timestamp": "2026-09-19T12:00:00Z",
            "features": {
                "ambient_temp_c": -28.4,
                "wind_speed_ms": 14.2,
                "generator_power_kw": 41.8,
                "vibration_hz": 24.1,
                "fuel_level_pct": 84.5,
            },
            "metadata": {
                "station_code": "MTR",
                "operational_mode": "STANDARD_BALANCED",
            },
        },
        "example_response": {
            "model_version": "polaris-anomaly-v1.0",
            "anomaly_detected": False,
            "anomaly_score": 0.04,
            "predicted_component": None,
            "confidence": 0.98,
            "recommendation": "Nominal operations",
        },
    }


@router.post(
    "/infer",
    response_model=MLAdapterResult,
    status_code=status.HTTP_200_OK,
)
def run_ml_inference(payload: MLInferenceRequestPlaceholder):
    """Slot for testing or invoking inference through the ML adapter.

    Guarantees no fake anomaly scores: returns 'ML INTEGRATION: NOT CONNECTED'
    if Person C's API is unavailable.
    """
    return ml_adapter.send_inference(
        station_id=payload.station_id,
        timestamp=payload.timestamp,
        features=payload.features,
        metadata=payload.metadata,
    )
