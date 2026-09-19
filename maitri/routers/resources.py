from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from maitri.database import get_db
from maitri.schemas.resource import (
    ResourceCreate,
    ResourceForecastResponse,
    ResourceResponse,
    ResourceUpdate,
)
from maitri.services.resource_service import (
    create_resource,
    get_resource_by_id,
    get_resource_forecast,
    update_resource,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def post_resource(resource_in: ResourceCreate, db: Session = Depends(get_db)):
    try:
        return create_resource(db, resource_in)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource_id}' not found",
        )
    return resource


@router.patch("/{resource_id}", response_model=ResourceResponse)
def patch_resource(
    resource_id: int,
    resource_update: ResourceUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_resource(db, resource_id, resource_update)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.get("/{resource_id}/forecast", response_model=ResourceForecastResponse)
def get_single_resource_forecast(
    resource_id: int, db: Session = Depends(get_db)
):
    try:
        return get_resource_forecast(db, resource_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

