"""Unified Event Schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    station_id: int
    event_type: str
    severity: str = "INFO"
    source: str
    description: str
    details: str | None = None


class EventCreate(EventBase):
    event_id: str | None = None
    timestamp: datetime | None = None


class EventResponse(EventBase):
    id: int
    event_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
