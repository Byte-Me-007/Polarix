from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SensorBase(BaseModel):
    sensor_code: str
    sensor_name: str
    domain: str
    unit: str | None = None
    location_x: float | None = None
    location_y: float | None = None
    location_z: float | None = None
    criticality: str = "MEDIUM"
    minimum_value: float | None = None
    maximum_value: float | None = None
    active: bool = True
    asset_id: str | None = None
    zone: str | None = None


class SensorCreate(SensorBase):
    station_id: int | None = None
    station_code: str | None = None


class SensorResponse(SensorBase):
    id: int
    station_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StationBase(BaseModel):
    station_code: str
    station_name: str
    description: str | None = None
    latitude: float
    longitude: float
    status: str = "ACTIVE"


class StationCreate(StationBase):
    pass


class StationResponse(StationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StationDetailResponse(StationResponse):
    sensors: list[SensorResponse] = []

    model_config = ConfigDict(from_attributes=True)
