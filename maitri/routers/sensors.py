from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.sensor_reading import (
    SensorReadingCreate,
    SensorReadingResponse,
)
from maitri.services.sensor_service import (
    create_sensor_reading,
    list_sensor_readings,
)

router = APIRouter(prefix="/sensor-readings", tags=["sensor-readings"])


@router.post(
    "/", response_model=SensorReadingResponse, status_code=status.HTTP_201_CREATED
)
def record_sensor_reading(
    reading: SensorReadingCreate, db: Session = Depends(get_db)
):
    return create_sensor_reading(db, reading)


@router.get("/", response_model=list[SensorReadingResponse])
def get_sensor_readings(db: Session = Depends(get_db)):
    return list_sensor_readings(db)


@router.get("/device/{device_id}", response_model=list[SensorReadingResponse])
def get_device_sensor_readings(device_id: str, db: Session = Depends(get_db)):
    return list_sensor_readings(db, device_id=device_id)
