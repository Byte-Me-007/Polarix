"""Mission Readiness Schemas."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SubsystemReadiness(BaseModel):
    name: str
    status: str  # OPERATIONAL, DEGRADED, AT_RISK, CRITICAL
    score: float = Field(..., ge=0.0, le=100.0)
    details: str


class MissionReadinessResponse(BaseModel):
    station_id: int
    station_code: str
    overall_status: str  # OPERATIONAL, DEGRADED, AT_RISK, CRITICAL
    readiness_score: float = Field(..., ge=0.0, le=100.0)
    subsystems: dict[str, SubsystemReadiness]
    active_alerts_count: dict[str, int]
    critical_factors: list[str] = []
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
