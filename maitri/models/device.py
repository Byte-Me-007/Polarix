from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String

from maitri.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, default="inactive")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
