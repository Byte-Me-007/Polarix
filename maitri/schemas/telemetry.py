from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TelemetryCreate(BaseModel):
    station_id: int | None = None
    station_code: str | None = None
    sensor_id: int | None = None
    sensor_code: str | None = None
    value: float
    unit: str | None = None
    quality: str = "GOOD"  # GOOD, WARNING, BAD, UNKNOWN, OFFLINE
    source: str = "API"  # SIMULATOR, MQTT, API
    timestamp: datetime | None = None
    anomaly_score: float | None = None
    synced: bool | None = None


class TelemetryResponse(BaseModel):
    id: int
    station_id: int
    sensor_id: int
    timestamp: datetime
    value: float
    unit: str | None = None
    quality: str
    source: str
    anomaly_score: float | None = None
    synced: bool

    model_config = ConfigDict(from_attributes=True)
