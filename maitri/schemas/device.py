from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    device_id: str
    name: str
    location: str | None = None
    status: str = "inactive"


class DeviceCreate(DeviceBase):
    pass


class DeviceResponse(DeviceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
