"""
Energy ML Inference Route for Polarix ML Service (SIH26060 - Person C).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status

from ml.energy.inference.backend_adapter import EnergyMLBackendAdapter
from ml.service.schemas import EnergyTelemetryInput

router = APIRouter(prefix="/api/v1/ml/energy", tags=["Energy ML"])

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = REPO_ROOT / "ml/energy/models"

# Long-lived singleton adapter instance preserving station ring buffers across requests
_adapter_instance: Optional[EnergyMLBackendAdapter] = None


def get_energy_adapter() -> EnergyMLBackendAdapter:
    """Retrieve or lazily initialize the singleton EnergyMLBackendAdapter."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    return _adapter_instance


def reset_energy_adapter(station_id: Optional[str] = None) -> None:
    """Reset the energy adapter history (primarily for tests)."""
    global _adapter_instance
    if _adapter_instance is not None:
        _adapter_instance.reset(station_id=station_id)


@router.post("/predict", response_model=Dict[str, Any])
def predict_energy(telemetry: EnergyTelemetryInput) -> Dict[str, Any]:
    """
    Ingest a single canonical hourly energy telemetry record and generate a unified prediction.

    - If history < 24 contiguous hours: Returns status 'INSUFFICIENT_HISTORY' with prediction = null.
    - If history >= 24 contiguous hours: Returns status 'PREDICTION_AVAILABLE' with unified forecast & deficit risk.
    - Rejects 'BHR' station code (requires Person A backend normalization to 'BRT').
    - Rejects duplicate or out-of-order timestamps deterministically.
    """
    adapter = get_energy_adapter()
    payload = telemetry.model_dump(exclude_none=False)

    # Explicit check for BHR legacy code to return descriptive 400 error
    if telemetry.station_id == "BHR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid station_id 'BHR'. Person C ML contracts strictly enforce canonical station ID 'BRT' "
                "for Bharati station. Person A backend must normalize 'BHR' to 'BRT' before invoking Energy ML."
            ),
        )

    try:
        response = adapter.ingest_and_predict(payload)
        return response.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Energy ML inference error: {str(e)}",
        )


@router.post("/reset", response_model=Dict[str, str])
def reset_energy_history(station_id: Optional[str] = None) -> Dict[str, str]:
    """Reset energy station buffer history."""
    reset_energy_adapter(station_id=station_id)
    target = station_id if station_id else "ALL_STATIONS"
    return {"status": "ok", "message": f"Energy ML buffer reset for {target}"}
