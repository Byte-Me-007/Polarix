from sqlalchemy.orm import Session

from maitri.models.sensor_reading import SensorReading
from maitri.schemas.sensor_reading import SensorReadingCreate


def create_sensor_reading(db: Session, reading: SensorReadingCreate) -> SensorReading:
    db_reading = SensorReading(
        device_id=reading.device_id,
        metric=reading.metric,
        value=reading.value,
        unit=reading.unit,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


def list_sensor_readings(
    db: Session, device_id: str | None = None
) -> list[SensorReading]:
    query = db.query(SensorReading)
    if device_id is not None:
        query = query.filter(SensorReading.device_id == device_id)
    return query.all()
