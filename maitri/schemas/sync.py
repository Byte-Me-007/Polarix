from datetime import datetime
from pydantic import BaseModel


class SyncStatusResponse(BaseModel):
    network_status: str  # ONLINE, OFFLINE, SYNCING
    is_online: bool
    pending_count: int
    synced_count: int
    total_count: int
    last_sync_timestamp: datetime | None = None
    message: str | None = None


class NetworkToggleResponse(BaseModel):
    network_status: str  # ONLINE, OFFLINE, SYNCING
    is_online: bool
    pending_count: int
    synced_count: int
    synced_now: int = 0
    message: str
