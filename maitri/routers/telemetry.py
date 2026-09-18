from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.telemetry import TelemetryCreate, TelemetryResponse
from maitri.services.telemetry_service import create_telemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post(
    "/", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED
)
def record_telemetry(
    telemetry_in: TelemetryCreate, db: Session = Depends(get_db)
):
    try:
        return create_telemetry(db, telemetry_in)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc
