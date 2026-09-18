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


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=False
    )
    sensor_code = Column(String, unique=True, index=True, nullable=False)
    sensor_name = Column(String, nullable=False)
    domain = Column(
        String, index=True, nullable=False
    )  # ENVIRONMENT, STRUCTURE, ENERGY, LOGISTICS
    unit = Column(String, nullable=True)
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    location_z = Column(Float, nullable=True)
    criticality = Column(String, default="MEDIUM", nullable=False)
    minimum_value = Column(Float, nullable=True)
    maximum_value = Column(Float, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    station = relationship("Station", back_populates="sensors")
