from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from maitri.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=False
    )
    sensor_id = Column(
        Integer, ForeignKey("sensors.id"), index=True, nullable=False
    )
    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    quality = Column(
        String, default="GOOD", nullable=False
    )  # GOOD, WARNING, BAD, UNKNOWN, OFFLINE
    source = Column(String, default="API", nullable=False)  # SIMULATOR, MQTT, API
    anomaly_score = Column(Float, nullable=True)
    synced = Column(Boolean, default=False, nullable=False)

    station = relationship("Station")
    sensor = relationship("Sensor")
