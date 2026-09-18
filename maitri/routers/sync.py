from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.sync import NetworkToggleResponse, SyncStatusResponse
from maitri.services.sync_service import (
    get_sync_status,
    set_network_offline,
    set_network_online_and_sync,
)

router = APIRouter(tags=["sync"])


@router.get("/sync/status", response_model=SyncStatusResponse)
def read_sync_status(db: Session = Depends(get_db)):
    """Get current synchronization status and telemetry queue counts."""
    return get_sync_status(db)


@router.post(
    "/demo/network/offline",
    response_model=NetworkToggleResponse,
    status_code=status.HTTP_200_OK,
)
def trigger_network_offline(db: Session = Depends(get_db)):
    """Simulate a network / satellite outage (OFFLINE mode). Incoming telemetry will be queued."""
    return set_network_offline(db)


@router.post(
    "/demo/network/online",
    response_model=NetworkToggleResponse,
    status_code=status.HTTP_200_OK,
)
def trigger_network_online(db: Session = Depends(get_db)):
    """Simulate network recovery (ONLINE mode) and synchronize all queued pending records."""
    return set_network_online_and_sync(db)
