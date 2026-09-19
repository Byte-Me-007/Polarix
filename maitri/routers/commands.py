from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.command import CommandCreate, CommandResponse
from maitri.services.command_service import (
    create_command,
    execute_command,
    get_command_by_id_or_code,
    list_commands,
)

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post(
    "/", response_model=CommandResponse, status_code=status.HTTP_201_CREATED
)
def create_new_command(
    command_in: CommandCreate, db: Session = Depends(get_db)
):
    try:
        return create_command(db, command_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=list[CommandResponse])
def get_all_commands(
    station_id: int | None = Query(None, description="Filter by station ID"),
    status: str | None = Query(None, description="Filter by status (PENDING, EXECUTED, FAILED)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_commands(db, station_id=station_id, status=status, limit=limit)


@router.get("/{command_id}", response_model=CommandResponse)
def get_single_command(command_id: str, db: Session = Depends(get_db)):
    cmd = get_command_by_id_or_code(db, command_id)
    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command '{command_id}' not found",
        )
    return cmd


@router.post("/{command_id}/execute", response_model=CommandResponse)
def run_command_execution(command_id: str, db: Session = Depends(get_db)):
    try:
        return execute_command(db, command_id)
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
