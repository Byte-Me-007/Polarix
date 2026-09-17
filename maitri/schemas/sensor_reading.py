from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SensorReadingBase(BaseModel):
    device_id: str
    metric: str
    value: float
    unit: str | None = None


class SensorReadingCreate(SensorReadingBase):
    pass


class SensorReadingResponse(SensorReadingBase):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
