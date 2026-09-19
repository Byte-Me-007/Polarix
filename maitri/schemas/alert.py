from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

AlertSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
AlertStatus = Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]


class AlertCreate(BaseModel):
    station_id: int | None = None
    station_code: str | None = None
    sensor_id: int | None = None
    sensor_code: str | None = None
    severity: str = "MEDIUM"
    alert_type: str = "GENERIC"
    title: str
    message: str
    anomaly_score: float | None = None


class AlertResponse(BaseModel):
    id: int
    station_id: int
    sensor_id: int | None = None
    severity: str
    alert_type: str
    title: str
    message: str
    anomaly_score: float | None = None
    created_at: datetime
    status: str
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
