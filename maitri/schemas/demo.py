from datetime import datetime
from typing import Any
from pydantic import BaseModel


class DemoScenarioStatusResponse(BaseModel):
    station_id: int
    station_code: str
    active_scenario: str | None = None
    is_active: bool = False
    started_at: datetime | None = None
    message: str | None = None
    sync_status: str
    active_alerts_count: int


class DemoScenarioStartResponse(BaseModel):
    station_id: int
    station_code: str
    scenario_name: str
    status: str
    is_active: bool
    telemetry_generated_count: int
    active_alerts_count: int
    sync_status: dict[str, Any]
    energy_optimization: dict[str, Any]
    resource_forecast_summary: list[dict[str, Any]]
    message: str


class DemoPhaseResult(BaseModel):
    phase: str
    scenario_name: str
    telemetry_ingested_count: int
    network_status: str
    pending_sync_count: int
    active_alerts_count: int
    energy_mode: str | None = None
    message: str


class DemoFullSequenceResponse(BaseModel):
    station_id: int
    station_code: str
    total_phases: int
    phases: list[DemoPhaseResult]
    final_sync_status: dict[str, Any]
    final_energy_optimization: dict[str, Any]
    message: str
