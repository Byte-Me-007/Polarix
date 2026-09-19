"""Unified Event Service.

Handles operational event logging, filtering, and retrieval per station.
Operational events represent state transitions (alerts, commands, scenario switches, network changes),
NOT high-frequency raw telemetry observations.
"""

from datetime import datetime, timezone
import json
from typing import Any
from sqlalchemy import desc
from sqlalchemy.orm import Session

from maitri.models.event import Event
from maitri.schemas.event import EventCreate
from maitri.services.station_service import get_station_by_id_or_code


def log_event(
    db: Session,
    station_id_or_code: int | str,
    event_type: str,
    description: str,
    severity: str = "INFO",
    source: str = "SYSTEM",
    details: dict[str, Any] | str | None = None,
) -> Event | None:
    """Logs an operational event for a station."""
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        return None

    details_str = (
        json.dumps(details)
        if isinstance(details, dict)
        else (details if details is not None else None)
    )

    event_record = Event(
        station_id=station.id,
        event_type=event_type,
        severity=severity.upper(),
        source=source,
        description=description,
        details=details_str,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event_record)
    db.commit()
    db.refresh(event_record)
    return event_record


def list_events_by_station(
    db: Session,
    station_id_or_code: int | str,
    limit: int = 50,
) -> list[Event]:
    """Retrieves chronological operational events for a station."""
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        return []

    return (
        db.query(Event)
        .filter(Event.station_id == station.id)
        .order_by(desc(Event.timestamp), desc(Event.id))
        .limit(limit)
        .all()
    )
