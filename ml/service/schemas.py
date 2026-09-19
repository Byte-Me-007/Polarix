"""
Pydantic Schemas for Polarix ML Service (SIH26060 - Person C).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Service health status")
    service: str = Field(default="polarix-ml", description="Service identifier")


class VersionResponse(BaseModel):
    """Detailed version and model status metadata."""
    service_name: str = "polarix-ml-service"
    service_version: str = "1.0.0"
    contract_version: str = "energy-ml-contract-v1"
    sensor_models: Dict[str, Any]
    energy_models: Dict[str, Any]
    provenance: Dict[str, Any]


class EnergyTelemetryInput(BaseModel):
    """Canonical Energy Telemetry Input Payload."""
    model_config = ConfigDict(extra="ignore")

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    station_id: str = Field(..., description="Station identifier ('MTR' or 'BRT')")
    power_demand_kw: float = Field(..., description="Instantaneous aggregate station electrical power demand (kW)")
    generator_output_kw: float = Field(..., description="Instantaneous active diesel generator electrical output (kW)")
    battery_soc_percent: float = Field(..., description="Battery Energy Storage System (BESS) state-of-charge (%)")
    battery_charge_kw: float = Field(..., description="Instantaneous battery charging power (kW)")
    battery_discharge_kw: float = Field(..., description="Instantaneous battery discharging power (kW)")
    fuel_consumption_l: float = Field(..., description="Fuel consumption rate (L/h)")
    temperature_c: float = Field(..., description="Ambient air temperature (deg C)")
    humidity_percent: float = Field(..., description="Relative humidity (%)")
    pressure_hpa: float = Field(..., description="Atmospheric barometric pressure (hPa)")
    wind_speed_mps: float = Field(..., description="Wind speed (m/s)")

    # Optional upstream context
    sensor_anomaly_score: Optional[float] = Field(default=None, description="Optional upstream Sensor ML anomaly score")
    sensor_anomaly_status: Optional[str] = Field(default=None, description="Optional upstream Sensor ML anomaly status")
    sensor_anomaly_type: Optional[str] = Field(default=None, description="Optional upstream Sensor ML anomaly type")
    data_quality: Optional[str] = Field(default=None, description="Data quality flag (e.g. 'GOOD', 'MISSING')")
    source: Optional[str] = Field(default=None, description="Data provenance source (e.g. 'SIMULATOR')")


class SensorTelemetryInput(BaseModel):
    """Canonical Sensor Telemetry Input Payload."""
    model_config = ConfigDict(extra="ignore")

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    station_id: str = Field(..., description="Station identifier ('MTR' or 'BRT')")
    sensor_id: str = Field(..., description="Sensor identifier")
    value: float = Field(..., description="Observed sensor measurement value")
    quality: Optional[str] = Field(default="GOOD", description="Sensor quality flag ('GOOD', 'MISSING', 'DEGRADED')")
    unit: Optional[str] = Field(default="", description="Engineering unit")
    source: Optional[str] = Field(default="SIMULATOR", description="Data source tag")


class ErrorResponse(BaseModel):
    """Standard structured error response."""
    error: str = Field(..., description="Error category or exception type")
    detail: str = Field(..., description="Descriptive error explanation")
    code: Optional[str] = Field(default=None, description="Machine-readable error code")
