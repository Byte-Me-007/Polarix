from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from maitri.models.telemetry import Telemetry

_network_status: str = "ONLINE"
_last_sync_time: datetime | None = None


def get_network_status() -> str:
    """Return the current network status: ONLINE, OFFLINE, or SYNCING."""
    global _network_status
    return _network_status


def set_network_status(status: str) -> None:
    """Set the network status."""
    global _network_status
    st = status.upper()
    if st not in ("ONLINE", "OFFLINE", "SYNCING"):
        raise ValueError(f"Invalid network status: {status}")
    _network_status = st


def is_network_online() -> bool:
    """Check if the network status is currently ONLINE."""
    return get_network_status() == "ONLINE"


def reset_network_state() -> None:
    """Reset network state back to default ONLINE."""
    global _network_status, _last_sync_time
    _network_status = "ONLINE"
    _last_sync_time = None


def get_sync_status(db: Session) -> dict[str, Any]:
    """Retrieve synchronization counts and network status from database."""
    global _last_sync_time
    pending = db.query(Telemetry).filter(Telemetry.synced == False).count()  # noqa: E712
    synced = db.query(Telemetry).filter(Telemetry.synced == True).count()  # noqa: E712
    total = pending + synced
    status = get_network_status()
    online = status == "ONLINE"

    if status == "OFFLINE":
        msg = f"Network is OFFLINE. {pending} records queued locally in pending state."
    elif status == "SYNCING":
        msg = "Network is SYNCING queued records."
    elif pending > 0:
        msg = f"Network is ONLINE with {pending} unsynced records awaiting sync."
    else:
        msg = "Network is ONLINE. All telemetry records synchronized."

    return {
        "network_status": status,
        "is_online": online,
        "pending_count": pending,
        "synced_count": synced,
        "total_count": total,
        "last_sync_timestamp": _last_sync_time,
        "message": msg,
    }


def set_network_offline(db: Session) -> dict[str, Any]:
    """Simulate network outage / OFFLINE mode."""
    set_network_status("OFFLINE")
    stats = get_sync_status(db)
    return {
        "network_status": "OFFLINE",
        "is_online": False,
        "pending_count": stats["pending_count"],
        "synced_count": stats["synced_count"],
        "synced_now": 0,
        "message": "Network set to OFFLINE. Incoming telemetry will be queued locally.",
    }


def set_network_online_and_sync(db: Session) -> dict[str, Any]:
    """Simulate recovery, flush pending queue by marking unsynced records as synced, and set status to ONLINE."""
    global _last_sync_time
    set_network_status("SYNCING")

    pending_records = (
        db.query(Telemetry).filter(Telemetry.synced == False).all()  # noqa: E712
    )
    synced_now = len(pending_records)
    for record in pending_records:
        record.synced = True
    db.commit()

    _last_sync_time = datetime.now(timezone.utc)
    set_network_status("ONLINE")
    stats = get_sync_status(db)

    return {
        "network_status": "ONLINE",
        "is_online": True,
        "pending_count": stats["pending_count"],
        "synced_count": stats["synced_count"],
        "synced_now": synced_now,
        "message": f"Network restored to ONLINE. Replayed and synced {synced_now} pending telemetry records.",
    }
