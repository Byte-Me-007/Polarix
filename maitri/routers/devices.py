from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.device import DeviceCreate, DeviceResponse
from maitri.services.device_service import (
    create_device,
    get_device_by_device_id,
    list_devices,
)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_new_device(device: DeviceCreate, db: Session = Depends(get_db)):
    existing = get_device_by_device_id(db, device.device_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device with id '{device.device_id}' already exists",
        )
    return create_device(db, device)


@router.get("/", response_model=list[DeviceResponse])
def get_all_devices(db: Session = Depends(get_db)):
    return list_devices(db)


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str, db: Session = Depends(get_db)):
    device = get_device_by_device_id(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )
    return device
