from pydantic import BaseModel, ConfigDict


class EnergyOptimizationResponse(BaseModel):
    station_id: int
    current_energy_status: str  # OPTIMAL, MODERATE, DEGRADED, CRITICAL
    risk_level: str  # NORMAL, LOW, WARNING, CRITICAL
    recommended_mode: str  # STANDARD_BALANCED, SOLAR_PRIORITY, FUEL_CONSERVATION, POWER_CRISIS_MINIMAL
    actions: list[str]
    reason: str
    diesel_reserve_pct: float | None = None
    battery_reserve_pct: float | None = None
    solar_output_kw: float | None = None
    estimated_diesel_days: float | None = None

    model_config = ConfigDict(from_attributes=True)
