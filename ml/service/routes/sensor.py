"""
Sensor ML Inference Route for Polarix ML Service (SIH26060 - Person C).
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status

from ml.inference.maitri_backend_contract import process_backend_payload as process_mtr_payload
from ml.inference.bharati_backend_contract import process_backend_payload as process_brt_payload
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.inference_contract import (
    DuplicateTelemetryError as MTR_DuplicateError,
    InvalidContractError as MTR_InvalidContractError,
    StaleTelemetryError as MTR_StaleError,
    UnsupportedSensorError as MTR_UnsupportedSensorError,
    UnsupportedStationError as MTR_UnsupportedStationError,
)
from ml.inference.bharati_inference_contract import (
    DuplicateTelemetryError as BRT_DuplicateError,
    InvalidContractError as BRT_InvalidContractError,
    StaleTelemetryError as BRT_StaleError,
    UnsupportedSensorError as BRT_UnsupportedSensorError,
    UnsupportedStationError as BRT_UnsupportedStationError,
)
from ml.service.schemas import SensorTelemetryInput

router = APIRouter(prefix="/api/v1/ml/sensor", tags=["Sensor ML"])

# Long-lived singleton instances for Maitri and Bharati Sensor ML services
_maitri_service: Optional[MaitriMLService] = None
_bharati_service: Optional[BharatiMLService] = None


def get_maitri_service() -> MaitriMLService:
    global _maitri_service
    if _maitri_service is None:
        _maitri_service = MaitriMLService()
    return _maitri_service


def get_bharati_service() -> BharatiMLService:
    global _bharati_service
    if _bharati_service is None:
        _bharati_service = BharatiMLService()
    return _bharati_service


def reset_sensor_services(station_id: Optional[str] = None) -> None:
    """Reset sensor ML services history buffers."""
    if station_id is None or station_id == "MTR":
        if _maitri_service is not None:
            _maitri_service.reset_all()
    if station_id is None or station_id == "BRT":
        if _bharati_service is not None:
            _bharati_service.reset_all()


@router.post("/analyze", response_model=Dict[str, Any])
def analyze_sensor(telemetry: SensorTelemetryInput) -> Dict[str, Any]:
    """
    Ingest a single sensor observation and execute LSTM-Autoencoder anomaly detection.

    - Returns anomaly_status ('NORMAL', 'ANOMALY', 'INSUFFICIENT_DATA', 'MISSING_DATA')
    - Returns anomaly_type ('NORMAL', 'SPIKE', 'DRIFT', 'STUCK_VALUE', 'STEP_CHANGE', etc.)
    - Returns anomaly_score (finite float or null during warmup/missing)
    - Rejects 'BHR' (requires Person A normalization to 'BRT')
    """
    payload = telemetry.model_dump()
    station = telemetry.station_id

    if station == "BHR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid station_id 'BHR'. Person C Sensor ML contracts enforce canonical station ID 'BRT'. "
                "Person A backend must normalize 'BHR' to 'BRT' before invoking Sensor ML."
            ),
        )

    if station == "MTR":
        svc = get_maitri_service()
        try:
            return process_mtr_payload(svc, payload)
        except (
            MTR_DuplicateError,
            MTR_StaleError,
            MTR_UnsupportedSensorError,
            MTR_UnsupportedStationError,
            MTR_InvalidContractError,
            ValueError,
        ) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Maitri Sensor ML inference error: {str(e)}",
            )

    elif station == "BRT":
        svc = get_bharati_service()
        try:
            return process_brt_payload(svc, payload)
        except (
            BRT_DuplicateError,
            BRT_StaleError,
            BRT_UnsupportedSensorError,
            BRT_UnsupportedStationError,
            BRT_InvalidContractError,
            ValueError,
        ) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bharati Sensor ML inference error: {str(e)}",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported station_id '{station}'. Supported stations: ['MTR', 'BRT'].",
        )


@router.post("/reset", response_model=Dict[str, str])
def reset_sensor_history(station_id: Optional[str] = None) -> Dict[str, str]:
    """Reset sensor history buffers."""
    reset_sensor_services(station_id=station_id)
    target = station_id if station_id else "ALL_STATIONS"
    return {"status": "ok", "message": f"Sensor ML buffer reset for {target}"}
