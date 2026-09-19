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


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=False
    )
    resource_type = Column(
        String, nullable=False, index=True
    )  # DIESEL, BATTERY, WATER, FOOD, MEDICAL, SPARE_PARTS
    current_quantity = Column(Float, nullable=False)
    capacity = Column(Float, nullable=False)
    consumption_rate = Column(Float, default=0.0, nullable=False)
    unit = Column(String, nullable=False)
    status = Column(
        String, default="NORMAL", nullable=False
    )  # NORMAL, LOW, WARNING, CRITICAL
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    station = relationship("Station")
