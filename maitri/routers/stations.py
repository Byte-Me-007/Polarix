from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.alert import AlertResponse
from maitri.schemas.energy import EnergyOptimizationResponse
from maitri.schemas.event import EventResponse
from maitri.schemas.readiness import MissionReadinessResponse
from maitri.schemas.resource import ResourceForecastResponse, ResourceResponse
from maitri.schemas.station import SensorResponse, StationResponse
from maitri.schemas.telemetry import TelemetryResponse
from maitri.services.alert_service import list_alerts_by_station
from maitri.services.energy_service import get_station_energy_optimization
from maitri.services.event_service import list_events_by_station
from maitri.services.readiness_service import calculate_mission_readiness
from maitri.services.resource_service import (
    get_station_resources_forecast,
    list_resources_by_station,
)
from maitri.services.station_service import (
    get_sensors_by_station,
    get_station_by_id_or_code,
    list_stations,
)
from maitri.services.telemetry_service import (
    get_latest_telemetry_by_station,
    get_telemetry_by_station,
)

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("/", response_model=list[StationResponse])
def get_all_stations(db: Session = Depends(get_db)):
    return list_stations(db)


@router.get("/{station_id}", response_model=StationResponse)
def get_station(station_id: str, db: Session = Depends(get_db)):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return station


@router.get("/{station_id}/sensors", response_model=list[SensorResponse])
def get_station_sensors(station_id: str, db: Session = Depends(get_db)):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return get_sensors_by_station(db, station.id)


@router.get("/{station_id}/telemetry", response_model=list[TelemetryResponse])
def get_station_telemetry_history(
    station_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return get_telemetry_by_station(db, station.id, limit=limit)


@router.get(
    "/{station_id}/telemetry/latest", response_model=list[TelemetryResponse]
)
def get_station_latest_telemetry(
    station_id: str,
    db: Session = Depends(get_db),
):
    station = get_station_by_id_or_code(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_id}' not found",
        )
    return get_latest_telemetry_by_station(db, station.id)


@router.get("/{station_id}/alerts", response_model=list[AlertResponse])
def get_station_alerts(
    station_id: str,
    alert_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        return list_alerts_by_station(
            db, station_id_or_code=station_id, status=alert_status, limit=limit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{station_id}/resources", response_model=list[ResourceResponse])
def get_station_resources(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return list_resources_by_station(db, station_id_or_code=station_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{station_id}/resources/forecast",
    response_model=list[ResourceForecastResponse],
)
def get_station_resources_forecast_route(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_station_resources_forecast(
            db, station_id_or_code=station_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{station_id}/energy/optimization",
    response_model=EnergyOptimizationResponse,
)
def get_station_energy_optimization_route(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_station_energy_optimization(
            db, station_id_or_code=station_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{station_id}/events",
    response_model=list[EventResponse],
)
def get_station_events_route(
    station_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieves chronological operational events for the station."""
    try:
        return list_events_by_station(db, station_id_or_code=station_id, limit=limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{station_id}/mission-readiness",
    response_model=MissionReadinessResponse,
)
def get_station_mission_readiness_route(
    station_id: str,
    db: Session = Depends(get_db),
):
    """Single source of truth for Station Mission Readiness."""
    try:
        return calculate_mission_readiness(db, station_id_or_code=station_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )





