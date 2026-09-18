from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.station import SensorResponse, StationResponse
from maitri.services.station_service import (
    get_sensors_by_station,
    get_station_by_id_or_code,
    list_stations,
)

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("/", response_model=list[StationResponse])
def get_all_stations(db: Session = Depends(get_db)):
    return list_stations(db)


@router.get("/{station_id}", response_model=StationResponse)
def get_station(station_id: str, db: Session = Depends(get_db)):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return station


@router.get("/{station_id}/sensors", response_model=list[SensorResponse])
def get_station_sensors(station_id: str, db: Session = Depends(get_db)):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return get_sensors_by_station(db, station.id)
