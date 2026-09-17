from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String

from maitri.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
