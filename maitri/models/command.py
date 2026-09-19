from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from maitri.database import Base


class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, index=True, nullable=False)
    station_id = Column(
        Integer, ForeignKey("stations.id"), index=True, nullable=True
    )
    command_type = Column(String, nullable=False)  # START_SCENARIO, STOP_SCENARIO, SET_NETWORK_OFFLINE, SET_NETWORK_ONLINE, REQUEST_SYNC, ACKNOWLEDGE_ALERT, RESOLVE_ALERT
    status = Column(
        String, default="PENDING", index=True, nullable=False
    )  # PENDING, EXECUTED, FAILED
    payload = Column(Text, nullable=True)  # JSON serialized string
    result_message = Column(String, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    executed_at = Column(DateTime, nullable=True)

    station = relationship("Station")
