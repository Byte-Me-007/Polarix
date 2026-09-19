from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from maitri.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=False
    )
    sensor_id = Column(
        Integer, ForeignKey("sensors.id"), index=True, nullable=True
    )
    severity = Column(
        String, default="MEDIUM", nullable=False
    )  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    alert_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    anomaly_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    status = Column(
        String, default="ACTIVE", index=True, nullable=False
    )  # ACTIVE, ACKNOWLEDGED, RESOLVED
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    station = relationship("Station")
    sensor = relationship("Sensor")
