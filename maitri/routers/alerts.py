from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.alert import AlertCreate, AlertResponse
from maitri.services.alert_service import (
    acknowledge_alert,
    create_alert,
    get_alert_by_id,
    resolve_alert,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def post_alert(alert_in: AlertCreate, db: Session = Depends(get_db)):
    try:
        return create_alert(db, alert_in)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found",
        )
    return alert


@router.post("/{alert_id}/ack", response_model=AlertResponse)
def ack_alert(alert_id: int, db: Session = Depends(get_db)):
    try:
        return acknowledge_alert(db, alert_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_station_alert(alert_id: int, db: Session = Depends(get_db)):
    try:
        return resolve_alert(db, alert_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
