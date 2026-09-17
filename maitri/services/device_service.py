from sqlalchemy.orm import Session

from maitri.models.device import Device
from maitri.schemas.device import DeviceCreate


def create_device(db: Session, device: DeviceCreate) -> Device:
    db_device = Device(
        device_id=device.device_id,
        name=device.name,
        location=device.location,
        status=device.status,
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_device_by_id(db: Session, device_id: int) -> Device | None:
    return db.query(Device).filter(Device.id == device_id).first()


def get_device_by_device_id(db: Session, device_id: str) -> Device | None:
    return db.query(Device).filter(Device.device_id == device_id).first()


def list_devices(db: Session) -> list[Device]:
    return db.query(Device).all()
