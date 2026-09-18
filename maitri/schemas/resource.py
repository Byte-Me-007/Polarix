from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ResourceType = Literal["DIESEL", "BATTERY", "WATER", "FOOD", "MEDICAL", "SPARE_PARTS"]
ResourceStatus = Literal["NORMAL", "LOW", "WARNING", "CRITICAL"]


class ResourceBase(BaseModel):
    resource_type: str
    current_quantity: float = Field(ge=0.0)
    capacity: float = Field(gt=0.0)
    consumption_rate: float = Field(default=0.0, ge=0.0)
    unit: str
    status: str = "NORMAL"


class ResourceCreate(ResourceBase):
    station_id: int | None = None
    station_code: str | None = None


class ResourceUpdate(BaseModel):
    current_quantity: float | None = Field(default=None, ge=0.0)
    capacity: float | None = Field(default=None, gt=0.0)
    consumption_rate: float | None = Field(default=None, ge=0.0)
    unit: str | None = None
    status: str | None = None


class ResourceResponse(ResourceBase):
    id: int
    station_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceForecastResponse(BaseModel):
    resource_id: int
    station_id: int
    resource_type: str
    current_quantity: float
    capacity: float
    consumption_rate: float
    unit: str
    estimated_hours_remaining: float | None = None
    estimated_days_remaining: float | None = None
    risk_level: str
    forecast_message: str

    model_config = ConfigDict(from_attributes=True)

