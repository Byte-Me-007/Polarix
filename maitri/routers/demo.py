from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.demo import (
    DemoFullSequenceResponse,
    DemoScenarioStartResponse,
    DemoScenarioStatusResponse,
)
from maitri.services.demo_service import (
    get_station_scenario_status,
    run_full_demo_sequence,
    start_station_scenario,
    stop_station_scenario,
)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post(
    "/scenarios/{station_id}/{scenario_name}/start",
    response_model=DemoScenarioStartResponse,
    status_code=status.HTTP_200_OK,
)
def start_demo_scenario(
    station_id: str,
    scenario_name: str,
    step: int = Query(0, ge=0, description="Time series step index"),
    db: Session = Depends(get_db),
):
    try:
        return start_station_scenario(
            db, station_id_or_code=station_id, scenario_name=scenario_name, step=step
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


@router.post(
    "/scenarios/{station_id}/stop",
    response_model=DemoScenarioStatusResponse,
    status_code=status.HTTP_200_OK,
)
def stop_demo_scenario(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return stop_station_scenario(db, station_id_or_code=station_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/scenarios/{station_id}/status",
    response_model=DemoScenarioStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_scenario_status(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_station_scenario_status(db, station_id_or_code=station_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/run/full-sequence/{station_id}",
    response_model=DemoFullSequenceResponse,
    status_code=status.HTTP_200_OK,
)
def run_full_demo_sequence_route(
    station_id: str,
    db: Session = Depends(get_db),
):
    try:
        return run_full_demo_sequence(db, station_id_or_code=station_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
