"""Unified Event Model.

Records high-level operational events across stations (alerts, commands, scenario transitions).
Does NOT record high-frequency raw telemetry ticks.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from maitri.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        String,
        default=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}",
        index=True,
        nullable=False,
    )
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=False
    )
    event_type = Column(String, index=True, nullable=False)
    severity = Column(String, default="INFO", nullable=False)
    source = Column(String, nullable=False)
    description = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    station = relationship("Station")
